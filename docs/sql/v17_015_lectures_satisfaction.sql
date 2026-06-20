-- ============================================================
-- DragonEyes v1.7 — Phase 10 추가 (015)
-- 외부 초청강사 강연 + 학교 만족도 조사 (1차/2차)
-- ============================================================
-- 적용일 : 2026-06-20
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. institution_lectures — 외부 초청강사 강연 일정·실시 기록
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.institution_lectures (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id  UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,

    title           TEXT NOT NULL,
    lecturer_name   TEXT,
    lecturer_affiliation TEXT,
    topic           TEXT,                              -- 그루밍/저작권/디지털성범죄 등

    -- 일정
    scheduled_at    TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    duration_minutes INT,

    -- 대상
    target_grades   TEXT,                              -- '1,2,3' 콤마구분
    target_count    INT,                               -- 예상 참여 인원
    actual_count    INT,                               -- 실제 참여 인원

    status          TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled','completed','cancelled','postponed')),

    photo_url       TEXT,                              -- 사진 1장 (확장 가능)
    note            TEXT,

    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lec_inst       ON public.institution_lectures(institution_id);
CREATE INDEX IF NOT EXISTS idx_lec_status     ON public.institution_lectures(status);
CREATE INDEX IF NOT EXISTS idx_lec_scheduled  ON public.institution_lectures(scheduled_at);


-- ─────────────────────────────────────────────────────────────
-- 2. satisfaction_surveys — 만족도 조사 (상급 기관이 일괄 발송)
-- ─────────────────────────────────────────────────────────────
-- 1차/2차 등 round_number로 차수 관리.
CREATE TABLE IF NOT EXISTS public.satisfaction_surveys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID REFERENCES public.campaigns(id) ON DELETE SET NULL,

    title           TEXT NOT NULL,
    description     TEXT,
    round_number    INT NOT NULL DEFAULT 1
                        CHECK (round_number BETWEEN 1 AND 10),

    -- 마감
    deadline        TIMESTAMPTZ NOT NULL,

    -- 문항 (JSONB)
    --   [{qno, qtype:'single_choice'/'scale'/'long_text', text, options:[...]}]
    questions       JSONB NOT NULL,

    -- 대상
    target_audience TEXT NOT NULL DEFAULT 'institution_admin'
        CHECK (target_audience IN ('institution_admin','student','parent','all')),

    -- 배포자
    launched_by     UUID,                              -- 배포 user_id
    launched_inst_id UUID REFERENCES public.institutions(id) ON DELETE SET NULL,
    launched_scope  TEXT CHECK (launched_scope IN ('nation','metro','district')),

    status          TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('draft','active','closed','archived')),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (campaign_id, round_number, launched_inst_id)
);

CREATE INDEX IF NOT EXISTS idx_ss_status   ON public.satisfaction_surveys(status);
CREATE INDEX IF NOT EXISTS idx_ss_deadline ON public.satisfaction_surveys(deadline);
CREATE INDEX IF NOT EXISTS idx_ss_launched ON public.satisfaction_surveys(launched_inst_id);


-- ─────────────────────────────────────────────────────────────
-- 3. satisfaction_targets — 학교별 응답 대상 + 응답
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.satisfaction_targets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_id       UUID NOT NULL REFERENCES public.satisfaction_surveys(id) ON DELETE CASCADE,
    institution_id  UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,

    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at    TIMESTAMPTZ,
    respondent_user_id UUID,
    response_data   JSONB,                             -- {qno: answer}

    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','completed','overdue')),

    UNIQUE (survey_id, institution_id)
);

CREATE INDEX IF NOT EXISTS idx_st_survey  ON public.satisfaction_targets(survey_id);
CREATE INDEX IF NOT EXISTS idx_st_inst    ON public.satisfaction_targets(institution_id);
CREATE INDEX IF NOT EXISTS idx_st_status  ON public.satisfaction_targets(status);


-- ─────────────────────────────────────────────────────────────
-- 4. 트리거 (updated_at)
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_lec_updated_at ON public.institution_lectures;
CREATE TRIGGER trg_lec_updated_at
    BEFORE UPDATE ON public.institution_lectures
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_ss_updated_at ON public.satisfaction_surveys;
CREATE TRIGGER trg_ss_updated_at
    BEFORE UPDATE ON public.satisfaction_surveys
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 5. 헬퍼 함수 — 권한 범위 내 참여/미참여 학교 분류
-- ─────────────────────────────────────────────────────────────
-- '참여' 정의: 그 학교에 캠페인 학생(role_v2='student')이 1명 이상 등록되어 있음
CREATE OR REPLACE FUNCTION public.get_participating_institutions(p_inst_id UUID)
RETURNS TABLE (
    inst_id UUID,
    inst_name TEXT,
    inst_type TEXT,
    region TEXT,
    district TEXT,
    student_count BIGINT,
    is_participating BOOLEAN,
    has_lecture BOOLEAN,
    lecture_status TEXT,
    nearest_lecture_at TIMESTAMPTZ
) LANGUAGE SQL STABLE AS $$
    WITH visible AS (
        SELECT * FROM public.get_visible_institutions(p_inst_id)
        WHERE type IN ('elementary','middle','high','special','youth_facility')
    ),
    stu_count AS (
        SELECT institution_id, COUNT(*)::BIGINT AS n
        FROM public.users
        WHERE role_v2 = 'student' AND deleted_at IS NULL
          AND institution_id IS NOT NULL
        GROUP BY institution_id
    ),
    lec_summary AS (
        SELECT
            institution_id,
            COUNT(*) FILTER (WHERE status='completed')::BIGINT AS done_cnt,
            COUNT(*) FILTER (WHERE status='scheduled')::BIGINT AS scheduled_cnt,
            MIN(scheduled_at) FILTER (WHERE status='scheduled') AS next_lec
        FROM public.institution_lectures
        GROUP BY institution_id
    )
    SELECT
        v.id, v.name, v.type, v.region, v.district,
        COALESCE(s.n, 0) AS student_count,
        (COALESCE(s.n, 0) > 0) AS is_participating,
        (COALESCE(l.done_cnt, 0) + COALESCE(l.scheduled_cnt, 0)) > 0 AS has_lecture,
        CASE
            WHEN COALESCE(l.done_cnt, 0) > 0 AND COALESCE(l.scheduled_cnt, 0) > 0 THEN 'done+upcoming'
            WHEN COALESCE(l.done_cnt, 0) > 0 THEN 'done'
            WHEN COALESCE(l.scheduled_cnt, 0) > 0 THEN 'scheduled'
            ELSE 'none'
        END AS lecture_status,
        l.next_lec AS nearest_lecture_at
    FROM visible v
    LEFT JOIN stu_count s ON s.institution_id = v.id
    LEFT JOIN lec_summary l ON l.institution_id = v.id
    ORDER BY v.region, v.district, v.name;
$$;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'institution_lectures'     AS tbl, COUNT(*) AS rows FROM public.institution_lectures
UNION ALL
SELECT 'satisfaction_surveys'     AS tbl, COUNT(*) FROM public.satisfaction_surveys
UNION ALL
SELECT 'satisfaction_targets'     AS tbl, COUNT(*) FROM public.satisfaction_targets;
-- 기대: 모두 rows=0

SELECT routine_name FROM information_schema.routines
WHERE routine_schema='public'
  AND routine_name = 'get_participating_institutions';
-- 기대: 1행

-- 끝.
