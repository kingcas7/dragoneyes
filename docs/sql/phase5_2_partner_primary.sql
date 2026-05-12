-- ═══════════════════════════════════════════════════════════════
-- DragonEyes Phase 5-2: 파트너 대표 담당자 (is_partner_primary)
-- ═══════════════════════════════════════════════════════════════
-- 작성일: 2026-05-12
-- 목적: 파트너관리자 화면 "담당자: 미연결" 문제 해결
-- ═══════════════════════════════════════════════════════════════

BEGIN;

-- Step 1: 컬럼 추가
ALTER TABLE public.users 
    ADD COLUMN IF NOT EXISTS is_partner_primary BOOLEAN DEFAULT FALSE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' 
          AND table_name = 'users'
          AND column_name = 'is_partner_primary'
    ) THEN
        RAISE EXCEPTION '❌ Step 1 실패';
    END IF;
    RAISE NOTICE '✅ Step 1 완료: is_partner_primary 컬럼 추가';
END $$;

-- Step 2: 제약 조건
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_partner_primary_unique
    ON public.users(partner_id)
    WHERE is_partner_primary = TRUE AND deleted_at IS NULL;

ALTER TABLE public.users 
    DROP CONSTRAINT IF EXISTS check_partner_primary_requires_partner;

ALTER TABLE public.users
    ADD CONSTRAINT check_partner_primary_requires_partner
    CHECK (NOT (is_partner_primary = TRUE AND partner_id IS NULL));

DO $$
BEGIN
    RAISE NOTICE '✅ Step 2 완료: 유니크 인덱스 + 체크 제약';
END $$;

-- Step 3: 초기 데이터
UPDATE public.users 
SET is_partner_primary = TRUE, updated_at = NOW()
WHERE email = 'wjdheeyoung@naver.com'
  AND partner_id IS NOT NULL
  AND role = 'admin'
  AND deleted_at IS NULL;

UPDATE public.users 
SET is_partner_primary = TRUE, updated_at = NOW()
WHERE email = 'rapid1120@daum.net'
  AND partner_id IS NOT NULL
  AND role = 'admin'
  AND deleted_at IS NULL;

UPDATE public.users 
SET is_partner_primary = FALSE, updated_at = NOW()
WHERE email = 'long8282@gmail.com'
  AND deleted_at IS NULL;

DO $$
DECLARE
    primary_count INTEGER;
    jung_set BOOLEAN;
    hwang_set BOOLEAN;
BEGIN
    SELECT COUNT(*) INTO primary_count FROM public.users
    WHERE is_partner_primary = TRUE AND deleted_at IS NULL;
    
    SELECT is_partner_primary INTO jung_set FROM public.users
    WHERE email = 'wjdheeyoung@naver.com' AND deleted_at IS NULL;
    
    SELECT is_partner_primary INTO hwang_set FROM public.users
    WHERE email = 'rapid1120@daum.net' AND deleted_at IS NULL;
    
    RAISE NOTICE '📊 전체 primary: % 명', primary_count;
    RAISE NOTICE '   정희영: %', jung_set;
    RAISE NOTICE '   황철희: %', hwang_set;
    
    IF primary_count != 2 THEN
        RAISE EXCEPTION '❌ primary 카운트 이상 (expected 2, got %)', primary_count;
    END IF;
    
    IF jung_set IS NOT TRUE OR hwang_set IS NOT TRUE THEN
        RAISE EXCEPTION '❌ 정희영/황철희 설정 실패';
    END IF;
    
    RAISE NOTICE '✅ Step 3 완료: 정희영/황철희 → primary';
END $$;

-- Step 4: 최종 검증
DO $$
DECLARE
    total_admins INTEGER;
    partner_admins INTEGER;
    primary_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_admins FROM public.users
    WHERE role = 'admin' AND deleted_at IS NULL;
    
    SELECT COUNT(*) INTO partner_admins FROM public.users
    WHERE role = 'admin' AND partner_id IS NOT NULL AND deleted_at IS NULL;
    
    SELECT COUNT(*) INTO primary_count FROM public.users
    WHERE is_partner_primary = TRUE AND deleted_at IS NULL;
    
    RAISE NOTICE '═══════════════════════════════════════════════════════';
    RAISE NOTICE '🎉 Phase 5-2 완료';
    RAISE NOTICE '   전체 admin: % 명', total_admins;
    RAISE NOTICE '   파트너 admin: % 명', partner_admins;
    RAISE NOTICE '   primary: % 명', primary_count;
    RAISE NOTICE '═══════════════════════════════════════════════════════';
END $$;

COMMIT;
