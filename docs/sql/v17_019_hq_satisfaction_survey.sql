-- ============================================================
-- DragonEyes v1.7 — Phase 10 추가 (019)
-- 본부 발송 만족도 조사 (드래곤아이즈 → 참여 학교)
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   드래곤아이즈 본부 admin이 캠페인에 참여한 학교(학생 1명 이상 등록)들에게
--   만족도 조사를 일괄 발송하고, 학교 담당자(institution_admin)가 응답.
--
--   설계:
--     - satisfaction_survey_templates: 본부가 관리하는 표준 문항 템플릿
--     - launch_hq_satisfaction_survey: 본부 admin 발송 함수
--       → 참여 학교 자동으로 satisfaction_targets에 INSERT
--     - get_pending_surveys_for_inst: 학교 admin 응답 대기 목록
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. satisfaction_survey_templates — 본부 표준 문항 템플릿
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.satisfaction_survey_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            TEXT UNIQUE NOT NULL,                -- 'default_v1' 등
    title           TEXT NOT NULL,
    description     TEXT,
    questions       JSONB NOT NULL,
    -- [{qno, qtype:'scale'|'single_choice'|'multi_choice'|'long_text',
    --   text, options:[...], required:true}]
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- 2. 기본 템플릿 SEED (10문항)
-- ─────────────────────────────────────────────────────────────
INSERT INTO public.satisfaction_survey_templates (code, title, description, questions, is_default)
VALUES (
    'default_v1',
    '드래곤아이즈 캠페인 만족도 조사',
    '온라인 유해컨텐츠 근절 캠페인 운영에 대한 학교 담당자 만족도 조사입니다.',
    '[
      {"qno":1,"qtype":"scale","text":"캠페인 운영 전반 만족도","options":[1,2,3,4,5],"required":true},
      {"qno":2,"qtype":"scale","text":"학습 자료(영상·PDF)의 학생 적합성","options":[1,2,3,4,5],"required":true},
      {"qno":3,"qtype":"scale","text":"설문 문항의 학년대 적정성","options":[1,2,3,4,5],"required":true},
      {"qno":4,"qtype":"scale","text":"외부 초청강사 강연 만족도 (해당시)","options":[1,2,3,4,5],"required":false},
      {"qno":5,"qtype":"scale","text":"봉사시간 인증서 발급 프로세스 편의성","options":[1,2,3,4,5],"required":true},
      {"qno":6,"qtype":"single_choice","text":"캠페인이 학생들의 온라인 안전 의식 향상에 기여했다고 느끼시나요?","options":["매우 그렇다","그렇다","보통","그렇지 않다","전혀 아니다"],"required":true},
      {"qno":7,"qtype":"multi_choice","text":"가장 유익했던 컨텐츠 (복수 선택)","options":["디지털 그루밍 예방","개인정보 보호","저작권 교육","사이버 폭력","유해 사이트 식별"],"required":false},
      {"qno":8,"qtype":"long_text","text":"개선이 필요한 점이 있다면 적어주세요.","required":false},
      {"qno":9,"qtype":"long_text","text":"추가로 필요한 컨텐츠/주제가 있다면?","required":false},
      {"qno":10,"qtype":"single_choice","text":"다음 학년도에도 이 캠페인을 계속 운영하시겠습니까?","options":["반드시 운영","가능하면 운영","미정","운영 안 함"],"required":true}
    ]'::JSONB,
    TRUE
)
ON CONFLICT (code) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 3. satisfaction_surveys 에 'launched_scope' = 'nation' 사용 확인
-- ─────────────────────────────────────────────────────────────
-- (이미 v17_015 에서 정의됨 — 본부 발송 시 'nation' 사용)


-- ─────────────────────────────────────────────────────────────
-- 4. 본부 admin 만족도 조사 발송 함수
-- ─────────────────────────────────────────────────────────────
-- 참여 학교 = 학생 1명 이상 등록된 학교
-- elementary/middle/high/special/youth_facility 만 대상
CREATE OR REPLACE FUNCTION public.launch_hq_satisfaction_survey(
    p_title       TEXT,
    p_description TEXT,
    p_round_number INT,
    p_deadline    TIMESTAMPTZ,
    p_questions   JSONB,
    p_launched_by UUID,
    p_campaign_id UUID DEFAULT NULL
) RETURNS TABLE (
    survey_id    UUID,
    target_count INT
) LANGUAGE plpgsql AS $$
DECLARE
    v_survey_id    UUID;
    v_target_count INT := 0;
BEGIN
    -- 1) satisfaction_surveys INSERT
    INSERT INTO public.satisfaction_surveys (
        campaign_id, title, description, round_number,
        deadline, questions,
        target_audience, launched_by, launched_inst_id, launched_scope,
        status
    ) VALUES (
        p_campaign_id, p_title, p_description, p_round_number,
        p_deadline, p_questions,
        'institution_admin', p_launched_by, NULL, 'nation',
        'active'
    ) RETURNING id INTO v_survey_id;

    -- 2) 참여 학교 자동 대상 INSERT
    --    학생이 1명 이상 등록된 학교 ('elementary'/'middle'/'high'/'special'/'youth_facility')
    WITH participating AS (
        SELECT DISTINCT u.institution_id
          FROM public.users u
          JOIN public.institutions i ON i.id = u.institution_id
         WHERE u.role_v2 = 'student'
           AND u.deleted_at IS NULL
           AND i.deleted_at IS NULL
           AND i.type IN ('elementary','middle','high','special','youth_facility')
    )
    INSERT INTO public.satisfaction_targets (survey_id, institution_id, status)
    SELECT v_survey_id, p.institution_id, 'pending'
      FROM participating p
    ON CONFLICT (survey_id, institution_id) DO NOTHING;

    GET DIAGNOSTICS v_target_count = ROW_COUNT;

    survey_id := v_survey_id;
    target_count := v_target_count;
    RETURN NEXT;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 5. 학교 admin 응답 대기 list
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_pending_surveys_for_inst(p_inst_id UUID)
RETURNS TABLE (
    target_id        UUID,
    survey_id        UUID,
    title            TEXT,
    description      TEXT,
    round_number     INT,
    deadline         TIMESTAMPTZ,
    questions        JSONB,
    status           TEXT,
    submitted_at     TIMESTAMPTZ,
    response_data    JSONB
) LANGUAGE SQL STABLE AS $$
    SELECT
        st.id              AS target_id,
        ss.id              AS survey_id,
        ss.title, ss.description, ss.round_number,
        ss.deadline, ss.questions,
        st.status, st.submitted_at, st.response_data
    FROM public.satisfaction_targets st
    JOIN public.satisfaction_surveys ss ON ss.id = st.survey_id
    WHERE st.institution_id = p_inst_id
      AND ss.status = 'active'
      AND ss.launched_scope = 'nation'
    ORDER BY
        CASE WHEN st.status = 'pending' THEN 0 ELSE 1 END,
        ss.deadline ASC NULLS LAST,
        ss.created_at DESC;
$$;


-- ─────────────────────────────────────────────────────────────
-- 6. 응답 저장 함수 (학교 admin)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.submit_satisfaction_response(
    p_target_id      UUID,
    p_respondent_id  UUID,
    p_response_data  JSONB
) RETURNS BOOLEAN LANGUAGE plpgsql AS $$
BEGIN
    UPDATE public.satisfaction_targets
       SET response_data      = p_response_data,
           respondent_user_id = p_respondent_id,
           submitted_at       = NOW(),
           status             = 'completed'
     WHERE id = p_target_id
       AND status <> 'completed';
    RETURN FOUND;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 7. 본부 발송 조사 응답 집계
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_hq_survey_summary(p_survey_id UUID)
RETURNS TABLE (
    total_targets INT,
    completed     INT,
    pending       INT,
    overdue       INT,
    completion_rate NUMERIC
) LANGUAGE SQL STABLE AS $$
    SELECT
        COUNT(*)::INT                                             AS total_targets,
        COUNT(*) FILTER (WHERE status = 'completed')::INT         AS completed,
        COUNT(*) FILTER (WHERE status = 'pending')::INT           AS pending,
        COUNT(*) FILTER (WHERE status = 'overdue')::INT           AS overdue,
        CASE WHEN COUNT(*) > 0
            THEN ROUND(COUNT(*) FILTER (WHERE status = 'completed')::NUMERIC / COUNT(*) * 100, 1)
            ELSE 0
        END AS completion_rate
    FROM public.satisfaction_targets
    WHERE survey_id = p_survey_id;
$$;


-- ─────────────────────────────────────────────────────────────
-- 8. 본부 발송 응답 raw data (분석용)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_hq_survey_responses(p_survey_id UUID)
RETURNS TABLE (
    target_id      UUID,
    institution_id UUID,
    institution_name TEXT,
    region         TEXT,
    district       TEXT,
    submitted_at   TIMESTAMPTZ,
    response_data  JSONB,
    respondent_name TEXT
) LANGUAGE SQL STABLE AS $$
    SELECT
        st.id, st.institution_id,
        i.name AS institution_name,
        i.region, i.district,
        st.submitted_at, st.response_data,
        u.name AS respondent_name
    FROM public.satisfaction_targets st
    JOIN public.institutions i ON i.id = st.institution_id
    LEFT JOIN public.users u   ON u.id = st.respondent_user_id
    WHERE st.survey_id = p_survey_id
    ORDER BY i.region, i.district, i.name;
$$;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'satisfaction_survey_templates' AS tbl, COUNT(*) AS rows
  FROM public.satisfaction_survey_templates;
-- 기대: 1행 (default_v1)

SELECT routine_name FROM information_schema.routines
 WHERE routine_schema='public'
   AND routine_name IN (
       'launch_hq_satisfaction_survey',
       'get_pending_surveys_for_inst',
       'submit_satisfaction_response',
       'get_hq_survey_summary',
       'get_hq_survey_responses'
   )
 ORDER BY routine_name;
-- 기대: 5행

SELECT code, title, jsonb_array_length(questions) AS qcount, is_default
  FROM public.satisfaction_survey_templates;
-- 기대: default_v1 | ... | 10 | true

-- 끝.
