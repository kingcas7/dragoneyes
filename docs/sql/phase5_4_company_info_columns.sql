-- ════════════════════════════════════════════════════════════════
-- Phase 5-4: 법인 정보 관리 컬럼 확장
-- 작성: 2026-05-14
-- 목적: 고객사(tenants) + 파트너(partners) 회사 정보 관리 페이지 지원
--       PO 양식 ①TO ②FROM 정보를 시스템에서 직접 관리 가능하게
-- ════════════════════════════════════════════════════════════════

-- ┌──────────────────────────────────────────────────────────────┐
-- │ A. tenants 테이블 (고객사) 회사 정보 컬럼 추가
-- │    현재: name, license_plan, contact_email/phone, dates만 있음
-- │    추가: PO 양식 ② FROM 영역 완전 커버
-- └──────────────────────────────────────────────────────────────┘
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS business_number TEXT,
    ADD COLUMN IF NOT EXISTS representative_name TEXT,
    ADD COLUMN IF NOT EXISTS address TEXT,
    ADD COLUMN IF NOT EXISTS admin_name TEXT,
    ADD COLUMN IF NOT EXISTS admin_title TEXT,
    ADD COLUMN IF NOT EXISTS admin_phone TEXT,
    ADD COLUMN IF NOT EXISTS admin_email TEXT,
    ADD COLUMN IF NOT EXISTS regulatory_authority TEXT,  -- 관할 기관 (5/14 시장 확장)
    ADD COLUMN IF NOT EXISTS business_field TEXT,        -- 지원 사업 분야
    ADD COLUMN IF NOT EXISTS company_updated_at TIMESTAMPTZ DEFAULT NOW();

COMMENT ON COLUMN tenants.business_number IS '사업자등록번호 (10자리, 예: 123-45-67890)';
COMMENT ON COLUMN tenants.representative_name IS '대표이사 이름';
COMMENT ON COLUMN tenants.regulatory_authority IS '관할 기관 (장애인공단/노인공단/지자체 등)';
COMMENT ON COLUMN tenants.business_field IS '지원 사업 분야 (장애인고용/시니어고용/지자체 등)';


-- ┌──────────────────────────────────────────────────────────────┐
-- │ B. partners 테이블 (대리점/파트너) 담당자 정보 추가
-- │    현재: name, business_number, representative_name, address, 
-- │          phone, email 있음 (회사 정보 충분)
-- │    추가: 담당자(연락 실무자) 정보 — PO 양식 ① TO의 담당자 영역
-- └──────────────────────────────────────────────────────────────┘
ALTER TABLE partners
    ADD COLUMN IF NOT EXISTS admin_name TEXT,
    ADD COLUMN IF NOT EXISTS admin_title TEXT,
    ADD COLUMN IF NOT EXISTS admin_phone TEXT,
    ADD COLUMN IF NOT EXISTS company_updated_at TIMESTAMPTZ DEFAULT NOW();

COMMENT ON COLUMN partners.admin_name IS '실무 담당자 이름 (회사 대표 이메일과 별개)';
COMMENT ON COLUMN partners.admin_title IS '담당자 직책';
COMMENT ON COLUMN partners.admin_phone IS '담당자 직통 연락처';


-- ┌──────────────────────────────────────────────────────────────┐
-- │ 검증 쿼리
-- └──────────────────────────────────────────────────────────────┘
SELECT 
    'tenants' AS table_name,
    column_name, 
    data_type
FROM information_schema.columns 
WHERE table_name = 'tenants'
  AND column_name IN ('business_number', 'representative_name', 'address',
                       'admin_name', 'admin_title', 'admin_phone', 'admin_email',
                       'regulatory_authority', 'business_field', 'company_updated_at')
ORDER BY ordinal_position;

SELECT 
    'partners' AS table_name,
    column_name, 
    data_type
FROM information_schema.columns 
WHERE table_name = 'partners'
  AND column_name IN ('admin_name', 'admin_title', 'admin_phone', 'company_updated_at')
ORDER BY ordinal_position;
