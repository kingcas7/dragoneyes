-- ============================================================
-- DragonEyes v1.6 — Fix 04
-- 모니터링 통계 인프라 (monitoring_events + 일배치 집계)
-- ============================================================
-- 적용일 : 2026-06-08
-- 적용처 : 운영 Supabase (project xtqgxtdflemuphkzmzti)
--          → Supabase SQL Editor에서 아래 전체 실행
--
-- [목적]
--   "📊 모니터링 통계" 페이지를 위한 raw 이벤트 로깅 + 일배치 집계 인프라.
--   설계: docs/v2.1_pending_additions.md §모니터링 통계 페이지
--
-- [추가 테이블]
--   monitoring_events       — 모든 분석/모니터링 이벤트 raw 기록
--   monitoring_daily_stats  — 일별·스코프별 집계 (대시보드용)
--   batch_job_runs          — pg_cron 배치 실행 추적
--
-- [후속]
--   - app.py: 텍스트/유튜브/네이버/디스코드 분석 시점에 INSERT
--   - 통계 페이지(4단계): SELECT FROM monitoring_daily_stats
--   - pg_cron: 자정 일배치 함수 자동 실행
-- ============================================================


-- ════════════════════════════════════════════════════════════
-- 1. monitoring_events — Raw 이벤트 로깅 테이블
-- ════════════════════════════════════════════════════════════
-- 모든 분석·모니터링·보고서 생성 이벤트를 시간순으로 적재.
-- 일배치 집계의 source.
-- 권한별 스코핑은 user_id / partner_id / company_id 컬럼으로 처리.

CREATE TABLE IF NOT EXISTS public.monitoring_events (
    id              uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      timestamptz   NOT NULL DEFAULT now(),

    -- 스코핑 필드 (권한별 범위 필터링용)
    user_id         uuid          REFERENCES public.users(id) ON DELETE SET NULL,
    partner_id      uuid          REFERENCES public.partners(id) ON DELETE SET NULL,
    company_id      uuid          ,  -- customer/company FK는 환경별 다를 수 있어 FK 미설정

    -- 이벤트 분류
    event_type      text          NOT NULL,
    -- 예: 'analyze_text', 'analyze_youtube', 'analyze_naver',
    --     'analyze_discord', 'report_create', 'report_action',
    --     'keyword_search', 'channel_monitor'
    platform        text          ,  -- 'youtube' / 'naver' / 'discord' / 'general'
    keyword         text          ,  -- 검색어 (있는 경우)

    -- 분석 결과
    severity        smallint      ,  -- 1~5 (1=안전, 5=매우위험)
    category        text          ,  -- '그루밍' / '도박' / '섹스토션' / '부적절' / '안전' 등
    target_url      text          ,  -- 분석 대상 URL (유튜브 영상, 네이버 카페글 등)
    is_action_completed boolean   DEFAULT false,  -- 보고서 작성·신고 완료 여부

    -- Raw 데이터
    result_json     jsonb         ,  -- 분석 결과 원본
    meta_json       jsonb         DEFAULT '{}'::jsonb  -- 추가 메타 (브라우저, IP, 세션 등)
);

-- 인덱스 — 통계 쿼리 패턴 기준
CREATE INDEX IF NOT EXISTS idx_mon_events_created_at
    ON public.monitoring_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mon_events_partner_created
    ON public.monitoring_events (partner_id, created_at DESC)
    WHERE partner_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mon_events_user_created
    ON public.monitoring_events (user_id, created_at DESC)
    WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mon_events_company_created
    ON public.monitoring_events (company_id, created_at DESC)
    WHERE company_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mon_events_event_type
    ON public.monitoring_events (event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mon_events_severity
    ON public.monitoring_events (severity)
    WHERE severity >= 3;  -- 심각 이상만 필터링 자주 함
CREATE INDEX IF NOT EXISTS idx_mon_events_keyword
    ON public.monitoring_events (keyword)
    WHERE keyword IS NOT NULL;

COMMENT ON TABLE public.monitoring_events IS
    'DragonEyes 모니터링·분석 이벤트 raw 로깅. 일배치 집계의 source.';


-- ════════════════════════════════════════════════════════════
-- 2. monitoring_daily_stats — 일별 집계 (대시보드용)
-- ════════════════════════════════════════════════════════════
-- 매일 자정 pg_cron이 monitoring_events를 집계해서 이 테이블로.
-- 통계 페이지는 이 테이블만 읽음 (raw 테이블 직접 쿼리 X → 빠름).
-- scope/scope_id로 권한별 캐시 분리.

CREATE TABLE IF NOT EXISTS public.monitoring_daily_stats (
    id              uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_date       date          NOT NULL,
    scope           text          NOT NULL,
    -- 'system'   — 전체 시스템 (본부용)
    -- 'partner'  — 파트너별 (파트너 관리자용)
    -- 'company'  — 고객사별 (고객 관리자용)
    -- 'user'     — 사용자별 (일반 사용자용)
    scope_id        uuid          ,  -- scope=system이면 NULL, 그 외 해당 ID

    -- KPI 4종
    total_analyses     integer    NOT NULL DEFAULT 0,  -- 총 분석 건수
    risk_found         integer    NOT NULL DEFAULT 0,  -- 위험 발견 (severity >= 3)
    action_completed   integer    NOT NULL DEFAULT 0,  -- 조치 완료 (보고서 작성)
    action_pending     integer    NOT NULL DEFAULT 0,  -- 미조치

    -- 상세 분포 (JSONB로 유연하게)
    by_category_json   jsonb      DEFAULT '{}'::jsonb,
    -- {"그루밍": 12, "도박": 8, "섹스토션": 3, ...}
    by_platform_json   jsonb      DEFAULT '{}'::jsonb,
    -- {"youtube": 45, "naver": 23, "discord": 5, "general": 12}
    by_severity_json   jsonb      DEFAULT '{}'::jsonb,
    -- {"1": 50, "2": 20, "3": 10, "4": 5, "5": 2}
    top_keywords_json  jsonb      DEFAULT '[]'::jsonb,
    -- [{"keyword": "초등학생 친구", "count": 5}, ...]
    new_keywords_json  jsonb      DEFAULT '[]'::jsonb,
    -- 신규 학습 후보 키워드

    -- 메타
    aggregated_at      timestamptz NOT NULL DEFAULT now(),

    -- 멱등성 보장
    CONSTRAINT uq_mon_daily_scope UNIQUE (stat_date, scope, scope_id)
);

CREATE INDEX IF NOT EXISTS idx_mon_daily_date
    ON public.monitoring_daily_stats (stat_date DESC);
CREATE INDEX IF NOT EXISTS idx_mon_daily_scope
    ON public.monitoring_daily_stats (scope, scope_id, stat_date DESC);

COMMENT ON TABLE public.monitoring_daily_stats IS
    '모니터링 일별 집계. 매일 자정 pg_cron이 monitoring_events에서 생성.';


-- ════════════════════════════════════════════════════════════
-- 3. batch_job_runs — pg_cron 배치 실행 추적
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.batch_job_runs (
    id              uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name        text          NOT NULL,
    target_date     date          ,  -- 어느 날짜 데이터 처리 (집계의 경우)
    started_at      timestamptz   NOT NULL DEFAULT now(),
    completed_at    timestamptz   ,
    status          text          NOT NULL DEFAULT 'running',
    -- 'running' / 'success' / 'failed'
    error_msg       text          ,
    rows_affected   integer       ,
    meta_json       jsonb         DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_batch_runs_job_started
    ON public.batch_job_runs (job_name, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_batch_runs_status
    ON public.batch_job_runs (status, started_at DESC);

COMMENT ON TABLE public.batch_job_runs IS
    'pg_cron / Railway Cron 배치 실행 추적. 헬스체크·디버깅용.';


-- ════════════════════════════════════════════════════════════
-- 4. 집계 함수 — run_daily_monitoring_aggregation(target_date)
-- ════════════════════════════════════════════════════════════
-- monitoring_events → monitoring_daily_stats 집계.
-- target_date의 데이터를 system / partner / company / user 스코프별로 생성.
-- ON CONFLICT로 멱등 (같은 날짜 재실행해도 안전).

CREATE OR REPLACE FUNCTION public.run_daily_monitoring_aggregation(p_date date)
RETURNS TABLE (scope text, rows_inserted integer)
LANGUAGE plpgsql
AS $$
DECLARE
    v_run_id uuid;
    v_total_rows integer := 0;
    v_scope_rows integer;
BEGIN
    -- 배치 실행 시작 기록
    INSERT INTO public.batch_job_runs (job_name, target_date, status)
    VALUES ('daily_monitoring_aggregation', p_date, 'running')
    RETURNING id INTO v_run_id;

    -- ── 1) system 스코프 (전체) ──
    INSERT INTO public.monitoring_daily_stats (
        stat_date, scope, scope_id,
        total_analyses, risk_found, action_completed, action_pending,
        by_category_json, by_platform_json, by_severity_json
    )
    SELECT
        p_date, 'system', NULL,
        COUNT(*)::int,
        COUNT(*) FILTER (WHERE severity >= 3)::int,
        COUNT(*) FILTER (WHERE is_action_completed = true)::int,
        COUNT(*) FILTER (WHERE severity >= 3 AND is_action_completed = false)::int,
        COALESCE(jsonb_object_agg(category, cat_cnt) FILTER (WHERE category IS NOT NULL), '{}'::jsonb),
        COALESCE(jsonb_object_agg(platform, plt_cnt) FILTER (WHERE platform IS NOT NULL), '{}'::jsonb),
        COALESCE(jsonb_object_agg(sev_text, sev_cnt) FILTER (WHERE sev_text IS NOT NULL), '{}'::jsonb)
    FROM (
        SELECT
            severity, is_action_completed, category, platform,
            severity::text AS sev_text,
            COUNT(*) OVER (PARTITION BY category) AS cat_cnt,
            COUNT(*) OVER (PARTITION BY platform) AS plt_cnt,
            COUNT(*) OVER (PARTITION BY severity) AS sev_cnt
        FROM public.monitoring_events
        WHERE created_at::date = p_date
    ) ev
    ON CONFLICT (stat_date, scope, scope_id) DO UPDATE SET
        total_analyses    = EXCLUDED.total_analyses,
        risk_found        = EXCLUDED.risk_found,
        action_completed  = EXCLUDED.action_completed,
        action_pending    = EXCLUDED.action_pending,
        by_category_json  = EXCLUDED.by_category_json,
        by_platform_json  = EXCLUDED.by_platform_json,
        by_severity_json  = EXCLUDED.by_severity_json,
        aggregated_at     = now();
    GET DIAGNOSTICS v_scope_rows = ROW_COUNT;
    v_total_rows := v_total_rows + v_scope_rows;
    scope := 'system'; rows_inserted := v_scope_rows; RETURN NEXT;

    -- ── 2) partner 스코프 ──
    INSERT INTO public.monitoring_daily_stats (
        stat_date, scope, scope_id,
        total_analyses, risk_found, action_completed, action_pending
    )
    SELECT
        p_date, 'partner', partner_id,
        COUNT(*)::int,
        COUNT(*) FILTER (WHERE severity >= 3)::int,
        COUNT(*) FILTER (WHERE is_action_completed = true)::int,
        COUNT(*) FILTER (WHERE severity >= 3 AND is_action_completed = false)::int
    FROM public.monitoring_events
    WHERE created_at::date = p_date AND partner_id IS NOT NULL
    GROUP BY partner_id
    ON CONFLICT (stat_date, scope, scope_id) DO UPDATE SET
        total_analyses    = EXCLUDED.total_analyses,
        risk_found        = EXCLUDED.risk_found,
        action_completed  = EXCLUDED.action_completed,
        action_pending    = EXCLUDED.action_pending,
        aggregated_at     = now();
    GET DIAGNOSTICS v_scope_rows = ROW_COUNT;
    v_total_rows := v_total_rows + v_scope_rows;
    scope := 'partner'; rows_inserted := v_scope_rows; RETURN NEXT;

    -- ── 3) company 스코프 ──
    INSERT INTO public.monitoring_daily_stats (
        stat_date, scope, scope_id,
        total_analyses, risk_found, action_completed, action_pending
    )
    SELECT
        p_date, 'company', company_id,
        COUNT(*)::int,
        COUNT(*) FILTER (WHERE severity >= 3)::int,
        COUNT(*) FILTER (WHERE is_action_completed = true)::int,
        COUNT(*) FILTER (WHERE severity >= 3 AND is_action_completed = false)::int
    FROM public.monitoring_events
    WHERE created_at::date = p_date AND company_id IS NOT NULL
    GROUP BY company_id
    ON CONFLICT (stat_date, scope, scope_id) DO UPDATE SET
        total_analyses    = EXCLUDED.total_analyses,
        risk_found        = EXCLUDED.risk_found,
        action_completed  = EXCLUDED.action_completed,
        action_pending    = EXCLUDED.action_pending,
        aggregated_at     = now();
    GET DIAGNOSTICS v_scope_rows = ROW_COUNT;
    v_total_rows := v_total_rows + v_scope_rows;
    scope := 'company'; rows_inserted := v_scope_rows; RETURN NEXT;

    -- ── 4) user 스코프 ──
    INSERT INTO public.monitoring_daily_stats (
        stat_date, scope, scope_id,
        total_analyses, risk_found, action_completed, action_pending
    )
    SELECT
        p_date, 'user', user_id,
        COUNT(*)::int,
        COUNT(*) FILTER (WHERE severity >= 3)::int,
        COUNT(*) FILTER (WHERE is_action_completed = true)::int,
        COUNT(*) FILTER (WHERE severity >= 3 AND is_action_completed = false)::int
    FROM public.monitoring_events
    WHERE created_at::date = p_date AND user_id IS NOT NULL
    GROUP BY user_id
    ON CONFLICT (stat_date, scope, scope_id) DO UPDATE SET
        total_analyses    = EXCLUDED.total_analyses,
        risk_found        = EXCLUDED.risk_found,
        action_completed  = EXCLUDED.action_completed,
        action_pending    = EXCLUDED.action_pending,
        aggregated_at     = now();
    GET DIAGNOSTICS v_scope_rows = ROW_COUNT;
    v_total_rows := v_total_rows + v_scope_rows;
    scope := 'user'; rows_inserted := v_scope_rows; RETURN NEXT;

    -- 배치 실행 완료 기록
    UPDATE public.batch_job_runs
       SET completed_at = now(),
           status = 'success',
           rows_affected = v_total_rows
     WHERE id = v_run_id;

    RETURN;

EXCEPTION WHEN OTHERS THEN
    UPDATE public.batch_job_runs
       SET completed_at = now(),
           status = 'failed',
           error_msg = SQLERRM
     WHERE id = v_run_id;
    RAISE;
END;
$$;

COMMENT ON FUNCTION public.run_daily_monitoring_aggregation(date) IS
    '특정 날짜의 monitoring_events를 monitoring_daily_stats로 집계. 멱등.';


-- ════════════════════════════════════════════════════════════
-- 5. 헬스체크 함수 — check_yesterday_batch_health()
-- ════════════════════════════════════════════════════════════
-- 어제 일배치가 정상 실행됐는지 확인.
-- 매일 09:00 (한국시간) pg_cron이 호출 → 실패면 알림 처리.

CREATE OR REPLACE FUNCTION public.check_yesterday_batch_health()
RETURNS TABLE (
    healthy boolean,
    last_run_status text,
    last_run_at timestamptz,
    rows_affected integer,
    error_msg text
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_yesterday date := (now() AT TIME ZONE 'Asia/Seoul')::date - 1;
BEGIN
    RETURN QUERY
    SELECT
        (status = 'success' AND completed_at > now() - interval '24 hours') AS healthy,
        status,
        COALESCE(completed_at, started_at),
        rows_affected,
        error_msg
    FROM public.batch_job_runs
    WHERE job_name = 'daily_monitoring_aggregation'
      AND target_date = v_yesterday
    ORDER BY started_at DESC
    LIMIT 1;
END;
$$;


-- ════════════════════════════════════════════════════════════
-- 6. pg_cron 등록 (Supabase Pro 이상에서만 작동)
-- ════════════════════════════════════════════════════════════
-- ⚠️ 이 섹션은 Supabase 프로젝트가 Pro tier 이상이고
--    pg_cron extension이 enable된 경우에만 적용됨.
--    Free tier는 수동 또는 Railway Cron으로 대체.
--
-- 실행 방법: Supabase Dashboard → Database → Extensions → pg_cron Enable
--           그 후 아래 SQL 실행.

-- 매일 KST 23:55 (UTC 14:55) → 그날 데이터 집계
-- SELECT cron.schedule(
--     'daily_monitoring_aggregation',
--     '55 14 * * *',  -- UTC 14:55 = KST 23:55
--     $$SELECT public.run_daily_monitoring_aggregation((now() AT TIME ZONE 'Asia/Seoul')::date)$$
-- );

-- 매일 KST 09:00 (UTC 00:00) → 어제 집계 헬스체크
-- SELECT cron.schedule(
--     'monitoring_batch_healthcheck',
--     '0 0 * * *',  -- UTC 00:00 = KST 09:00
--     $$SELECT public.check_yesterday_batch_health()$$
-- );


-- ════════════════════════════════════════════════════════════
-- 검증 쿼리 (적용 후 실행)
-- ════════════════════════════════════════════════════════════
-- SELECT table_name FROM information_schema.tables
--  WHERE table_schema='public'
--    AND table_name IN ('monitoring_events', 'monitoring_daily_stats', 'batch_job_runs');
-- → 3행 나와야 정상.
--
-- SELECT proname FROM pg_proc
--  WHERE proname IN ('run_daily_monitoring_aggregation', 'check_yesterday_batch_health');
-- → 2행 나와야 정상.
--
-- 수동 테스트:
-- SELECT * FROM public.run_daily_monitoring_aggregation(CURRENT_DATE);
-- → scope별 rows_inserted 4행 (system/partner/company/user)
