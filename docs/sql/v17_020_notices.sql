-- ============================================================
-- DragonEyes v1.7 — Phase 10 추가 (020)
-- 공지 시스템 (Notices) — 사용자 그룹별 공지 + 이메일 큐 (나중 발송)
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   본부 admin / 학교 admin이 공지를 작성·발송하면 사용자 그룹별로 노출.
--   카테고리:
--     content_update      — 새 교육 컨텐츠 업데이트
--     survey_deadline     — 설문 마감/봉사점수 안내
--     lecture_invitation  — 외부강사 강연 초청 (특정 학교 선정)
--     satisfaction        — 만족도 조사 발송 안내
--     general             — 일반 공지
--   대상:
--     audience_group = student | parent | institution_admin | all
--     + specific_institutions (학교 단위 추가 필터)
--   이메일:
--     notice_email_queue 에 INSERT 만 해두고 실제 발송은 추후 워커가 처리
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. notices — 공지 마스터
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.notices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    category        TEXT NOT NULL DEFAULT 'general'
        CHECK (category IN (
            'content_update','survey_deadline','lecture_invitation',
            'satisfaction','general'
        )),

    title           TEXT NOT NULL,
    body_md         TEXT NOT NULL,                          -- Markdown 본문

    -- 대상 그룹
    audience_group  TEXT NOT NULL DEFAULT 'all'
        CHECK (audience_group IN (
            'student','parent','institution_admin','all'
        )),

    -- 특정 학교만 대상으로 할 때 TRUE (외부강사 강연 초청 등)
    is_targeted     BOOLEAN NOT NULL DEFAULT FALSE,

    -- 발행
    priority        SMALLINT NOT NULL DEFAULT 0,            -- 0=일반, 1=중요, 2=긴급
    published_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,                            -- 만료 (null=영구)
    pinned          BOOLEAN NOT NULL DEFAULT FALSE,         -- 상단 고정

    -- 마감/CTA
    action_url      TEXT,                                   -- '바로가기' 링크 (선택)
    action_label    TEXT,                                   -- 버튼 텍스트 (예: '설문 응시하기')
    deadline_at     TIMESTAMPTZ,                            -- 마감 (설문/조사 등)

    -- 발송자
    created_by      UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_by_inst UUID REFERENCES public.institutions(id) ON DELETE SET NULL,

    -- 첨부
    attachment_url  TEXT,                                   -- Supabase Storage URL

    -- 상태
    status          TEXT NOT NULL DEFAULT 'published'
        CHECK (status IN ('draft','published','archived')),

    -- 이메일 발송 여부
    send_email      BOOLEAN NOT NULL DEFAULT TRUE,
    email_queued_at TIMESTAMPTZ,                            -- 큐 INSERT 시각

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notices_published ON public.notices(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_notices_audience  ON public.notices(audience_group);
CREATE INDEX IF NOT EXISTS idx_notices_category  ON public.notices(category);
CREATE INDEX IF NOT EXISTS idx_notices_status    ON public.notices(status);
CREATE INDEX IF NOT EXISTS idx_notices_pinned    ON public.notices(pinned) WHERE pinned = TRUE;


-- ─────────────────────────────────────────────────────────────
-- 2. notice_institution_targets — 특정 기관 대상 공지
-- ─────────────────────────────────────────────────────────────
-- is_targeted=TRUE 인 공지의 대상 학교 list (외부강사 강연 선정 학교 등)
CREATE TABLE IF NOT EXISTS public.notice_institution_targets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notice_id       UUID NOT NULL REFERENCES public.notices(id) ON DELETE CASCADE,
    institution_id  UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (notice_id, institution_id)
);

CREATE INDEX IF NOT EXISTS idx_nit_notice ON public.notice_institution_targets(notice_id);
CREATE INDEX IF NOT EXISTS idx_nit_inst   ON public.notice_institution_targets(institution_id);


-- ─────────────────────────────────────────────────────────────
-- 3. notice_reads — 사용자별 읽음 기록
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.notice_reads (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notice_id   UUID NOT NULL REFERENCES public.notices(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    read_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (notice_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_nr_user   ON public.notice_reads(user_id);
CREATE INDEX IF NOT EXISTS idx_nr_notice ON public.notice_reads(notice_id);


-- ─────────────────────────────────────────────────────────────
-- 4. notice_email_queue — 이메일 발송 큐 (나중에 워커가 처리)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.notice_email_queue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notice_id       UUID NOT NULL REFERENCES public.notices(id) ON DELETE CASCADE,
    recipient_user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    recipient_email TEXT NOT NULL,
    recipient_name  TEXT,

    subject         TEXT NOT NULL,
    body_html       TEXT,                                   -- 변환된 HTML 본문
    body_text       TEXT,                                   -- 변환된 plain text

    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','sending','sent','failed','skipped')),
    attempt_count   INT NOT NULL DEFAULT 0,
    last_error      TEXT,
    sent_at         TIMESTAMPTZ,
    scheduled_for   TIMESTAMPTZ NOT NULL DEFAULT NOW(),     -- 예약 발송 가능

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_neq_status        ON public.notice_email_queue(status);
CREATE INDEX IF NOT EXISTS idx_neq_scheduled     ON public.notice_email_queue(scheduled_for)
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_neq_notice        ON public.notice_email_queue(notice_id);
CREATE INDEX IF NOT EXISTS idx_neq_recipient     ON public.notice_email_queue(recipient_user_id);


-- ─────────────────────────────────────────────────────────────
-- 5. 트리거 (updated_at)
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_notices_updated_at ON public.notices;
CREATE TRIGGER trg_notices_updated_at
    BEFORE UPDATE ON public.notices
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_neq_updated_at ON public.notice_email_queue;
CREATE TRIGGER trg_neq_updated_at
    BEFORE UPDATE ON public.notice_email_queue
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 6. 공지 대상자 후보 list 함수 (이메일 큐 INSERT 시 사용)
-- ─────────────────────────────────────────────────────────────
-- audience_group + is_targeted + notice_institution_targets 를 종합해 대상자 user list
CREATE OR REPLACE FUNCTION public.get_notice_recipients(p_notice_id UUID)
RETURNS TABLE (
    user_id    UUID,
    email      TEXT,
    name       TEXT,
    role_v2    TEXT,
    institution_id UUID
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_audience    TEXT;
    v_is_targeted BOOLEAN;
BEGIN
    SELECT audience_group, is_targeted
      INTO v_audience, v_is_targeted
      FROM public.notices
     WHERE id = p_notice_id;

    IF v_audience IS NULL THEN RETURN; END IF;

    -- 특정 기관 대상 (is_targeted=TRUE)
    IF v_is_targeted THEN
        RETURN QUERY
        SELECT u.id, u.email, u.name, u.role_v2, u.institution_id
          FROM public.users u
          JOIN public.notice_institution_targets nit
            ON nit.institution_id = u.institution_id
         WHERE nit.notice_id = p_notice_id
           AND u.deleted_at IS NULL
           AND u.email IS NOT NULL
           AND (
                v_audience = 'all'
                OR u.role_v2 = v_audience
                OR (v_audience = 'parent'    AND u.role_v2 = 'parent')
                OR (v_audience = 'student'   AND u.role_v2 = 'student')
                OR (v_audience = 'institution_admin' AND u.role_v2 = 'institution_admin')
           );
        RETURN;
    END IF;

    -- 전체 대상 (audience_group)
    IF v_audience = 'all' THEN
        RETURN QUERY
        SELECT u.id, u.email, u.name, u.role_v2, u.institution_id
          FROM public.users u
         WHERE u.deleted_at IS NULL
           AND u.email IS NOT NULL
           AND u.role_v2 IN ('student','parent','institution_admin');
    ELSE
        RETURN QUERY
        SELECT u.id, u.email, u.name, u.role_v2, u.institution_id
          FROM public.users u
         WHERE u.deleted_at IS NULL
           AND u.email IS NOT NULL
           AND u.role_v2 = v_audience;
    END IF;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 7. 공지 발행 시 이메일 큐 자동 적재 함수
-- ─────────────────────────────────────────────────────────────
-- notice 발행 (status='published') 후 호출 — 대상자 전원에게 이메일 큐 INSERT
-- send_email=TRUE 인 경우만. 중복 방지 (notice_id + recipient_user_id UNIQUE은 없으나 큐 자체 중복 체크)
CREATE OR REPLACE FUNCTION public.queue_notice_emails(p_notice_id UUID)
RETURNS INT LANGUAGE plpgsql AS $$
DECLARE
    v_notice      public.notices;
    v_inserted    INT := 0;
    v_html_body   TEXT;
    v_text_body   TEXT;
BEGIN
    SELECT * INTO v_notice FROM public.notices WHERE id = p_notice_id;
    IF v_notice IS NULL OR NOT v_notice.send_email OR v_notice.status <> 'published' THEN
        RETURN 0;
    END IF;

    -- 본문 (markdown은 일단 그대로 — 실제 발송 워커가 HTML로 변환)
    v_html_body := v_notice.body_md;
    v_text_body := v_notice.body_md;

    -- 이미 큐에 들어간 적 있으면 skip
    IF v_notice.email_queued_at IS NOT NULL THEN
        RETURN 0;
    END IF;

    INSERT INTO public.notice_email_queue (
        notice_id, recipient_user_id, recipient_email, recipient_name,
        subject, body_html, body_text, status
    )
    SELECT
        p_notice_id, r.user_id, r.email, r.name,
        '[드래곤아이즈 공지] ' || v_notice.title,
        v_html_body, v_text_body,
        'pending'
    FROM public.get_notice_recipients(p_notice_id) r
    WHERE r.email IS NOT NULL AND r.email <> '';

    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    UPDATE public.notices
       SET email_queued_at = NOW()
     WHERE id = p_notice_id;

    RETURN v_inserted;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 8. 사용자별 공지 목록 (페이지에서 사용)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_notices_for_user(p_user_id UUID)
RETURNS TABLE (
    notice_id     UUID,
    category      TEXT,
    title         TEXT,
    body_md       TEXT,
    priority      SMALLINT,
    pinned        BOOLEAN,
    published_at  TIMESTAMPTZ,
    expires_at    TIMESTAMPTZ,
    deadline_at   TIMESTAMPTZ,
    action_url    TEXT,
    action_label  TEXT,
    attachment_url TEXT,
    is_read       BOOLEAN,
    read_at       TIMESTAMPTZ,
    is_targeted   BOOLEAN
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_user public.users;
BEGIN
    SELECT * INTO v_user FROM public.users WHERE id = p_user_id;
    IF v_user IS NULL THEN RETURN; END IF;

    RETURN QUERY
    SELECT
        n.id, n.category, n.title, n.body_md, n.priority, n.pinned,
        n.published_at, n.expires_at, n.deadline_at,
        n.action_url, n.action_label, n.attachment_url,
        (nr.id IS NOT NULL) AS is_read,
        nr.read_at,
        n.is_targeted
    FROM public.notices n
    LEFT JOIN public.notice_reads nr
           ON nr.notice_id = n.id AND nr.user_id = p_user_id
    WHERE n.status = 'published'
      AND (n.expires_at IS NULL OR n.expires_at > NOW())
      AND (
        -- 전체 대상
        n.audience_group = 'all'
        OR n.audience_group = v_user.role_v2
      )
      AND (
        -- 일반 공지 OR 특정 기관 대상이고 본인 기관 포함
        NOT n.is_targeted
        OR EXISTS (
            SELECT 1 FROM public.notice_institution_targets nit
             WHERE nit.notice_id = n.id
               AND nit.institution_id = v_user.institution_id
        )
      )
    ORDER BY
        n.pinned DESC,
        n.priority DESC,
        n.published_at DESC;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 9. 미읽음 개수 (헤더 배지용)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_unread_notice_count(p_user_id UUID)
RETURNS INT LANGUAGE SQL STABLE AS $$
    SELECT COUNT(*)::INT
      FROM public.get_notices_for_user(p_user_id) n
     WHERE n.is_read = FALSE;
$$;


-- ─────────────────────────────────────────────────────────────
-- 10. 읽음 처리
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.mark_notice_read(p_notice_id UUID, p_user_id UUID)
RETURNS VOID LANGUAGE SQL AS $$
    INSERT INTO public.notice_reads (notice_id, user_id)
    VALUES (p_notice_id, p_user_id)
    ON CONFLICT (notice_id, user_id) DO NOTHING;
$$;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'notices' AS tbl, COUNT(*) AS rows FROM public.notices
UNION ALL
SELECT 'notice_institution_targets', COUNT(*) FROM public.notice_institution_targets
UNION ALL
SELECT 'notice_reads', COUNT(*) FROM public.notice_reads
UNION ALL
SELECT 'notice_email_queue', COUNT(*) FROM public.notice_email_queue;
-- 기대: 모두 rows=0

SELECT routine_name FROM information_schema.routines
 WHERE routine_schema='public'
   AND routine_name IN (
       'get_notice_recipients',
       'queue_notice_emails',
       'get_notices_for_user',
       'get_unread_notice_count',
       'mark_notice_read'
   )
 ORDER BY routine_name;
-- 기대: 5행

-- 끝.
