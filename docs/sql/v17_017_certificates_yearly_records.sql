-- ============================================================
-- DragonEyes v1.7 — Phase 10 추가 (017)
-- 봉사활동 인증서 (영구·재발급) + 년도별 캠페인 기록 + 매년 담당자 갱신
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   1) 학생 봉사활동 인증서 = 영구 보존 + 언제든 재출력
--      - 발급 시점 스냅샷 (학교명·학생명·발급자 등) — 학생 전학/학교명 변경에도 인증서 원본 유지
--      - 재출력 시 시리얼·QR 검증 가능
--      - 본인 + 재학 중인 학교의 담당자(institution_admin) + 담임 모두 조회/PDF 출력 가능
--   2) 캠페인 년도별 기록 자동 보관 (연말 archive)
--   3) 교육기관 매년 담당자 갱신 (등록 한 번 → 다음년도 담당자만 변경 또는 유지)
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. volunteer_certificates — 봉사활동 인증서 (영구)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.volunteer_certificates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 시리얼 번호 (검증/위변조 방지)
    -- 형식: DE-YYYY-NNNNNNNN  예: DE-2026-00001234
    serial_no       TEXT NOT NULL UNIQUE,

    -- 원 봉사기록 연결 (지워져도 인증서는 유지 — SET NULL)
    credit_id       UUID REFERENCES public.volunteer_credits(id) ON DELETE SET NULL,

    -- 학생 (FK, 학생 탈퇴 시도 인증서는 유지)
    student_id      UUID REFERENCES public.users(id) ON DELETE SET NULL,

    -- 발급 시점 스냅샷 (학교 이름/학생 이름 등은 그 당시 정보로 영구 보존)
    snapshot_student_name      TEXT NOT NULL,
    snapshot_student_birth     DATE,
    snapshot_school_name       TEXT NOT NULL,
    snapshot_school_address    TEXT,
    snapshot_school_id         UUID REFERENCES public.institutions(id) ON DELETE SET NULL,
    snapshot_grade             SMALLINT,
    snapshot_class_no          SMALLINT,

    -- 봉사 내역 스냅샷
    hours_decimal              NUMERIC(4,2) NOT NULL,
    activity_title             TEXT NOT NULL DEFAULT '온라인 유해컨텐츠 근절 캠페인 참여',
    activity_description       TEXT,
    activity_period_start      DATE,
    activity_period_end        DATE,

    -- 발급자 (학교 도장/사인 — 학교장 또는 담당자)
    issuer_name                TEXT NOT NULL,
    issuer_title               TEXT,                              -- 학교장/교감/담당교사
    issuer_user_id             UUID REFERENCES public.users(id) ON DELETE SET NULL,
    issued_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 재출력 추적
    reprint_count              INT NOT NULL DEFAULT 0,
    last_reprinted_at          TIMESTAMPTZ,

    -- 상태
    status                     TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','revoked','superseded')),
    revoked_at                 TIMESTAMPTZ,
    revoked_reason             TEXT,

    -- 검증 토큰 (QR 코드 — 외부에서 인증서 진위 확인용)
    verify_token               TEXT NOT NULL DEFAULT encode(gen_random_bytes(16), 'hex'),

    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vcert_student     ON public.volunteer_certificates(student_id);
CREATE INDEX IF NOT EXISTS idx_vcert_school      ON public.volunteer_certificates(snapshot_school_id);
CREATE INDEX IF NOT EXISTS idx_vcert_serial      ON public.volunteer_certificates(serial_no);
CREATE INDEX IF NOT EXISTS idx_vcert_status      ON public.volunteer_certificates(status);
CREATE INDEX IF NOT EXISTS idx_vcert_issued_at   ON public.volunteer_certificates(issued_at);
CREATE INDEX IF NOT EXISTS idx_vcert_verify      ON public.volunteer_certificates(verify_token);


-- ─────────────────────────────────────────────────────────────
-- 2. serial_no 자동 생성 함수
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.gen_certificate_serial()
RETURNS TEXT LANGUAGE plpgsql AS $$
DECLARE
    v_year TEXT := TO_CHAR(NOW(), 'YYYY');
    v_seq  INT;
BEGIN
    SELECT COUNT(*) + 1
    INTO v_seq
    FROM public.volunteer_certificates
    WHERE serial_no LIKE 'DE-' || v_year || '-%';

    RETURN 'DE-' || v_year || '-' || LPAD(v_seq::TEXT, 8, '0');
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 3. 인증서 발급 (issue) — volunteer_credits.status='issued'가 되면 호출
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.issue_volunteer_certificate(
    p_credit_id    UUID,
    p_issuer_user_id UUID,
    p_issuer_name  TEXT DEFAULT NULL,
    p_issuer_title TEXT DEFAULT NULL,
    p_activity_period_start DATE DEFAULT NULL,
    p_activity_period_end   DATE DEFAULT NULL
) RETURNS UUID LANGUAGE plpgsql AS $$
DECLARE
    v_cert_id   UUID;
    v_serial    TEXT;
    v_credit    public.volunteer_credits;
    v_student   public.users;
    v_school    public.institutions;
    v_issuer    public.users;
BEGIN
    -- 봉사기록 조회
    SELECT * INTO v_credit FROM public.volunteer_credits WHERE id = p_credit_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'volunteer_credits not found: %', p_credit_id;
    END IF;

    -- 학생 + 학교
    SELECT * INTO v_student FROM public.users WHERE id = v_credit.student_id;
    SELECT * INTO v_school  FROM public.institutions WHERE id = v_student.institution_id;
    SELECT * INTO v_issuer  FROM public.users WHERE id = p_issuer_user_id;

    -- 중복 발급 방지 (active 상태로 이미 발급된 게 있으면 그 id 리턴)
    SELECT id INTO v_cert_id
    FROM public.volunteer_certificates
    WHERE credit_id = p_credit_id AND status = 'active'
    LIMIT 1;
    IF FOUND THEN
        RETURN v_cert_id;
    END IF;

    -- 시리얼 생성
    v_serial := public.gen_certificate_serial();

    -- 인증서 INSERT
    INSERT INTO public.volunteer_certificates (
        serial_no, credit_id, student_id,
        snapshot_student_name, snapshot_student_birth,
        snapshot_school_name, snapshot_school_address, snapshot_school_id,
        snapshot_grade, snapshot_class_no,
        hours_decimal,
        activity_description,
        activity_period_start, activity_period_end,
        issuer_name, issuer_title, issuer_user_id
    ) VALUES (
        v_serial, p_credit_id, v_credit.student_id,
        COALESCE(v_student.name, '미상'),
        v_student.birth_date,
        COALESCE(v_school.name, '미상'),
        v_school.address,
        v_student.institution_id,
        v_student.grade,
        v_student.class_no,
        v_credit.hours_decimal,
        v_credit.note,
        p_activity_period_start,
        p_activity_period_end,
        COALESCE(p_issuer_name, v_issuer.name, '학교 담당자'),
        COALESCE(p_issuer_title, '담당자'),
        p_issuer_user_id
    )
    RETURNING id INTO v_cert_id;

    -- volunteer_credits 상태도 'issued'로 동기화 (이미 그 상태면 noop)
    UPDATE public.volunteer_credits
    SET status = 'issued', issued_at = NOW(), updated_at = NOW()
    WHERE id = p_credit_id AND status <> 'issued';

    RETURN v_cert_id;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 4. 재출력 카운터 증가
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.bump_certificate_reprint(p_cert_id UUID)
RETURNS VOID LANGUAGE SQL AS $$
    UPDATE public.volunteer_certificates
       SET reprint_count = reprint_count + 1,
           last_reprinted_at = NOW()
     WHERE id = p_cert_id AND status = 'active';
$$;


-- ─────────────────────────────────────────────────────────────
-- 5. 학생 본인의 인증서 list
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_my_certificates(p_student_id UUID)
RETURNS TABLE (
    id UUID,
    serial_no TEXT,
    snapshot_student_name TEXT,
    snapshot_school_name TEXT,
    snapshot_grade SMALLINT,
    snapshot_class_no SMALLINT,
    hours_decimal NUMERIC,
    activity_title TEXT,
    issuer_name TEXT,
    issuer_title TEXT,
    issued_at TIMESTAMPTZ,
    status TEXT,
    reprint_count INT
) LANGUAGE SQL STABLE AS $$
    SELECT
        id, serial_no,
        snapshot_student_name, snapshot_school_name,
        snapshot_grade, snapshot_class_no,
        hours_decimal, activity_title,
        issuer_name, issuer_title,
        issued_at, status, reprint_count
    FROM public.volunteer_certificates
    WHERE student_id = p_student_id
      AND status = 'active'
    ORDER BY issued_at DESC;
$$;


-- ─────────────────────────────────────────────────────────────
-- 6. 학교 담당자/담임용 — 학교 전체 인증서 조회
-- ─────────────────────────────────────────────────────────────
-- 학교 admin: 전체 학생 인증서 조회 가능
-- 담임 (teacher_role='homeroom'): 자기 반(grade+class_no) 학생만
-- p_viewer_user_id 의 teacher_charge.classes 를 기준으로 필터링 (담임)
CREATE OR REPLACE FUNCTION public.get_school_certificates(
    p_viewer_user_id UUID,
    p_inst_id        UUID DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    serial_no TEXT,
    student_id UUID,
    student_name TEXT,
    grade SMALLINT,
    class_no SMALLINT,
    school_name TEXT,
    hours_decimal NUMERIC,
    activity_title TEXT,
    issuer_name TEXT,
    issued_at TIMESTAMPTZ,
    status TEXT,
    reprint_count INT
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_viewer    public.users;
    v_inst_id   UUID;
    v_is_homeroom BOOLEAN := FALSE;
    v_classes   JSONB;
BEGIN
    SELECT * INTO v_viewer FROM public.users WHERE id = p_viewer_user_id;

    -- 권한 확인: institution_admin 또는 admin
    IF v_viewer.role_v2 NOT IN ('institution_admin','admin') THEN
        RETURN;
    END IF;

    v_inst_id := COALESCE(p_inst_id, v_viewer.institution_id);
    IF v_inst_id IS NULL THEN
        RETURN;
    END IF;

    -- 담임 여부 판단
    IF v_viewer.teacher_role = 'homeroom' AND v_viewer.teacher_charge IS NOT NULL THEN
        v_is_homeroom := TRUE;
        v_classes := v_viewer.teacher_charge -> 'classes';
    END IF;

    RETURN QUERY
    SELECT
        c.id, c.serial_no,
        c.student_id,
        c.snapshot_student_name,
        c.snapshot_grade,
        c.snapshot_class_no,
        c.snapshot_school_name,
        c.hours_decimal,
        c.activity_title,
        c.issuer_name,
        c.issued_at,
        c.status,
        c.reprint_count
    FROM public.volunteer_certificates c
    WHERE c.snapshot_school_id = v_inst_id
      AND c.status = 'active'
      AND (
        -- 담임이 아니면 학교 전체 (institution_admin/admin 모두)
        NOT v_is_homeroom
        -- 담임이면 본인 담임 반만
        OR EXISTS (
            SELECT 1 FROM jsonb_array_elements(v_classes) AS cls
            WHERE (cls ->> 'grade')::INT = c.snapshot_grade
              AND (cls ->> 'class_no')::INT = c.snapshot_class_no
              AND (cls ->> 'subject') = '담임'
        )
      )
    ORDER BY c.snapshot_grade, c.snapshot_class_no, c.snapshot_student_name, c.issued_at DESC;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 7. campaign_year_archives — 년도별 캠페인 기록 자동 보관
-- ─────────────────────────────────────────────────────────────
-- 매년 말 (또는 학년도 종료 시) 학교별 캠페인 통계를 snapshot으로 저장
-- 이후 어느 시점에 조회해도 그 해의 기록이 그대로 나옴
CREATE TABLE IF NOT EXISTS public.campaign_year_archives (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id  UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    school_year     INT NOT NULL CHECK (school_year BETWEEN 2024 AND 2100),

    -- 학교 정보 스냅샷
    snapshot_school_name TEXT NOT NULL,
    snapshot_region      TEXT,
    snapshot_district    TEXT,

    -- 통계 스냅샷
    student_count           INT NOT NULL DEFAULT 0,
    survey_completed_count  INT NOT NULL DEFAULT 0,
    completion_rate         NUMERIC(5,2) NOT NULL DEFAULT 0,
    total_hours             NUMERIC(10,2) NOT NULL DEFAULT 0,
    issued_hours            NUMERIC(10,2) NOT NULL DEFAULT 0,
    certificate_count       INT NOT NULL DEFAULT 0,
    lecture_count           INT NOT NULL DEFAULT 0,
    parent_subscription_cnt INT NOT NULL DEFAULT 0,

    -- 원본 데이터 (필요시 상세 조회용)
    raw_data        JSONB,

    archived_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_by     UUID REFERENCES public.users(id) ON DELETE SET NULL,

    UNIQUE (institution_id, school_year)
);

CREATE INDEX IF NOT EXISTS idx_cya_inst_year ON public.campaign_year_archives(institution_id, school_year);
CREATE INDEX IF NOT EXISTS idx_cya_year      ON public.campaign_year_archives(school_year);


-- ─────────────────────────────────────────────────────────────
-- 8. 캠페인 년도별 기록 archive 생성 함수
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.archive_campaign_year(
    p_inst_id    UUID,
    p_school_year INT,
    p_archived_by UUID DEFAULT NULL
) RETURNS UUID LANGUAGE plpgsql AS $$
DECLARE
    v_archive_id UUID;
    v_inst       public.institutions;
    v_stu_cnt    INT;
    v_survey_cnt INT;
    v_compl_rate NUMERIC;
    v_total_hrs  NUMERIC;
    v_issued_hrs NUMERIC;
    v_cert_cnt   INT;
    v_lec_cnt    INT;
    v_psub_cnt   INT;
    v_year_start TIMESTAMPTZ;
    v_year_end   TIMESTAMPTZ;
BEGIN
    SELECT * INTO v_inst FROM public.institutions WHERE id = p_inst_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'institution not found'; END IF;

    -- 학년도 = 3월 1일 ~ 다음해 2월 28일
    v_year_start := MAKE_TIMESTAMPTZ(p_school_year,     3, 1, 0, 0, 0);
    v_year_end   := MAKE_TIMESTAMPTZ(p_school_year + 1, 3, 1, 0, 0, 0);

    -- 학생 수
    SELECT COUNT(*) INTO v_stu_cnt
    FROM public.users
    WHERE institution_id = p_inst_id
      AND role_v2 = 'student'
      AND deleted_at IS NULL;

    -- 설문 완료
    SELECT COUNT(DISTINCT sr.student_id) INTO v_survey_cnt
    FROM public.survey_responses sr
    JOIN public.users u ON u.id = sr.student_id
    WHERE u.institution_id = p_inst_id
      AND sr.status = 'completed'
      AND sr.completed_at >= v_year_start
      AND sr.completed_at < v_year_end;

    v_compl_rate := CASE WHEN v_stu_cnt > 0 THEN ROUND(v_survey_cnt::NUMERIC / v_stu_cnt * 100, 2) ELSE 0 END;

    -- 봉사 시간 (해당 학년도)
    SELECT
        COALESCE(SUM(hours_decimal) FILTER (WHERE status IN ('earned','issued')), 0),
        COALESCE(SUM(hours_decimal) FILTER (WHERE status = 'issued'), 0)
    INTO v_total_hrs, v_issued_hrs
    FROM public.volunteer_credits vc
    JOIN public.users u ON u.id = vc.student_id
    WHERE u.institution_id = p_inst_id
      AND vc.created_at >= v_year_start
      AND vc.created_at < v_year_end;

    -- 인증서 발급 수
    SELECT COUNT(*) INTO v_cert_cnt
    FROM public.volunteer_certificates
    WHERE snapshot_school_id = p_inst_id
      AND issued_at >= v_year_start
      AND issued_at < v_year_end
      AND status = 'active';

    -- 강연 수
    SELECT COUNT(*) INTO v_lec_cnt
    FROM public.institution_lectures
    WHERE institution_id = p_inst_id
      AND status = 'completed'
      AND COALESCE(completed_at, scheduled_at) >= v_year_start
      AND COALESCE(completed_at, scheduled_at) < v_year_end;

    -- 학부모 구독
    SELECT COUNT(DISTINCT ps.parent_id) INTO v_psub_cnt
    FROM public.parent_subscriptions ps
    JOIN public.parent_student_links psl ON psl.parent_id = ps.parent_id
    JOIN public.users s ON s.id = psl.student_id
    WHERE s.institution_id = p_inst_id
      AND ps.status = 'active'
      AND ps.started_at >= v_year_start
      AND ps.started_at < v_year_end;

    -- UPSERT
    INSERT INTO public.campaign_year_archives (
        institution_id, school_year,
        snapshot_school_name, snapshot_region, snapshot_district,
        student_count, survey_completed_count, completion_rate,
        total_hours, issued_hours, certificate_count, lecture_count,
        parent_subscription_cnt, archived_by
    ) VALUES (
        p_inst_id, p_school_year,
        v_inst.name, v_inst.region, v_inst.district,
        v_stu_cnt, v_survey_cnt, v_compl_rate,
        v_total_hrs, v_issued_hrs, v_cert_cnt, v_lec_cnt,
        v_psub_cnt, p_archived_by
    )
    ON CONFLICT (institution_id, school_year) DO UPDATE
    SET snapshot_school_name = EXCLUDED.snapshot_school_name,
        student_count = EXCLUDED.student_count,
        survey_completed_count = EXCLUDED.survey_completed_count,
        completion_rate = EXCLUDED.completion_rate,
        total_hours = EXCLUDED.total_hours,
        issued_hours = EXCLUDED.issued_hours,
        certificate_count = EXCLUDED.certificate_count,
        lecture_count = EXCLUDED.lecture_count,
        parent_subscription_cnt = EXCLUDED.parent_subscription_cnt,
        archived_at = NOW(),
        archived_by = EXCLUDED.archived_by
    RETURNING id INTO v_archive_id;

    RETURN v_archive_id;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 9. institution_renewals — 매년 담당자 갱신 이력
-- ─────────────────────────────────────────────────────────────
-- 교육기관은 1번만 등록 (institutions.status='approved' 유지)
-- 매년 새 학기 시작 시 담당자 정보만 변경(or 유지) → 이력 row 추가
CREATE TABLE IF NOT EXISTS public.institution_renewals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id  UUID NOT NULL REFERENCES public.institutions(id) ON DELETE CASCADE,
    school_year     INT NOT NULL CHECK (school_year BETWEEN 2024 AND 2100),

    -- 담당자 정보
    contact_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    contact_name    TEXT NOT NULL,
    contact_title   TEXT,                                      -- 교감/생활부장/담당교사 등
    contact_phone   TEXT,
    contact_email   TEXT,

    -- 갱신 유형
    renewal_type    TEXT NOT NULL DEFAULT 'continue'
        CHECK (renewal_type IN ('continue','change','skip')),
    note            TEXT,

    renewed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    renewed_by      UUID REFERENCES public.users(id) ON DELETE SET NULL,

    UNIQUE (institution_id, school_year)
);

CREATE INDEX IF NOT EXISTS idx_ir_inst_year ON public.institution_renewals(institution_id, school_year);


-- ─────────────────────────────────────────────────────────────
-- 10. 갱신 현황 조회 (해당 학년도에 갱신했는지)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_renewal_status(p_inst_id UUID, p_school_year INT)
RETURNS TABLE (
    is_renewed BOOLEAN,
    renewal_type TEXT,
    contact_name TEXT,
    contact_title TEXT,
    renewed_at TIMESTAMPTZ
) LANGUAGE SQL STABLE AS $$
    SELECT
        TRUE AS is_renewed,
        renewal_type,
        contact_name,
        contact_title,
        renewed_at
    FROM public.institution_renewals
    WHERE institution_id = p_inst_id
      AND school_year = p_school_year
    UNION ALL
    SELECT FALSE, NULL::TEXT, NULL::TEXT, NULL::TEXT, NULL::TIMESTAMPTZ
    WHERE NOT EXISTS (
        SELECT 1 FROM public.institution_renewals
        WHERE institution_id = p_inst_id AND school_year = p_school_year
    )
    LIMIT 1;
$$;


-- ─────────────────────────────────────────────────────────────
-- 11. 트리거 (updated_at)
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_vcert_updated_at ON public.volunteer_certificates;
CREATE TRIGGER trg_vcert_updated_at
    BEFORE UPDATE ON public.volunteer_certificates
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'volunteer_certificates' AS tbl, COUNT(*) AS rows FROM public.volunteer_certificates
UNION ALL
SELECT 'campaign_year_archives',          COUNT(*) FROM public.campaign_year_archives
UNION ALL
SELECT 'institution_renewals',            COUNT(*) FROM public.institution_renewals;
-- 기대: 모두 rows=0

SELECT routine_name FROM information_schema.routines
WHERE routine_schema='public'
  AND routine_name IN (
      'gen_certificate_serial',
      'issue_volunteer_certificate',
      'bump_certificate_reprint',
      'get_my_certificates',
      'get_school_certificates',
      'archive_campaign_year',
      'get_renewal_status'
  )
ORDER BY routine_name;
-- 기대: 7행

-- 끝.
