-- ============================================================
-- DragonEyes v1.7 — Phase 10 추가 (022)
-- 구독 라이프사이클: 약관 동의 + 만료 알림 + 자동갱신 + 갱신 이력
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   학부모 결제 프로토콜 완성:
--     - 약관 동의 기록 (이용약관·환불약관·자동갱신 동의)
--     - 구독 만료 30/7일 전 자동 공지 발송
--     - 자동갱신 ON/OFF (현재는 알림만, 빌링키는 추후)
--     - 갱신·해지·환불 이력 로그
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. parent_subscriptions 컬럼 보강
-- ─────────────────────────────────────────────────────────────
ALTER TABLE public.parent_subscriptions
    ADD COLUMN IF NOT EXISTS auto_renewal_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE public.parent_subscriptions
    ADD COLUMN IF NOT EXISTS tos_version TEXT;
ALTER TABLE public.parent_subscriptions
    ADD COLUMN IF NOT EXISTS tos_agreed_at TIMESTAMPTZ;
ALTER TABLE public.parent_subscriptions
    ADD COLUMN IF NOT EXISTS refund_tos_version TEXT;
ALTER TABLE public.parent_subscriptions
    ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE public.parent_subscriptions
    ADD COLUMN IF NOT EXISTS cancel_reason TEXT;
ALTER TABLE public.parent_subscriptions
    ADD COLUMN IF NOT EXISTS notified_d30_at TIMESTAMPTZ;
ALTER TABLE public.parent_subscriptions
    ADD COLUMN IF NOT EXISTS notified_d7_at TIMESTAMPTZ;


-- ─────────────────────────────────────────────────────────────
-- 2. terms_of_service_versions — 약관 버전 관리
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.terms_of_service_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind            TEXT NOT NULL CHECK (kind IN ('service','refund','privacy','auto_renewal')),
    version         TEXT NOT NULL,                        -- e.g. '2026-06-20'
    title           TEXT NOT NULL,
    body_md         TEXT NOT NULL,                        -- Markdown 본문
    effective_from  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (kind, version)
);

CREATE INDEX IF NOT EXISTS idx_tos_kind_active
    ON public.terms_of_service_versions(kind, is_active);

-- 초기 SEED — 기본 약관 4종 (v2026-06-20)
INSERT INTO public.terms_of_service_versions (kind, version, title, body_md, is_active)
VALUES
('service','2026-06-20','드래곤아이즈 캠페인 이용약관',
'### 제1조 (목적)
본 약관은 (주)드래곤아이즈가 운영하는 **온라인 유해컨텐츠 근절 캠페인** 서비스의 이용 조건을 규정합니다.

### 제2조 (서비스 내용)
- 유료 학습 자료 (영상·PDF) 열람
- 자녀 설문 결과 모니터링
- 봉사활동 인증서 발급 자료 활용
- 캠페인 공지·만족도 조사 참여

### 제3조 (이용료)
- 연 17,000원, 결제일 ~ 동년 12월 31일까지 유효
- 결제 즉시 활성화', TRUE),

('refund','2026-06-20','환불 정책',
'### 환불 가능 기간
- **결제 후 7일 이내**: 자료 열람 전이면 전액 환불
- **자료 열람 시작 후**: 사용한 자료 비율에 따라 부분 환불 가능
- **6개월 경과**: 환불 불가

### 신청 방법
- 학부모 dashboard → 결제 내역 → "환불 요청" 버튼
- 본부 admin 검토 후 영업일 5일 이내 처리
- 결제 PG사로부터 카드 매입 취소 (카드 결제) 또는 계좌 환급

### 환불 제외 사유
- 본인 사정으로 인한 미사용
- 회원 정보 부정 사용으로 인한 정지', TRUE),

('privacy','2026-06-20','개인정보 처리방침',
'### 수집 항목
- 이메일, 이름, 휴대폰 (선택)
- 결제 정보 (PG사를 통한 처리)
- 자녀와의 가족관계 인증 자료

### 이용 목적
- 캠페인 서비스 제공
- 결제·환불 처리
- 자녀 학습 모니터링

### 보유 기간
- 회원 탈퇴 시 즉시 파기
- 결제 정보는 법정 보존 기간(5년)까지 보관', TRUE),

('auto_renewal','2026-06-20','자동갱신 약관',
'### 자동갱신 동의
- 매년 12월 1일에 다음 해 구독 (17,000원)이 자동 갱신됩니다
- 갱신 30일/7일 전에 공지로 안내됩니다

### 해지
- 갱신일 1일 전까지 자동갱신 OFF 시 다음 연도 갱신 안 됨
- 학부모 dashboard에서 언제든 토글 가능

### 결제 수단
- 최초 결제 시 사용한 카드의 결제 토큰(빌링키)을 PG사가 보관
- 변경 시 신규 결제 필요', TRUE)
ON CONFLICT (kind, version) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 3. subscription_renewal_log — 갱신·해지·환불 이력
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.subscription_renewal_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id       UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES public.parent_subscriptions(id) ON DELETE SET NULL,
    event_type      TEXT NOT NULL
        CHECK (event_type IN ('created','renewed','cancelled','expired',
                              'refunded','auto_renew_on','auto_renew_off',
                              'notified_d30','notified_d7')),
    from_year       INT,
    to_year         INT,
    amount          INT,
    note            TEXT,
    actor_user_id   UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_srl_parent ON public.subscription_renewal_log(parent_id);
CREATE INDEX IF NOT EXISTS idx_srl_event  ON public.subscription_renewal_log(event_type);


-- ─────────────────────────────────────────────────────────────
-- 4. 약관 조회 함수
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_active_terms()
RETURNS TABLE (
    kind TEXT, version TEXT, title TEXT, body_md TEXT, effective_from TIMESTAMPTZ
) LANGUAGE SQL STABLE AS $$
    SELECT DISTINCT ON (kind) kind, version, title, body_md, effective_from
      FROM public.terms_of_service_versions
     WHERE is_active = TRUE
     ORDER BY kind, effective_from DESC;
$$;


-- ─────────────────────────────────────────────────────────────
-- 5. 자동갱신 토글 + 이력 기록
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.toggle_auto_renewal(
    p_subscription_id UUID,
    p_enable          BOOLEAN,
    p_actor_id        UUID
) RETURNS BOOLEAN LANGUAGE plpgsql AS $$
DECLARE
    v_sub public.parent_subscriptions;
BEGIN
    SELECT * INTO v_sub FROM public.parent_subscriptions WHERE id = p_subscription_id;
    IF NOT FOUND THEN RETURN FALSE; END IF;

    UPDATE public.parent_subscriptions
       SET auto_renewal_enabled = p_enable,
           updated_at = NOW()
     WHERE id = p_subscription_id;

    INSERT INTO public.subscription_renewal_log (
        parent_id, subscription_id, event_type, from_year, to_year, actor_user_id
    ) VALUES (
        v_sub.parent_id, p_subscription_id,
        CASE WHEN p_enable THEN 'auto_renew_on' ELSE 'auto_renew_off' END,
        v_sub.year, v_sub.year, p_actor_id
    );

    RETURN TRUE;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 6. 만료 임박 구독 알림 — D-30 / D-7 자동 공지 INSERT
-- ─────────────────────────────────────────────────────────────
-- (스케줄러/Edge function에서 매일 호출 가정)
-- 각 만료 임박 구독 학부모에게 개별 공지 INSERT — is_targeted=FALSE, audience=parent
-- 중복 방지: notified_d30_at / notified_d7_at 컬럼 사용
CREATE OR REPLACE FUNCTION public.notify_expiring_subscriptions()
RETURNS TABLE (
    notice_id      UUID,
    parent_id      UUID,
    subscription_id UUID,
    days_left      INT
) LANGUAGE plpgsql AS $$
DECLARE
    r RECORD;
    v_notice_id UUID;
    v_days_left INT;
    v_title TEXT;
    v_body TEXT;
BEGIN
    -- D-30
    FOR r IN
        SELECT ps.id AS sub_id, ps.parent_id, ps.year, ps.end_date,
               u.name AS pname, u.email
          FROM public.parent_subscriptions ps
          JOIN public.users u ON u.id = ps.parent_id
         WHERE ps.status = 'active'
           AND ps.notified_d30_at IS NULL
           AND ps.end_date BETWEEN CURRENT_DATE + INTERVAL '29 days'
                               AND CURRENT_DATE + INTERVAL '31 days'
    LOOP
        v_days_left := 30;
        v_title := format('%s년 구독 만료 30일 전 안내', r.year);
        v_body := format(
'%s님, 안녕하세요.

올해 드래곤아이즈 캠페인 구독이 **30일 후 (%s)** 만료될 예정입니다.

자녀의 학습 자료 열람을 계속하시려면 만료 전 갱신해주세요.

- 구독 만료일: %s
- 갱신 금액: 17,000원 / 연

학부모 dashboard → 결제·구독 탭에서 갱신 가능합니다.', r.pname, r.end_date, r.end_date);

        INSERT INTO public.notices (
            category, title, body_md, audience_group, is_targeted,
            priority, status, send_email,
            action_label, action_url, deadline_at
        ) VALUES (
            'survey_deadline', v_title, v_body, 'parent', FALSE,
            1, 'published', TRUE,
            '🔄 갱신하기',
            '/?page=parent_dashboard&tab=payment',
            r.end_date::TIMESTAMPTZ
        ) RETURNING id INTO v_notice_id;

        UPDATE public.parent_subscriptions
           SET notified_d30_at = NOW()
         WHERE id = r.sub_id;

        INSERT INTO public.subscription_renewal_log (
            parent_id, subscription_id, event_type, from_year, to_year, note
        ) VALUES (
            r.parent_id, r.sub_id, 'notified_d30', r.year, r.year, v_title
        );

        notice_id := v_notice_id;
        parent_id := r.parent_id;
        subscription_id := r.sub_id;
        days_left := v_days_left;
        RETURN NEXT;
    END LOOP;

    -- D-7
    FOR r IN
        SELECT ps.id AS sub_id, ps.parent_id, ps.year, ps.end_date,
               u.name AS pname, u.email
          FROM public.parent_subscriptions ps
          JOIN public.users u ON u.id = ps.parent_id
         WHERE ps.status = 'active'
           AND ps.notified_d7_at IS NULL
           AND ps.end_date BETWEEN CURRENT_DATE + INTERVAL '6 days'
                               AND CURRENT_DATE + INTERVAL '8 days'
    LOOP
        v_days_left := 7;
        v_title := format('🚨 %s년 구독 만료 7일 전 — 갱신 안내', r.year);
        v_body := format(
'%s님, **마지막 안내**입니다.

올해 드래곤아이즈 캠페인 구독이 **7일 후 (%s)** 만료됩니다.

만료 후에는 자녀의 프리미엄 학습 자료 열람이 중단됩니다. 지금 바로 갱신해주세요.

- 갱신 금액: 17,000원 / 연', r.pname, r.end_date);

        INSERT INTO public.notices (
            category, title, body_md, audience_group, is_targeted,
            priority, status, send_email,
            action_label, action_url, deadline_at
        ) VALUES (
            'survey_deadline', v_title, v_body, 'parent', FALSE,
            2, 'published', TRUE,
            '🚨 지금 갱신하기',
            '/?page=parent_dashboard&tab=payment',
            r.end_date::TIMESTAMPTZ
        ) RETURNING id INTO v_notice_id;

        UPDATE public.parent_subscriptions
           SET notified_d7_at = NOW()
         WHERE id = r.sub_id;

        INSERT INTO public.subscription_renewal_log (
            parent_id, subscription_id, event_type, from_year, to_year, note
        ) VALUES (
            r.parent_id, r.sub_id, 'notified_d7', r.year, r.year, v_title
        );

        notice_id := v_notice_id;
        parent_id := r.parent_id;
        subscription_id := r.sub_id;
        days_left := v_days_left;
        RETURN NEXT;
    END LOOP;

    -- D-Day 도래 시 expired 상태 처리
    UPDATE public.parent_subscriptions
       SET status = 'expired', updated_at = NOW()
     WHERE status = 'active'
       AND end_date < CURRENT_DATE;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 7. 학부모 자기 구독 list (갱신·해지 표시)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_my_subscriptions(p_parent_id UUID)
RETURNS TABLE (
    id              UUID,
    year            INT,
    amount          INT,
    status          TEXT,
    start_date      DATE,
    end_date        DATE,
    days_left       INT,
    auto_renewal_enabled BOOLEAN,
    payment_id      UUID,
    receipt_url     TEXT,
    refund_amount   INT,
    cancelled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ
) LANGUAGE SQL STABLE AS $$
    SELECT
        ps.id, ps.year, ps.amount, ps.status,
        ps.start_date, ps.end_date,
        (ps.end_date - CURRENT_DATE)::INT AS days_left,
        ps.auto_renewal_enabled,
        ps.payment_id,
        p.receipt_url,
        p.refund_amount,
        ps.cancelled_at,
        ps.created_at
      FROM public.parent_subscriptions ps
      LEFT JOIN public.payments p ON p.id = ps.payment_id
     WHERE ps.parent_id = p_parent_id
     ORDER BY ps.year DESC, ps.created_at DESC;
$$;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT column_name FROM information_schema.columns
 WHERE table_schema='public' AND table_name='parent_subscriptions'
   AND column_name IN ('auto_renewal_enabled','tos_version','tos_agreed_at',
                       'cancelled_at','cancel_reason','notified_d30_at','notified_d7_at')
 ORDER BY column_name;
-- 기대: 7행

SELECT kind, version, is_active FROM public.terms_of_service_versions ORDER BY kind;
-- 기대: 4행 (service / refund / privacy / auto_renewal)

SELECT routine_name FROM information_schema.routines
 WHERE routine_schema='public'
   AND routine_name IN (
       'get_active_terms','toggle_auto_renewal',
       'notify_expiring_subscriptions','get_my_subscriptions')
 ORDER BY routine_name;
-- 기대: 4행

-- 끝.
