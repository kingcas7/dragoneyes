-- ============================================================
-- DragonEyes v1.7 — 캠페인 시스템 Phase 7+8 Step A (009)
-- 학생 설문 token + 캠페인 overview content + 학년 매칭 보강
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   1) 학생별 영구 access_token 발급 (개인 식별 가능 링크/QR)
--      → 학부모/학생 본인이 배포해서 응답자가 접속 → 그 학생의 봉사 점수에 반영
--   2) 캠페인 안내 컨텐츠 (학생/학부모용) — 관리자 수정 가능
--   3) surveys.target_band 컬럼 — 초/중/고 단계 명시
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. surveys.target_band — 학년대 (초/중/고) 매칭 단순화
-- ─────────────────────────────────────────────────────────────
ALTER TABLE public.surveys
    ADD COLUMN IF NOT EXISTS target_band TEXT
        CHECK (target_band IN ('elementary', 'middle', 'high', 'all'));

CREATE INDEX IF NOT EXISTS idx_surveys_target_band
    ON public.surveys(target_band) WHERE target_band IS NOT NULL;


-- ─────────────────────────────────────────────────────────────
-- 2. student_survey_tokens — 학생별 영구 설문 토큰
-- ─────────────────────────────────────────────────────────────
-- 학생 1명 + 설문 1개 = 토큰 1개 (UNIQUE).
-- 학생이 캠페인 가입하면 학년대 매칭된 설문에 대해 자동 발급.
-- QR code는 application 측에서 access_token을 인코딩해 생성.
-- 응답자가 token으로 접속 → survey_responses 생성 시 access_token 기록.
CREATE TABLE IF NOT EXISTS public.student_survey_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL,                      -- users.id
    survey_id       UUID NOT NULL REFERENCES public.surveys(id) ON DELETE CASCADE,

    access_token    TEXT NOT NULL UNIQUE
                        DEFAULT replace(gen_random_uuid()::text, '-', ''),
    qr_data_url     TEXT,                               -- base64 PNG (선택 캐시)

    issued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ,                        -- 무효화 시
    revoked_reason  TEXT,

    -- 응답 수집 통계 (캐시 — 비싼 join 우회)
    response_count  INT NOT NULL DEFAULT 0,
    last_response_at TIMESTAMPTZ,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (student_id, survey_id),
    CONSTRAINT sst_student_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sst_student ON public.student_survey_tokens(student_id);
CREATE INDEX IF NOT EXISTS idx_sst_survey  ON public.student_survey_tokens(survey_id);
CREATE INDEX IF NOT EXISTS idx_sst_token   ON public.student_survey_tokens(access_token);


-- ─────────────────────────────────────────────────────────────
-- 3. campaign_overview_content — 캠페인 안내 컨텐츠 (관리자 수정 가능)
-- ─────────────────────────────────────────────────────────────
-- 학생/학부모 페이지에 표시되는 캠페인 소개·취지·진행 순서·학부모 토론 가이드 등
-- 관리자 (본부 admin) 가 수정·추가·삭제 가능.
CREATE TABLE IF NOT EXISTS public.campaign_overview_content (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audience        TEXT NOT NULL CHECK (audience IN ('student', 'parent', 'institution', 'all')),
    section_key     TEXT NOT NULL,                      -- 'intro', 'purpose', 'benefits', 'steps', 'parent_discussion', 'closing'
    title           TEXT,
    body_md         TEXT NOT NULL,                      -- markdown 본문
    sort_order      INT NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,

    updated_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (audience, section_key)
);

CREATE INDEX IF NOT EXISTS idx_coc_audience ON public.campaign_overview_content(audience, sort_order) WHERE is_active;


-- ─────────────────────────────────────────────────────────────
-- 4. 학생 → 학년대(band) 판정 함수
-- ─────────────────────────────────────────────────────────────
-- institution.type 우선, 없으면 users.grade 기반 추정.
--   초등(elementary): grade 1~6
--   중등(middle):     grade 7~9 또는 institution.type='middle' + grade 1~3
--   고등(high):       grade 10~12 또는 institution.type='high' + grade 1~3
CREATE OR REPLACE FUNCTION public.get_student_band(p_student_id UUID)
RETURNS TEXT LANGUAGE SQL STABLE AS $$
    SELECT COALESCE(
        -- 1순위: 소속 기관 type
        CASE
            WHEN inst.type = 'elementary' THEN 'elementary'
            WHEN inst.type = 'middle'     THEN 'middle'
            WHEN inst.type = 'high'       THEN 'high'
        END,
        -- 2순위: users.grade 추정
        CASE
            WHEN u.grade BETWEEN 1  AND 6  THEN 'elementary'
            WHEN u.grade BETWEEN 7  AND 9  THEN 'middle'
            WHEN u.grade BETWEEN 10 AND 12 THEN 'high'
        END
    )
    FROM public.users u
    LEFT JOIN public.institutions inst ON inst.id = u.institution_id
    WHERE u.id = p_student_id;
$$;


-- ─────────────────────────────────────────────────────────────
-- 5. 학생 가입 시 자동으로 학년대 매칭 설문 token 발급
-- ─────────────────────────────────────────────────────────────
-- trigger: users INSERT/UPDATE → role_v2='student'인 경우 자동 token 발급
CREATE OR REPLACE FUNCTION public._auto_issue_student_survey_token() RETURNS TRIGGER AS $$
DECLARE
    v_band TEXT;
    v_survey_id UUID;
BEGIN
    -- 학생만 대상
    IF NEW.role_v2 IS DISTINCT FROM 'student' THEN
        RETURN NEW;
    END IF;

    -- 학년대 판정
    v_band := public.get_student_band(NEW.id);
    IF v_band IS NULL THEN
        RETURN NEW;
    END IF;

    -- 학년대 매칭 active 설문 찾기 (national + scope)
    SELECT s.id INTO v_survey_id
    FROM public.surveys s
    WHERE s.status = 'active'
      AND s.scope  = 'national'
      AND s.target_band IN (v_band, 'all')
    ORDER BY s.published_at DESC NULLS LAST
    LIMIT 1;

    IF v_survey_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- 토큰 발급 (중복 무시)
    INSERT INTO public.student_survey_tokens (student_id, survey_id)
    VALUES (NEW.id, v_survey_id)
    ON CONFLICT (student_id, survey_id) DO NOTHING;

    RETURN NEW;
END$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_auto_survey_token ON public.users;
CREATE TRIGGER trg_user_auto_survey_token
    AFTER INSERT OR UPDATE OF role_v2, institution_id, grade ON public.users
    FOR EACH ROW EXECUTE FUNCTION public._auto_issue_student_survey_token();


-- ─────────────────────────────────────────────────────────────
-- 6. 학생 설문 응답 완료 시 봉사 점수 자동 발급 트리거
-- ─────────────────────────────────────────────────────────────
-- survey_responses.status가 'completed'로 변경되면
-- volunteer_credits에 자동 INSERT (성실도 통과 시).
CREATE OR REPLACE FUNCTION public._auto_issue_volunteer_on_complete() RETURNS TRIGGER AS $$
DECLARE
    v_survey RECORD;
    v_hours NUMERIC(4,2);
BEGIN
    -- completed로 전환되는 순간만
    IF NEW.status <> 'completed' OR OLD.status = 'completed' THEN
        RETURN NEW;
    END IF;

    -- 설문 메타 조회
    SELECT * INTO v_survey FROM public.surveys WHERE id = NEW.survey_id;
    IF v_survey IS NULL THEN
        RETURN NEW;
    END IF;

    -- 성실도 통과 여부
    IF NEW.integrity_score IS NULL OR NEW.integrity_score < v_survey.pass_integrity_score THEN
        RETURN NEW;
    END IF;

    -- 봉사 시간 (분 → 시간)
    v_hours := v_survey.target_minutes / 60.0;

    -- 봉사 점수 INSERT (응답당 1건 UNIQUE 보장)
    INSERT INTO public.volunteer_credits (
        student_id, response_id, survey_id, institution_id,
        hours_decimal, integrity_score, status, earned_at
    )
    SELECT
        NEW.student_id, NEW.id, NEW.survey_id,
        (SELECT institution_id FROM public.users WHERE id = NEW.student_id),
        v_hours, NEW.integrity_score, 'earned', NOW()
    ON CONFLICT (response_id) DO NOTHING;

    -- 학생 토큰 stats 업데이트
    UPDATE public.student_survey_tokens
    SET response_count = response_count + 1,
        last_response_at = NOW()
    WHERE student_id = NEW.student_id AND survey_id = NEW.survey_id;

    RETURN NEW;
END$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_response_complete_volunteer ON public.survey_responses;
CREATE TRIGGER trg_response_complete_volunteer
    AFTER UPDATE OF status ON public.survey_responses
    FOR EACH ROW EXECUTE FUNCTION public._auto_issue_volunteer_on_complete();


-- ─────────────────────────────────────────────────────────────
-- 7. 문항별 답변 통계 조회 함수 (학생/관리자/교육기관용)
-- ─────────────────────────────────────────────────────────────
-- 설문 1건의 모든 문항에 대한 응답 분포 반환.
-- single_choice / multi_choice 는 option별 count, scale은 점수별 count.
CREATE OR REPLACE FUNCTION public.get_survey_answer_stats(p_survey_id UUID)
RETURNS TABLE (
    question_id UUID,
    qno INT,
    qtype TEXT,
    answer_value TEXT,
    answer_count BIGINT
) LANGUAGE SQL STABLE AS $$
    SELECT
        q.id AS question_id,
        q.qno,
        q.qtype,
        ans.answer_value::TEXT,
        COUNT(*) AS answer_count
    FROM public.survey_questions q
    LEFT JOIN public.survey_answers a ON a.question_id = q.id
    LEFT JOIN public.survey_responses r ON r.id = a.response_id AND r.status = 'completed'
    LEFT JOIN LATERAL (
        -- single_choice / scale / yes_no 등은 단일 값, multi_choice는 array 펼침
        SELECT jsonb_array_elements_text(
            CASE
                WHEN jsonb_typeof(a.answer) = 'array' THEN a.answer
                ELSE jsonb_build_array(a.answer)
            END
        ) AS answer_value
    ) ans ON a.answer IS NOT NULL
    WHERE q.survey_id = p_survey_id
    GROUP BY q.id, q.qno, q.qtype, ans.answer_value
    ORDER BY q.qno, ans.answer_value;
$$;


-- ─────────────────────────────────────────────────────────────
-- 트리거 (updated_at)
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_sst_updated_at ON public.student_survey_tokens;
CREATE TRIGGER trg_sst_updated_at
    BEFORE UPDATE ON public.student_survey_tokens
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_coc_updated_at ON public.campaign_overview_content;
CREATE TRIGGER trg_coc_updated_at
    BEFORE UPDATE ON public.campaign_overview_content
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'student_survey_tokens'     AS tbl, COUNT(*) AS rows FROM public.student_survey_tokens
UNION ALL
SELECT 'campaign_overview_content' AS tbl, COUNT(*) FROM public.campaign_overview_content;
-- 기대: 두 행 모두 rows=0

-- 함수 확인
SELECT routine_name FROM information_schema.routines
WHERE routine_schema='public'
  AND routine_name IN (
      'get_student_band',
      '_auto_issue_student_survey_token',
      '_auto_issue_volunteer_on_complete',
      'get_survey_answer_stats'
  )
ORDER BY routine_name;
-- 기대: 4개 행

-- 끝.
