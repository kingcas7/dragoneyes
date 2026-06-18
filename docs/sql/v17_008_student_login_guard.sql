-- ============================================================
-- DragonEyes v1.7 — 캠페인 시스템 Phase 1 (008/008)
-- 학생 사용자 모니터링 사이트 로그인·접근 차단 가드
-- ============================================================
-- 적용일 : 2026-06-18
-- 목적   : 학생(role_v2='student') 사용자가 유해 컨텐츠 모니터링
--          시스템에 접근하지 못하도록 DB 측에서도 명시적 차단.
--          (앱 측 라우팅 가드는 Phase 2에서 별도 구현)
--
-- 사용자 결정 (C 답변):
--   '학생에게 부여된 ID는 모니터링 사이트에 로그인이 안되게 차단해줘.
--    학생은 그냥 온라인 유해컨텐츠 근절 캠페인 쪽만 접근 할 수 있어.'
--
-- 사용자 결정 (D 답변):
--   '모니터링 통계는 모든 사용자(학생포함)가 공유 할수 있게 해줘.'
--   → 학생도 monitoring_stats 페이지는 볼 수 있음 (통계만, 원본 데이터 X)
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. is_campaign_student — 학생 여부 판단 헬퍼
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.is_campaign_student(p_user_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE AS $$
    SELECT COALESCE(
        (SELECT role_v2 = 'student' OR is_campaign_only = TRUE
         FROM public.users
         WHERE id = p_user_id),
        FALSE
    );
$$;

COMMENT ON FUNCTION public.is_campaign_student(UUID)
    IS '학생 사용자 여부 — 모니터링 데이터 접근 차단 가드용';


-- ─────────────────────────────────────────────────────────────
-- 2. can_access_monitoring — 모니터링 사이트 접근 가능 여부
-- ─────────────────────────────────────────────────────────────
-- 학생만 차단. 그 외 모든 role은 모니터링 접근 가능.
-- (교육기관 사용자·학부모는 같은 ID로 모니터링 사용 가능 — 사용자 결정 #9)
CREATE OR REPLACE FUNCTION public.can_access_monitoring(p_user_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE AS $$
    SELECT NOT public.is_campaign_student(p_user_id);
$$;


-- ─────────────────────────────────────────────────────────────
-- 3. can_access_monitoring_stats — 모니터링 통계 페이지 (학생도 OK)
-- ─────────────────────────────────────────────────────────────
-- 사용자 결정 D: 모니터링 통계는 모든 사용자(학생 포함) 공유.
-- 정부/공인기관 제공 자료라 학생도 조회 가능.
CREATE OR REPLACE FUNCTION public.can_access_monitoring_stats(p_user_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.users
        WHERE id = p_user_id AND deleted_at IS NULL
    );
$$;


-- ─────────────────────────────────────────────────────────────
-- 4. v_user_access_summary — 사용자별 접근 권한 요약 view
-- ─────────────────────────────────────────────────────────────
-- 디버깅·관리 콘솔에서 사용.
CREATE OR REPLACE VIEW public.v_user_access_summary AS
SELECT
    u.id,
    u.email,
    u.name,
    u.role_v2,
    u.is_campaign_only,
    public.is_campaign_student(u.id)         AS is_student,
    public.can_access_monitoring(u.id)       AS can_monitor,
    public.can_access_monitoring_stats(u.id) AS can_view_stats,
    CASE
        WHEN public.is_campaign_student(u.id) THEN 'campaign_only'
        WHEN u.role_v2 IN ('institution_admin','parent') THEN 'campaign + monitoring'
        ELSE 'monitoring (기존 사용자)'
    END AS access_zone
FROM public.users u
WHERE u.deleted_at IS NULL;


-- ─────────────────────────────────────────────────────────────
-- 5. trigger: 학생 사용자 생성 시 is_campaign_only 자동 강제
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public._enforce_student_campaign_only() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.role_v2 = 'student' THEN
        NEW.is_campaign_only := TRUE;
    END IF;
    RETURN NEW;
END$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_student_guard ON public.users;
CREATE TRIGGER trg_user_student_guard
    BEFORE INSERT OR UPDATE OF role_v2 ON public.users
    FOR EACH ROW EXECUTE FUNCTION public._enforce_student_campaign_only();


-- ─────────────────────────────────────────────────────────────
-- 6. RLS 정책 예시 (참고 — 활성화는 별도 검토)
-- ─────────────────────────────────────────────────────────────
-- 아래는 모니터링 핵심 테이블에 Row Level Security를 적용해
-- 학생이 직접 DB 쿼리하더라도 데이터를 못 보게 막는 정책 예시.
-- 운영 정책 확정 후 ENABLE.
--
-- ALTER TABLE public.analyzed_urls ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY block_students_on_analyzed_urls
--     ON public.analyzed_urls
--     FOR ALL
--     USING (NOT public.is_campaign_student(auth.uid()));
--
-- ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY block_students_on_reports
--     ON public.reports
--     FOR ALL
--     USING (NOT public.is_campaign_student(auth.uid()));


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
-- 함수 등록 확인
SELECT routine_name, data_type AS returns
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
      'is_campaign_student',
      'can_access_monitoring',
      'can_access_monitoring_stats'
  )
ORDER BY routine_name;
-- 기대: 3개 행

-- view 확인
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public' AND table_name = 'v_user_access_summary';
-- 기대: 1개 행

-- 트리거 확인
SELECT trigger_name FROM information_schema.triggers
WHERE event_object_schema = 'public'
  AND event_object_table = 'users'
  AND trigger_name = 'trg_user_student_guard';
-- 기대: 1개 행

-- 끝.
