-- ============================================================
-- DragonEyes v1.7 — Phase 11 (025)
-- 외부 응답자 설문 — 정적 HTML 페이지에서 anon으로 직접 응답 저장
-- ============================================================
-- 적용일 : 2026-06-21
-- 목적   :
--   학생이 본인의 token 링크/QR을 친구·가족·SNS에 공유 → 응답자가 정적
--   HTML 페이지에서 응답 → Supabase JS SDK로 anon role 직접 호출 →
--   external_survey_responses INSERT → student_survey_tokens.response_count
--   자동 증가 → 임계값(20/30/50) 도달 시 v17_018 트리거가 자동 인증서 발급.
--
-- 보안:
--   - anon role에 직접 INSERT 권한 X
--   - 모든 응답 저장은 SECURITY DEFINER 함수(submit_external_response) 경유
--   - 토큰 검증 + 응답 무결성 검사
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. external_survey_responses — 외부 응답자(친구·가족) 응답 저장
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.external_survey_responses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 어느 학생의 token으로 들어왔는지 (배포자 식별)
    token_id        UUID NOT NULL REFERENCES public.student_survey_tokens(id)
                       ON DELETE CASCADE,
    survey_id       UUID NOT NULL REFERENCES public.surveys(id) ON DELETE CASCADE,

    -- 응답자 정보 (응답자가 입력)
    respondent_name      TEXT NOT NULL,
    respondent_age       INT CHECK (respondent_age IS NULL OR respondent_age BETWEEN 5 AND 110),
    respondent_gender    TEXT CHECK (respondent_gender IS NULL
                            OR respondent_gender IN ('male','female','other','prefer_not')),
    respondent_region    TEXT,  -- 시·도 단위

    -- 응답 데이터 (JSONB: {qno: answer, ...})
    answers              JSONB NOT NULL,

    -- 무결성·검증
    integrity_score      INT,         -- 0~100, 트랩 문항 통과 점수 (선택)
    completion_seconds   INT,         -- 실제 소요 시간 (초)
    is_valid             BOOLEAN NOT NULL DEFAULT TRUE,

    -- 메타
    ip_address           TEXT,
    user_agent           TEXT,
    submitted_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_esr_token        ON public.external_survey_responses(token_id);
CREATE INDEX IF NOT EXISTS idx_esr_survey       ON public.external_survey_responses(survey_id);
CREATE INDEX IF NOT EXISTS idx_esr_submitted    ON public.external_survey_responses(submitted_at);
CREATE INDEX IF NOT EXISTS idx_esr_valid        ON public.external_survey_responses(is_valid)
    WHERE is_valid = TRUE;

-- 중복 차단용 일반 인덱스 (함수에서 SELECT EXISTS로 5분 이내 체크)
-- (DATE_TRUNC는 STABLE/generated column 모두 사용 불가하여 인덱스 대신 함수 로직으로 처리)
CREATE INDEX IF NOT EXISTS idx_esr_token_name_time
    ON public.external_survey_responses(token_id, respondent_name, submitted_at DESC);


-- ─────────────────────────────────────────────────────────────
-- 2. get_survey_by_token — anon에서 토큰으로 설문·학생 정보 조회
-- ─────────────────────────────────────────────────────────────
-- 정적 HTML 페이지가 URL의 token으로 처음 호출하는 함수.
-- 반환:
--   - 토큰 유효 여부
--   - 배포자(학생) 정보 (학교·학년·반·이름)
--   - 설문 메타 (학년대·제목·설명·소요분)
--   - 26문항 (qno, qtype, text, options, topic_tag, required)
CREATE OR REPLACE FUNCTION public.get_survey_by_token(p_token TEXT)
RETURNS JSONB
LANGUAGE plpgsql STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_tok    public.student_survey_tokens;
    v_stu    public.users;
    v_inst   public.institutions;
    v_sv     public.surveys;
    v_questions JSONB;
BEGIN
    SELECT * INTO v_tok FROM public.student_survey_tokens
     WHERE access_token = p_token LIMIT 1;
    IF v_tok IS NULL THEN
        RETURN jsonb_build_object('valid', FALSE, 'error', 'invalid_token');
    END IF;
    IF v_tok.revoked_at IS NOT NULL THEN
        RETURN jsonb_build_object('valid', FALSE, 'error', 'revoked');
    END IF;

    SELECT * INTO v_stu FROM public.users WHERE id = v_tok.student_id;
    IF v_stu.institution_id IS NOT NULL THEN
        SELECT * INTO v_inst FROM public.institutions WHERE id = v_stu.institution_id;
    END IF;
    SELECT * INTO v_sv FROM public.surveys WHERE id = v_tok.survey_id;

    -- 문항 목록 (qno 순)
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'qno', q.qno,
            'qtype', q.qtype,
            'text', q.text,
            'options', q.options,
            'topic_tag', q.topic_tag,
            'required', q.required
        ) ORDER BY q.qno
    ), '[]'::jsonb) INTO v_questions
      FROM public.survey_questions q
     WHERE q.survey_id = v_tok.survey_id;

    RETURN jsonb_build_object(
        'valid', TRUE,
        'token_id', v_tok.id,
        'survey_id', v_tok.survey_id,
        'response_count', v_tok.response_count,
        'student', jsonb_build_object(
            'name', v_stu.name,
            'school_name', COALESCE(v_inst.name, v_stu.school_name),
            'grade', v_stu.grade,
            'class_no', v_stu.class_no
        ),
        'survey', jsonb_build_object(
            'title', v_sv.title,
            'description', v_sv.description,
            'target_band', v_sv.target_band,
            'target_minutes', v_sv.target_minutes,
            'total_questions', v_sv.total_questions
        ),
        'questions', v_questions
    );
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 3. submit_external_response — anon에서 응답 저장
-- ─────────────────────────────────────────────────────────────
-- 정적 HTML 페이지가 응답 제출 시 호출.
-- - 토큰 유효성 검사
-- - 응답자 정보 + answers 저장
-- - student_survey_tokens.response_count 자동 증가
--   → v17_018 트리거가 임계값 도달 시 인증서 자동 발급
CREATE OR REPLACE FUNCTION public.submit_external_response(
    p_token              TEXT,
    p_respondent_name    TEXT,
    p_respondent_age     INT DEFAULT NULL,
    p_respondent_gender  TEXT DEFAULT NULL,
    p_respondent_region  TEXT DEFAULT NULL,
    p_answers            JSONB DEFAULT '{}'::jsonb,
    p_completion_seconds INT DEFAULT NULL,
    p_integrity_score    INT DEFAULT NULL,
    p_ip                 TEXT DEFAULT NULL,
    p_user_agent         TEXT DEFAULT NULL
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_tok        public.student_survey_tokens;
    v_response_id UUID;
    v_is_valid   BOOLEAN := TRUE;
    v_dup_exists BOOLEAN;
BEGIN
    -- 토큰 검증
    SELECT * INTO v_tok FROM public.student_survey_tokens
     WHERE access_token = p_token LIMIT 1;
    IF v_tok IS NULL THEN
        RETURN jsonb_build_object('ok', FALSE, 'error', 'invalid_token');
    END IF;
    IF v_tok.revoked_at IS NOT NULL THEN
        RETURN jsonb_build_object('ok', FALSE, 'error', 'revoked');
    END IF;

    -- 응답자 이름 필수
    IF p_respondent_name IS NULL OR LENGTH(TRIM(p_respondent_name)) < 1 THEN
        RETURN jsonb_build_object('ok', FALSE, 'error', 'name_required');
    END IF;

    -- 중복 제출 차단 (같은 token + 같은 응답자명 + 5분 이내)
    SELECT EXISTS(
        SELECT 1 FROM public.external_survey_responses
         WHERE token_id = v_tok.id
           AND respondent_name = TRIM(p_respondent_name)
           AND submitted_at > NOW() - INTERVAL '5 minutes'
    ) INTO v_dup_exists;
    IF v_dup_exists THEN
        RETURN jsonb_build_object('ok', FALSE, 'error', 'duplicate_recent');
    END IF;

    -- 무결성 — 너무 짧은 시간(60초 미만)이면 무효 처리
    IF p_completion_seconds IS NOT NULL AND p_completion_seconds < 60 THEN
        v_is_valid := FALSE;
    END IF;

    -- 응답 INSERT
    INSERT INTO public.external_survey_responses (
        token_id, survey_id,
        respondent_name, respondent_age, respondent_gender, respondent_region,
        answers, integrity_score, completion_seconds, is_valid,
        ip_address, user_agent
    ) VALUES (
        v_tok.id, v_tok.survey_id,
        TRIM(p_respondent_name), p_respondent_age, p_respondent_gender, p_respondent_region,
        p_answers, p_integrity_score, p_completion_seconds, v_is_valid,
        p_ip, p_user_agent
    )
    RETURNING id INTO v_response_id;

    -- 유효 응답만 카운트 증가
    -- (v17_018 트리거가 response_count UPDATE 감지 → 임계값 도달 시 인증서 자동 발급)
    IF v_is_valid THEN
        UPDATE public.student_survey_tokens
           SET response_count = response_count + 1,
               last_response_at = NOW()
         WHERE id = v_tok.id;
    END IF;

    RETURN jsonb_build_object(
        'ok', TRUE,
        'response_id', v_response_id,
        'is_valid', v_is_valid,
        'new_count', (SELECT response_count FROM public.student_survey_tokens
                       WHERE id = v_tok.id)
    );
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 4. anon 권한 부여
-- ─────────────────────────────────────────────────────────────
-- anon role이 위 두 함수만 호출할 수 있도록 GRANT (테이블 직접 접근은 X)
GRANT EXECUTE ON FUNCTION public.get_survey_by_token(TEXT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.submit_external_response(
    TEXT, TEXT, INT, TEXT, TEXT, JSONB, INT, INT, TEXT, TEXT
) TO anon, authenticated;

-- 테이블 자체에는 anon RLS 차단 (함수만 SECURITY DEFINER로 우회)
ALTER TABLE public.external_survey_responses ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Admin full access" ON public.external_survey_responses;
CREATE POLICY "Admin full access"
    ON public.external_survey_responses
    FOR ALL
    TO service_role, authenticated
    USING (TRUE)
    WITH CHECK (TRUE);


-- ─────────────────────────────────────────────────────────────
-- 5. 응답 집계 함수 (학생 본부 admin용)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_external_response_stats(p_student_id UUID)
RETURNS TABLE (
    total_responses INT,
    valid_responses INT,
    male_n INT, female_n INT, other_n INT,
    avg_age NUMERIC,
    last_response_at TIMESTAMPTZ
) LANGUAGE SQL STABLE AS $$
    SELECT
        COUNT(*)::INT                                           AS total_responses,
        COUNT(*) FILTER (WHERE is_valid)::INT                   AS valid_responses,
        COUNT(*) FILTER (WHERE respondent_gender='male')::INT   AS male_n,
        COUNT(*) FILTER (WHERE respondent_gender='female')::INT AS female_n,
        COUNT(*) FILTER (WHERE respondent_gender NOT IN ('male','female')
                          OR respondent_gender IS NULL)::INT    AS other_n,
        ROUND(AVG(respondent_age) FILTER (WHERE respondent_age IS NOT NULL), 1) AS avg_age,
        MAX(submitted_at)                                       AS last_response_at
      FROM public.external_survey_responses esr
      JOIN public.student_survey_tokens t ON t.id = esr.token_id
     WHERE t.student_id = p_student_id;
$$;
GRANT EXECUTE ON FUNCTION public.get_external_response_stats(UUID)
    TO anon, authenticated;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'external_survey_responses' AS tbl, COUNT(*) AS rows
  FROM public.external_survey_responses;
-- 기대: 0행

SELECT routine_name FROM information_schema.routines
 WHERE routine_schema='public'
   AND routine_name IN (
       'get_survey_by_token',
       'submit_external_response',
       'get_external_response_stats')
 ORDER BY routine_name;
-- 기대: 3행

-- 끝.
