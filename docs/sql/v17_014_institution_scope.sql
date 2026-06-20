-- ============================================================
-- DragonEyes v1.7 — Phase 10 보강 (014)
-- 교육기관 권한 scope (계층 + 지역) — 상·하급 + 수평 데이터 공유
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   상급 기관(교육부/시·도 교육청/교육지원청)이 산하 학교들의 캠페인 통계
--   조회 + 같은 지역 학교들 간 수평 공유. 학생 개인정보는 본교만, 집계
--   통계는 상급 기관/지역 동급 기관과 공유.
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. get_institution_scope — 기관의 권한 범위 판정
-- ─────────────────────────────────────────────────────────────
-- 반환: 'nation' / 'metro' / 'district' / 'school' / NULL
CREATE OR REPLACE FUNCTION public.get_institution_scope(p_inst_id UUID)
RETURNS TEXT LANGUAGE SQL STABLE AS $$
    SELECT CASE
        WHEN type = 'ministry'                                   THEN 'nation'
        WHEN type IN ('metro_office', 'metro_council')           THEN 'metro'
        WHEN type IN ('district_office', 'local_council')        THEN 'district'
        WHEN type IN ('elementary','middle','high','special',
                      'youth_facility','other')                  THEN 'school'
        ELSE NULL
    END
    FROM public.institutions
    WHERE id = p_inst_id AND deleted_at IS NULL;
$$;


-- ─────────────────────────────────────────────────────────────
-- 2. get_visible_institutions — 권한 범위 내 모든 학교 list
-- ─────────────────────────────────────────────────────────────
-- 계층 기반 (상→하) + 수평 (같은 지역 동급) 모두 포함.
-- school 단위는 본교만, 상급은 권한 범위 전체.
CREATE OR REPLACE FUNCTION public.get_visible_institutions(p_inst_id UUID)
RETURNS TABLE (
    id UUID,
    name TEXT,
    type TEXT,
    region TEXT,
    district TEXT,
    address TEXT,
    status TEXT
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_scope TEXT;
    v_region TEXT;
    v_district TEXT;
BEGIN
    SELECT i.region, i.district INTO v_region, v_district
    FROM public.institutions i
    WHERE i.id = p_inst_id AND i.deleted_at IS NULL;

    v_scope := public.get_institution_scope(p_inst_id);

    IF v_scope = 'nation' THEN
        -- 교육부: 전국 모든 학교
        RETURN QUERY
            SELECT i.id, i.name, i.type, i.region, i.district, i.address, i.status
            FROM public.institutions i
            WHERE i.deleted_at IS NULL
              AND i.type IN ('elementary','middle','high','special','youth_facility');
    ELSIF v_scope = 'metro' THEN
        -- 시·도 교육청 / 시·도의회 교육위: 같은 시·도 내 모든 학교 + 교육지원청
        RETURN QUERY
            SELECT i.id, i.name, i.type, i.region, i.district, i.address, i.status
            FROM public.institutions i
            WHERE i.deleted_at IS NULL
              AND i.region = v_region
              AND i.type IN ('elementary','middle','high','special','youth_facility',
                             'district_office','local_council');
    ELSIF v_scope = 'district' THEN
        -- 교육지원청 / 시·군·구의회 교육위: 같은 시·군·구 내 학교
        RETURN QUERY
            SELECT i.id, i.name, i.type, i.region, i.district, i.address, i.status
            FROM public.institutions i
            WHERE i.deleted_at IS NULL
              AND i.region = v_region
              AND (i.district = v_district OR v_district IS NULL)
              AND i.type IN ('elementary','middle','high','special','youth_facility');
    ELSE
        -- school 등 그 외: 본교만
        RETURN QUERY
            SELECT i.id, i.name, i.type, i.region, i.district, i.address, i.status
            FROM public.institutions i
            WHERE i.id = p_inst_id;
    END IF;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 3. get_peer_institutions — 같은 지역 동급 기관 (수평 공유)
-- ─────────────────────────────────────────────────────────────
-- 같은 시·도 내 같은 학교급 학교들. 학교 간 횡적 통계 비교 용도.
CREATE OR REPLACE FUNCTION public.get_peer_institutions(p_inst_id UUID)
RETURNS TABLE (
    id UUID,
    name TEXT,
    type TEXT,
    region TEXT,
    district TEXT
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_type TEXT;
    v_region TEXT;
BEGIN
    SELECT i.type, i.region INTO v_type, v_region
    FROM public.institutions i
    WHERE i.id = p_inst_id AND i.deleted_at IS NULL;

    IF v_type IN ('elementary','middle','high','special') AND v_region IS NOT NULL THEN
        RETURN QUERY
            SELECT i.id, i.name, i.type, i.region, i.district
            FROM public.institutions i
            WHERE i.deleted_at IS NULL
              AND i.region = v_region
              AND i.type = v_type
              AND i.status = 'approved';
    END IF;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 4. get_campaign_stats_by_institution — 학교별 캠페인 통계 (집계만, 개인정보 X)
-- ─────────────────────────────────────────────────────────────
-- 입력 학교 list에 대한 학생 수, 봉사 점수 합계, 설문 완료율 반환.
-- 상급 기관/지역 동급 공유 시 사용 — 개별 학생 정보는 노출 안 함.
CREATE OR REPLACE FUNCTION public.get_campaign_stats_for_inst(p_inst_id UUID)
RETURNS TABLE (
    inst_id UUID,
    inst_name TEXT,
    inst_type TEXT,
    region TEXT,
    district TEXT,
    student_count BIGINT,
    survey_completed_count BIGINT,
    completion_rate NUMERIC,
    total_hours NUMERIC,
    issued_hours NUMERIC,
    friend_response_count BIGINT
) LANGUAGE SQL STABLE AS $$
    WITH visible AS (
        SELECT * FROM public.get_visible_institutions(p_inst_id)
    ),
    student_summary AS (
        SELECT
            u.institution_id,
            COUNT(*)::BIGINT AS student_count
        FROM public.users u
        WHERE u.role_v2 = 'student' AND u.deleted_at IS NULL
          AND u.institution_id IN (SELECT id FROM visible)
        GROUP BY u.institution_id
    ),
    survey_summary AS (
        SELECT
            u.institution_id,
            COUNT(DISTINCT sr.student_id)::BIGINT AS completed_count
        FROM public.survey_responses sr
        JOIN public.users u ON u.id = sr.student_id
        WHERE sr.status = 'completed'
          AND u.institution_id IN (SELECT id FROM visible)
        GROUP BY u.institution_id
    ),
    vc_summary AS (
        SELECT
            vc.institution_id,
            COALESCE(SUM(vc.hours_decimal) FILTER (WHERE vc.status IN ('earned','issued')), 0) AS total_hours,
            COALESCE(SUM(vc.hours_decimal) FILTER (WHERE vc.status = 'issued'), 0) AS issued_hours
        FROM public.volunteer_credits vc
        WHERE vc.institution_id IN (SELECT id FROM visible)
        GROUP BY vc.institution_id
    ),
    token_summary AS (
        SELECT
            u.institution_id,
            COALESCE(SUM(sst.response_count), 0)::BIGINT AS friend_resp
        FROM public.student_survey_tokens sst
        JOIN public.users u ON u.id = sst.student_id
        WHERE u.institution_id IN (SELECT id FROM visible)
        GROUP BY u.institution_id
    )
    SELECT
        v.id, v.name, v.type, v.region, v.district,
        COALESCE(ss.student_count, 0)                      AS student_count,
        COALESCE(sv.completed_count, 0)                    AS survey_completed_count,
        CASE WHEN COALESCE(ss.student_count, 0) > 0
            THEN ROUND(COALESCE(sv.completed_count, 0)::NUMERIC / ss.student_count * 100, 1)
            ELSE 0
        END                                                AS completion_rate,
        COALESCE(vs.total_hours, 0)                        AS total_hours,
        COALESCE(vs.issued_hours, 0)                       AS issued_hours,
        COALESCE(ts.friend_resp, 0)                        AS friend_response_count
    FROM visible v
    LEFT JOIN student_summary  ss ON ss.institution_id = v.id
    LEFT JOIN survey_summary   sv ON sv.institution_id = v.id
    LEFT JOIN vc_summary       vs ON vs.institution_id = v.id
    LEFT JOIN token_summary    ts ON ts.institution_id = v.id
    WHERE v.type IN ('elementary','middle','high','special','youth_facility')
    ORDER BY v.region, v.district, v.name;
$$;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
-- 1) scope 함수 테스트 (서울특별시교육청 → metro)
SELECT name, type, public.get_institution_scope(id) AS scope
FROM public.institutions
WHERE code IN ('GOV-MOE','METRO-OFFICE-11','METRO-COUNCIL-11')
ORDER BY type;
-- 기대:
--   교육부               | ministry      | nation
--   서울특별시교육청     | metro_office  | metro
--   서울특별시의회 교육위 | metro_council | metro

-- 2) 시·도 교육청이 보는 학교 수 (서울)
SELECT COUNT(*) AS visible_count
FROM public.get_visible_institutions(
    (SELECT id FROM public.institutions WHERE code = 'METRO-OFFICE-11')
);
-- 기대: 서울 내 학교 + 교육지원청 + 시·군·구의회 (현재 학교 데이터 없으면 0)

-- 3) 함수 등록 확인
SELECT routine_name FROM information_schema.routines
WHERE routine_schema='public'
  AND routine_name IN (
      'get_institution_scope',
      'get_visible_institutions',
      'get_peer_institutions',
      'get_campaign_stats_for_inst'
  )
ORDER BY routine_name;
-- 기대: 4개 행

-- 끝.
