-- ============================================================
-- DragonEyes v1.7 — 캠페인 시스템 Phase 1 (002/008)
-- 교육기관 마스터 + 등록 신청 큐
-- ============================================================
-- 적용일 : 2026-06-18
-- 목적   : 교육부 / 시도교육청 / 전국 초·중·고 / 인가 교육시설을
--          본부 수동 등록 + 공공데이터 NEIS 매칭 모두 지원.
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. institutions — 교육기관 마스터
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.institutions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type            TEXT NOT NULL CHECK (type IN (
                        'ministry',         -- 교육부
                        'metro_office',     -- 시·도 교육청
                        'district_office',  -- 교육지원청
                        'elementary',       -- 초등학교
                        'middle',           -- 중학교
                        'high',             -- 고등학교
                        'special',          -- 특수학교
                        'youth_facility',   -- 교육부 인가 청소년 교육시설
                        'other'             -- 기타 정규 교육기관
                    )),
    name            TEXT NOT NULL,
    code            TEXT,                   -- 학교 표준 코드 (NEIS school code 등)
    neis_id         TEXT,                   -- 공공데이터 매칭 시 NEIS 학교 ID
    region          TEXT,                   -- 시도 (서울/경기/...)
    district        TEXT,                   -- 시군구
    address         TEXT,
    phone           TEXT,
    email           TEXT,
    homepage_url    TEXT,
    representative  TEXT,                   -- 교장/대표자 이름

    -- 등록 / 검증 상태
    verification_source TEXT NOT NULL DEFAULT 'manual'
        CHECK (verification_source IN ('manual', 'neis', 'edit', 'import')),
    status          TEXT NOT NULL DEFAULT 'approved'
        CHECK (status IN ('pending', 'approved', 'suspended', 'rejected')),
    approved_at     TIMESTAMPTZ,
    approved_by     UUID,                   -- users.id (본부 승인자)

    -- 메타
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,            -- soft delete

    UNIQUE (type, name, region, district)   -- 동일 지역 동일명 중복 방지
);

CREATE INDEX IF NOT EXISTS idx_institutions_type      ON public.institutions(type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_institutions_region    ON public.institutions(region) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_institutions_status    ON public.institutions(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_institutions_neis_id   ON public.institutions(neis_id) WHERE neis_id IS NOT NULL;
-- 학교명 검색은 일반 B-tree + LIKE 'name%' 으로 충분. fuzzy 검색이 필요해지면
-- 별도 SQL로 pg_trgm + GIN 인덱스 추가 (Supabase extensions 스키마 명시 필요).
CREATE INDEX IF NOT EXISTS idx_institutions_name      ON public.institutions(name) WHERE deleted_at IS NULL;


-- ─────────────────────────────────────────────────────────────
-- 2. institution_requests — 등록·수정·삭제 신청 큐
-- ─────────────────────────────────────────────────────────────
-- 교육기관 관리자가 신청 → 본부 admin 승인 워크플로우.
-- request_type:
--   add    = 신규 등록 신청 (institution_id NULL)
--   update = 기존 기관 정보 수정 신청
--   delete = 기관 삭제 신청
CREATE TABLE IF NOT EXISTS public.institution_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id  UUID,                   -- 기존 기관 ID (add면 NULL)
    request_type    TEXT NOT NULL CHECK (request_type IN ('add', 'update', 'delete')),
    requested_by    UUID NOT NULL,          -- 신청자 user_id
    requested_data  JSONB NOT NULL,         -- 폼 데이터 스냅샷
    note            TEXT,                   -- 신청자 메모

    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    processed_by    UUID,                   -- 본부 처리자 user_id
    processed_at    TIMESTAMPTZ,
    process_note    TEXT,                   -- 본부 처리 메모

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inst_req_status      ON public.institution_requests(status);
CREATE INDEX IF NOT EXISTS idx_inst_req_requested_by ON public.institution_requests(requested_by);


-- ─────────────────────────────────────────────────────────────
-- 3. updated_at 자동 갱신 트리거
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public._set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_institutions_updated_at ON public.institutions;
CREATE TRIGGER trg_institutions_updated_at
    BEFORE UPDATE ON public.institutions
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_inst_req_updated_at ON public.institution_requests;
CREATE TRIGGER trg_inst_req_updated_at
    BEFORE UPDATE ON public.institution_requests
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 4. users.institution_id ↔ institutions FK 연결
-- ─────────────────────────────────────────────────────────────
ALTER TABLE public.users
    ADD CONSTRAINT users_institution_id_fkey
    FOREIGN KEY (institution_id) REFERENCES public.institutions(id)
    ON DELETE SET NULL
    DEFERRABLE INITIALLY IMMEDIATE
    NOT VALID;  -- 기존 데이터에 미적용 (안전), 신규 INSERT/UPDATE만 검증

ALTER TABLE public.users VALIDATE CONSTRAINT users_institution_id_fkey;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'institutions'         AS tbl, COUNT(*) AS rows FROM public.institutions
UNION ALL
SELECT 'institution_requests' AS tbl, COUNT(*) AS rows FROM public.institution_requests;

-- 기대: 두 행 모두 rows=0 (신규 테이블)

-- 끝.
