-- ═══════════════════════════════════════════════════════════════════
-- DragonEyes Migration: Phase 0 — 백업
-- ═══════════════════════════════════════════════════════════════════
-- 실행 시점: 다음주 마이그레이션 시작 직전
-- 실행 위치: Supabase SQL Editor
-- 예상 소요 시간: 1~2분
-- 위험도: 매우 낮음 (읽기만, 새 스키마 생성)
-- 롤백 방법: DROP SCHEMA backup_YYYYMMDD CASCADE;
-- ═══════════════════════════════════════════════════════════════════

-- 한국 시간 기준 오늘 날짜로 백업 스키마 이름 사용
-- 실행 전 아래 'YYYYMMDD'를 실제 날짜로 변경하세요 (예: 20260517)

BEGIN;

-- ───────────────────────────────────────────────────────────────────
-- Step 1: 백업 스키마 생성
-- ───────────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS backup_YYYYMMDD;

-- ───────────────────────────────────────────────────────────────────
-- Step 2: 영향 받는 테이블 백업 (CTAS = Create Table As Select)
-- ───────────────────────────────────────────────────────────────────

-- agencies (가장 중요 — partners로 마이그레이션됨)
CREATE TABLE backup_YYYYMMDD.agencies AS 
    SELECT * FROM public.agencies;

-- users (partner_id, customer_id 컬럼 추가됨)
CREATE TABLE backup_YYYYMMDD.users AS 
    SELECT * FROM public.users;

-- user_documents (FK 관계 변경 가능성)
CREATE TABLE backup_YYYYMMDD.user_documents AS 
    SELECT * FROM public.user_documents;

-- 추가로 안전하게 백업할 테이블들 (있으면 백업, 없으면 무시)
-- 좋아요님 시스템 상황에 따라 아래 중 일부만 적용

-- 모니터링 관련 (있으면 주석 해제)
-- CREATE TABLE backup_YYYYMMDD.analyzed_urls AS 
--     SELECT * FROM public.analyzed_urls;
-- CREATE TABLE backup_YYYYMMDD.learned_keywords AS 
--     SELECT * FROM public.learned_keywords;
-- CREATE TABLE backup_YYYYMMDD.monitoring_events AS 
--     SELECT * FROM public.monitoring_events;

-- 다운로드 로그 (감사 증거)
-- CREATE TABLE backup_YYYYMMDD.download_logs AS 
--     SELECT * FROM public.download_logs;

-- 지원 요청 (5/7 추가됨)
-- CREATE TABLE backup_YYYYMMDD.support_requests AS 
--     SELECT * FROM public.support_requests;

-- ───────────────────────────────────────────────────────────────────
-- Step 3: 권한 잠금 (좋아요님 본부 임원 외 접근 차단)
-- ───────────────────────────────────────────────────────────────────
REVOKE ALL ON SCHEMA backup_YYYYMMDD FROM PUBLIC;
REVOKE ALL ON SCHEMA backup_YYYYMMDD FROM authenticated;
REVOKE ALL ON SCHEMA backup_YYYYMMDD FROM anon;
REVOKE ALL ON ALL TABLES IN SCHEMA backup_YYYYMMDD FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA backup_YYYYMMDD FROM authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA backup_YYYYMMDD FROM anon;

ALTER DEFAULT PRIVILEGES IN SCHEMA backup_YYYYMMDD 
    REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA backup_YYYYMMDD 
    REVOKE ALL ON TABLES FROM authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA backup_YYYYMMDD 
    REVOKE ALL ON TABLES FROM anon;

COMMIT;

-- ═══════════════════════════════════════════════════════════════════
-- 검증 (별도 쿼리로 실행)
-- ═══════════════════════════════════════════════════════════════════

-- 백업 스키마 존재 확인
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name = 'backup_YYYYMMDD';
-- 기대: 1 row 반환

-- 백업된 테이블 목록 + 행 수 확인
SELECT 
    schemaname,
    tablename,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = schemaname AND table_name = tablename) AS column_count
FROM pg_tables 
WHERE schemaname = 'backup_YYYYMMDD'
ORDER BY tablename;

-- 행 수 비교 (원본 vs 백업) — agencies 예시
SELECT 
    'agencies original' AS source, COUNT(*) AS cnt FROM public.agencies
UNION ALL
SELECT 'agencies backup', COUNT(*) FROM backup_YYYYMMDD.agencies
UNION ALL
SELECT 'users original', COUNT(*) FROM public.users
UNION ALL
SELECT 'users backup', COUNT(*) FROM backup_YYYYMMDD.users;
-- 기대: original과 backup의 cnt가 같아야 함

-- 권한 확인 (모두 false여야 안전)
SELECT 
    'authenticated' AS role,
    has_schema_privilege('authenticated', 'backup_YYYYMMDD', 'USAGE') AS can_usage,
    has_schema_privilege('authenticated', 'backup_YYYYMMDD', 'CREATE') AS can_create
UNION ALL
SELECT 
    'anon',
    has_schema_privilege('anon', 'backup_YYYYMMDD', 'USAGE'),
    has_schema_privilege('anon', 'backup_YYYYMMDD', 'CREATE');

-- ═══════════════════════════════════════════════════════════════════
-- 롤백 (필요 시에만 실행 — 위험)
-- ═══════════════════════════════════════════════════════════════════
-- 백업 자체를 제거하려면:
-- DROP SCHEMA backup_YYYYMMDD CASCADE;
-- ⚠️ 주의: 한 번 DROP하면 복구 불가. Supabase 자동 백업으로만 복구 가능.

-- ═══════════════════════════════════════════════════════════════════
-- ✅ Phase 0 완료 후 다음 단계
-- ═══════════════════════════════════════════════════════════════════
-- 1. 위 검증 쿼리 모두 통과 확인
-- 2. Supabase Dashboard에서 자동 백업도 한 번 더 실행 (이중 안전망)
-- 3. phase1_create_tables.sql 실행 준비
