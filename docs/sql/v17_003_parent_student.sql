-- ============================================================
-- DragonEyes v1.7 — 캠페인 시스템 Phase 1 (003/008)
-- 학부모 ↔ 학생 매칭 테이블 (다대다, 다자녀·다보호자 지원)
-- ============================================================
-- 적용일 : 2026-06-18
-- 목적   : 학부모가 자녀를 등록하고, 결제·모니터링 권한을 가짐.
--          1명 학부모 → N명 자녀 (다자녀)
--          1명 학생 → N명 보호자 (양친·후견인)
--
-- 검증 시나리오:
--   (A) 학부모가 기존 학생 매칭 신청 → 학생 본인 확인 → verified
--   (B) 학부모가 자녀 ID 신규 생성 → 즉시 verified (학부모 동의로 처리)
--   (C) 학교가 학생 일괄 등록 → 학부모는 별도 매칭 신청 필요
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- parent_student_links — 학부모-학생 연결
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.parent_student_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id       UUID NOT NULL,                      -- users.id (role_v2='parent')
    student_id      UUID NOT NULL,                      -- users.id (role_v2='student')

    -- 관계
    relationship    TEXT CHECK (relationship IN (
                        'mother', 'father', 'guardian', 'grandparent', 'other'
                    )),
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE,     -- 주 보호자 여부 (결제·동의 우선권)

    -- 학부모 동의 (학생 만 14세 미만 가입 시 필수)
    consent_at      TIMESTAMPTZ,
    consent_method  TEXT CHECK (consent_method IN (
                        'electronic',       -- 전자 동의 (사이트 내)
                        'document_upload',  -- 동의서 업로드
                        'self_create'       -- 학부모가 자녀 ID 직접 생성 (동의 갈음)
                    )),

    -- 매칭 검증 상태
    verification_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (verification_status IN ('pending', 'verified', 'rejected', 'cancelled')),
    verification_method TEXT CHECK (verification_method IN (
                        'student_confirm',  -- 학생이 사이트에서 확인 클릭
                        'parent_self_create', -- 학부모가 자녀 직접 생성 (자동 verified)
                        'institution_proof',-- 학교 명부 대조 (오프라인)
                        'admin_override'    -- 본부 admin 강제 매칭
                    )),
    verified_at     TIMESTAMPTZ,
    verified_by     UUID,                               -- 본부 admin (override 시)

    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 동일 학부모-학생 중복 매칭 방지
    UNIQUE (parent_id, student_id),

    CONSTRAINT psl_parent_fkey  FOREIGN KEY (parent_id)  REFERENCES public.users(id) ON DELETE CASCADE,
    CONSTRAINT psl_student_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_psl_parent_id   ON public.parent_student_links(parent_id);
CREATE INDEX IF NOT EXISTS idx_psl_student_id  ON public.parent_student_links(student_id);
CREATE INDEX IF NOT EXISTS idx_psl_status      ON public.parent_student_links(verification_status);
CREATE INDEX IF NOT EXISTS idx_psl_parent_primary
    ON public.parent_student_links(parent_id, is_primary)
    WHERE is_primary = TRUE;


-- ─────────────────────────────────────────────────────────────
-- updated_at 트리거
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_psl_updated_at ON public.parent_student_links;
CREATE TRIGGER trg_psl_updated_at
    BEFORE UPDATE ON public.parent_student_links
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 헬퍼 함수: 학부모의 verified 자녀 목록
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_verified_children(p_parent_id UUID)
RETURNS TABLE (
    student_id UUID,
    student_name TEXT,
    grade SMALLINT,
    school_name TEXT,
    relationship TEXT,
    is_primary BOOLEAN,
    verified_at TIMESTAMPTZ
) LANGUAGE SQL STABLE AS $$
    SELECT
        u.id, u.name, u.grade, u.school_name,
        psl.relationship, psl.is_primary, psl.verified_at
    FROM public.parent_student_links psl
    JOIN public.users u ON u.id = psl.student_id
    WHERE psl.parent_id = p_parent_id
      AND psl.verification_status = 'verified'
      AND u.deleted_at IS NULL
    ORDER BY psl.is_primary DESC, u.name;
$$;

-- 사용 예:
--   SELECT * FROM public.get_verified_children('<학부모-uuid>');


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'parent_student_links' AS tbl, COUNT(*) AS rows
FROM public.parent_student_links;

-- 기대: rows=0 (신규 테이블)

-- 끝.
