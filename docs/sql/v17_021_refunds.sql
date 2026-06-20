-- ============================================================
-- DragonEyes v1.7 — Phase 10 추가 (021)
-- 결제 환불 처리 + 환불 이력 + 본부 admin 조회 함수
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   본부 admin이 결제 기록을 조회·필터링하고 환불 처리할 수 있게.
--   부분 환불 여러 번 가능 (payment_refunds 이력 테이블).
--   환불 시 학부모 구독은 status='refunded', 기관 계약은 cancelled.
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. payments 컬럼 보강
-- ─────────────────────────────────────────────────────────────
ALTER TABLE public.payments
    ADD COLUMN IF NOT EXISTS refund_reason TEXT;
ALTER TABLE public.payments
    ADD COLUMN IF NOT EXISTS refunded_by UUID REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE public.payments
    ADD COLUMN IF NOT EXISTS refund_method TEXT
        CHECK (refund_method IS NULL OR refund_method IN ('admin_manual','pg_auto','system'));


-- ─────────────────────────────────────────────────────────────
-- 2. payment_refunds — 환불 이력 (부분 환불 여러 건 추적)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.payment_refunds (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id      UUID NOT NULL REFERENCES public.payments(id) ON DELETE CASCADE,

    amount          INT NOT NULL CHECK (amount > 0),
    reason          TEXT,
    method          TEXT NOT NULL DEFAULT 'admin_manual'
        CHECK (method IN ('admin_manual','pg_auto','system')),

    status          TEXT NOT NULL DEFAULT 'completed'
        CHECK (status IN ('pending','completed','failed')),

    -- PG 응답
    pg_refund_id    TEXT,
    raw_response    JSONB,

    processed_by    UUID REFERENCES public.users(id) ON DELETE SET NULL,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pr_payment ON public.payment_refunds(payment_id);
CREATE INDEX IF NOT EXISTS idx_pr_status  ON public.payment_refunds(status);


-- ─────────────────────────────────────────────────────────────
-- 3. 환불 처리 함수
-- ─────────────────────────────────────────────────────────────
-- 부분 환불 / 전액 환불 모두 처리.
-- - payment_refunds INSERT
-- - payments.refund_amount 누적, status 갱신
-- - 학부모 구독은 status='refunded' (전액 환불 시)
-- - 기관 계약은 status='cancelled' (전액 환불 시)
CREATE OR REPLACE FUNCTION public.process_refund(
    p_payment_id    UUID,
    p_amount        INT,
    p_reason        TEXT,
    p_processed_by  UUID,
    p_method        TEXT DEFAULT 'admin_manual',
    p_pg_refund_id  TEXT DEFAULT NULL
) RETURNS TABLE (
    refund_id        UUID,
    new_payment_status TEXT,
    total_refunded   INT,
    is_full_refund   BOOLEAN
) LANGUAGE plpgsql AS $$
DECLARE
    v_payment        public.payments;
    v_refund_id      UUID;
    v_total_refunded INT;
    v_new_status     TEXT;
    v_is_full        BOOLEAN;
BEGIN
    SELECT * INTO v_payment FROM public.payments WHERE id = p_payment_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'payment not found: %', p_payment_id;
    END IF;

    IF v_payment.status NOT IN ('completed','partial_refund') THEN
        RAISE EXCEPTION 'cannot refund payment in status %', v_payment.status;
    END IF;

    -- 누적 환불액 + 신규 환불액 ≤ 결제액
    v_total_refunded := COALESCE(v_payment.refund_amount, 0) + p_amount;
    IF v_total_refunded > v_payment.amount THEN
        RAISE EXCEPTION '환불 누계(%s원)가 결제액(%s원)을 초과합니다',
            v_total_refunded, v_payment.amount;
    END IF;

    -- 환불 이력 INSERT
    INSERT INTO public.payment_refunds (
        payment_id, amount, reason, method, status,
        pg_refund_id, processed_by
    ) VALUES (
        p_payment_id, p_amount, p_reason, p_method, 'completed',
        p_pg_refund_id, p_processed_by
    ) RETURNING id INTO v_refund_id;

    -- 결제 상태 갱신
    v_is_full := (v_total_refunded >= v_payment.amount);
    v_new_status := CASE WHEN v_is_full THEN 'refunded' ELSE 'partial_refund' END;

    UPDATE public.payments
       SET status        = v_new_status,
           refund_amount = v_total_refunded,
           refunded_at   = CASE WHEN v_is_full THEN NOW() ELSE refunded_at END,
           refunded_by   = p_processed_by,
           refund_method = p_method,
           refund_reason = COALESCE(refund_reason, p_reason),
           updated_at    = NOW()
     WHERE id = p_payment_id;

    -- 학부모 구독 / 기관 계약 연동 (전액 환불 시)
    IF v_is_full THEN
        IF v_payment.target_type = 'parent' THEN
            UPDATE public.parent_subscriptions
               SET status      = 'refunded',
                   updated_at  = NOW()
             WHERE payment_id = p_payment_id;
        ELSIF v_payment.target_type = 'institution' THEN
            UPDATE public.institution_contracts
               SET status      = 'cancelled',
                   updated_at  = NOW()
             WHERE payment_id = p_payment_id;
        END IF;
    END IF;

    refund_id := v_refund_id;
    new_payment_status := v_new_status;
    total_refunded := v_total_refunded;
    is_full_refund := v_is_full;
    RETURN NEXT;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 4. 본부 admin 결제 list 조회 함수
-- ─────────────────────────────────────────────────────────────
-- target_name (학부모 이름 or 기관 이름) 까지 같이 반환해 검색 편의
CREATE OR REPLACE FUNCTION public.get_payments_admin(
    p_status      TEXT DEFAULT NULL,        -- NULL=전체
    p_target_type TEXT DEFAULT NULL,        -- NULL=전체
    p_product_year SMALLINT DEFAULT NULL,
    p_limit       INT  DEFAULT 200
) RETURNS TABLE (
    id              UUID,
    provider        TEXT,
    target_type     TEXT,
    target_id       UUID,
    target_name     TEXT,
    target_email    TEXT,
    amount          INT,
    refund_amount   INT,
    product_type    TEXT,
    product_year    SMALLINT,
    status          TEXT,
    paid_at         TIMESTAMPTZ,
    refunded_at     TIMESTAMPTZ,
    refund_reason   TEXT,
    pg_order_id     TEXT,
    created_at      TIMESTAMPTZ
) LANGUAGE SQL STABLE AS $$
    SELECT
        p.id, p.provider, p.target_type, p.target_id,
        CASE p.target_type
            WHEN 'parent'      THEN u.name
            WHEN 'institution' THEN i.name
            ELSE NULL
        END AS target_name,
        CASE p.target_type
            WHEN 'parent' THEN u.email
            ELSE NULL
        END AS target_email,
        p.amount, p.refund_amount,
        p.product_type, p.product_year,
        p.status, p.paid_at, p.refunded_at, p.refund_reason,
        p.pg_order_id, p.created_at
    FROM public.payments p
    LEFT JOIN public.users        u ON p.target_type = 'parent'      AND u.id = p.target_id
    LEFT JOIN public.institutions i ON p.target_type = 'institution' AND i.id = p.target_id
    WHERE (p_status IS NULL OR p.status = p_status)
      AND (p_target_type IS NULL OR p.target_type = p_target_type)
      AND (p_product_year IS NULL OR p.product_year = p_product_year)
    ORDER BY p.created_at DESC
    LIMIT p_limit;
$$;


-- ─────────────────────────────────────────────────────────────
-- 5. 환불 이력 조회
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_refund_history(p_payment_id UUID)
RETURNS TABLE (
    refund_id       UUID,
    amount          INT,
    reason          TEXT,
    method          TEXT,
    status          TEXT,
    pg_refund_id    TEXT,
    processed_at    TIMESTAMPTZ,
    processed_by    UUID,
    processed_by_name TEXT
) LANGUAGE SQL STABLE AS $$
    SELECT
        pr.id, pr.amount, pr.reason, pr.method, pr.status,
        pr.pg_refund_id, pr.processed_at, pr.processed_by,
        u.name
      FROM public.payment_refunds pr
      LEFT JOIN public.users u ON u.id = pr.processed_by
     WHERE pr.payment_id = p_payment_id
     ORDER BY pr.processed_at DESC;
$$;


-- ─────────────────────────────────────────────────────────────
-- 6. 매출 요약 (KPI용)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_payment_summary(p_year SMALLINT DEFAULT NULL)
RETURNS TABLE (
    total_paid         BIGINT,
    total_refunded     BIGINT,
    net_revenue        BIGINT,
    paid_count         INT,
    refunded_count     INT,
    partial_count      INT,
    pending_count      INT,
    failed_count       INT
) LANGUAGE SQL STABLE AS $$
    SELECT
        COALESCE(SUM(amount) FILTER (WHERE status IN ('completed','partial_refund')), 0)::BIGINT AS total_paid,
        COALESCE(SUM(refund_amount), 0)::BIGINT                                                  AS total_refunded,
        (COALESCE(SUM(amount) FILTER (WHERE status IN ('completed','partial_refund')), 0)
         - COALESCE(SUM(refund_amount), 0))::BIGINT                                              AS net_revenue,
        COUNT(*) FILTER (WHERE status = 'completed')::INT                                        AS paid_count,
        COUNT(*) FILTER (WHERE status = 'refunded')::INT                                         AS refunded_count,
        COUNT(*) FILTER (WHERE status = 'partial_refund')::INT                                   AS partial_count,
        COUNT(*) FILTER (WHERE status = 'pending')::INT                                          AS pending_count,
        COUNT(*) FILTER (WHERE status = 'failed')::INT                                           AS failed_count
    FROM public.payments
    WHERE (p_year IS NULL OR product_year = p_year);
$$;


-- ─────────────────────────────────────────────────────────────
-- 7. 일별 매출 (기간)
-- ─────────────────────────────────────────────────────────────
-- paid_at 기준 날짜별 매출 / 환불 / 순매출
CREATE OR REPLACE FUNCTION public.get_revenue_daily(
    p_start DATE,
    p_end   DATE
) RETURNS TABLE (
    bucket_date     DATE,
    parent_revenue  BIGINT,
    institution_revenue BIGINT,
    other_revenue   BIGINT,
    gross_revenue   BIGINT,
    refunded        BIGINT,
    net_revenue     BIGINT,
    paid_count      INT,
    refund_count    INT
) LANGUAGE SQL STABLE AS $$
    WITH days AS (
        SELECT generate_series(p_start, p_end, INTERVAL '1 day')::DATE AS d
    ),
    paid AS (
        SELECT
            paid_at::DATE                                        AS d,
            target_type,
            SUM(amount) FILTER (WHERE status IN ('completed','partial_refund'))::BIGINT
                                                                 AS gross,
            COUNT(*) FILTER (WHERE status IN ('completed','partial_refund'))::INT
                                                                 AS paid_cnt
        FROM public.payments
        WHERE paid_at::DATE BETWEEN p_start AND p_end
        GROUP BY paid_at::DATE, target_type
    ),
    refunds AS (
        SELECT
            processed_at::DATE        AS d,
            SUM(amount)::BIGINT       AS r_amount,
            COUNT(*)::INT             AS r_count
        FROM public.payment_refunds
        WHERE status = 'completed'
          AND processed_at::DATE BETWEEN p_start AND p_end
        GROUP BY processed_at::DATE
    )
    SELECT
        days.d                                                            AS bucket_date,
        COALESCE(SUM(paid.gross) FILTER (WHERE paid.target_type='parent'), 0)::BIGINT       AS parent_revenue,
        COALESCE(SUM(paid.gross) FILTER (WHERE paid.target_type='institution'), 0)::BIGINT  AS institution_revenue,
        COALESCE(SUM(paid.gross) FILTER (WHERE paid.target_type='other'), 0)::BIGINT        AS other_revenue,
        COALESCE(SUM(paid.gross), 0)::BIGINT                              AS gross_revenue,
        COALESCE(MAX(refunds.r_amount), 0)::BIGINT                        AS refunded,
        (COALESCE(SUM(paid.gross), 0) - COALESCE(MAX(refunds.r_amount), 0))::BIGINT
                                                                          AS net_revenue,
        COALESCE(SUM(paid.paid_cnt), 0)::INT                              AS paid_count,
        COALESCE(MAX(refunds.r_count), 0)::INT                            AS refund_count
    FROM days
    LEFT JOIN paid    ON paid.d = days.d
    LEFT JOIN refunds ON refunds.d = days.d
    GROUP BY days.d
    ORDER BY days.d;
$$;


-- ─────────────────────────────────────────────────────────────
-- 8. 월별 매출 (해당 연도)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_revenue_monthly(p_year INT)
RETURNS TABLE (
    bucket_month        INT,
    parent_revenue      BIGINT,
    institution_revenue BIGINT,
    other_revenue       BIGINT,
    gross_revenue       BIGINT,
    refunded            BIGINT,
    net_revenue         BIGINT,
    paid_count          INT,
    refund_count        INT
) LANGUAGE SQL STABLE AS $$
    WITH months AS (
        SELECT generate_series(1, 12)::INT AS m
    ),
    paid AS (
        SELECT
            EXTRACT(MONTH FROM paid_at)::INT  AS m,
            target_type,
            SUM(amount) FILTER (WHERE status IN ('completed','partial_refund'))::BIGINT AS gross,
            COUNT(*) FILTER (WHERE status IN ('completed','partial_refund'))::INT       AS paid_cnt
        FROM public.payments
        WHERE EXTRACT(YEAR FROM paid_at) = p_year
        GROUP BY EXTRACT(MONTH FROM paid_at), target_type
    ),
    refunds AS (
        SELECT
            EXTRACT(MONTH FROM processed_at)::INT AS m,
            SUM(amount)::BIGINT                   AS r_amount,
            COUNT(*)::INT                         AS r_count
        FROM public.payment_refunds
        WHERE status='completed'
          AND EXTRACT(YEAR FROM processed_at) = p_year
        GROUP BY EXTRACT(MONTH FROM processed_at)
    )
    SELECT
        months.m AS bucket_month,
        COALESCE(SUM(paid.gross) FILTER (WHERE paid.target_type='parent'), 0)::BIGINT       AS parent_revenue,
        COALESCE(SUM(paid.gross) FILTER (WHERE paid.target_type='institution'), 0)::BIGINT  AS institution_revenue,
        COALESCE(SUM(paid.gross) FILTER (WHERE paid.target_type='other'), 0)::BIGINT        AS other_revenue,
        COALESCE(SUM(paid.gross), 0)::BIGINT      AS gross_revenue,
        COALESCE(MAX(refunds.r_amount), 0)::BIGINT AS refunded,
        (COALESCE(SUM(paid.gross), 0) - COALESCE(MAX(refunds.r_amount), 0))::BIGINT AS net_revenue,
        COALESCE(SUM(paid.paid_cnt), 0)::INT     AS paid_count,
        COALESCE(MAX(refunds.r_count), 0)::INT   AS refund_count
    FROM months
    LEFT JOIN paid    ON paid.m = months.m
    LEFT JOIN refunds ON refunds.m = months.m
    GROUP BY months.m
    ORDER BY months.m;
$$;


-- ─────────────────────────────────────────────────────────────
-- 9. 연도별 매출 (서비스 전체 누적)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_revenue_yearly()
RETURNS TABLE (
    bucket_year         INT,
    parent_revenue      BIGINT,
    institution_revenue BIGINT,
    other_revenue       BIGINT,
    gross_revenue       BIGINT,
    refunded            BIGINT,
    net_revenue         BIGINT,
    paid_count          INT,
    refund_count        INT
) LANGUAGE SQL STABLE AS $$
    WITH paid AS (
        SELECT
            EXTRACT(YEAR FROM paid_at)::INT AS y,
            target_type,
            SUM(amount) FILTER (WHERE status IN ('completed','partial_refund'))::BIGINT AS gross,
            COUNT(*) FILTER (WHERE status IN ('completed','partial_refund'))::INT       AS paid_cnt
        FROM public.payments
        WHERE paid_at IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM paid_at), target_type
    ),
    refunds AS (
        SELECT
            EXTRACT(YEAR FROM processed_at)::INT AS y,
            SUM(amount)::BIGINT                  AS r_amount,
            COUNT(*)::INT                        AS r_count
        FROM public.payment_refunds
        WHERE status='completed'
        GROUP BY EXTRACT(YEAR FROM processed_at)
    ),
    years AS (
        SELECT DISTINCT y FROM paid
        UNION
        SELECT DISTINCT y FROM refunds
    )
    SELECT
        years.y AS bucket_year,
        COALESCE(SUM(paid.gross) FILTER (WHERE paid.target_type='parent'), 0)::BIGINT       AS parent_revenue,
        COALESCE(SUM(paid.gross) FILTER (WHERE paid.target_type='institution'), 0)::BIGINT  AS institution_revenue,
        COALESCE(SUM(paid.gross) FILTER (WHERE paid.target_type='other'), 0)::BIGINT        AS other_revenue,
        COALESCE(SUM(paid.gross), 0)::BIGINT      AS gross_revenue,
        COALESCE(MAX(refunds.r_amount), 0)::BIGINT AS refunded,
        (COALESCE(SUM(paid.gross), 0) - COALESCE(MAX(refunds.r_amount), 0))::BIGINT AS net_revenue,
        COALESCE(SUM(paid.paid_cnt), 0)::INT     AS paid_count,
        COALESCE(MAX(refunds.r_count), 0)::INT   AS refund_count
    FROM years
    LEFT JOIN paid    ON paid.y = years.y
    LEFT JOIN refunds ON refunds.y = years.y
    GROUP BY years.y
    ORDER BY years.y DESC;
$$;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT column_name, data_type
  FROM information_schema.columns
 WHERE table_schema='public' AND table_name='payments'
   AND column_name IN ('refund_reason','refunded_by','refund_method')
 ORDER BY column_name;
-- 기대: 3행

SELECT 'payment_refunds' AS tbl, COUNT(*) AS rows FROM public.payment_refunds;
-- 기대: 0행

SELECT routine_name FROM information_schema.routines
 WHERE routine_schema='public'
   AND routine_name IN (
       'process_refund',
       'get_payments_admin',
       'get_refund_history',
       'get_payment_summary',
       'get_revenue_daily',
       'get_revenue_monthly',
       'get_revenue_yearly'
   )
 ORDER BY routine_name;
-- 기대: 7행

-- 끝.
