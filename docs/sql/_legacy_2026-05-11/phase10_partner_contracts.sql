-- ============================================================
-- DragonEyes v2.1 Phase 10: 파트너 계약 워크플로우
-- ============================================================
-- 작성일: 2026-05-11
-- 작성자: 좋아요님 (최승현)
-- 상태: 설계서 (적용 시점 별도 결정)
--
-- 사전 조건:
--   - Phase 6~8 적용 완료
--   - Phase 9 적용 시 권장 (license_order_history 패턴 재사용)
--
-- ⭐ 핵심 권한:
--   - 모든 파트너 계약 최종 승인 = 임원(사장) 전권
--   - Director는 검토 가능하지만 최종 승인 권한 없음
--   - 단, 운영팀 검토 단계는 대결재 가능 (위로 올라갈 수만 있음)
--
-- 비즈니스 흐름 (3종 동일):
--   계약 요청 → 운영팀 검토 → 임원 최종 승인 → 계약 체결
--
-- 테이블 분리:
--   - partner_distributor_contracts (대리점 계약)
--   - partner_reseller_contracts    (총판 계약)
--   - partner_related_org_contracts (유관기관 계약)
--
-- 분리 이유:
--   - 계약 종류마다 별도 컬럼 필요 (수수료율 vs 매출배분 vs 협력비율)
--   - 계약서 양식·법적 효력 다름
--   - 결재 흐름은 같지만 보고서·통계는 종류별 집계
-- ============================================================

BEGIN;

-- ============================================
-- 1. 공통 ENUM 타입 (3개 테이블 공유)
-- ============================================

DO $$ BEGIN
    CREATE TYPE partner_contract_status AS ENUM (
        'draft',                -- 작성 중
        'submitted',            -- 제출, 운영팀 대기
        'under_review',         -- 운영팀 검토 중
        'executive_approved',   -- 임원 최종 승인 = 계약 체결 직전
        'contracted',           -- 계약 체결 완료 (전자서명 완료)
        'sent_back',            -- 재검토 반려
        'rejected',             -- 거절
        'terminated'            -- 계약 해지
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============================================
-- 2. 대리점 계약 테이블 (partner_distributor_contracts)
-- ============================================

CREATE TABLE IF NOT EXISTS partner_distributor_contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_number TEXT UNIQUE,  -- "PDC-2026-0001"
    
    -- 계약 상대방
    partner_id UUID REFERENCES partners(id),  -- 이미 partners에 등록된 경우
    new_partner_name TEXT,                    -- 신규 등록 시 법인명
    new_partner_business_number TEXT,
    new_partner_representative TEXT,
    new_partner_address TEXT,
    new_partner_phone TEXT,
    new_partner_email TEXT,
    
    -- 대리점 계약 고유 조건
    commission_rate NUMERIC(5,2) NOT NULL,  -- 수수료율 (%)
    territory TEXT,                         -- 영업 권역
    exclusivity BOOLEAN DEFAULT FALSE,      -- 독점권 여부
    target_customer_count INT,              -- 목표 고객 수
    minimum_revenue NUMERIC(15,2),          -- 최소 매출 의무
    
    -- 계약 기간
    contract_start DATE,
    contract_end DATE,
    auto_renewal BOOLEAN DEFAULT FALSE,
    
    -- 첨부 서류
    attachment_paths TEXT[] DEFAULT ARRAY[]::TEXT[],
    contract_pdf_path TEXT,  -- 최종 계약서 PDF
    
    -- 워크플로우 상태
    status partner_contract_status NOT NULL DEFAULT 'draft',
    
    -- 신청자
    initiated_by_user_id UUID REFERENCES users(id),
    
    -- 운영팀 검토
    reviewed_by_user_id UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    
    -- 임원 최종 승인 (Director 단계 없음!)
    executive_approved_by_user_id UUID REFERENCES users(id),
    executive_approved_at TIMESTAMPTZ,
    executive_approval_notes TEXT,
    
    -- 일괄 승인 추적
    bulk_approved BOOLEAN DEFAULT FALSE,
    bulk_approval_reason TEXT,
    
    -- 계약 체결 완료
    contracted_at TIMESTAMPTZ,
    digital_signature_id TEXT,  -- KISA 전자서명 ID
    
    -- 재검토 반려
    sent_back_reason TEXT,
    sent_back_at TIMESTAMPTZ,
    
    -- 리젝
    rejected_by_user_id UUID REFERENCES users(id),
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,
    resubmission_allowed BOOLEAN DEFAULT TRUE,
    
    -- 해지
    terminated_at TIMESTAMPTZ,
    termination_reason TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- 제약: partner_id 또는 new_partner_* 둘 중 하나는 필수
    CONSTRAINT chk_partner_ref CHECK (
        partner_id IS NOT NULL 
        OR (new_partner_business_number IS NOT NULL AND new_partner_name IS NOT NULL)
    )
);

CREATE INDEX idx_pdc_status ON partner_distributor_contracts(status);
CREATE INDEX idx_pdc_partner ON partner_distributor_contracts(partner_id);
CREATE INDEX idx_pdc_pending 
    ON partner_distributor_contracts(created_at DESC)
    WHERE status IN ('submitted', 'under_review');

-- ============================================
-- 3. 총판 계약 테이블 (partner_reseller_contracts)
-- ============================================
-- 총판은 대리점보다 큰 규모, 매출배분 방식이 다름

CREATE TABLE IF NOT EXISTS partner_reseller_contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_number TEXT UNIQUE,  -- "PRC-2026-0001"
    
    partner_id UUID REFERENCES partners(id),
    new_partner_name TEXT,
    new_partner_business_number TEXT,
    new_partner_representative TEXT,
    new_partner_address TEXT,
    new_partner_phone TEXT,
    new_partner_email TEXT,
    
    -- 총판 고유 조건
    revenue_share_rate NUMERIC(5,2) NOT NULL,  -- 매출배분율 (%)
    territory TEXT,
    sub_partners_allowed BOOLEAN DEFAULT TRUE,  -- 하위 대리점 모집 가능
    minimum_annual_revenue NUMERIC(15,2),
    advance_payment NUMERIC(15,2),               -- 선급금
    
    contract_start DATE,
    contract_end DATE,
    auto_renewal BOOLEAN DEFAULT FALSE,
    
    attachment_paths TEXT[] DEFAULT ARRAY[]::TEXT[],
    contract_pdf_path TEXT,
    
    status partner_contract_status NOT NULL DEFAULT 'draft',
    
    initiated_by_user_id UUID REFERENCES users(id),
    reviewed_by_user_id UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    executive_approved_by_user_id UUID REFERENCES users(id),
    executive_approved_at TIMESTAMPTZ,
    executive_approval_notes TEXT,
    bulk_approved BOOLEAN DEFAULT FALSE,
    bulk_approval_reason TEXT,
    contracted_at TIMESTAMPTZ,
    digital_signature_id TEXT,
    sent_back_reason TEXT,
    sent_back_at TIMESTAMPTZ,
    rejected_by_user_id UUID REFERENCES users(id),
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,
    resubmission_allowed BOOLEAN DEFAULT TRUE,
    terminated_at TIMESTAMPTZ,
    termination_reason TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT chk_partner_ref_reseller CHECK (
        partner_id IS NOT NULL 
        OR (new_partner_business_number IS NOT NULL AND new_partner_name IS NOT NULL)
    )
);

CREATE INDEX idx_prc_status ON partner_reseller_contracts(status);
CREATE INDEX idx_prc_partner ON partner_reseller_contracts(partner_id);
CREATE INDEX idx_prc_pending 
    ON partner_reseller_contracts(created_at DESC)
    WHERE status IN ('submitted', 'under_review');

-- ============================================
-- 4. 유관기관 계약 테이블 (partner_related_org_contracts)
-- ============================================
-- 영업 목적이 아닌 협력 관계. 매출 분배 없거나 단순 협력비

CREATE TABLE IF NOT EXISTS partner_related_org_contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_number TEXT UNIQUE,  -- "PROC-2026-0001"
    
    partner_id UUID REFERENCES partners(id),
    new_partner_name TEXT,
    new_partner_business_number TEXT,
    new_partner_representative TEXT,
    new_partner_address TEXT,
    new_partner_phone TEXT,
    new_partner_email TEXT,
    
    -- 유관기관 고유 조건
    cooperation_type TEXT,           -- '추천', '공동마케팅', '데이터제공' 등
    cooperation_fee NUMERIC(15,2),   -- 협력비 (없을 수도)
    referral_bonus NUMERIC(15,2),    -- 소개 보너스
    data_sharing_scope TEXT,         -- 공유 데이터 범위
    
    contract_start DATE,
    contract_end DATE,
    auto_renewal BOOLEAN DEFAULT FALSE,
    
    attachment_paths TEXT[] DEFAULT ARRAY[]::TEXT[],
    contract_pdf_path TEXT,
    
    status partner_contract_status NOT NULL DEFAULT 'draft',
    
    initiated_by_user_id UUID REFERENCES users(id),
    reviewed_by_user_id UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    executive_approved_by_user_id UUID REFERENCES users(id),
    executive_approved_at TIMESTAMPTZ,
    executive_approval_notes TEXT,
    bulk_approved BOOLEAN DEFAULT FALSE,
    bulk_approval_reason TEXT,
    contracted_at TIMESTAMPTZ,
    digital_signature_id TEXT,
    sent_back_reason TEXT,
    sent_back_at TIMESTAMPTZ,
    rejected_by_user_id UUID REFERENCES users(id),
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,
    resubmission_allowed BOOLEAN DEFAULT TRUE,
    terminated_at TIMESTAMPTZ,
    termination_reason TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT chk_partner_ref_related CHECK (
        partner_id IS NOT NULL 
        OR (new_partner_business_number IS NOT NULL AND new_partner_name IS NOT NULL)
    )
);

CREATE INDEX idx_proc_status ON partner_related_org_contracts(status);
CREATE INDEX idx_proc_partner ON partner_related_org_contracts(partner_id);
CREATE INDEX idx_proc_pending 
    ON partner_related_org_contracts(created_at DESC)
    WHERE status IN ('submitted', 'under_review');

-- ============================================
-- 5. 공통 이력 테이블 (3개 계약 종류 통합)
-- ============================================

CREATE TABLE IF NOT EXISTS partner_contract_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 계약 종류 + ID (어느 테이블의 어느 행인지)
    contract_type TEXT NOT NULL CHECK (contract_type IN (
        'distributor', 'reseller', 'related_org'
    )),
    contract_id UUID NOT NULL,
    
    action TEXT NOT NULL CHECK (action IN (
        'submit', 'review', 'executive_approve', 'bulk_approve',
        'send_back', 'reject', 'contract', 'terminate'
    )),
    
    actor_user_id UUID REFERENCES users(id),
    actor_role TEXT,
    
    from_status partner_contract_status,
    to_status partner_contract_status,
    
    notes TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pch_contract ON partner_contract_history(contract_type, contract_id, created_at);
CREATE INDEX idx_pch_actor ON partner_contract_history(actor_user_id);

-- ============================================
-- 6. 계약번호 자동 생성 함수 (3개 테이블 공유)
-- ============================================

CREATE OR REPLACE FUNCTION generate_partner_contract_number(p_prefix TEXT)
RETURNS TEXT AS $$
DECLARE
    v_year INT;
    v_seq INT;
    v_table TEXT;
BEGIN
    v_year := EXTRACT(YEAR FROM now());
    
    v_table := CASE p_prefix
        WHEN 'PDC' THEN 'partner_distributor_contracts'
        WHEN 'PRC' THEN 'partner_reseller_contracts'
        WHEN 'PROC' THEN 'partner_related_org_contracts'
    END;
    
    EXECUTE format(
        'SELECT COALESCE(MAX(CAST(SUBSTRING(contract_number FROM ''%s-%s-(\d+)'') AS INT)), 0) + 1 FROM %I WHERE contract_number LIKE ''%s-%s-%%''',
        p_prefix, v_year, v_table, p_prefix, v_year
    ) INTO v_seq;
    
    RETURN p_prefix || '-' || v_year || '-' || LPAD(v_seq::TEXT, 4, '0');
END;
$$ LANGUAGE plpgsql;

-- 각 테이블별 자동 번호 트리거
CREATE OR REPLACE FUNCTION trg_pdc_set_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.contract_number IS NULL THEN
        NEW.contract_number := generate_partner_contract_number('PDC');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_pdc_number BEFORE INSERT ON partner_distributor_contracts
    FOR EACH ROW EXECUTE FUNCTION trg_pdc_set_number();

CREATE OR REPLACE FUNCTION trg_prc_set_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.contract_number IS NULL THEN
        NEW.contract_number := generate_partner_contract_number('PRC');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_prc_number BEFORE INSERT ON partner_reseller_contracts
    FOR EACH ROW EXECUTE FUNCTION trg_prc_set_number();

CREATE OR REPLACE FUNCTION trg_proc_set_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.contract_number IS NULL THEN
        NEW.contract_number := generate_partner_contract_number('PROC');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_proc_number BEFORE INSERT ON partner_related_org_contracts
    FOR EACH ROW EXECUTE FUNCTION trg_proc_set_number();

-- updated_at 트리거 3개
CREATE TRIGGER trg_pdc_updated_at BEFORE UPDATE ON partner_distributor_contracts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_prc_updated_at BEFORE UPDATE ON partner_reseller_contracts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_proc_updated_at BEFORE UPDATE ON partner_related_org_contracts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 7. 자동 partners 등록 트리거
-- ============================================
-- executive_approved → contracted 전환 시,
-- 신규 파트너인 경우 partners 테이블에 자동 등록

CREATE OR REPLACE FUNCTION auto_create_partner_on_contract(
    p_contract_id UUID,
    p_contract_type TEXT,
    p_partner_id UUID,
    p_new_name TEXT,
    p_new_business_number TEXT,
    p_new_rep TEXT,
    p_new_address TEXT,
    p_new_phone TEXT,
    p_new_email TEXT
)
RETURNS UUID AS $$
DECLARE
    v_partner_id UUID;
BEGIN
    -- 이미 partners에 있는 경우 기존 ID 반환
    IF p_partner_id IS NOT NULL THEN
        -- 자격 플래그 업데이트
        UPDATE partners SET
            is_distributor = is_distributor OR (p_contract_type = 'distributor'),
            is_reseller    = is_reseller    OR (p_contract_type = 'reseller'),
            is_related_org = is_related_org OR (p_contract_type = 'related_org'),
            updated_at = now()
        WHERE id = p_partner_id;
        RETURN p_partner_id;
    END IF;
    
    -- 신규 등록
    INSERT INTO partners (
        name, business_number, representative_name,
        address, phone, email,
        is_distributor, is_reseller, is_related_org,
        demo_monitoring_seats
    ) VALUES (
        p_new_name, p_new_business_number, p_new_rep,
        p_new_address, p_new_phone, p_new_email,
        p_contract_type = 'distributor',
        p_contract_type = 'reseller',
        p_contract_type = 'related_org',
        1  -- 기본 데모 1seat
    ) RETURNING id INTO v_partner_id;
    
    RETURN v_partner_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 8. 권한 체크 헬퍼
-- ============================================

-- 파트너 계약 최종 승인 권한 = 임원만 (Director는 검토만 가능)
-- 현재는 hq_admin = 임원이지만, 향후 hq_executive 분리 가능
CREATE OR REPLACE FUNCTION can_approve_partner_contract(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    -- TODO: v2.2에서 hq_executive group_type 분리 시 여기 수정
    RETURN user_is_hq_admin(p_user_id);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION can_approve_partner_contract(UUID) IS 
    '파트너 계약 최종 승인 = 임원 전권. 현재는 hq_admin 전체.';

-- 운영팀 검토는 HQ 직원 모두
-- (can_review_license를 재사용해도 됨)

-- ============================================
-- 9. RLS 정책 (3개 테이블 동일 패턴)
-- ============================================

-- 대리점 계약
ALTER TABLE partner_distributor_contracts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pdc_select ON partner_distributor_contracts;
CREATE POLICY pdc_select ON partner_distributor_contracts FOR SELECT
USING (
    user_is_hq_staff(auth.uid())
    OR partner_id = user_partner_id(auth.uid())
);

DROP POLICY IF EXISTS pdc_insert ON partner_distributor_contracts;
CREATE POLICY pdc_insert ON partner_distributor_contracts FOR INSERT
WITH CHECK (user_is_hq_staff(auth.uid()));  -- HQ만 신규 계약 작성

DROP POLICY IF EXISTS pdc_update ON partner_distributor_contracts;
CREATE POLICY pdc_update ON partner_distributor_contracts FOR UPDATE
USING (user_is_hq_staff(auth.uid()));

DROP POLICY IF EXISTS pdc_delete ON partner_distributor_contracts;
CREATE POLICY pdc_delete ON partner_distributor_contracts FOR DELETE
USING (user_is_hq_admin(auth.uid()));

-- 총판 계약
ALTER TABLE partner_reseller_contracts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS prc_select ON partner_reseller_contracts;
CREATE POLICY prc_select ON partner_reseller_contracts FOR SELECT
USING (
    user_is_hq_staff(auth.uid())
    OR partner_id = user_partner_id(auth.uid())
);

DROP POLICY IF EXISTS prc_insert ON partner_reseller_contracts;
CREATE POLICY prc_insert ON partner_reseller_contracts FOR INSERT
WITH CHECK (user_is_hq_staff(auth.uid()));

DROP POLICY IF EXISTS prc_update ON partner_reseller_contracts;
CREATE POLICY prc_update ON partner_reseller_contracts FOR UPDATE
USING (user_is_hq_staff(auth.uid()));

DROP POLICY IF EXISTS prc_delete ON partner_reseller_contracts;
CREATE POLICY prc_delete ON partner_reseller_contracts FOR DELETE
USING (user_is_hq_admin(auth.uid()));

-- 유관기관 계약
ALTER TABLE partner_related_org_contracts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS proc_select ON partner_related_org_contracts;
CREATE POLICY proc_select ON partner_related_org_contracts FOR SELECT
USING (
    user_is_hq_staff(auth.uid())
    OR partner_id = user_partner_id(auth.uid())
);

DROP POLICY IF EXISTS proc_insert ON partner_related_org_contracts;
CREATE POLICY proc_insert ON partner_related_org_contracts FOR INSERT
WITH CHECK (user_is_hq_staff(auth.uid()));

DROP POLICY IF EXISTS proc_update ON partner_related_org_contracts;
CREATE POLICY proc_update ON partner_related_org_contracts FOR UPDATE
USING (user_is_hq_staff(auth.uid()));

DROP POLICY IF EXISTS proc_delete ON partner_related_org_contracts;
CREATE POLICY proc_delete ON partner_related_org_contracts FOR DELETE
USING (user_is_hq_admin(auth.uid()));

-- 이력 테이블 RLS
ALTER TABLE partner_contract_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pch_select ON partner_contract_history;
CREATE POLICY pch_select ON partner_contract_history FOR SELECT
USING (user_is_hq_staff(auth.uid()));

-- ============================================
-- 10. 통합 조회 VIEW (3개 계약 합쳐 보기)
-- ============================================

CREATE OR REPLACE VIEW all_partner_contracts AS
SELECT 
    id, contract_number, 'distributor' AS contract_type,
    partner_id, new_partner_name, new_partner_business_number,
    status, initiated_by_user_id,
    executive_approved_by_user_id, executive_approved_at,
    contracted_at, created_at
FROM partner_distributor_contracts
UNION ALL
SELECT 
    id, contract_number, 'reseller',
    partner_id, new_partner_name, new_partner_business_number,
    status, initiated_by_user_id,
    executive_approved_by_user_id, executive_approved_at,
    contracted_at, created_at
FROM partner_reseller_contracts
UNION ALL
SELECT 
    id, contract_number, 'related_org',
    partner_id, new_partner_name, new_partner_business_number,
    status, initiated_by_user_id,
    executive_approved_by_user_id, executive_approved_at,
    contracted_at, created_at
FROM partner_related_org_contracts;

COMMENT ON VIEW all_partner_contracts IS 
    '3종 파트너 계약 통합 조회. 화면에 "전체 계약 대시보드" 만들 때 사용.';

-- ============================================
-- 11. 검증
-- ============================================

SELECT table_name, 
       EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name=t) AS exists
FROM (VALUES 
    ('partner_distributor_contracts'),
    ('partner_reseller_contracts'),
    ('partner_related_org_contracts'),
    ('partner_contract_history')
) AS x(t)
CROSS JOIN LATERAL (SELECT t AS table_name) y;

COMMIT;

-- ============================================
-- 롤백 SQL
-- ============================================
-- BEGIN;
-- DROP VIEW IF EXISTS all_partner_contracts;
-- DROP FUNCTION IF EXISTS can_approve_partner_contract(UUID);
-- DROP FUNCTION IF EXISTS auto_create_partner_on_contract(UUID,TEXT,UUID,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT);
-- DROP FUNCTION IF EXISTS generate_partner_contract_number(TEXT);
-- DROP FUNCTION IF EXISTS trg_pdc_set_number();
-- DROP FUNCTION IF EXISTS trg_prc_set_number();
-- DROP FUNCTION IF EXISTS trg_proc_set_number();
-- DROP TABLE IF EXISTS partner_contract_history CASCADE;
-- DROP TABLE IF EXISTS partner_related_org_contracts CASCADE;
-- DROP TABLE IF EXISTS partner_reseller_contracts CASCADE;
-- DROP TABLE IF EXISTS partner_distributor_contracts CASCADE;
-- DROP TYPE IF EXISTS partner_contract_status;
-- COMMIT;

-- ============================================================
-- 📋 앱 코드 통합 가이드 (참고)
-- ============================================================
--
-- 1. 신규 대리점 계약 작성 (운영팀 또는 임원)
--    INSERT INTO partner_distributor_contracts (
--        new_partner_name, new_partner_business_number,
--        commission_rate, territory, contract_start, contract_end,
--        initiated_by_user_id, status
--    ) VALUES (..., 'draft');
--
-- 2. 제출
--    UPDATE ... SET status='submitted'
--
-- 3. 운영팀 검토
--    UPDATE ... SET status='under_review', reviewed_by_user_id=me, ...
--
-- 4. 임원 최종 승인 (= 계약 체결 직전)
--    UPDATE ... SET status='executive_approved',
--                   executive_approved_by_user_id=me, ...
--
-- 5. 전자서명 완료 후 계약 체결
--    UPDATE ... SET status='contracted', contracted_at=now(),
--                   digital_signature_id=...
--    → 이때 auto_create_partner_on_contract() 호출하여 partners 자동 등록/업데이트
--
-- 6. 임원 대결재 일괄 승인
--    UPDATE ... SET status='executive_approved',
--                   bulk_approved=true,
--                   bulk_approval_reason='운영팀 부재로 대결재'
--
-- 7. 재검토 반려
--    UPDATE ... SET status='sent_back', sent_back_reason=...
--    → 다시 'under_review' 단계로 노출
--
-- 8. 리젝
--    UPDATE ... SET status='rejected', rejection_reason=...,
--                   resubmission_allowed=true/false
--    → 신청자에게 이메일+인앱 알림
--
-- 9. 계약 해지
--    UPDATE ... SET status='terminated', termination_reason=...
--
-- ============================================================
