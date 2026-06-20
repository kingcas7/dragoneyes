-- ============================================================
-- DragonEyes v1.7 — Phase 10 추가 (018)
-- 인증서 자동 발급 트리거 (설문 N개 응답 → 봉사시간 + 인증서)
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   학생 설문 토큰의 response_count가 임계값 도달 시 자동으로:
--     1) volunteer_credits INSERT (hours_decimal = 학년대별)
--     2) volunteer_certificates 자동 발급 (issue_volunteer_certificate)
--   임계값:
--     초등 (elementary) → 20응답 → 4.0h
--     중학 (middle)     → 30응답 → 5.0h
--     고등 (high)       → 50응답 → 6.0h
--   중복 발급 방지 — student_id 당 active 인증서 1장만 자동 생성
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. 학년대별 자동 발급 임계값 조회
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_cert_threshold(p_band TEXT)
RETURNS TABLE (
    threshold INT,
    hours_award NUMERIC(4,2)
) LANGUAGE SQL IMMUTABLE AS $$
    SELECT * FROM (VALUES
        ('elementary', 20, 4.0::NUMERIC(4,2)),
        ('middle',     30, 5.0::NUMERIC(4,2)),
        ('high',       50, 6.0::NUMERIC(4,2))
    ) AS t(band, threshold, hours_award)
    WHERE band = p_band;
$$;


-- ─────────────────────────────────────────────────────────────
-- 2. 자동 발급 트리거 함수
-- ─────────────────────────────────────────────────────────────
-- student_survey_tokens UPDATE 후 호출 (AFTER UPDATE OF response_count)
CREATE OR REPLACE FUNCTION public.trg_auto_issue_certificate()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_band         TEXT;
    v_threshold    INT;
    v_hours        NUMERIC(4,2);
    v_already_cert UUID;
    v_credit_id    UUID;
    v_student      public.users;
    v_issuer_id    UUID;
BEGIN
    -- response_count 증가가 아니면 skip
    IF NEW.response_count IS NULL THEN RETURN NEW; END IF;
    IF OLD.response_count IS NOT NULL AND NEW.response_count <= OLD.response_count THEN
        RETURN NEW;
    END IF;

    -- 학년대 판정
    v_band := public.get_student_band(NEW.student_id);
    IF v_band IS NULL OR v_band NOT IN ('elementary','middle','high') THEN
        RETURN NEW;
    END IF;

    -- 임계값 조회
    SELECT t.threshold, t.hours_award
      INTO v_threshold, v_hours
      FROM public.get_cert_threshold(v_band) AS t;

    IF NEW.response_count < v_threshold THEN
        RETURN NEW;
    END IF;

    -- 이미 자동 발급된 active 인증서 존재? (중복 방지)
    SELECT id INTO v_already_cert
      FROM public.volunteer_certificates
     WHERE student_id = NEW.student_id
       AND status = 'active'
       AND activity_description LIKE '%[AUTO]%'
     LIMIT 1;
    IF v_already_cert IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- 학생 정보
    SELECT * INTO v_student FROM public.users WHERE id = NEW.student_id;

    -- volunteer_credits INSERT (status='earned')
    INSERT INTO public.volunteer_credits (
        student_id, institution_id, survey_id,
        hours_decimal, status, issued_via,
        note
    ) VALUES (
        NEW.student_id,
        v_student.institution_id,
        NEW.survey_id,
        v_hours,
        'earned',
        'auto_survey',
        format('[AUTO] %s 학년대 자동 발급 (응답 %s개 도달)', v_band, NEW.response_count)
    ) RETURNING id INTO v_credit_id;

    -- 발급자 = 시스템 (드래곤아이즈 본사 admin 1명 자동 선택)
    SELECT id INTO v_issuer_id
      FROM public.users
     WHERE role_v2 = 'admin'
       AND deleted_at IS NULL
     ORDER BY created_at
     LIMIT 1;

    -- 인증서 발급
    PERFORM public.issue_volunteer_certificate(
        v_credit_id,
        v_issuer_id,
        '드래곤아이즈 주식회사',
        '대표이사'
    );

    -- volunteer_certificates 의 activity_description 에 [AUTO] 마커 추가
    UPDATE public.volunteer_certificates
       SET activity_description = COALESCE(activity_description,'') || ' [AUTO]'
     WHERE credit_id = v_credit_id;

    RETURN NEW;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 3. 트리거 등록
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_sst_auto_cert ON public.student_survey_tokens;
CREATE TRIGGER trg_sst_auto_cert
    AFTER UPDATE OF response_count ON public.student_survey_tokens
    FOR EACH ROW
    EXECUTE FUNCTION public.trg_auto_issue_certificate();


-- ─────────────────────────────────────────────────────────────
-- 4. 수동 강제 발급 (이미 임계값 넘은 학생들 일괄 처리용)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.backfill_auto_certificates()
RETURNS TABLE (
    student_id UUID,
    band TEXT,
    response_count INT,
    issued_cert_id UUID
) LANGUAGE plpgsql AS $$
DECLARE
    r RECORD;
    v_threshold INT;
    v_hours NUMERIC(4,2);
    v_band TEXT;
    v_credit_id UUID;
    v_cert_id UUID;
    v_issuer_id UUID;
    v_stu public.users;
BEGIN
    SELECT id INTO v_issuer_id FROM public.users
     WHERE role_v2='admin' AND deleted_at IS NULL ORDER BY created_at LIMIT 1;

    FOR r IN
        SELECT sst.student_id, sst.survey_id, sst.response_count
          FROM public.student_survey_tokens sst
         WHERE sst.response_count > 0
    LOOP
        v_band := public.get_student_band(r.student_id);
        IF v_band IS NULL OR v_band NOT IN ('elementary','middle','high') THEN CONTINUE; END IF;
        SELECT t.threshold, t.hours_award INTO v_threshold, v_hours
          FROM public.get_cert_threshold(v_band) AS t;
        IF r.response_count < v_threshold THEN CONTINUE; END IF;

        -- 이미 자동 발급 됐는지 확인
        IF EXISTS (
            SELECT 1 FROM public.volunteer_certificates
             WHERE student_id = r.student_id
               AND status='active'
               AND activity_description LIKE '%[AUTO]%'
        ) THEN CONTINUE; END IF;

        SELECT * INTO v_stu FROM public.users WHERE id = r.student_id;

        INSERT INTO public.volunteer_credits (
            student_id, institution_id, survey_id, hours_decimal,
            status, issued_via, note
        ) VALUES (
            r.student_id, v_stu.institution_id, r.survey_id, v_hours,
            'earned','auto_survey',
            format('[AUTO] %s 학년대 backfill (응답 %s개)', v_band, r.response_count)
        ) RETURNING id INTO v_credit_id;

        v_cert_id := public.issue_volunteer_certificate(
            v_credit_id, v_issuer_id,
            '드래곤아이즈 주식회사', '대표이사'
        );
        UPDATE public.volunteer_certificates
           SET activity_description = COALESCE(activity_description,'') || ' [AUTO]'
         WHERE id = v_cert_id;

        student_id := r.student_id;
        band := v_band;
        response_count := r.response_count;
        issued_cert_id := v_cert_id;
        RETURN NEXT;
    END LOOP;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
-- 1) 임계값 확인
SELECT 'elementary' AS band, * FROM public.get_cert_threshold('elementary')
UNION ALL
SELECT 'middle',                * FROM public.get_cert_threshold('middle')
UNION ALL
SELECT 'high',                  * FROM public.get_cert_threshold('high');
-- 기대: 초 20/4.0, 중 30/5.0, 고 50/6.0

-- 2) 트리거 등록 확인
SELECT trigger_name, event_manipulation, action_timing
  FROM information_schema.triggers
 WHERE event_object_table = 'student_survey_tokens'
   AND trigger_name = 'trg_sst_auto_cert';
-- 기대: 1행

-- 3) 함수 등록 확인
SELECT routine_name FROM information_schema.routines
 WHERE routine_schema='public'
   AND routine_name IN ('get_cert_threshold','trg_auto_issue_certificate','backfill_auto_certificates')
 ORDER BY routine_name;
-- 기대: 3행

-- 4) (선택) 기존 데이터 backfill 실행 — 이미 임계값 넘은 학생 자동 발급
-- SELECT * FROM public.backfill_auto_certificates();

-- 끝.
