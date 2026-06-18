-- ============================================================
-- DragonEyes v1.7 — 캠페인 시스템 Phase 1 (007/008)
-- 결제 시스템 (PG 통합 + 기관 계약 + 학부모 연 1만원 + 자녀 무료)
-- ============================================================
-- 적용일 : 2026-06-18
-- 목적   : 다양한 PG (토스/카카오/이니시스 등) 지원하는 통합 결제 로그 +
--          교육기관 연단위·일괄 계약 + 학부모 연 1만원 구독.
--
-- 정책 (사용자 결정):
--   학생       = 무료 (결제 불필요)
--   학부모     = 연 1만원 (당해 연도 모든 유료 자료 무제한 + 자녀 동시 권한)
--   교육기관   = 연단위 / 일괄 계약 (금액·기간 자유 협상)
--
-- 다자녀 가족:
--   학부모 1명이 결제 = 등록된 모든 자녀에게 권한 동시 부여 (material_access).
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. payment_providers — PG 마스터 (관할 신고 상태 추적)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.payment_providers (
    code            TEXT PRIMARY KEY,                   -- 'toss', 'kakao', 'inicis', ...
    label           TEXT NOT NULL,                      -- '토스페이먼츠'
    enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    regulatory_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (regulatory_status IN ('pending', 'submitted', 'approved', 'rejected')),
    regulatory_note TEXT,                               -- 신고 진행 메모
    sandbox_mode    BOOLEAN NOT NULL DEFAULT TRUE,
    api_key_alias   TEXT,                               -- 환경변수 alias (실 키 X)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 기본 PG 4종 등록 (모두 비활성·신고전 상태로 시작)
INSERT INTO public.payment_providers (code, label, enabled, regulatory_status)
VALUES
    ('toss',   '토스페이먼츠', FALSE, 'pending'),
    ('kakao',  '카카오페이',   FALSE, 'pending'),
    ('inicis', '이니시스',     FALSE, 'pending'),
    ('naver',  '네이버페이',   FALSE, 'pending')
ON CONFLICT (code) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 2. payments — 통합 결제 로그 (모든 PG 공통)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider        TEXT NOT NULL REFERENCES public.payment_providers(code),

    -- 결제 대상
    target_type     TEXT NOT NULL CHECK (target_type IN ('institution', 'parent', 'other')),
    target_id       UUID NOT NULL,                      -- institution_id 또는 parent user_id

    -- 금액
    amount          INT NOT NULL CHECK (amount >= 0),
    currency        TEXT NOT NULL DEFAULT 'KRW',

    -- 상품 식별
    product_type    TEXT NOT NULL CHECK (product_type IN (
                        'institution_yearly',
                        'institution_bulk',
                        'parent_yearly_10k'
                    )),
    product_year    SMALLINT,                           -- 적용 연도

    -- 결제 상태
    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'completed', 'failed', 'cancelled', 'refunded', 'partial_refund')),
    paid_at         TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    refunded_at     TIMESTAMPTZ,
    refund_amount   INT,

    -- PG raw 응답 (디버깅·환불 추적)
    pg_order_id     TEXT,                               -- PG측 주문번호
    pg_transaction_id TEXT,                             -- PG측 결제번호
    raw_request     JSONB,
    raw_response    JSONB,

    -- 영수증/세금계산서
    receipt_url     TEXT,
    tax_invoice_url TEXT,

    note            TEXT,
    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_target     ON public.payments(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_payments_status     ON public.payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_provider   ON public.payments(provider);
CREATE INDEX IF NOT EXISTS idx_payments_product_year ON public.payments(product_type, product_year);
CREATE INDEX IF NOT EXISTS idx_payments_paid_at    ON public.payments(paid_at) WHERE paid_at IS NOT NULL;


-- ─────────────────────────────────────────────────────────────
-- 3. institution_contracts — 교육기관 계약
-- ─────────────────────────────────────────────────────────────
-- term:
--   yearly  = 연단위 계약 (1년 자동 갱신·재계약)
--   bulk    = 일괄 계약 (커스텀 기간·금액)
CREATE TABLE IF NOT EXISTS public.institution_contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id  UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    term            TEXT NOT NULL CHECK (term IN ('yearly', 'bulk')),

    contract_no     TEXT UNIQUE,                        -- 'INST-2026-0001'
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    amount          INT NOT NULL CHECK (amount >= 0),
    currency        TEXT NOT NULL DEFAULT 'KRW',

    -- 적용 범위 (이 계약으로 권한 부여될 자료/학생 수)
    max_students    INT,                                -- NULL이면 무제한
    included_material_tier TEXT DEFAULT 'paid'          -- 어떤 tier 자료 포함
        CHECK (included_material_tier IN ('free', 'paid', 'all')),

    payment_id      UUID REFERENCES public.payments(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'expired', 'cancelled')),

    auto_renewal    BOOLEAN NOT NULL DEFAULT FALSE,
    note            TEXT,

    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_ic_institution ON public.institution_contracts(institution_id);
CREATE INDEX IF NOT EXISTS idx_ic_status      ON public.institution_contracts(status);
CREATE INDEX IF NOT EXISTS idx_ic_dates       ON public.institution_contracts(start_date, end_date);


-- ─────────────────────────────────────────────────────────────
-- 4. parent_subscriptions — 학부모 연 1만원 구독
-- ─────────────────────────────────────────────────────────────
-- 연도별 1건. 자녀 수 무관 단일 결제.
CREATE TABLE IF NOT EXISTS public.parent_subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id       UUID NOT NULL,                      -- users.id (role_v2='parent')
    year            SMALLINT NOT NULL,                  -- 2026

    amount          INT NOT NULL DEFAULT 10000          -- 정책 고정 1만원
                        CHECK (amount = 10000),
    currency        TEXT NOT NULL DEFAULT 'KRW',

    payment_id      UUID REFERENCES public.payments(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'expired', 'cancelled', 'refunded')),

    -- 적용 기간
    start_date      DATE NOT NULL,                      -- 결제일
    end_date        DATE NOT NULL,                      -- 당해 12월 31일

    -- 적용 자녀 수 (스냅샷, 구독 후 자녀 추가도 자동 권한 부여)
    children_at_purchase INT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (parent_id, year),                           -- 학부모 1명 = 연 1회
    CONSTRAINT ps_parent_fkey FOREIGN KEY (parent_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ps_parent ON public.parent_subscriptions(parent_id);
CREATE INDEX IF NOT EXISTS idx_ps_year   ON public.parent_subscriptions(year);
CREATE INDEX IF NOT EXISTS idx_ps_status ON public.parent_subscriptions(status);


-- ─────────────────────────────────────────────────────────────
-- 5. 헬퍼: 학부모 결제 여부 + 자녀 권한 일괄 부여
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.has_active_parent_subscription(p_user_id UUID, p_year SMALLINT DEFAULT NULL)
RETURNS BOOLEAN LANGUAGE SQL STABLE AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.parent_subscriptions
        WHERE parent_id = p_user_id
          AND status = 'active'
          AND (p_year IS NULL OR year = p_year)
          AND CURRENT_DATE BETWEEN start_date AND end_date
    );
$$;


-- ─────────────────────────────────────────────────────────────
-- 트리거
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_pp_updated_at ON public.payment_providers;
CREATE TRIGGER trg_pp_updated_at
    BEFORE UPDATE ON public.payment_providers
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_payments_updated_at ON public.payments;
CREATE TRIGGER trg_payments_updated_at
    BEFORE UPDATE ON public.payments
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_ic_updated_at ON public.institution_contracts;
CREATE TRIGGER trg_ic_updated_at
    BEFORE UPDATE ON public.institution_contracts
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_ps_updated_at ON public.parent_subscriptions;
CREATE TRIGGER trg_ps_updated_at
    BEFORE UPDATE ON public.parent_subscriptions
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'payment_providers'      AS tbl, COUNT(*) AS rows FROM public.payment_providers
UNION ALL
SELECT 'payments'                AS tbl, COUNT(*) FROM public.payments
UNION ALL
SELECT 'institution_contracts'   AS tbl, COUNT(*) FROM public.institution_contracts
UNION ALL
SELECT 'parent_subscriptions'    AS tbl, COUNT(*) FROM public.parent_subscriptions;

-- 기대:
--   payment_providers      rows=4 (toss/kakao/inicis/naver 기본 등록)
--   payments               rows=0
--   institution_contracts  rows=0
--   parent_subscriptions   rows=0

-- 끝.
