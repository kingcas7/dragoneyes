-- ════════════════════════════════════════════════════════════════
-- Phase 5-4 보완: license_requests에 representative_name 컬럼 추가
-- 작성: 2026-05-14 14:05
-- 목적: PO 양식 ② FROM 대표이사 정보를 신청서에 저장
-- ════════════════════════════════════════════════════════════════

ALTER TABLE license_requests
    ADD COLUMN IF NOT EXISTS representative_name TEXT;

COMMENT ON COLUMN license_requests.representative_name IS '고객사 대표이사 이름 (PO 양식 ② FROM)';

-- 2026-05-30 Supabase 정책 변경 대비 GRANT (P2 백로그 항목)
-- license_requests는 기존 테이블이라 자동 권한 유지되지만, 명시적으로 추가
GRANT SELECT, INSERT, UPDATE ON public.license_requests TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.license_requests TO service_role;

-- 검증
SELECT 
    column_name, 
    data_type
FROM information_schema.columns 
WHERE table_name = 'license_requests'
  AND column_name = 'representative_name';
