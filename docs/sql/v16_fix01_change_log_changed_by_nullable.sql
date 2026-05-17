-- ============================================================
-- DragonEyes v1.6 영업 거버넌스 — Fix 01
-- opportunity_change_log.changed_by NOT NULL 제거
-- ============================================================
-- 적용일 : 2026-05-17
-- 적용처 : 운영 Supabase (project xtqgxtdflemuphkzmzti) — SQL Editor 실행 완료
--
-- [문제]
--   영업 기회 거절(_reject_opportunity) 시 status 를 'closed_lost' 로 변경 →
--   트리거 log_opportunity_status_change() 가 opportunity_change_log 에 INSERT.
--   트리거는 changed_by 에 auth.uid() 를 넣는데, 이 앱은 Supabase Auth(JWT) 가
--   아닌 자체 로그인을 쓰므로 auth.uid() 가 항상 NULL.
--   → changed_by NOT NULL 제약 위반(23502) 으로 거절 처리 전체 실패.
--
-- [조치]
--   changed_by 를 nullable 로 변경. 트리거가 앱 사용자를 알 방법이 없으므로
--   NOT NULL 제약 자체가 부적절. "누가" 정보는 앱이 opportunity_status_log 에
--   실제 user id 로 별도 기록하므로 감사 추적은 유지됨.
--
-- [후속 검토 (미적용)]
--   opportunity_change_log(트리거) 와 opportunity_status_log(앱) 의 기능 중복.
--   트리거를 정리할지는 별도 결정 필요.
-- ============================================================

ALTER TABLE public.opportunity_change_log
    ALTER COLUMN changed_by DROP NOT NULL;
