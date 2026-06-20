-- ============================================================
-- DragonEyes v1.7 — Phase 9 보강 (013)
-- 학부모 연 구독료 10,000원 → 17,000원
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   : 양질의 컨텐츠 지속 공급을 위한 가격 조정.
-- ============================================================

-- 1) parent_subscriptions.amount CHECK 제약 변경 (10000 → 17000)
ALTER TABLE public.parent_subscriptions
    DROP CONSTRAINT IF EXISTS parent_subscriptions_amount_check;

ALTER TABLE public.parent_subscriptions
    ADD CONSTRAINT parent_subscriptions_amount_check
    CHECK (amount = 17000);

-- 2) DEFAULT 값도 변경
ALTER TABLE public.parent_subscriptions
    ALTER COLUMN amount SET DEFAULT 17000;

-- 3) 안내 컨텐츠 (campaign_overview_content) 학부모용 프리미엄 안내 UPDATE
UPDATE public.campaign_overview_content
SET body_md = REPLACE(REPLACE(body_md, '연 1만원', '연 1만 7천원'), '10,000원', '17,000원'),
    updated_at = NOW()
WHERE audience = 'parent';

-- 4) 검증
SELECT 'parent_subscriptions CHECK' AS label,
       conname, pg_get_constraintdef(oid) AS def
FROM pg_constraint
WHERE conrelid = 'public.parent_subscriptions'::regclass
  AND conname = 'parent_subscriptions_amount_check';
-- 기대: CHECK (amount = 17000)

SELECT 'parent_subscriptions DEFAULT' AS label,
       column_name, column_default
FROM information_schema.columns
WHERE table_schema='public' AND table_name='parent_subscriptions'
  AND column_name='amount';
-- 기대: 17000

SELECT 'campaign_overview_content 학부모 섹션' AS label,
       section_key, LEFT(body_md, 100) AS body_preview
FROM public.campaign_overview_content
WHERE audience='parent' AND body_md ~ '1만 7천원|17,000원'
ORDER BY sort_order;
-- 기대: premium_recommend 등 학부모 섹션 본문에 '1만 7천원' 또는 '17,000원' 등장

-- 끝.
