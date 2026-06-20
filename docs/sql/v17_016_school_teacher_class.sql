-- ============================================================
-- DragonEyes v1.7 — Phase 10 추가 (016)
-- 학교별 교사 계정 + 반(class) 관리
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   학교당 여러 교사 계정 허용 (공용 또는 개별) → institution_admin 다중 사용
--   학생을 반(class) 단위로 묶어서 관리 → users.class_no 추가
--   교사가 담당 반 학생들의 봉사 점수·캠페인 진행 실시간 모니터링
--   학생 정보 수정 권한 (학생 불이익 방지)
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. users 컬럼 확장
-- ─────────────────────────────────────────────────────────────
-- 학생용
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS class_no SMALLINT
        CHECK (class_no IS NULL OR class_no BETWEEN 1 AND 30);

-- 교사용 (담당 반·과목 — JSONB)
-- 예: {"classes": [{"grade":1,"class_no":3,"subject":"담임"},{"grade":2,"class_no":5,"subject":"국어"}]}
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS teacher_charge JSONB;

-- 교사 type 구분 (담임/교과/관리자)
-- institution_admin 안에서 세부 역할 구분
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS teacher_role TEXT
        CHECK (teacher_role IS NULL OR teacher_role IN (
            'principal',     -- 교장
            'vice_principal',-- 교감
            'homeroom',      -- 담임
            'subject',       -- 교과
            'admin',         -- 행정/일반 관리자
            'shared'         -- 학교 공용 계정
        ));

CREATE INDEX IF NOT EXISTS idx_users_class
    ON public.users(institution_id, grade, class_no)
    WHERE role_v2 = 'student' AND deleted_at IS NULL;


-- ─────────────────────────────────────────────────────────────
-- 2. 학교 교사 계정 조회 헬퍼
-- ─────────────────────────────────────────────────────────────
-- 학교의 모든 institution_admin 계정 list
CREATE OR REPLACE FUNCTION public.get_school_teachers(p_inst_id UUID)
RETURNS TABLE (
    id UUID,
    name TEXT,
    email TEXT,
    teacher_role TEXT,
    teacher_charge JSONB,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
) LANGUAGE SQL STABLE AS $$
    SELECT
        u.id, u.name, u.email,
        u.teacher_role,
        u.teacher_charge,
        u.last_login_at,
        u.created_at
    FROM public.users u
    WHERE u.institution_id = p_inst_id
      AND u.role_v2 = 'institution_admin'
      AND u.deleted_at IS NULL
    ORDER BY
        CASE u.teacher_role
            WHEN 'principal' THEN 1
            WHEN 'vice_principal' THEN 2
            WHEN 'shared' THEN 3
            WHEN 'admin' THEN 4
            WHEN 'homeroom' THEN 5
            WHEN 'subject' THEN 6
            ELSE 7
        END,
        u.name;
$$;


-- ─────────────────────────────────────────────────────────────
-- 3. 반별 학생 통계 조회 (교사용)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_class_summary(p_inst_id UUID)
RETURNS TABLE (
    grade SMALLINT,
    class_no SMALLINT,
    student_count BIGINT,
    survey_completed BIGINT,
    total_hours NUMERIC,
    issued_hours NUMERIC,
    avg_hours NUMERIC
) LANGUAGE SQL STABLE AS $$
    SELECT
        u.grade::SMALLINT,
        u.class_no,
        COUNT(u.id)::BIGINT AS student_count,
        COUNT(DISTINCT sr.student_id) FILTER (WHERE sr.status='completed')::BIGINT AS survey_completed,
        COALESCE(SUM(vc.hours_decimal) FILTER (WHERE vc.status IN ('earned','issued')), 0) AS total_hours,
        COALESCE(SUM(vc.hours_decimal) FILTER (WHERE vc.status='issued'), 0) AS issued_hours,
        CASE WHEN COUNT(u.id) > 0
            THEN COALESCE(SUM(vc.hours_decimal) FILTER (WHERE vc.status IN ('earned','issued')), 0) / COUNT(u.id)
            ELSE 0
        END AS avg_hours
    FROM public.users u
    LEFT JOIN public.survey_responses sr ON sr.student_id = u.id
    LEFT JOIN public.volunteer_credits vc ON vc.student_id = u.id
    WHERE u.institution_id = p_inst_id
      AND u.role_v2 = 'student'
      AND u.deleted_at IS NULL
    GROUP BY u.grade, u.class_no
    ORDER BY u.grade NULLS LAST, u.class_no NULLS LAST;
$$;


-- ─────────────────────────────────────────────────────────────
-- 4. last_login_at 컬럼 (없으면 추가 — 교사 계정 활동 추적용)
-- ─────────────────────────────────────────────────────────────
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema='public' AND table_name='users'
  AND column_name IN ('class_no','teacher_charge','teacher_role','last_login_at')
ORDER BY column_name;
-- 기대: 4행

SELECT routine_name FROM information_schema.routines
WHERE routine_schema='public'
  AND routine_name IN ('get_school_teachers','get_class_summary')
ORDER BY routine_name;
-- 기대: 2행

-- 끝.
