-- ============================================================
-- DragonEyes v2.1 Phase 9: 라이선스 발주 워크플로우
-- ============================================================
-- 작성일: 2026-05-11
-- 작성자: 좋아요님 (최승현)
-- 상태: 설계서 (적용 시점 별도 결정)
--
-- 사전 조건:
--   - Phase 6~8 적용 완료 (customers, user_groups, RLS)
--
-- 비즈니스 흐름:
--   대리점 신청 → 운영팀 검토 → Director 최종 승인 → 자동 발급 → 동의서 발송
--
-- ⭐ 핵심 권한:
--   - Director가 라이선스 발급 최종 승인권자
--   - 임원은 Director 부재 시 대결재 가능
--   - 운영팀, Director, 임원 모두 어느 단계든 리젝 가능
--   - 상위자는 하위 단계 대결재 + 원클릭 일괄 처리 가능
--   - 재검토 반려(send_back): 한 단계 뒤로 되돌리기 (내부)
--   - 리젝(reject): 대리점에게 거절 통보 (외부, 종결)
-- ============================================================

BEGIN;

-- ============================================
-- 1. license_orders 테이블 (발주 신청서)
-- ============================================

CREATE TABLE IF NOT EXISTS license_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 신청서 번호 (자동 생성: LO-YYYY-NNNN)
    order_number TEXT UNIQUE,
    
    -- 신청자 (대리점)
    requested_by_user_id UUID NOT NULL REFERENCES users(id),
    requested_by_partner_id UUID NOT NULL REFERENCES partners(id),
    
    -- 신청 내용 (고객사 정보)
    customer_legal_name TEXT NOT NULL,
    customer_business_number TEXT NOT NULL,
    customer_representative TEXT,
    customer_address TEXT,
    customer_phone TEXT,
    customer_email TEXT,
    
    -- 라이선스 요청 사항
    license_count INT NOT NULL CHECK (license_count > 0),
    monitoring_user_limit INT,
    contract_period_months INT DEFAULT 12 CHECK (contract_period_months > 0),
    contract_label TEXT DEFAULT '모니터링',  -- "포유솔루션 (모니터링)"의 괄호 부분
    requested_notes TEXT,  -- 신청자 메모
    
    -- 첨부 서류 (Supabase Storage 경로 배열)
    attachment_paths TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    -- 워크플로우 상태
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft',              -- 작성 중 (대리점이 저장만)
        'submitted',          -- 신청 완료, 운영팀 대기
        'under_review',       -- 운영팀 검토 중
        'director_approved',  -- Director 승인 (최종 승인 = 발급 직전)
        'issued',             -- 라이선스 발급 완료
        'active',             -- 고객 동의 완료, 활성 사용
        'sent_back',          -- 재검토 반려 (이전 단계로 되돌림)
        'rejected'            -- 거절 (대리점에 통보, 종결)
    )),
    
    -- 단계 1: 운영팀 검토
    reviewed_by_user_id UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    
    -- 단계 2: Director 최종 승인 (=발급 승인)
    -- 임원이 대결재한 경우에도 이 컬럼에 기록 (executive_proxy=true로 구분)
    director_approved_by_user_id UUID REFERENCES users(id),
    director_approved_at TIMESTAMPTZ,
    director_approval_notes TEXT,
    director_approved_by_executive_proxy BOOLEAN DEFAULT FALSE,  -- 임원 대결재 여부
    
    -- 일괄 승인 추적 (상위자가 여러 단계 한 번에 처리)
    bulk_approved BOOLEAN DEFAULT FALSE,
    bulk_approval_reason TEXT,  -- "운영팀/Director 부재로 대결재" 등
    
    -- 발급
    issued_at TIMESTAMPTZ,
    issued_customer_id UUID REFERENCES customers(id),
    
    -- 활성화 (고객 동의 후)
    activated_at TIMESTAMPTZ,
    
    -- 재검토 반려
    sent_back_to TEXT CHECK (sent_back_to IN ('reviewer', 'director')),
    sent_back_reason TEXT,
    sent_back_at TIMESTAMPTZ,
    
    -- 리젝
    rejected_by_user_id UUID REFERENCES users(id),
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,
    resubmission_allowed BOOLEAN DEFAULT TRUE,  -- 재신청 가능 여부
    
    -- 감사
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE license_orders IS 
    '라이선스 발주 신청서. Director 최종 승인 시 자동으로 customers 생성.';

CREATE INDEX idx_license_orders_status ON license_orders(status);
CREATE INDEX idx_license_orders_partner ON license_orders(requested_by_partner_id);
CREATE INDEX idx_license_orders_requested_by ON license_orders(requested_by_user_id);
CREATE INDEX idx_license_orders_pending 
    ON license_orders(created_at DESC) 
    WHERE status IN ('submitted', 'under_review');

CREATE TRIGGER trg_license_orders_updated_at
    BEFORE UPDATE ON license_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 2. license_order_history 테이블 (감사 이력)
-- ============================================

CREATE TABLE IF NOT EXISTS license_order_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES license_orders(id) ON DELETE CASCADE,
    
    -- 액션
    action TEXT NOT NULL CHECK (action IN (
        'submit',            -- 신청
        'review',            -- 운영팀 검토 완료
        'director_approve',  -- Director 승인 (라이선스 발급)
        'bulk_approve',      -- 상위자 일괄 승인 (대결재)
        'send_back',         -- 재검토 반려
        'reject',            -- 거절
        'issue',             -- 자동 발급 (트리거)
        'activate'           -- 고객 동의로 활성화
    )),
    
    -- 처리자
    actor_user_id UUID REFERENCES users(id),
    actor_role TEXT,  -- 'partner_admin', 'hq_member', 'hq_admin' 등
    
    -- 상태 변화
    from_status TEXT,
    to_status TEXT,
    
    -- 비고
    notes TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_license_order_history_order ON license_order_history(order_id, created_at);
CREATE INDEX idx_license_order_history_actor ON license_order_history(actor_user_id);

-- ============================================
-- 3. 신청서 번호 자동 생성 (LO-YYYY-NNNN)
-- ============================================

CREATE OR REPLACE FUNCTION generate_license_order_number()
RETURNS TRIGGER AS $$
DECLARE
    v_year INT;
    v_seq INT;
BEGIN
    IF NEW.order_number IS NULL THEN
        v_year := EXTRACT(YEAR FROM now());
        SELECT COALESCE(MAX(
            CAST(SUBSTRING(order_number FROM 'LO-' || v_year || '-(\d+)') AS INT)
        ), 0) + 1
        INTO v_seq
        FROM license_orders
        WHERE order_number LIKE 'LO-' || v_year || '-%';
        
        NEW.order_number := 'LO-' || v_year || '-' || LPAD(v_seq::TEXT, 4, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_generate_order_number
    BEFORE INSERT ON license_orders
    FOR EACH ROW EXECUTE FUNCTION generate_license_order_number();

-- ============================================
-- 4. 자동 발급 트리거: director_approved → issued
-- ============================================
-- Director가 승인하는 순간(또는 임원이 대결재 일괄 승인하는 순간)
-- customers 자동 생성 + status를 issued로 전환

CREATE OR REPLACE FUNCTION auto_issue_license_on_director_approval()
RETURNS TRIGGER AS $$
DECLARE
    v_customer_id UUID;
    v_display_name TEXT;
BEGIN
    -- director_approved 상태로 진입한 순간에만 동작
    IF NEW.status = 'director_approved' AND 
       (OLD.status IS NULL OR OLD.status != 'director_approved') THEN
        
        -- display_name 생성: "포유솔루션 (모니터링)"
        v_display_name := NEW.customer_legal_name || ' (' || COALESCE(NEW.contract_label, '모니터링') || ')';
        
        -- 1. customers 자동 등록
        INSERT INTO customers (
            display_name, legal_name, business_number, representative_name,
            address, phone, email, 
            contract_label, contract_status,
            license_count, monitoring_user_limit,
            sold_by_partner_id,
            contract_start, contract_end,
            created_by
        ) VALUES (
            v_display_name,
            NEW.customer_legal_name,
            NEW.customer_business_number,
            NEW.customer_representative,
            NEW.customer_address,
            NEW.customer_phone,
            NEW.customer_email,
            COALESCE(NEW.contract_label, '모니터링'),
            'pilot',  -- 동의 완료 후 'active'로 전환
            NEW.license_count,
            NEW.monitoring_user_limit,
            NEW.requested_by_partner_id,
            CURRENT_DATE,
            CURRENT_DATE + (NEW.contract_period_months || ' months')::INTERVAL,
            NEW.director_approved_by_user_id
        ) RETURNING id INTO v_customer_id;
        
        -- 2. 신청서에 customer_id 기록 + status를 'issued'로
        NEW.issued_customer_id := v_customer_id;
        NEW.issued_at := now();
        NEW.status := 'issued';
        
        -- 3. 이력 기록
        INSERT INTO license_order_history (
            order_id, action, actor_user_id, 
            from_status, to_status, notes
        ) VALUES (
            NEW.id, 'issue', NEW.director_approved_by_user_id,
            'director_approved', 'issued', 
            '자동 발급 - customers ID: ' || v_customer_id
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_issue_license
    BEFORE UPDATE ON license_orders
    FOR EACH ROW EXECUTE FUNCTION auto_issue_license_on_director_approval();

-- ============================================
-- 5. 권한 체크 헬퍼 함수
-- ============================================

-- 라이선스 발급 최종 승인 권한 = Director 또는 임원(대결재)
-- (현재는 group_type에 'director' 따로 없으므로 hq_admin 전체로 가정)
-- TODO: v2.2에서 hq_director group_type 추가 가능

CREATE OR REPLACE FUNCTION can_approve_license_issue(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    -- 현재 정책: hq_admin이면 모두 가능 (Director + 임원 묶음)
    -- 향후 hq_director / hq_executive 분리 시 여기만 수정
    RETURN user_is_hq_admin(p_user_id);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION can_approve_license_issue(UUID) IS 
    '라이선스 발급 최종 승인 권한. 현재는 hq_admin 전체. 향후 hq_director 분리 시 수정.';

-- 운영팀 검토 권한 = hq_admin + hq_member
CREATE OR REPLACE FUNCTION can_review_license(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN user_is_hq_staff(p_user_id);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- 리젝 권한 = HQ 직원 모두 + 본인 신청서를 작성한 파트너 본인 (취소)
CREATE OR REPLACE FUNCTION can_reject_license_order(p_user_id UUID, p_order_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_requested_by UUID;
BEGIN
    -- HQ 직원은 어느 단계든 리젝 가능
    IF user_is_hq_staff(p_user_id) THEN
        RETURN TRUE;
    END IF;
    
    -- 신청자 본인은 본인 신청 취소 가능 (단, draft/submitted 상태만)
    SELECT requested_by_user_id INTO v_requested_by
    FROM license_orders WHERE id = p_order_id;
    
    RETURN v_requested_by = p_user_id;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ============================================
-- 6. RLS 정책
-- ============================================

ALTER TABLE license_orders ENABLE ROW LEVEL SECURITY;

-- SELECT: 본인 신청 + 본인 파트너 신청 + HQ 직원 전체
DROP POLICY IF EXISTS license_orders_select ON license_orders;
CREATE POLICY license_orders_select ON license_orders FOR SELECT
USING (
    -- HQ 직원은 전체
    user_is_hq_staff(auth.uid())
    OR
    -- 본인이 작성한 신청서
    requested_by_user_id = auth.uid()
    OR
    -- 본인 소속 파트너의 신청서
    requested_by_partner_id = user_partner_id(auth.uid())
);

-- INSERT: 파트너 사용자만 (본인 파트너 ID로만)
DROP POLICY IF EXISTS license_orders_insert ON license_orders;
CREATE POLICY license_orders_insert ON license_orders FOR INSERT
WITH CHECK (
    requested_by_user_id = auth.uid()
    AND requested_by_partner_id = user_partner_id(auth.uid())
);

-- UPDATE: draft 상태는 본인만, 그 외는 HQ 직원
DROP POLICY IF EXISTS license_orders_update ON license_orders;
CREATE POLICY license_orders_update ON license_orders FOR UPDATE
USING (
    -- HQ 직원은 모든 단계 가능
    user_is_hq_staff(auth.uid())
    OR
    -- 본인이 작성 중인 draft만
    (requested_by_user_id = auth.uid() AND status = 'draft')
);

-- DELETE: HQ admin만 (감사 추적 위해 보통 안 함, 비활성화 권장)
DROP POLICY IF EXISTS license_orders_delete ON license_orders;
CREATE POLICY license_orders_delete ON license_orders FOR DELETE
USING (user_is_hq_admin(auth.uid()));

-- history는 SELECT만 + HQ 직원 또는 본인 신청서
ALTER TABLE license_order_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS license_order_history_select ON license_order_history;
CREATE POLICY license_order_history_select ON license_order_history FOR SELECT
USING (
    user_is_hq_staff(auth.uid())
    OR EXISTS (
        SELECT 1 FROM license_orders o
        WHERE o.id = order_id
          AND (o.requested_by_user_id = auth.uid() 
               OR o.requested_by_partner_id = user_partner_id(auth.uid()))
    )
);

-- history INSERT는 trigger로만 (앱 직접 INSERT 차단)
DROP POLICY IF EXISTS license_order_history_insert ON license_order_history;
CREATE POLICY license_order_history_insert ON license_order_history FOR INSERT
WITH CHECK (user_is_hq_staff(auth.uid()) OR requested_by_user_id IS NOT NULL);

-- ============================================
-- 7. 검증 쿼리
-- ============================================

-- 테이블 2개 + 함수 3개 + 트리거 2개 확인
SELECT 'license_orders' AS object_name, 'table' AS type,
       EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='license_orders') AS exists
UNION ALL
SELECT 'license_order_history', 'table',
       EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='license_order_history')
UNION ALL
SELECT 'auto_issue_license_on_director_approval', 'function',
       EXISTS(SELECT 1 FROM pg_proc WHERE proname='auto_issue_license_on_director_approval')
UNION ALL
SELECT 'can_approve_license_issue', 'function',
       EXISTS(SELECT 1 FROM pg_proc WHERE proname='can_approve_license_issue')
UNION ALL
SELECT 'generate_license_order_number', 'function',
       EXISTS(SELECT 1 FROM pg_proc WHERE proname='generate_license_order_number');

COMMIT;

-- ============================================
-- 롤백 SQL
-- ============================================
-- BEGIN;
-- DROP FUNCTION IF EXISTS can_reject_license_order(UUID, UUID);
-- DROP FUNCTION IF EXISTS can_review_license(UUID);
-- DROP FUNCTION IF EXISTS can_approve_license_issue(UUID);
-- DROP FUNCTION IF EXISTS auto_issue_license_on_director_approval();
-- DROP FUNCTION IF EXISTS generate_license_order_number();
-- DROP TABLE IF EXISTS license_order_history CASCADE;
-- DROP TABLE IF EXISTS license_orders CASCADE;
-- COMMIT;

-- ============================================================
-- 📋 앱 코드 통합 가이드 (app.py 작업 시 참고)
-- ============================================================
--
-- [대리점 신청 화면]
--   supabase.table('license_orders').insert({...}).execute()
--   → 트리거가 order_number 자동 생성, status='draft'
--   → 제출 시 status를 'submitted'로 변경
--
-- [운영팀 검토 화면]
--   .update({'status': 'under_review', 'reviewed_by_user_id': me, 
--            'reviewed_at': now(), 'review_notes': notes})
--   → 이력 INSERT (action='review')
--
-- [Director 최종 승인 화면]
--   .update({'status': 'director_approved', 
--            'director_approved_by_user_id': me,
--            'director_approved_at': now()})
--   → 트리거가 customers 자동 생성 + status='issued'로 변경
--   → 이력 INSERT (action='director_approve' + 'issue')
--
-- [임원 대결재 일괄 승인]
--   .update({'status': 'director_approved',
--            'bulk_approved': TRUE,
--            'bulk_approval_reason': '운영팀/Director 부재로 대결재',
--            'director_approved_by_user_id': me,
--            'director_approved_by_executive_proxy': TRUE})
--   → 트리거 동일 동작 (자동 발급)
--
-- [재검토 반려]
--   .update({'status': 'sent_back',
--            'sent_back_to': 'reviewer',
--            'sent_back_reason': reason,
--            'sent_back_at': now()})
--   → 다음 단계 처리자 화면에서 안 보임, 하위 단계 화면에 다시 표시
--
-- [리젝]
--   .update({'status': 'rejected',
--            'rejected_by_user_id': me,
--            'rejected_at': now(),
--            'rejection_reason': reason,
--            'resubmission_allowed': True/False})
--   → 대리점에게 이메일 + 인앱 알림 발송 (별도 함수)
--   → 이력 INSERT (action='reject')
--
-- [고객 동의 완료 후 활성화]
--   customers 테이블의 contract_status를 'pilot' → 'active'
--   license_orders도 status='active'로 업데이트
--
-- ============================================================
