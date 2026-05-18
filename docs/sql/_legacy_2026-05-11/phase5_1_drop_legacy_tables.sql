-- ═══════════════════════════════════════════════════════════════
-- DragonEyes Phase 5-1: agencies/agency_tenants 테이블 DROP
-- ═══════════════════════════════════════════════════════════════
-- 작성일: 2026-05-12
-- 작업자: 좋아요님 (확인) + Claude (작성)
-- 목적: Phase 4 완료 후 더 이상 사용하지 않는 레거시 테이블 제거
-- 
-- 사전 검증 완료 (2026-05-12 07:00~07:05):
--   ✅ public.agencies: 1 row (backup_20260510.agencies에 백업됨)
--   ✅ public.agency_tenants: 0 rows (데이터 없음)
--   ✅ 코드 'supabase.table("agencies")': 0건
--   ✅ 코드 'supabase.table("agency_tenants")': 0건
--   ⚠️ users.agency_id 컬럼: 33곳 참조 잔존 → 이번 단계에서 안 건드림
--                            (Phase 5-2에서 코드 정리 후 컬럼 DROP)
-- 
-- 안전장치:
--   1. BEGIN/COMMIT 트랜잭션 (중간 에러 시 자동 롤백)
--   2. agency_tenants 구조 백업 (0 rows라도 스키마 보존)
--   3. FK/뷰 의존성 사전 재점검
--   4. DROP 후 검증
-- 
-- 롤백 가능성:
--   - 트랜잭션 중간에 에러 발생 시: 자동 ROLLBACK
--   - COMMIT 후 롤백 필요 시: backup_20260510.agencies에서 복원 가능
--                          (agency_tenants는 데이터 0이므로 구조만 복원)
-- ═══════════════════════════════════════════════════════════════

BEGIN;

-- ───────────────────────────────────────────────────────────────
-- Step 1: agency_tenants 구조 백업 (0 rows라도 스키마 보존)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS backup_20260510.agency_tenants AS
    SELECT * FROM public.agency_tenants WHERE FALSE;

-- 백업 확인
DO $$
DECLARE
    backup_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'backup_20260510' 
          AND table_name = 'agency_tenants'
    ) INTO backup_exists;
    
    IF NOT backup_exists THEN
        RAISE EXCEPTION '❌ Step 1 실패: agency_tenants 백업 생성 안됨';
    END IF;
    
    RAISE NOTICE '✅ Step 1 완료: backup_20260510.agency_tenants 구조 백업';
END $$;

-- ───────────────────────────────────────────────────────────────
-- Step 2: FK/뷰 의존성 최종 재점검 (DROP 직전 안전망)
-- ───────────────────────────────────────────────────────────────
DO $$
DECLARE
    fk_count INTEGER;
    view_count INTEGER;
BEGIN
    -- 외래키 의존성
    SELECT COUNT(*) INTO fk_count
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND ccu.table_name IN ('agencies', 'agency_tenants')
      AND ccu.table_schema = 'public'
      AND tc.table_schema = 'public';  -- public 내 FK만
    
    -- 뷰 의존성 (public 스키마)
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views
    WHERE table_schema = 'public'
      AND (view_definition LIKE '%public.agencies%'
        OR view_definition LIKE '%public.agency_tenants%');
    
    RAISE NOTICE '📊 FK 의존성 (public 내): % 개', fk_count;
    RAISE NOTICE '📊 View 의존성 (public 내): % 개', view_count;
    
    -- 의존성 있으면 CASCADE로 처리하므로 경고만
    IF fk_count > 0 OR view_count > 0 THEN
        RAISE WARNING '⚠️ 의존성 발견. CASCADE로 함께 삭제됨. 계속 진행.';
    END IF;
END $$;

-- ───────────────────────────────────────────────────────────────
-- Step 3: DROP 실행
-- ───────────────────────────────────────────────────────────────
-- agency_tenants 먼저 (agencies 참조하므로)
DROP TABLE IF EXISTS public.agency_tenants CASCADE;

-- agencies 다음
DROP TABLE IF EXISTS public.agencies CASCADE;

DO $$
BEGIN
    RAISE NOTICE '✅ Step 3 완료: agencies, agency_tenants DROP 실행';
END $$;

-- ───────────────────────────────────────────────────────────────
-- Step 4: DROP 검증
-- ───────────────────────────────────────────────────────────────
DO $$
DECLARE
    agencies_exists BOOLEAN;
    agency_tenants_exists BOOLEAN;
    backup_agencies_count INTEGER;
BEGIN
    -- public 스키마에서 사라졌는지
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'agencies'
    ) INTO agencies_exists;
    
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'agency_tenants'
    ) INTO agency_tenants_exists;
    
    -- 백업 보존 확인
    SELECT COUNT(*) INTO backup_agencies_count 
    FROM backup_20260510.agencies;
    
    IF agencies_exists THEN
        RAISE EXCEPTION '❌ public.agencies가 아직 존재함';
    END IF;
    
    IF agency_tenants_exists THEN
        RAISE EXCEPTION '❌ public.agency_tenants가 아직 존재함';
    END IF;
    
    IF backup_agencies_count < 1 THEN
        RAISE EXCEPTION '❌ backup_20260510.agencies 백업이 손상됨 (% rows)', backup_agencies_count;
    END IF;
    
    RAISE NOTICE '═══════════════════════════════════════════════════════';
    RAISE NOTICE '🎉 Phase 5-1 완료';
    RAISE NOTICE '   public.agencies: 삭제됨 ✅';
    RAISE NOTICE '   public.agency_tenants: 삭제됨 ✅';
    RAISE NOTICE '   backup_20260510.agencies: % rows 보존 ✅', backup_agencies_count;
    RAISE NOTICE '   backup_20260510.agency_tenants: 구조 보존 ✅';
    RAISE NOTICE '═══════════════════════════════════════════════════════';
    RAISE NOTICE '⏳ 다음 작업 (Phase 5-2):';
    RAISE NOTICE '   - app.py의 agency_id 참조 33곳 정리';
    RAISE NOTICE '   - get_all_agencies 함수 partners 기반으로 교체';
    RAISE NOTICE '   - 정리 후 users.agency_id 컬럼 DROP';
END $$;

COMMIT;

-- ═══════════════════════════════════════════════════════════════
-- 롤백 SQL (커밋 후 긴급 복원 필요 시)
-- ═══════════════════════════════════════════════════════════════
-- 주의: 정상 작업 시 실행하지 말 것
-- 사용 시점: Streamlit이 깨졌거나 다른 코드가 agencies를 참조해서 에러 나는 경우
/*
BEGIN;

-- agencies 복원
CREATE TABLE public.agencies AS 
    SELECT * FROM backup_20260510.agencies;

-- agency_tenants 복원 (구조만, 0 rows)
CREATE TABLE public.agency_tenants AS 
    SELECT * FROM backup_20260510.agency_tenants;

-- 검증
SELECT 'agencies 복원' AS status, COUNT(*) AS rows FROM public.agencies
UNION ALL
SELECT 'agency_tenants 복원', COUNT(*) FROM public.agency_tenants;

COMMIT;
*/
