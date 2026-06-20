-- ============================================================
-- DragonEyes v1.7 — Phase 7+8 보강 (011)
-- 시·도/시·군·구 의회 교육위원회 type 추가
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   : 지방의회 산하 교육위원회도 캠페인 시스템 사용자로 등록 가능하게.
--          그 외 예외 케이스는 'other'로 수기 등록.
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- 1. institutions.type CHECK 제약 확장
-- ─────────────────────────────────────────────────────────────
ALTER TABLE public.institutions
    DROP CONSTRAINT IF EXISTS institutions_type_check;

ALTER TABLE public.institutions
    ADD CONSTRAINT institutions_type_check CHECK (type IN (
        -- 정부/교육 행정
        'ministry',                 -- 교육부
        'metro_office',             -- 시·도 교육청
        'district_office',          -- 교육지원청

        -- 지방의회 교육위원회 (신규)
        'metro_council',            -- 시·도의회 교육위원회
        'local_council',            -- 시·군·구의회 교육위원회

        -- 학교
        'elementary',               -- 초등학교
        'middle',                   -- 중학교
        'high',                     -- 고등학교
        'special',                  -- 특수학교

        -- 인가 시설
        'youth_facility',           -- 교육부 인가 청소년 교육시설

        -- 예외 (수기 등록)
        'other'                     -- 기타 정규 교육기관
    ));


-- ─────────────────────────────────────────────────────────────
-- 2. 검증
-- ─────────────────────────────────────────────────────────────
-- 신규 type INSERT 테스트 (rollback 가능하므로 안전)
DO $$
BEGIN
    -- metro_council 시도 INSERT
    INSERT INTO public.institutions (type, name, region, status, verification_source)
    VALUES ('metro_council', '_TEST_시도의회_교육위', '테스트', 'pending', 'manual');
    INSERT INTO public.institutions (type, name, region, status, verification_source)
    VALUES ('local_council', '_TEST_시군구의회_교육위', '테스트', 'pending', 'manual');
    -- 즉시 삭제 (테스트만)
    DELETE FROM public.institutions WHERE name LIKE '_TEST_%';
    RAISE NOTICE '✅ metro_council / local_council type 정상 등록 가능';
END$$;

-- 현재 등록된 type 별 카운트
SELECT type, COUNT(*) AS cnt
FROM public.institutions
WHERE deleted_at IS NULL
GROUP BY type
ORDER BY type;

-- 끝.
