-- ============================================================
-- DragonEyes v1.7 — 캠페인 시스템 Phase 1 (004/008)
-- 캠페인 메타 + 학습 자료 + 열람 권한
-- ============================================================
-- 적용일 : 2026-06-18
-- 목적   : '온라인 유해컨텐츠 근절 캠페인' 의 연도별 캠페인 +
--          자료(PDF/동영상/기타) + 무료·유료 구분 + 열람 권한 추적.
--
-- 다운로드 차단 정책:
--   storage_url은 직접 노출 X. 시청 토큰 발급 후 스트리밍 프록시 경유.
--   view_only=TRUE 모든 자료에 적용 (기본값).
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. campaigns — 연도별 캠페인
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.campaigns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    year            SMALLINT NOT NULL,                  -- 2026, 2027, ...
    code            TEXT UNIQUE,                        -- 외부 식별자 (예: 'CAMP-2026')
    title           TEXT NOT NULL,
    subtitle        TEXT,
    description     TEXT,

    target_grade_min SMALLINT DEFAULT 1,                -- 최소 학년
    target_grade_max SMALLINT DEFAULT 12,               -- 최대 학년

    status          TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'active', 'closed', 'archived')),
    start_at        TIMESTAMPTZ,
    end_at          TIMESTAMPTZ,

    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_year   ON public.campaigns(year);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON public.campaigns(status);


-- ─────────────────────────────────────────────────────────────
-- 2. campaign_materials — 학습 자료 (PDF/동영상/기타)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.campaign_materials (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,

    type            TEXT NOT NULL CHECK (type IN ('pdf', 'video', 'audio', 'interactive', 'other')),
    title           TEXT NOT NULL,
    description     TEXT,
    thumbnail_url   TEXT,

    -- 가격 정책
    tier            TEXT NOT NULL DEFAULT 'free'
        CHECK (tier IN ('free', 'paid')),

    -- 스토리지 (직접 노출 금지)
    storage_url     TEXT NOT NULL,                      -- 내부 경로 (signed URL 생성용)
    storage_provider TEXT DEFAULT 'supabase',           -- supabase / s3 / cdn
    duration_seconds INT,                               -- 동영상·오디오 길이
    page_count      INT,                                -- PDF 페이지 수
    file_size_bytes BIGINT,

    -- 다운로드 차단 (모든 자료 강제 view-only)
    view_only       BOOLEAN NOT NULL DEFAULT TRUE,

    -- 대상 학년
    target_grade_min SMALLINT,
    target_grade_max SMALLINT,
    -- 주제 태그 (저작권/그루밍/도박/기타)
    topic_tags      TEXT[],

    display_order   INT DEFAULT 0,
    is_published    BOOLEAN NOT NULL DEFAULT FALSE,
    published_at    TIMESTAMPTZ,

    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_materials_campaign ON public.campaign_materials(campaign_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_materials_tier     ON public.campaign_materials(tier);
CREATE INDEX IF NOT EXISTS idx_materials_published ON public.campaign_materials(is_published) WHERE is_published = TRUE;


-- ─────────────────────────────────────────────────────────────
-- 3. material_access — 열람 권한 grant
-- ─────────────────────────────────────────────────────────────
-- 어떤 사용자가 어떤 자료를 볼 수 있는지 추적.
-- granted_via:
--   free                  = 무료 자료 (모든 사용자)
--   institution_contract  = 교육기관 계약으로 권한 부여
--   parent_subscription   = 학부모 연 1만원 결제로 권한 부여
--                           (학부모 본인 + 등록된 자녀 모두)
CREATE TABLE IF NOT EXISTS public.material_access (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    material_id     UUID NOT NULL REFERENCES public.campaign_materials(id) ON DELETE CASCADE,
    granted_via     TEXT NOT NULL CHECK (granted_via IN (
                        'free', 'institution_contract', 'parent_subscription', 'admin_grant'
                    )),
    granted_ref_id  UUID,                               -- contract/subscription id 참조
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,                        -- 당해 연도 말 등

    UNIQUE (user_id, material_id),
    CONSTRAINT ma_user_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ma_user_id     ON public.material_access(user_id);
CREATE INDEX IF NOT EXISTS idx_ma_material_id ON public.material_access(material_id);
CREATE INDEX IF NOT EXISTS idx_ma_expires_at  ON public.material_access(expires_at) WHERE expires_at IS NOT NULL;


-- ─────────────────────────────────────────────────────────────
-- 4. material_view_logs — 시청 로그 (다운로드 시도 감지·통계)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.material_view_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    material_id     UUID NOT NULL REFERENCES public.campaign_materials(id) ON DELETE CASCADE,
    view_token      TEXT,                               -- 발급된 시청 토큰
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    duration_seconds INT,
    completion_rate NUMERIC(5,2),                       -- 0~100%
    ip_address      INET,
    user_agent      TEXT,
    suspicious_action TEXT,                             -- 우클릭/devtools 감지 등 (선택)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mvl_user_id    ON public.material_view_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_mvl_material_id ON public.material_view_logs(material_id);
CREATE INDEX IF NOT EXISTS idx_mvl_started_at ON public.material_view_logs(started_at);


-- ─────────────────────────────────────────────────────────────
-- 트리거
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_campaigns_updated_at ON public.campaigns;
CREATE TRIGGER trg_campaigns_updated_at
    BEFORE UPDATE ON public.campaigns
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_materials_updated_at ON public.campaign_materials;
CREATE TRIGGER trg_materials_updated_at
    BEFORE UPDATE ON public.campaign_materials
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'campaigns'           AS tbl, COUNT(*) AS rows FROM public.campaigns
UNION ALL
SELECT 'campaign_materials'  AS tbl, COUNT(*) FROM public.campaign_materials
UNION ALL
SELECT 'material_access'     AS tbl, COUNT(*) FROM public.material_access
UNION ALL
SELECT 'material_view_logs'  AS tbl, COUNT(*) FROM public.material_view_logs;

-- 기대: 4개 행 모두 rows=0

-- 끝.
