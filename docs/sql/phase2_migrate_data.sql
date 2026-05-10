-- ═══════════════════════════════════════════════════════════════════
-- DragonEyes Migration: Phase 2 — 데이터 복사 (agencies → partners)
-- ═══════════════════════════════════════════════════════════════════
-- 실행 시점: phase1_create_tables.sql 검증 완료 후
-- 실행 위치: Supabase SQL Editor
-- 예상 소요 시간: 1~3분
-- 위험도: 중간 (데이터 INSERT/UPDATE)
-- 롤백: 본 파일 맨 아래 ROLLBACK 섹션 참조
-- ═══════════════════════════════════════════════════════════════════
-- ⚠️ 실행 전 확인:
--   1. phase1 완료 + 검증 통과
--   2. Streamlit 앱 일시 정지 권장 (데이터 정합성)
--   3. 백업 스키마 정상 (롤백 대비)
-- ═══════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════
-- 사전 점검 (READ ONLY)
-- ═══════════════════════════════════════════════════════════════════

-- 활성 agencies 수
SELECT 
    COUNT(*) FILTER (WHERE deleted_at IS NULL) AS active_agencies,
    COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted_agencies,
    COUNT(*) AS total
FROM public.agencies;

-- agency_id가 있는 활성 사용자 수
SELECT 
    COUNT(*) FILTER (WHERE agency_id IS NOT NULL AND deleted_at IS NULL) AS users_with_agency,
    COUNT(*) FILTER (WHERE deleted_at IS NULL) AS total_active_users
FROM public.users;

-- 이미 partner_id 채워진 사용자가 있는지 (이전 마이그레이션 잔재)
SELECT COUNT(*) FROM public.users WHERE partner_id IS NOT NULL;
-- 기대: 0 (Phase 1에서는 컬럼만 추가)

-- ═══════════════════════════════════════════════════════════════════
-- 메인 마이그레이션
-- ═══════════════════════════════════════════════════════════════════

BEGIN;

-- ───────────────────────────────────────────────────────────────────
-- Step 1: agencies → partners 복사
-- ───────────────────────────────────────────────────────────────────
-- 정책: 모든 기존 agencies는 일단 "직접계약 대리점 (영업 가능)"으로 분류
-- 이후 좋아요님이 수동으로 총판/유관기관 재분류

INSERT INTO public.partners (
    name, 
    business_number, 
    representative_name, 
    address, 
    phone, 
    email,
    is_distributor, 
    is_reseller, 
    is_related_org,
    business_channel,
    has_sales_contract,
    sales_contract_active_from,
    legacy_agency_id,
    created_at
)
SELECT 
    a.name,
    a.business_number,
    a.representative_name,
    a.address,
    a.phone,
    a.email,
    -- 기본 분류: 직접계약 대리점
    false,                          -- is_distributor (수동 재분류 필요)
    true,                           -- is_reseller
    false,                          -- is_related_org
    'reseller_direct',              -- business_channel
    true,                           -- has_sales_contract (기존은 모두 영업 가능)
    a.created_at::date,             -- 기존 가입일을 계약 시작일로
    a.id,                           -- legacy_agency_id (역추적용)
    a.created_at
FROM public.agencies a
WHERE a.deleted_at IS NULL
  AND NOT EXISTS (                  -- 멱등성 (재실행 안전)
      SELECT 1 FROM public.partners p 
      WHERE p.legacy_agency_id = a.id
  );

-- ───────────────────────────────────────────────────────────────────
-- Step 2: users.partner_id 채우기
-- ───────────────────────────────────────────────────────────────────

UPDATE public.users u
SET partner_id = p.id
FROM public.partners p
WHERE p.legacy_agency_id = u.agency_id
  AND u.agency_id IS NOT NULL
  AND u.deleted_at IS NULL
  AND u.partner_id IS NULL;        -- 이미 채워졌으면 스킵 (멱등성)

-- ───────────────────────────────────────────────────────────────────
-- Step 3: Workspace 멤버십 자동 생성 (partner 기반)
-- ───────────────────────────────────────────────────────────────────

INSERT INTO public.workspace_memberships (
    user_id, 
    partner_id, 
    role_in_workspace, 
    is_default
)
SELECT 
    u.id,
    u.partner_id,
    CASE u.role
        WHEN 'admin' THEN 'admin'
        WHEN 'agency_admin' THEN 'admin'      -- 레거시 호환
        WHEN 'partner_admin' THEN 'admin'
        ELSE 'member'
    END,
    true                                       -- 기본 워크스페이스
FROM public.users u
WHERE u.partner_id IS NOT NULL
  AND u.deleted_at IS NULL
  AND NOT EXISTS (                             -- 멱등성
      SELECT 1 FROM public.workspace_memberships wm
      WHERE wm.user_id = u.id 
        AND wm.partner_id = u.partner_id
  );

COMMIT;

-- ═══════════════════════════════════════════════════════════════════
-- 검증 (별도 실행)
-- ═══════════════════════════════════════════════════════════════════

-- ⓐ 복사 누락 확인
SELECT 
    'agencies (active)' AS source, 
    COUNT(*) AS cnt 
FROM public.agencies 
WHERE deleted_at IS NULL
UNION ALL
SELECT 
    'partners (from legacy)', 
    COUNT(*) 
FROM public.partners 
WHERE legacy_agency_id IS NOT NULL;
-- 기대: 두 cnt가 같아야 함

-- ⓑ 사용자 partner_id 마이그레이션 비율
SELECT 
    COUNT(*) FILTER (WHERE partner_id IS NOT NULL AND deleted_at IS NULL) AS migrated,
    COUNT(*) FILTER (WHERE agency_id IS NOT NULL AND deleted_at IS NULL) AS had_agency,
    COUNT(*) FILTER (WHERE deleted_at IS NULL) AS total_active,
    ROUND(100.0 * COUNT(*) FILTER (WHERE partner_id IS NOT NULL AND deleted_at IS NULL) 
          / NULLIF(COUNT(*) FILTER (WHERE agency_id IS NOT NULL AND deleted_at IS NULL), 0), 2) 
        AS migration_rate_pct
FROM public.users;
-- 기대: migrated = had_agency, migration_rate_pct = 100.00

-- ⓒ Workspace 자동 생성 확인
SELECT 
    COUNT(*) AS total_memberships,
    COUNT(*) FILTER (WHERE is_default = true) AS default_count,
    COUNT(DISTINCT user_id) AS unique_users
FROM public.workspace_memberships
WHERE left_at IS NULL;
-- 기대: total = default = unique_users (각 사용자에 1개 기본 ws)

-- ⓓ 박광남 케이스 검증 (5/10에 agency_id NULL 처리한 본부 관리자)
SELECT 
    email, 
    role, 
    agency_id, 
    partner_id,
    customer_id
FROM public.users
WHERE email = 'toast1234@naver.com';
-- 기대: agency_id NULL, partner_id NULL (본부 관리자는 워크스페이스 없음)

-- ⓔ 위드루트 케이스 검증 (5/10에 soft delete 한 3명)
SELECT 
    email, 
    role,
    deleted_at IS NOT NULL AS is_deleted,
    partner_id IS NULL AS partner_unset
FROM public.users
WHERE email IN ('coalacoco@hanmail.net', 'laco8@naver.com', 'rbtax@naver.com');
-- 기대: 3명 모두 is_deleted=true, partner_unset=true

-- ⓕ 마이그레이션 추적 (legacy_agency_id 매핑)
SELECT 
    a.name AS agency_name,
    a.id AS agency_id,
    p.id AS partner_id,
    p.business_channel,
    p.partnership_status
FROM public.agencies a
JOIN public.partners p ON p.legacy_agency_id = a.id
WHERE a.deleted_at IS NULL
ORDER BY a.created_at;
-- 모든 활성 agency가 매핑되어 있는지 확인

-- ═══════════════════════════════════════════════════════════════════
-- 수동 후속 작업 (검증 통과 후)
-- ═══════════════════════════════════════════════════════════════════
-- Phase 2 완료 후 좋아요님이 수동으로 해야 할 것:
--
-- 1. 총판으로 분류해야 할 partner 수동 변경
--    (어느 agency가 총판이었는지 좋아요님만 아심)
--    예시:
--    UPDATE public.partners 
--    SET is_distributor = true, 
--        is_reseller = false, 
--        business_channel = 'direct',
--        can_recruit_resellers = true
--    WHERE name = '특정 총판 이름';
--
-- 2. 유관기관으로 분류해야 할 partner 수동 변경
--    UPDATE public.partners 
--    SET is_related_org = true,
--        is_reseller = false,
--        business_channel = 'related_org',
--        has_org_admin_contract = true,
--        org_admin_contract_active_from = CURRENT_DATE
--    WHERE name = '특정 유관기관 이름';
--
-- 3. 총판 산하 대리점 parent_partner_id 설정
--    UPDATE public.partners 
--    SET parent_partner_id = (SELECT id FROM partners WHERE name = '총판이름'),
--        business_channel = 'via_distributor'
--    WHERE name = '대리점이름';
--
-- 4. hq_staff_capabilities 등록 (본부 직원에게 권한 부여)
--    -- 좋아요님 본인 (super_admin)
--    INSERT INTO public.hq_staff_capabilities (user_id, capability)
--    SELECT id, 'director' FROM users WHERE email = 'toast1234@naver.com';
--    
--    -- 운영팀 합류 시
--    INSERT INTO public.hq_staff_capabilities (user_id, capability)
--    SELECT id, 'ops_review' FROM users WHERE email = '운영팀이메일';

-- ═══════════════════════════════════════════════════════════════════
-- 롤백 (필요 시 — 데이터 복사만 되돌림, 테이블은 유지)
-- ═══════════════════════════════════════════════════════════════════
/*
BEGIN;

-- Workspace 멤버십 제거
DELETE FROM public.workspace_memberships
WHERE user_id IN (
    SELECT id FROM public.users WHERE partner_id IS NOT NULL
);

-- 사용자 partner_id 초기화
UPDATE public.users SET partner_id = NULL WHERE partner_id IS NOT NULL;

-- 마이그레이션된 partner 제거
DELETE FROM public.partners WHERE legacy_agency_id IS NOT NULL;

COMMIT;
*/

-- ═══════════════════════════════════════════════════════════════════
-- ✅ Phase 2 완료 후 다음 단계
-- ═══════════════════════════════════════════════════════════════════
-- 1. 위 검증 쿼리 모두 통과 확인
-- 2. Streamlit 앱 재시작 → 기존 기능 정상 작동 확인
-- 3. 수동 후속 작업 (총판/유관기관 분류, capabilities 등록)
-- 4. Phase 3 (코드 듀얼 리드) 시작 — app.py 수정
--    헬퍼 함수 추가, agency_id → partner_id 점진적 전환
