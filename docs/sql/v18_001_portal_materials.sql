-- ============================================================
-- DragonEyes v1.8 — 직원·파트너 포털 (001)
-- 홈페이지(dragoneyes.co.kr) 로그인 → 포털 자료실
-- ============================================================
-- 적용일 : 2026-07-19
-- 목적   :
--   - 직원·파트너 전용 포털의 교육/영업 자료실 메타데이터
--   - 파일 실체는 Storage 'Documents' 버킷 portal/ 경로 (기존 패턴)
--   - 모니터링/캠페인 일반 사용자는 포털 로그인 자체가 차단됨(앱 레벨)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.portal_materials (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category         TEXT NOT NULL CHECK (category IN ('edu', 'sales')),
    title            TEXT NOT NULL,
    description      TEXT,
    file_name        TEXT,              -- 업로드 파일명 (링크형이면 NULL)
    file_url         TEXT,              -- Storage signed URL (1년)
    file_path        TEXT,              -- Storage 경로 (URL 재발급용)
    link_url         TEXT,              -- 외부 링크형 자료 (영상 등)
    sort_no          INT  NOT NULL DEFAULT 0,
    uploaded_by      UUID,
    uploaded_by_name TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_portal_materials_cat
    ON public.portal_materials (category, sort_no, created_at DESC);

-- 기존 운영 테이블과 동일 정책 (앱 레벨 권한 제어)
ALTER TABLE public.portal_materials DISABLE ROW LEVEL SECURITY;
