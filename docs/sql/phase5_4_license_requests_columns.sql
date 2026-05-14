-- ════════════════════════════════════════════════════════════════
-- Phase 5-4 보완: license_requests 시장 확장 컬럼 추가
-- 작성: 2026-05-14 12:30
-- 목적: 신청 페이지에 사업 분야 + 관할 기관 동적 선택 도입
-- ════════════════════════════════════════════════════════════════

ALTER TABLE license_requests
    ADD COLUMN IF NOT EXISTS business_field TEXT,
    ADD COLUMN IF NOT EXISTS regulatory_authority TEXT;

COMMENT ON COLUMN license_requests.business_field IS '지원 사업 분야 (장애인고용/시니어고용/지자체/사회복지 등)';
COMMENT ON COLUMN license_requests.regulatory_authority IS '관할 기관 (기타 선택 시 직접 입력값 저장)';

-- 검증
SELECT 
    column_name, 
    data_type
FROM information_schema.columns 
WHERE table_name = 'license_requests'
  AND column_name IN ('business_field', 'regulatory_authority', 'disability_office', 'disability_org')
ORDER BY ordinal_position;
