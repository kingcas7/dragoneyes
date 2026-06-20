-- ============================================================
-- DragonEyes v1.7 — Phase 10 추가 (024)
-- 학습자료실 — 학년대별 기본/프리미엄 자료 + 접근 권한
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   - 학습자료실 카테고리 신설 (campaign_landing 진입점)
--   - 1개 자료 = 1개 페이지 (slug or id로 라우팅)
--   - 학년대(초/중/고/all) + tier(free/premium) 분류
--   - 프리미엄은 결제 사용자에게만 해금
--   - 모든 사용자가 학습자료실 카테고리 진입 가능 (잠금만 표시)
--   - 10개 예상 → 확장 가능 (chapter_no INT)
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. campaign_learning_materials — 학습자료 마스터
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.campaign_learning_materials (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 식별·정렬
    slug            TEXT UNIQUE,                    -- 'safety-grooming-1' 등 URL 친화적
    chapter_no      INT NOT NULL DEFAULT 0
                        CHECK (chapter_no >= 0 AND chapter_no <= 999),

    -- 분류
    target_band     TEXT NOT NULL DEFAULT 'all'
        CHECK (target_band IN ('elementary','middle','high','all')),
    tier            TEXT NOT NULL DEFAULT 'free'
        CHECK (tier IN ('free','premium')),
    category_tag    TEXT,                           -- 'grooming','copyright','deepfake' 등

    -- 표시
    title           TEXT NOT NULL,
    summary         TEXT,                            -- 1~2줄 요약
    cover_emoji     TEXT NOT NULL DEFAULT '📚',      -- 카드용 이모지
    cover_color     TEXT,                            -- '#3b82f6' 등 (선택)
    reading_time_min INT,                            -- 예상 읽기 시간 (분)

    -- 본문
    body_md         TEXT,                            -- Markdown 본문 (선택)
    attachment_url  TEXT,                            -- Supabase Storage PDF URL (선택)

    -- 상태
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    published_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 메타
    created_by      UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 조회 통계
    view_count      INT NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_clm_band_tier  ON public.campaign_learning_materials(target_band, tier);
CREATE INDEX IF NOT EXISTS idx_clm_active     ON public.campaign_learning_materials(is_active, chapter_no);
CREATE INDEX IF NOT EXISTS idx_clm_slug       ON public.campaign_learning_materials(slug);


-- ─────────────────────────────────────────────────────────────
-- 2. 트리거 (updated_at)
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_clm_updated_at ON public.campaign_learning_materials;
CREATE TRIGGER trg_clm_updated_at
    BEFORE UPDATE ON public.campaign_learning_materials
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 3. 프리미엄 접근 권한 판정
-- ─────────────────────────────────────────────────────────────
-- 학생: parent_student_links → parent → parent_subscriptions.active 또는
--       소속 institution → institution_contracts.active
-- 학부모: 본인 parent_subscriptions.active
-- institution_admin: 소속 institution → institution_contracts.active
-- 본부 admin: 항상 TRUE
CREATE OR REPLACE FUNCTION public.check_premium_access(p_user_id UUID)
RETURNS BOOLEAN LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_user   public.users;
    v_now    DATE := CURRENT_DATE;
BEGIN
    SELECT * INTO v_user FROM public.users WHERE id = p_user_id;
    IF v_user IS NULL THEN RETURN FALSE; END IF;

    -- 본부 admin
    IF v_user.role = 'admin' AND v_user.partner_id IS NULL THEN
        RETURN TRUE;
    END IF;

    -- 학부모: 본인 활성 구독
    IF v_user.role_v2 = 'parent' THEN
        IF EXISTS (
            SELECT 1 FROM public.parent_subscriptions
             WHERE parent_id = p_user_id
               AND status = 'active'
               AND start_date <= v_now AND end_date >= v_now
        ) THEN
            RETURN TRUE;
        END IF;
    END IF;

    -- 학생: 부모(parent_student_links) 활성 구독 OR 본인 학교 계약
    IF v_user.role_v2 = 'student' THEN
        IF EXISTS (
            SELECT 1
              FROM public.parent_student_links psl
              JOIN public.parent_subscriptions ps ON ps.parent_id = psl.parent_id
             WHERE psl.student_id = p_user_id
               AND psl.verification_status = 'verified'
               AND ps.status = 'active'
               AND ps.start_date <= v_now AND ps.end_date >= v_now
        ) THEN
            RETURN TRUE;
        END IF;

        IF v_user.institution_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM public.institution_contracts
             WHERE institution_id = v_user.institution_id
               AND status = 'active'
               AND start_date <= v_now AND end_date >= v_now
        ) THEN
            RETURN TRUE;
        END IF;
    END IF;

    -- 기관 admin: 소속 기관 활성 계약
    IF v_user.role_v2 = 'institution_admin' AND v_user.institution_id IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM public.institution_contracts
             WHERE institution_id = v_user.institution_id
               AND status = 'active'
               AND start_date <= v_now AND end_date >= v_now
        ) THEN
            RETURN TRUE;
        END IF;
    END IF;

    RETURN FALSE;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 4. 학습자료실 — 사용자별 가시 자료 list
-- ─────────────────────────────────────────────────────────────
-- 학생: 자기 학년대 + 'all' 자료만
-- 학부모: 모든 학년대 자료 (자녀들이 학년대별로 다르므로)
-- institution_admin/admin: 전체
-- locked = NOT 본인의 premium 접근 권한 (단, tier='premium'일 때만)
CREATE OR REPLACE FUNCTION public.get_visible_materials(p_user_id UUID)
RETURNS TABLE (
    id              UUID,
    slug            TEXT,
    chapter_no      INT,
    target_band     TEXT,
    tier            TEXT,
    category_tag    TEXT,
    title           TEXT,
    summary         TEXT,
    cover_emoji     TEXT,
    cover_color     TEXT,
    reading_time_min INT,
    has_body        BOOLEAN,
    has_attachment  BOOLEAN,
    view_count      INT,
    published_at    TIMESTAMPTZ,
    is_locked       BOOLEAN
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_user        public.users;
    v_has_premium BOOLEAN := FALSE;
    v_band        TEXT := NULL;
BEGIN
    SELECT * INTO v_user FROM public.users WHERE id = p_user_id;
    IF v_user IS NULL THEN RETURN; END IF;

    v_has_premium := public.check_premium_access(p_user_id);

    -- 학생 학년대 판정
    IF v_user.role_v2 = 'student' THEN
        v_band := public.get_student_band(p_user_id);
    END IF;

    RETURN QUERY
    SELECT
        m.id, m.slug, m.chapter_no, m.target_band, m.tier, m.category_tag,
        m.title, m.summary, m.cover_emoji, m.cover_color, m.reading_time_min,
        (m.body_md IS NOT NULL AND m.body_md <> '') AS has_body,
        (m.attachment_url IS NOT NULL AND m.attachment_url <> '') AS has_attachment,
        m.view_count, m.published_at,
        -- 잠금 판정
        CASE
            WHEN m.tier = 'free' THEN FALSE
            WHEN v_has_premium THEN FALSE
            ELSE TRUE
        END AS is_locked
    FROM public.campaign_learning_materials m
    WHERE m.is_active = TRUE
      AND (
        -- 학생: 학년대 매칭
        v_user.role_v2 <> 'student'
        OR m.target_band = 'all'
        OR m.target_band = v_band
        OR v_band IS NULL  -- 학년대 판정 실패 시 'all'만
      )
    ORDER BY m.chapter_no, m.published_at DESC;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 5. 자료 조회 카운터 증가 (열람 시 호출)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.bump_material_view(p_material_id UUID)
RETURNS VOID LANGUAGE SQL AS $$
    UPDATE public.campaign_learning_materials
       SET view_count = view_count + 1
     WHERE id = p_material_id AND is_active = TRUE;
$$;


-- ─────────────────────────────────────────────────────────────
-- 6. SEED — 학년대별 기본 자료 3종 (이미 만든 PDF 메타데이터)
--    실제 PDF는 Storage 업로드 후 attachment_url 채워야 함
-- ─────────────────────────────────────────────────────────────
INSERT INTO public.campaign_learning_materials
    (slug, chapter_no, target_band, tier, category_tag,
     title, summary, cover_emoji, cover_color, reading_time_min,
     body_md, is_active)
VALUES
('basic-elementary', 1, 'elementary', 'free', 'basic',
 '온라인 안전 기본 — 초등학생용',
 '온라인 유해컨텐츠 7가지·그루밍·신고 채널·봉사시간까지 한 번에 익히는 기본 학습자료 (초등).',
 '🎒', '#10b981', 20,
 '본 자료는 PDF로 제공됩니다. 본부 관리자 메뉴 → 학습자료 관리에서 PDF를 업로드해주세요.',
 TRUE),

('basic-middle', 2, 'middle', 'free', 'basic',
 '온라인 안전 기본 — 중학생용',
 '7대 유해컨텐츠 + 그루밍 6단계 + 저작권 처벌·민사 손해배상까지 깊이 있게 다룬 기본 학습자료 (중학).',
 '📚', '#3b82f6', 25,
 '본 자료는 PDF로 제공됩니다. 본부 관리자 메뉴 → 학습자료 관리에서 PDF를 업로드해주세요.',
 TRUE),

('basic-high', 3, 'high', 'free', 'basic',
 '온라인 안전 기본 — 고등학생용',
 '7대 유해컨텐츠 + 통계·정책·법률·민사 손해배상·전과 영향까지 정리한 기본 학습자료 (고등).',
 '🎓', '#6366f1', 30,
 '본 자료는 PDF로 제공됩니다. 본부 관리자 메뉴 → 학습자료 관리에서 PDF를 업로드해주세요.',
 TRUE),

-- 프리미엄 자료 placeholder (본부에서 PDF 업로드 시 활성화)
('premium-grooming-deep', 11, 'all', 'premium', 'grooming',
 '심화 — 디지털 그루밍 케이스 스터디',
 '실제 사례 기반 그루밍 단계 분석 + 대응 시나리오 (프리미엄).',
 '🔒', '#f59e0b', 40,
 NULL, FALSE),

('premium-copyright-law', 12, 'all', 'premium', 'copyright',
 '심화 — 청소년 저작권 침해 법률 가이드',
 '청소년이 저작권을 침해했을 때 형사처벌·민사 손해배상·전과 영향 상세 (프리미엄).',
 '⚖️', '#dc2626', 45,
 NULL, FALSE)
ON CONFLICT (slug) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'campaign_learning_materials' AS tbl, COUNT(*) AS rows
  FROM public.campaign_learning_materials;
-- 기대: 5행 (또는 그 이상)

SELECT slug, target_band, tier, is_active
  FROM public.campaign_learning_materials
 ORDER BY chapter_no;

SELECT routine_name FROM information_schema.routines
 WHERE routine_schema='public'
   AND routine_name IN (
       'check_premium_access','get_visible_materials','bump_material_view')
 ORDER BY routine_name;
-- 기대: 3행

-- 끝.
