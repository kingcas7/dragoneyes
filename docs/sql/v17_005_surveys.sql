-- ============================================================
-- DragonEyes v1.7 — 캠페인 시스템 Phase 1 (005/008)
-- 설문 시스템 (전국 표준 + 학교 커스텀, 50문항·봉사점수 연동)
-- ============================================================
-- 적용일 : 2026-06-18
-- 목적   : 학생이 50문항 설문 성실 완료 → 봉사 점수 4~6시간 획득.
--
-- scope 설계:
--   scope='national' → institution_id NULL, 전국 모든 학생 활성
--   scope='school'   → institution_id NOT NULL, 해당 학교 학생만 활성
--   학교가 커스텀 미등록 시 → national만 활성 (학생이 'national' 선택)
--   학교 커스텀 등록 시   → 학생이 'national' / 'school' 중 선택
--
-- 성실도 (integrity_score) 0~100:
--   응답 시간 / 응답 길이 / 동일 답변 패턴 등으로 자동 산정
--   80 이상 → 봉사 점수 발급 가능
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. surveys — 설문지 메타
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.surveys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,

    -- 범위
    scope           TEXT NOT NULL CHECK (scope IN ('national', 'school')),
    institution_id  UUID REFERENCES public.institutions(id) ON DELETE CASCADE,

    title           TEXT NOT NULL,
    description     TEXT,
    target_grade_min SMALLINT,
    target_grade_max SMALLINT,

    -- 봉사 시간 (교육부 한도 — 일반적으로 4~6시간)
    target_minutes   INT NOT NULL DEFAULT 240
        CHECK (target_minutes BETWEEN 60 AND 600),

    -- 문항 수 (50개 기본)
    total_questions  INT NOT NULL DEFAULT 50
        CHECK (total_questions BETWEEN 10 AND 200),

    -- 성실도 통과 기준 (이 이상이어야 봉사 점수 발급)
    pass_integrity_score INT NOT NULL DEFAULT 80
        CHECK (pass_integrity_score BETWEEN 0 AND 100),

    -- 최소 응답 시간 (성실도 판단용)
    min_completion_seconds INT NOT NULL DEFAULT 600,    -- 10분

    status          TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'active', 'closed', 'archived')),
    published_at    TIMESTAMPTZ,

    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- scope=school이면 institution_id NOT NULL
    CONSTRAINT surveys_school_inst_check CHECK (
        (scope = 'national' AND institution_id IS NULL) OR
        (scope = 'school'   AND institution_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_surveys_campaign ON public.surveys(campaign_id);
CREATE INDEX IF NOT EXISTS idx_surveys_scope    ON public.surveys(scope);
CREATE INDEX IF NOT EXISTS idx_surveys_inst     ON public.surveys(institution_id) WHERE institution_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_surveys_status   ON public.surveys(status);


-- ─────────────────────────────────────────────────────────────
-- 2. survey_questions — 문항
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.survey_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_id       UUID NOT NULL REFERENCES public.surveys(id) ON DELETE CASCADE,

    qno             INT NOT NULL,                       -- 1, 2, 3, ...
    qtype           TEXT NOT NULL CHECK (qtype IN (
                        'single_choice',    -- 단일 선택
                        'multi_choice',     -- 복수 선택
                        'scale',            -- 척도 (1~5, 1~7)
                        'short_text',       -- 단답
                        'long_text',        -- 서술
                        'yes_no'            -- 예/아니오
                    )),
    text            TEXT NOT NULL,                      -- 문항
    description     TEXT,                               -- 추가 설명
    options         JSONB,                              -- choice/scale 선택지
    required        BOOLEAN NOT NULL DEFAULT TRUE,
    min_chars       INT,                                -- text 최소 글자수
    topic_tag       TEXT,                               -- 그루밍/도박/저작권/...
    sort_order      INT NOT NULL DEFAULT 0,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (survey_id, qno)
);

CREATE INDEX IF NOT EXISTS idx_sq_survey  ON public.survey_questions(survey_id, sort_order);


-- ─────────────────────────────────────────────────────────────
-- 3. survey_responses — 응답 헤더 (학생별 1건)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.survey_responses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_id       UUID NOT NULL REFERENCES public.surveys(id) ON DELETE CASCADE,
    student_id      UUID NOT NULL,                      -- users.id

    -- 시간 추적
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at    TIMESTAMPTZ,
    total_time_seconds INT,

    -- 진행 상태
    status          TEXT NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('in_progress', 'completed', 'abandoned', 'cancelled')),
    completion_rate NUMERIC(5,2) DEFAULT 0,             -- 0~100

    -- 성실도 (자동 계산)
    integrity_score INT,                                -- 0~100
    integrity_flags JSONB,                              -- 의심 항목 기록

    -- 학부모 도움 여부 (선택 기록)
    parent_assisted BOOLEAN DEFAULT FALSE,
    parent_id       UUID,                               -- 도움 준 학부모

    -- QR/링크 추적
    access_token    TEXT,                               -- 학생별 발급 토큰
    access_source   TEXT,                               -- 'qr' | 'link' | 'direct'

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (survey_id, student_id),                     -- 학생 1명 = 설문 1개당 응답 1건
    CONSTRAINT sr_student_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sr_survey      ON public.survey_responses(survey_id);
CREATE INDEX IF NOT EXISTS idx_sr_student     ON public.survey_responses(student_id);
CREATE INDEX IF NOT EXISTS idx_sr_status      ON public.survey_responses(status);
CREATE INDEX IF NOT EXISTS idx_sr_token       ON public.survey_responses(access_token) WHERE access_token IS NOT NULL;


-- ─────────────────────────────────────────────────────────────
-- 4. survey_answers — 개별 문항 응답
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.survey_answers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id     UUID NOT NULL REFERENCES public.survey_responses(id) ON DELETE CASCADE,
    question_id     UUID NOT NULL REFERENCES public.survey_questions(id) ON DELETE CASCADE,

    answer          JSONB NOT NULL,                     -- 모든 형식 통합 (text/choice/scale)
    answered_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    time_spent_seconds INT,                             -- 문항당 응답 시간

    UNIQUE (response_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_sa_response  ON public.survey_answers(response_id);
CREATE INDEX IF NOT EXISTS idx_sa_question  ON public.survey_answers(question_id);


-- ─────────────────────────────────────────────────────────────
-- 5. 학생용 활성 설문 조회 함수
-- ─────────────────────────────────────────────────────────────
-- 학교가 커스텀 등록 시 national + school 둘 다,
-- 미등록 시 national만 반환.
CREATE OR REPLACE FUNCTION public.get_available_surveys_for_student(p_student_id UUID)
RETURNS TABLE (
    survey_id UUID,
    campaign_id UUID,
    scope TEXT,
    title TEXT,
    target_minutes INT,
    total_questions INT,
    response_status TEXT
) LANGUAGE SQL STABLE AS $$
    WITH stu AS (
        SELECT id, institution_id, grade FROM public.users WHERE id = p_student_id
    )
    SELECT
        s.id AS survey_id,
        s.campaign_id,
        s.scope,
        s.title,
        s.target_minutes,
        s.total_questions,
        COALESCE(sr.status, 'not_started') AS response_status
    FROM public.surveys s
    LEFT JOIN public.survey_responses sr
        ON sr.survey_id = s.id AND sr.student_id = p_student_id
    CROSS JOIN stu
    WHERE s.status = 'active'
      AND (
          -- national은 모든 학생
          s.scope = 'national'
          OR
          -- school은 같은 학교 소속만
          (s.scope = 'school' AND s.institution_id = stu.institution_id)
      )
      AND (
          -- 학년 필터 (소속 학교 + 학년 매칭)
          s.target_grade_min IS NULL OR stu.grade IS NULL OR stu.grade >= s.target_grade_min
      )
      AND (
          s.target_grade_max IS NULL OR stu.grade IS NULL OR stu.grade <= s.target_grade_max
      )
    ORDER BY s.scope DESC,  -- school 먼저, national 다음
             s.published_at DESC NULLS LAST;
$$;


-- ─────────────────────────────────────────────────────────────
-- 트리거
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_surveys_updated_at ON public.surveys;
CREATE TRIGGER trg_surveys_updated_at
    BEFORE UPDATE ON public.surveys
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_sq_updated_at ON public.survey_questions;
CREATE TRIGGER trg_sq_updated_at
    BEFORE UPDATE ON public.survey_questions
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_sr_updated_at ON public.survey_responses;
CREATE TRIGGER trg_sr_updated_at
    BEFORE UPDATE ON public.survey_responses
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'surveys'           AS tbl, COUNT(*) AS rows FROM public.surveys
UNION ALL
SELECT 'survey_questions'  AS tbl, COUNT(*) FROM public.survey_questions
UNION ALL
SELECT 'survey_responses'  AS tbl, COUNT(*) FROM public.survey_responses
UNION ALL
SELECT 'survey_answers'    AS tbl, COUNT(*) FROM public.survey_answers;

-- 기대: 4개 행 모두 rows=0

-- 끝.
