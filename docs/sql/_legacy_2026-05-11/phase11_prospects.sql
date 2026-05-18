-- ============================================================
-- DragonEyes v2.1 Phase 11: 영업권/Prospect 관리 워크플로우
-- ============================================================
-- 작성일: 2026-05-11
-- 작성자: 좋아요님 (최승현)
-- 상태: 설계서 (적용 시점 별도 결정)
--
-- 사전 조건:
--   - Phase 6~9 적용 완료
--
-- 비즈니스 핵심:
--   1. 승인 기반 영업권 모델 (License-to-Sell)
--      - 등록만으로는 영업권 없음, 본부 승인 후 부여
--      - 미승인 영업도 가능하지만 라이선스 우선권 없음
--   2. 정찰제 → 출혈경쟁 불필요, 본부가 영업권 통제
--   3. 자동 소멸 정책:
--      - 6개월 동안 업데이트 없으면 expired_inactive
--      - 1년 동안 계약 못 하면 expired_timeout
--   4. 재배정: Director 또는 임원 승인으로 다른 대리점에 부여
--   5. 중복 영업: 선등록 우선, 이의 시 본부 중재
--   6. 진행 단계: 도입의사, 예산의중, 계약진행중 등
--   7. 예상 계약 시기: 년/월 단위
--
-- 권한:
--   - 파트너는 본인 prospect만 조회/수정
--   - 본부는 전체 조회 + 승인/반려/재배정 권한
--   - Director/임원만 재배정 승인 가능
-- ============================================================

BEGIN;

-- ============================================
-- 1. customer_prospects 테이블 (영업 중인 잠재 고객)
-- ============================================

CREATE TABLE IF NOT EXISTS customer_prospects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_number TEXT UNIQUE,  -- "CP-2026-0001"
    
    -- 고객사 정보
    prospect_name TEXT NOT NULL,
    business_number TEXT,  -- 있으면 중복 감지에 활용
    representative_name TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    industry TEXT,
    employee_count INT,
    disabled_employee_count INT,  -- 장애인 고용 인원 (DragonEyes 타겟)
    estimated_seats INT,
    estimated_revenue NUMERIC(15,2),
    
    -- 영업권 보유자
    claimed_by_partner_id UUID NOT NULL REFERENCES partners(id),
    claimed_by_user_id UUID NOT NULL REFERENCES users(id),
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- ⭐ 영업권 상태
    approval_status TEXT NOT NULL DEFAULT 'pending_approval' CHECK (approval_status IN (
        'pending_approval',  -- 본부 승인 대기
        'approved',          -- 영업권 부여 (우선권 있음)
        'denied',            -- 본부 반려 (영업은 가능, 우선권 없음)
        'under_dispute',     -- 이의제기 중 (본부 중재)
        'expired_inactive',  -- 6개월 무업데이트로 만료
        'expired_timeout',   -- 1년 무수주로 만료
        'won',               -- 수주 완료
        'lost'               -- 실주
    )),
    
    -- 본부 승인 처리
    approved_by_user_id UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    approval_notes TEXT,
    denial_reason TEXT,
    
    -- 영업 진행 단계
    sales_stage TEXT DEFAULT 'initial_contact' CHECK (sales_stage IN (
        'initial_contact',   -- 초기 접촉
        'interest_shown',    -- 도입 의사 있음
        'budget_review',     -- 예산 의중
        'proposal_sent',     -- 제안서 발송
        'demo_completed',    -- 시연 완료
        'negotiation',       -- 협상 중
        'contract_pending'   -- 계약 진행 중
    )),
    
    -- 예상 계약 시기 (년/월 셀렉션)
    expected_contract_year INT,
    expected_contract_month INT CHECK (expected_contract_month BETWEEN 1 AND 12),
    
    -- 영업 메모
    notes TEXT,
    
    -- ⭐ 자동 만료 추적
    last_activity_at TIMESTAMPTZ DEFAULT now(),  -- 마지막 활동 시점
    -- 6개월 무업데이트 = last_activity_at + 6 months < now()
    -- 1년 무수주 = claimed_at + 1 year < now() AND approval_status != 'won'
    
    -- 중복/이의 처리
    coordination_notes TEXT,
    coordinated_by_user_id UUID REFERENCES users(id),
    coordinated_at TIMESTAMPTZ,
    
    -- 재배정 추적
    reassigned_from_user_id UUID REFERENCES users(id),  -- 이전 영업권자
    reassigned_from_partner_id UUID REFERENCES partners(id),
    reassigned_at TIMESTAMPTZ,
    reassigned_reason TEXT,
    
    -- 수주/실주 연결
    won_license_order_id UUID REFERENCES license_orders(id),
    won_at TIMESTAMPTZ,
    lost_at TIMESTAMPTZ,
    lost_reason TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE customer_prospects IS 
    '영업 중인 잠재 고객. 본부 승인 후 영업권 부여. 6개월 무업데이트 또는 1년 무수주 시 자동 만료.';

CREATE INDEX idx_prospects_partner ON customer_prospects(claimed_by_partner_id);
CREATE INDEX idx_prospects_approval ON customer_prospects(approval_status);
CREATE INDEX idx_prospects_sales_stage ON customer_prospects(sales_stage);
CREATE INDEX idx_prospects_business_number 
    ON customer_prospects(business_number) WHERE business_number IS NOT NULL;
CREATE INDEX idx_prospects_pending_approval 
    ON customer_prospects(created_at DESC) WHERE approval_status = 'pending_approval';
CREATE INDEX idx_prospects_active 
    ON customer_prospects(last_activity_at) 
    WHERE approval_status IN ('approved', 'pending_approval');
CREATE INDEX idx_prospects_expected_contract 
    ON customer_prospects(expected_contract_year, expected_contract_month) 
    WHERE approval_status = 'approved';

CREATE TRIGGER trg_prospects_updated_at
    BEFORE UPDATE ON customer_prospects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 2. prospect 활동 로그
-- ============================================

CREATE TABLE IF NOT EXISTS customer_prospect_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES customer_prospects(id) ON DELETE CASCADE,
    
    activity_type TEXT NOT NULL CHECK (activity_type IN (
        'meeting',       -- 미팅
        'phone_call',    -- 전화
        'email',         -- 이메일
        'proposal',      -- 제안서 발송
        'demo',          -- 시연
        'follow_up',     -- 후속 조치
        'site_visit',    -- 방문
        'other'          -- 기타
    )),
    activity_date DATE NOT NULL,
    duration_minutes INT,
    
    summary TEXT NOT NULL,
    next_action TEXT,
    next_action_date DATE,
    
    attachment_paths TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    recorded_by_user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_activities_prospect ON customer_prospect_activities(prospect_id, activity_date DESC);

-- ⭐ 활동 기록 시 prospect의 last_activity_at 자동 갱신
CREATE OR REPLACE FUNCTION update_prospect_last_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE customer_prospects 
    SET last_activity_at = now(),
        updated_at = now()
    WHERE id = NEW.prospect_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prospect_activity_updates_last_activity
    AFTER INSERT ON customer_prospect_activities
    FOR EACH ROW EXECUTE FUNCTION update_prospect_last_activity();

-- ============================================
-- 3. prospect 이력 (감사 로그)
-- ============================================

CREATE TABLE IF NOT EXISTS customer_prospect_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES customer_prospects(id) ON DELETE CASCADE,
    
    action TEXT NOT NULL CHECK (action IN (
        'create',         -- 등록
        'approve',        -- 본부 승인
        'deny',           -- 본부 반려
        'stage_change',   -- 단계 변경
        'dispute_raised', -- 이의제기
        'coordinate',     -- 본부 조정
        'reassign',       -- 재배정
        'expire',         -- 자동 만료
        'win',            -- 수주
        'lose'            -- 실주
    )),
    
    actor_user_id UUID REFERENCES users(id),
    actor_role TEXT,
    
    from_status TEXT,
    to_status TEXT,
    from_stage TEXT,
    to_stage TEXT,
    
    notes TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_prospect_history_prospect ON customer_prospect_history(prospect_id, created_at);

-- ============================================
-- 4. 이의제기 테이블 (중복 영업 분쟁)
-- ============================================

CREATE TABLE IF NOT EXISTS prospect_disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES customer_prospects(id),
    
    -- 이의 제기자
    disputed_by_partner_id UUID NOT NULL REFERENCES partners(id),
    disputed_by_user_id UUID NOT NULL REFERENCES users(id),
    
    -- 이의 사유
    dispute_reason TEXT NOT NULL,
    evidence_paths TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    -- 처리 상태
    resolution_status TEXT NOT NULL DEFAULT 'pending' CHECK (resolution_status IN (
        'pending',          -- 처리 대기
        'under_mediation',  -- 본부 중재 중
        'resolved_keep',    -- 원 영업권자 유지
        'resolved_transfer',-- 이의 제기자에게 이전
        'resolved_split',   -- 본부가 다른 해결책 제시 (예: 공동 영업)
        'withdrawn'         -- 이의 철회
    )),
    
    -- 본부 처리
    resolved_by_user_id UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_disputes_prospect ON prospect_disputes(prospect_id);
CREATE INDEX idx_disputes_pending 
    ON prospect_disputes(created_at DESC) WHERE resolution_status = 'pending';

CREATE TRIGGER trg_disputes_updated_at
    BEFORE UPDATE ON prospect_disputes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 5. 자동 번호 생성
-- ============================================

CREATE OR REPLACE FUNCTION generate_prospect_number()
RETURNS TRIGGER AS $$
DECLARE
    v_year INT;
    v_seq INT;
BEGIN
    IF NEW.prospect_number IS NULL THEN
        v_year := EXTRACT(YEAR FROM now());
        SELECT COALESCE(MAX(
            CAST(SUBSTRING(prospect_number FROM 'CP-' || v_year || '-(\d+)') AS INT)
        ), 0) + 1
        INTO v_seq
        FROM customer_prospects
        WHERE prospect_number LIKE 'CP-' || v_year || '-%';
        
        NEW.prospect_number := 'CP-' || v_year || '-' || LPAD(v_seq::TEXT, 4, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prospect_number
    BEFORE INSERT ON customer_prospects
    FOR EACH ROW EXECUTE FUNCTION generate_prospect_number();

-- ============================================
-- 6. 중복 영업 자동 감지 트리거
-- ============================================
-- 같은 business_number로 활성 prospect가 이미 있으면 본부 알림

CREATE OR REPLACE FUNCTION detect_duplicate_prospect()
RETURNS TRIGGER AS $$
DECLARE
    v_existing_count INT;
BEGIN
    -- business_number가 있고, 같은 번호로 이미 활성 prospect 존재 시
    IF NEW.business_number IS NOT NULL THEN
        SELECT COUNT(*) INTO v_existing_count
        FROM customer_prospects
        WHERE business_number = NEW.business_number
          AND id != NEW.id
          AND approval_status IN ('pending_approval', 'approved')
          AND claimed_by_partner_id != NEW.claimed_by_partner_id;
        
        IF v_existing_count > 0 THEN
            -- 본부 알림용 컬럼에 표시 (별도 알림 테이블이 있다면 INSERT)
            -- 여기서는 coordination_notes에 자동 메모
            NEW.coordination_notes := COALESCE(NEW.coordination_notes, '') || 
                '⚠️ 중복 영업 감지: 사업자번호 ' || NEW.business_number || 
                '로 다른 대리점이 이미 등록함 (' || v_existing_count || '건). 본부 검토 필요.';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_detect_duplicate_prospect
    BEFORE INSERT ON customer_prospects
    FOR EACH ROW EXECUTE FUNCTION detect_duplicate_prospect();

-- ============================================
-- 7. 자동 만료 처리 함수 (Cron으로 매일 호출)
-- ============================================

CREATE OR REPLACE FUNCTION expire_inactive_prospects()
RETURNS TABLE(expired_id UUID, expire_type TEXT) AS $$
BEGIN
    -- 6개월 무업데이트 만료
    RETURN QUERY
    UPDATE customer_prospects
    SET approval_status = 'expired_inactive',
        updated_at = now()
    WHERE approval_status = 'approved'
      AND last_activity_at < now() - INTERVAL '6 months'
    RETURNING id, 'expired_inactive'::TEXT;
    
    -- 1년 무수주 만료
    RETURN QUERY
    UPDATE customer_prospects
    SET approval_status = 'expired_timeout',
        updated_at = now()
    WHERE approval_status = 'approved'
      AND claimed_at < now() - INTERVAL '1 year'
    RETURNING id, 'expired_timeout'::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION expire_inactive_prospects() IS 
    'Railway Cron 또는 pg_cron에서 매일 자정 호출 권장. 만료된 prospect를 expired_inactive/timeout으로 전환.';

-- ============================================
-- 8. license_order 발급 시 prospect 자동 won 연결
-- ============================================
-- 같은 business_number의 활성 prospect를 자동으로 'won' 처리
-- (트리거를 license_orders 테이블에 추가)

CREATE OR REPLACE FUNCTION link_license_order_to_prospect()
RETURNS TRIGGER AS $$
DECLARE
    v_prospect_id UUID;
BEGIN
    -- issued 상태로 전환 시점에만 동작
    IF NEW.status = 'issued' AND (OLD.status IS NULL OR OLD.status != 'issued') THEN
        -- 같은 business_number + 같은 파트너의 활성 prospect 찾기
        SELECT id INTO v_prospect_id
        FROM customer_prospects
        WHERE business_number = NEW.customer_business_number
          AND claimed_by_partner_id = NEW.requested_by_partner_id
          AND approval_status IN ('approved', 'pending_approval')
        ORDER BY 
            CASE approval_status WHEN 'approved' THEN 1 ELSE 2 END,  -- approved 우선
            claimed_at DESC
        LIMIT 1;
        
        IF v_prospect_id IS NOT NULL THEN
            UPDATE customer_prospects
            SET approval_status = 'won',
                won_license_order_id = NEW.id,
                won_at = now(),
                sales_stage = 'contract_pending',
                updated_at = now()
            WHERE id = v_prospect_id;
            
            -- 이력 기록
            INSERT INTO customer_prospect_history (
                prospect_id, action, actor_user_id, 
                from_status, to_status, notes
            ) VALUES (
                v_prospect_id, 'win', NEW.director_approved_by_user_id,
                'approved', 'won', 
                'license_order 자동 연결: ' || NEW.order_number
            );
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_link_license_order_to_prospect
    AFTER UPDATE ON license_orders
    FOR EACH ROW EXECUTE FUNCTION link_license_order_to_prospect();

-- ============================================
-- 9. 권한 헬퍼 함수
-- ============================================

-- 영업권 승인 권한 = 본부 직원
CREATE OR REPLACE FUNCTION can_approve_prospect(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN user_is_hq_staff(p_user_id);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- 영업권 재배정 권한 = Director 또는 임원 (현재는 hq_admin)
CREATE OR REPLACE FUNCTION can_reassign_prospect(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN user_is_hq_admin(p_user_id);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ============================================
-- 10. RLS 정책
-- ============================================

ALTER TABLE customer_prospects ENABLE ROW LEVEL SECURITY;

-- SELECT: HQ 전체 + 본인 파트너 prospect만
DROP POLICY IF EXISTS prospects_select ON customer_prospects;
CREATE POLICY prospects_select ON customer_prospects FOR SELECT
USING (
    user_is_hq_staff(auth.uid())
    OR claimed_by_partner_id = user_partner_id(auth.uid())
);

-- INSERT: 파트너는 본인 명의로만, HQ는 자유
DROP POLICY IF EXISTS prospects_insert ON customer_prospects;
CREATE POLICY prospects_insert ON customer_prospects FOR INSERT
WITH CHECK (
    user_is_hq_staff(auth.uid())
    OR (
        claimed_by_user_id = auth.uid()
        AND claimed_by_partner_id = user_partner_id(auth.uid())
    )
);

-- UPDATE: HQ는 모든 필드, 파트너는 본인 prospect의 영업 정보만
-- (approval_status, reassignment 관련 필드는 RLS로는 제어 못 함 → 앱 레벨에서)
DROP POLICY IF EXISTS prospects_update ON customer_prospects;
CREATE POLICY prospects_update ON customer_prospects FOR UPDATE
USING (
    user_is_hq_staff(auth.uid())
    OR claimed_by_partner_id = user_partner_id(auth.uid())
);

DROP POLICY IF EXISTS prospects_delete ON customer_prospects;
CREATE POLICY prospects_delete ON customer_prospects FOR DELETE
USING (user_is_hq_admin(auth.uid()));

-- 활동 로그
ALTER TABLE customer_prospect_activities ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS activities_select ON customer_prospect_activities;
CREATE POLICY activities_select ON customer_prospect_activities FOR SELECT
USING (
    user_is_hq_staff(auth.uid())
    OR EXISTS (
        SELECT 1 FROM customer_prospects p
        WHERE p.id = prospect_id
          AND p.claimed_by_partner_id = user_partner_id(auth.uid())
    )
);

DROP POLICY IF EXISTS activities_insert ON customer_prospect_activities;
CREATE POLICY activities_insert ON customer_prospect_activities FOR INSERT
WITH CHECK (
    user_is_hq_staff(auth.uid())
    OR EXISTS (
        SELECT 1 FROM customer_prospects p
        WHERE p.id = prospect_id
          AND p.claimed_by_partner_id = user_partner_id(auth.uid())
    )
);

-- 이력
ALTER TABLE customer_prospect_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS history_select ON customer_prospect_history;
CREATE POLICY history_select ON customer_prospect_history FOR SELECT
USING (
    user_is_hq_staff(auth.uid())
    OR EXISTS (
        SELECT 1 FROM customer_prospects p
        WHERE p.id = prospect_id
          AND p.claimed_by_partner_id = user_partner_id(auth.uid())
    )
);

-- 이의제기
ALTER TABLE prospect_disputes ENABLE ROW LEVEL SECURITY;

-- 이의제기는 HQ가 보고, 이의제기자도 본인 건만 봄
DROP POLICY IF EXISTS disputes_select ON prospect_disputes;
CREATE POLICY disputes_select ON prospect_disputes FOR SELECT
USING (
    user_is_hq_staff(auth.uid())
    OR disputed_by_partner_id = user_partner_id(auth.uid())
    OR EXISTS (
        SELECT 1 FROM customer_prospects p
        WHERE p.id = prospect_id
          AND p.claimed_by_partner_id = user_partner_id(auth.uid())
    )
);

-- 이의제기 INSERT: 파트너는 본인 이름으로
DROP POLICY IF EXISTS disputes_insert ON prospect_disputes;
CREATE POLICY disputes_insert ON prospect_disputes FOR INSERT
WITH CHECK (
    user_is_hq_staff(auth.uid())
    OR (
        disputed_by_user_id = auth.uid()
        AND disputed_by_partner_id = user_partner_id(auth.uid())
    )
);

-- 이의제기 처리는 HQ만
DROP POLICY IF EXISTS disputes_update ON prospect_disputes;
CREATE POLICY disputes_update ON prospect_disputes FOR UPDATE
USING (user_is_hq_staff(auth.uid()));

-- ============================================
-- 11. 통합 조회 VIEW
-- ============================================

-- 본부 대시보드용: 모든 prospect + 영업 활동 요약
CREATE OR REPLACE VIEW prospects_dashboard AS
SELECT 
    p.id,
    p.prospect_number,
    p.prospect_name,
    p.business_number,
    p.approval_status,
    p.sales_stage,
    p.expected_contract_year,
    p.expected_contract_month,
    p.estimated_seats,
    p.estimated_revenue,
    
    -- 파트너 정보
    p.claimed_by_partner_id,
    pt.name AS partner_name,
    
    -- 시간 추적
    p.claimed_at,
    p.last_activity_at,
    p.claimed_at + INTERVAL '1 year' AS timeout_expires_at,
    p.last_activity_at + INTERVAL '6 months' AS inactive_expires_at,
    
    -- 활동 카운트
    (SELECT COUNT(*) FROM customer_prospect_activities WHERE prospect_id = p.id) AS activity_count,
    (SELECT MAX(activity_date) FROM customer_prospect_activities WHERE prospect_id = p.id) AS last_activity_date,
    
    -- 중복 여부
    (SELECT COUNT(*) > 0 FROM customer_prospects p2 
     WHERE p2.business_number = p.business_number 
       AND p2.id != p.id 
       AND p2.business_number IS NOT NULL
       AND p2.approval_status IN ('pending_approval', 'approved')
    ) AS has_duplicate,
    
    -- 이의제기 여부
    (SELECT COUNT(*) > 0 FROM prospect_disputes WHERE prospect_id = p.id AND resolution_status IN ('pending', 'under_mediation')) AS has_active_dispute,
    
    p.created_at,
    p.updated_at
FROM customer_prospects p
LEFT JOIN partners pt ON pt.id = p.claimed_by_partner_id;

COMMENT ON VIEW prospects_dashboard IS 
    '본부 영업현황 대시보드용. 만료 임박, 중복, 이의제기 등을 한눈에 확인.';

-- 파트너 본인용 대시보드
CREATE OR REPLACE VIEW my_prospects_dashboard AS
SELECT 
    p.id,
    p.prospect_number,
    p.prospect_name,
    p.business_number,
    p.approval_status,
    p.sales_stage,
    p.expected_contract_year,
    p.expected_contract_month,
    p.estimated_seats,
    p.claimed_at,
    p.last_activity_at,
    -- 남은 일수
    EXTRACT(DAY FROM (p.claimed_at + INTERVAL '1 year') - now()) AS days_until_timeout,
    EXTRACT(DAY FROM (p.last_activity_at + INTERVAL '6 months') - now()) AS days_until_inactive,
    -- 최근 활동
    (SELECT activity_date FROM customer_prospect_activities WHERE prospect_id = p.id ORDER BY activity_date DESC LIMIT 1) AS last_activity_date,
    (SELECT activity_type FROM customer_prospect_activities WHERE prospect_id = p.id ORDER BY activity_date DESC LIMIT 1) AS last_activity_type,
    p.notes
FROM customer_prospects p;

-- ============================================
-- 12. 검증
-- ============================================

SELECT 
    table_name, 
    EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name=t) AS exists
FROM (VALUES 
    ('customer_prospects'),
    ('customer_prospect_activities'),
    ('customer_prospect_history'),
    ('prospect_disputes')
) AS x(t)
CROSS JOIN LATERAL (SELECT t AS table_name) y;

COMMIT;

-- ============================================================
-- 📋 앱 코드 통합 가이드
-- ============================================================
--
-- [대리점 영업 등록]
--   INSERT INTO customer_prospects (
--       prospect_name, business_number, claimed_by_user_id,
--       claimed_by_partner_id, sales_stage, 
--       expected_contract_year, expected_contract_month
--   ) VALUES (..., 'initial_contact', 2026, 9);
--   → 자동: prospect_number 생성, 중복 감지 메모
--   → status='pending_approval' (본부 승인 대기)
--
-- [본부 영업권 승인]
--   UPDATE customer_prospects SET
--       approval_status = 'approved',
--       approved_by_user_id = me, approved_at = now()
--   WHERE id = ?;
--
-- [본부 영업권 반려]
--   UPDATE ... SET approval_status='denied', denial_reason=...
--
-- [대리점 활동 기록 (가장 자주 발생)]
--   INSERT INTO customer_prospect_activities (
--       prospect_id, activity_type, activity_date, 
--       summary, next_action, recorded_by_user_id
--   );
--   → 트리거가 prospect.last_activity_at 자동 갱신
--   → 6개월 카운트 리셋
--
-- [영업 단계 변경]
--   UPDATE customer_prospects SET sales_stage='budget_review'
--   → 이력 기록
--
-- [다른 대리점 이의제기]
--   INSERT INTO prospect_disputes (
--       prospect_id, disputed_by_user_id, disputed_by_partner_id,
--       dispute_reason
--   );
--   → 본부 알림 발송
--
-- [본부 중재 결정]
--   UPDATE prospect_disputes SET 
--       resolution_status='resolved_transfer',  -- 또는 keep
--       resolved_by_user_id=me, resolution_notes=...
--   → 'resolved_transfer'인 경우 prospect의 claimed_by_partner_id 변경 + 재배정 이력
--
-- [라이선스 발급 시 자동 win]
--   license_orders.status='issued' → 트리거가 prospect.approval_status='won'
--
-- [매일 자정 (Cron)]
--   SELECT expire_inactive_prospects();
--   → 6개월 무업데이트 또는 1년 무수주 자동 만료
--
-- [Director/임원 재배정]
--   UPDATE customer_prospects SET
--       claimed_by_partner_id = new_partner,
--       claimed_by_user_id = new_user,
--       approval_status = 'approved',
--       reassigned_from_partner_id = old_partner,
--       reassigned_at = now(),
--       reassigned_reason = ...
--   WHERE id = ?;
--   → 만료된 prospect를 다른 대리점에 부여
--
-- ============================================================

-- ============================================
-- 롤백 SQL
-- ============================================
-- BEGIN;
-- DROP VIEW IF EXISTS my_prospects_dashboard;
-- DROP VIEW IF EXISTS prospects_dashboard;
-- DROP FUNCTION IF EXISTS can_reassign_prospect(UUID);
-- DROP FUNCTION IF EXISTS can_approve_prospect(UUID);
-- DROP FUNCTION IF EXISTS link_license_order_to_prospect();
-- DROP FUNCTION IF EXISTS expire_inactive_prospects();
-- DROP FUNCTION IF EXISTS detect_duplicate_prospect();
-- DROP FUNCTION IF EXISTS update_prospect_last_activity();
-- DROP FUNCTION IF EXISTS generate_prospect_number();
-- DROP TABLE IF EXISTS prospect_disputes CASCADE;
-- DROP TABLE IF EXISTS customer_prospect_history CASCADE;
-- DROP TABLE IF EXISTS customer_prospect_activities CASCADE;
-- DROP TABLE IF EXISTS customer_prospects CASCADE;
-- COMMIT;
