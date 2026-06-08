-- ============================================================
-- DragonEyes v1.6 — Fix 03
-- users 테이블: preferences JSONB 컬럼 추가 (시각장애인 접근성)
-- ============================================================
-- 적용일 : 2026-06-08
-- 적용처 : 운영 Supabase (project xtqgxtdflemuphkzmzti)
--          → Supabase SQL Editor에서 아래 ALTER 실행
--
-- [목적]
--   시각장애인 접근성 음성 안내 기능을 위해 users 테이블에
--   사용자 선호 설정 저장용 preferences JSONB 컬럼 추가.
--   v2.1_pending_additions.md 음성 안내 시스템 설계 §설정 저장 위치 반영.
--
-- [추가 컬럼]
--   preferences  jsonb   DEFAULT '{}'::jsonb
--     예: {
--           "voice_guide_enabled": true,
--           "voice_speed": 1.0,
--           "voice_lang": "ko-KR"
--         }
--
-- [후속 사용처]
--   - accessibility.py 모듈 (load_from_user / save_to_user)
--   - 로그인 페이지·홈 페이지 상단의 음성 안내 토글
--   - 추후 통계 페이지·모니터링 페이지에서 음성 안내 사용
--   - 향후 다른 사용자 선호 항목 추가 시 동일 컬럼 활용
--     (테마, 폰트 크기, 알림 설정 등)
--
-- [안전성]
--   - IF NOT EXISTS로 멱등성 보장
--   - DEFAULT '{}'::jsonb로 기존 행에는 빈 객체 자동 채움
--   - NOT NULL 미설정 (선택적 사용)
-- ============================================================

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS preferences jsonb DEFAULT '{}'::jsonb;

-- 기존 NULL 행을 빈 객체로 보정 (멱등)
UPDATE public.users
   SET preferences = '{}'::jsonb
 WHERE preferences IS NULL;

-- 인덱스 (선호 키별 필터링 가능성 대비, 작은 비용)
CREATE INDEX IF NOT EXISTS idx_users_preferences_gin
    ON public.users USING gin (preferences);
