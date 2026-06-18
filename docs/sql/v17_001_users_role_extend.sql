-- ============================================================
-- DragonEyes v1.7 — 캠페인 시스템 Phase 1 (001/008)
-- users 테이블에 캠페인 사용자(교육기관/학부모/학생) 컬럼 추가
-- ============================================================
-- 적용일 : 2026-06-18
-- 목적   : '온라인 유해컨텐츠 근절 캠페인' 사용자 3종 지원
--          ① institution_admin = 교육기관 사용자 (모니터링 연동 OK)
--          ② parent            = 학부모 (모니터링 연동 OK, 다자녀 가능)
--          ③ student           = 학생 (캠페인 전용, 모니터링 차단)
--
-- 안전성 : 모든 ALTER는 IF NOT EXISTS 사용. 기존 데이터 영향 없음.
--          신규 컬럼은 모두 nullable.
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- STEP 1 : users 확장 컬럼 추가
-- ─────────────────────────────────────────────────────────────

ALTER TABLE public.users
    -- 학교 소속 (학생 / institution_admin 둘 다 사용)
    ADD COLUMN IF NOT EXISTS institution_id UUID,
    -- 학년 (학생 — 1~12)
    ADD COLUMN IF NOT EXISTS grade SMALLINT,
    -- 학교명 자율 입력 (기관 매칭 전 임시값 fallback)
    ADD COLUMN IF NOT EXISTS school_name TEXT,
    -- 생년월일 (만 14세 미만 판단)
    ADD COLUMN IF NOT EXISTS birth_date DATE,
    -- 학부모 사전 동의 (만 14세 미만 학생 필수)
    ADD COLUMN IF NOT EXISTS parent_consent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS parent_consent_by UUID,  -- 동의한 학부모 user_id
    -- 가입 경로 (학생만 의미)
    ADD COLUMN IF NOT EXISTS signup_source TEXT
        CHECK (signup_source IS NULL OR signup_source IN ('self', 'institution_bulk', 'parent_create')),
    -- 캠페인 전용 사용자 (학생 = TRUE → 모니터링 로그인 차단)
    ADD COLUMN IF NOT EXISTS is_campaign_only BOOLEAN NOT NULL DEFAULT FALSE,
    -- 휴대전화 (학부모용 알림 채널 — 기존 phone과 별개로 필요시)
    ADD COLUMN IF NOT EXISTS notify_phone TEXT,
    -- 휴대전화 SMS 동의
    ADD COLUMN IF NOT EXISTS notify_sms_consent BOOLEAN DEFAULT FALSE;


-- ─────────────────────────────────────────────────────────────
-- STEP 2 : role_v2에 캠페인 3종 추가 (CHECK 제약 갱신)
-- ─────────────────────────────────────────────────────────────
-- 기존 role_v2 값: superadmin / director / director_2~4 / admin /
--                  agency_admin / tenant_admin / user
-- 추가:           institution_admin / parent / student

-- 기존 CHECK 제약이 있다면 일단 DROP (있을 때만)
DO $$
DECLARE
    _constraint_name TEXT;
BEGIN
    SELECT con.conname INTO _constraint_name
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE nsp.nspname = 'public'
      AND rel.relname = 'users'
      AND con.contype = 'c'
      AND pg_get_constraintdef(con.oid) ILIKE '%role_v2%';

    IF _constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE public.users DROP CONSTRAINT %I', _constraint_name);
    END IF;
END$$;

-- 새 CHECK 제약 추가 (캠페인 3종 포함)
ALTER TABLE public.users
    ADD CONSTRAINT users_role_v2_check CHECK (
        role_v2 IS NULL OR role_v2 IN (
            'superadmin', 'director', 'director_2', 'director_3', 'director_4',
            'admin', 'agency_admin', 'tenant_admin', 'user',
            'institution_admin', 'parent', 'student'
        )
    );


-- ─────────────────────────────────────────────────────────────
-- STEP 3 : 인덱스 (조회 패턴 기반)
-- ─────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_users_institution_id
    ON public.users(institution_id)
    WHERE institution_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_role_v2_campaign
    ON public.users(role_v2)
    WHERE role_v2 IN ('institution_admin', 'parent', 'student');

CREATE INDEX IF NOT EXISTS idx_users_is_campaign_only
    ON public.users(is_campaign_only)
    WHERE is_campaign_only = TRUE;


-- ─────────────────────────────────────────────────────────────
-- STEP 4 : 코멘트 (테이블·컬럼 문서화)
-- ─────────────────────────────────────────────────────────────

COMMENT ON COLUMN public.users.institution_id      IS '소속 교육기관 ID (학생/institution_admin)';
COMMENT ON COLUMN public.users.grade               IS '학년 1~12 (학생만)';
COMMENT ON COLUMN public.users.school_name         IS '학교명 자율 입력 (기관 매칭 전 fallback)';
COMMENT ON COLUMN public.users.birth_date          IS '생년월일 — 만 14세 미만 판단용';
COMMENT ON COLUMN public.users.parent_consent_at   IS '학부모 사전 동의 시각 (만 14세 미만 학생 필수)';
COMMENT ON COLUMN public.users.parent_consent_by   IS '동의한 학부모 user_id';
COMMENT ON COLUMN public.users.signup_source       IS '학생 가입 경로: self / institution_bulk / parent_create';
COMMENT ON COLUMN public.users.is_campaign_only    IS 'TRUE면 캠페인 전용 (모니터링 사이트 로그인 차단)';


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'users'
  AND column_name IN (
    'institution_id', 'grade', 'school_name', 'birth_date',
    'parent_consent_at', 'parent_consent_by', 'signup_source',
    'is_campaign_only', 'notify_phone', 'notify_sms_consent'
  )
ORDER BY column_name;

-- 기대: 10개 행 반환

-- 끝.
