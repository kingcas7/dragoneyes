-- ============================================================
-- DragonEyes v1.6 영업 거버넌스 — Fix 02
-- partners 테이블: 결제·정산 필드 컬럼 추가
-- ============================================================
-- 적용일 : 2026-05-18
-- 적용처 : 운영 Supabase (project xtqgxtdflemuphkzmzti)
--          → Supabase SQL Editor에서 아래 ALTER 실행
--
-- [목적]
--   파트너사 신규 등록 + 결제·정산 관리를 위해 partners 테이블에
--   결제 계좌 / 시스템 사용료 / 미수금 컬럼 추가.
--
-- [추가 컬럼]
--   bank_name           text          은행명
--   account_number      text          계좌번호
--   account_holder      text          예금주
--   system_fee_monthly  numeric(15,2) 드래곤아이즈 시스템 사용료(월, 원)
--   outstanding_balance numeric(15,2) 미수금(라이선스 발주대금 미입금 합계)
--
-- [후속 사용처]
--   - 관리자 콘솔 > 파트너관리자 관리 > '신규 파트너 등록' 폼
--   - 파트너 정보 페이지(partner_info)에서 표시·수정
--   - 추후 license_orders 연동 시 outstanding_balance 자동 계산 예정
-- ============================================================

ALTER TABLE public.partners
    ADD COLUMN IF NOT EXISTS bank_name           text,
    ADD COLUMN IF NOT EXISTS account_number      text,
    ADD COLUMN IF NOT EXISTS account_holder      text,
    ADD COLUMN IF NOT EXISTS system_fee_monthly  numeric(15,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS outstanding_balance numeric(15,2) DEFAULT 0;
