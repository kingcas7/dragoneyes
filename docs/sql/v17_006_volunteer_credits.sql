-- ============================================================
-- DragonEyes v1.7 — 캠페인 시스템 Phase 1 (006/008)
-- 봉사 점수 시스템 (3가지 발급 방식)
-- ============================================================
-- 적용일 : 2026-06-18
-- 목적   : 학생이 설문 성실 완료 → 봉사 시간 발급.
--          교육부 한도 4~6시간 (240~360분).
--
-- 발급 모드 (issued_via):
--   pdf           = 드래곤아이즈 자체 PDF 인증서 (즉시)
--   1365          = 1365 봉사포털 연동 (관할 신고 완료 후)
--   school_batch  = 학교 일괄 전송 (교육기관 대시보드에서 CSV/PDF)
--
-- 한 응답(response)당 1건 봉사 점수 (UNIQUE 보장).
-- 발급 후 재발급 가능 (issued_via 변경 시 새 row, 이전 row 'superseded').
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. volunteer_credits — 봉사 점수 마스터
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.volunteer_credits (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL,                      -- users.id
    response_id     UUID NOT NULL UNIQUE                -- 응답 1건당 1 봉사
                        REFERENCES public.survey_responses(id) ON DELETE CASCADE,
    survey_id       UUID NOT NULL REFERENCES public.surveys(id) ON DELETE CASCADE,
    institution_id  UUID REFERENCES public.institutions(id) ON DELETE SET NULL,

    -- 발급 시간
    hours_decimal   NUMERIC(4,2) NOT NULL                -- 4.00, 5.50, 6.00
                        CHECK (hours_decimal BETWEEN 0.5 AND 12.0),
    minutes_total   INT GENERATED ALWAYS AS ((hours_decimal * 60)::INT) STORED,

    -- 성실도 (응답 시점 snapshot)
    integrity_score INT NOT NULL CHECK (integrity_score BETWEEN 0 AND 100),

    -- 상태
    status          TEXT NOT NULL DEFAULT 'earned'
        CHECK (status IN ('earned', 'issued', 'revoked', 'superseded')),

    -- 발급 정보
    issued_via      TEXT CHECK (issued_via IN ('pdf', '1365', 'school_batch')),
    issued_at       TIMESTAMPTZ,
    issued_by       UUID,                               -- 발급 처리자 (admin/system)

    -- 발급 결과
    certificate_url TEXT,                               -- PDF 인증서 URL
    certificate_no  TEXT UNIQUE,                        -- 인증서 번호 (재발급 추적)
    portal_1365_id  TEXT,                               -- 1365 봉사포털 등록 ID
    school_batch_id UUID,                               -- 학교 일괄 발급 batch ID

    -- 메타
    earned_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT vc_student_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vc_student     ON public.volunteer_credits(student_id);
CREATE INDEX IF NOT EXISTS idx_vc_survey      ON public.volunteer_credits(survey_id);
CREATE INDEX IF NOT EXISTS idx_vc_status      ON public.volunteer_credits(status);
CREATE INDEX IF NOT EXISTS idx_vc_issued_via  ON public.volunteer_credits(issued_via);
CREATE INDEX IF NOT EXISTS idx_vc_school_batch ON public.volunteer_credits(school_batch_id) WHERE school_batch_id IS NOT NULL;


-- ─────────────────────────────────────────────────────────────
-- 2. school_volunteer_batches — 학교 일괄 발급 묶음
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.school_volunteer_batches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id  UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    batch_name      TEXT NOT NULL,                      -- '2026년 1학기 봉사 일괄 발급'
    target_year     SMALLINT,
    target_semester SMALLINT CHECK (target_semester IN (1, 2)),

    -- 처리 상태
    status          TEXT NOT NULL DEFAULT 'preparing'
        CHECK (status IN ('preparing', 'ready', 'sent', 'completed', 'cancelled')),

    total_students  INT,
    total_hours     NUMERIC(10,2),
    export_format   TEXT CHECK (export_format IN ('csv', 'pdf', 'excel')),
    export_url      TEXT,
    sent_at         TIMESTAMPTZ,
    sent_to_email   TEXT,                               -- 학교 봉사 담당자 이메일

    created_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_svb_institution ON public.school_volunteer_batches(institution_id);
CREATE INDEX IF NOT EXISTS idx_svb_status      ON public.school_volunteer_batches(status);


-- ─────────────────────────────────────────────────────────────
-- 3. 학생별 누적 봉사 시간 조회 함수
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_student_volunteer_summary(p_student_id UUID)
RETURNS TABLE (
    total_hours NUMERIC,
    issued_hours NUMERIC,
    pending_hours NUMERIC,
    cert_count INT
) LANGUAGE SQL STABLE AS $$
    SELECT
        COALESCE(SUM(CASE WHEN status IN ('earned','issued') THEN hours_decimal END), 0) AS total_hours,
        COALESCE(SUM(CASE WHEN status = 'issued'             THEN hours_decimal END), 0) AS issued_hours,
        COALESCE(SUM(CASE WHEN status = 'earned'             THEN hours_decimal END), 0) AS pending_hours,
        COUNT(*) FILTER (WHERE status = 'issued')::INT                                   AS cert_count
    FROM public.volunteer_credits
    WHERE student_id = p_student_id
      AND status IN ('earned', 'issued');
$$;


-- ─────────────────────────────────────────────────────────────
-- 트리거
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_vc_updated_at ON public.volunteer_credits;
CREATE TRIGGER trg_vc_updated_at
    BEFORE UPDATE ON public.volunteer_credits
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

DROP TRIGGER IF EXISTS trg_svb_updated_at ON public.school_volunteer_batches;
CREATE TRIGGER trg_svb_updated_at
    BEFORE UPDATE ON public.school_volunteer_batches
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'volunteer_credits'         AS tbl, COUNT(*) AS rows FROM public.volunteer_credits
UNION ALL
SELECT 'school_volunteer_batches'  AS tbl, COUNT(*) FROM public.school_volunteer_batches;

-- 기대: 2개 행 rows=0

-- 끝.
