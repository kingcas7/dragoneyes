-- ============================================================
-- DragonEyes v1.6 — Fix 05
-- 권찬 (ckwon2000@gmail.com) → director 권한 명시적 부여
-- ============================================================
-- 적용일 : 2026-06-10
-- 적용처 : 운영 Supabase (project xtqgxtdflemuphkzmzti)
--          → Supabase SQL Editor에서 아래 단계 순차 실행
--
-- [목적]
--   권찬을 본부 디렉터(director)로 정식 설정.
--   파트너 페이지·영업 파이프라인·통계 등 본부 관리 화면 접근 권한 확보.
--
-- [현황 추정]
--   화면 표시: "🎯 1그룹 디렉터" → 이미 role_v2 ≒ director 계열일 가능성 큼.
--   본 스크립트는 명시적으로 role_v2='director', role='admin'을 강제 세팅하여
--   가드 함수들(is_director, is_admin, guard_page allowed_roles)을 안전 통과.
--
-- [안전성]
--   - WHERE email 정확 매칭 (lower 비교) → 다른 계정 미영향
--   - partner_id IS NULL 조건 → 파트너사 직원이면 변경 차단
--   - RETURNING 으로 변경 직후 결과 즉시 확인
--   - 트랜잭션 없이 단일 UPDATE (롤백은 수동 BACKUP 이후 가능)
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- STEP 1 : 변경 전 현재 상태 확인 (BEFORE)
-- ─────────────────────────────────────────────────────────────
SELECT
    id,
    email,
    name,
    role,
    role_v2,
    partner_id,
    is_tenant_admin,
    created_at
FROM public.users
WHERE lower(email) = lower('ckwon2000@gmail.com');

-- 결과 확인 후 STEP 2 실행. 위 SELECT가 0건이면 가입 안 된 계정 → 중단.
-- partner_id가 NULL이 아니면 파트너사 소속 → 본부 권한 부여 부적절 (관리자 검토).


-- ─────────────────────────────────────────────────────────────
-- STEP 2 : director 권한 부여 (본부 admin + role_v2=director)
-- ─────────────────────────────────────────────────────────────
UPDATE public.users
   SET role     = 'admin',          -- 본부 admin (파트너 admin 구분: partner_id IS NULL)
       role_v2  = 'director',       -- 본부 디렉터 (1그룹 → 추후 director_2~4로 변경 가능)
       updated_at = NOW()
 WHERE lower(email) = lower('ckwon2000@gmail.com')
   AND (partner_id IS NULL OR partner_id::text = '')
RETURNING
    id,
    email,
    name,
    role        AS new_role,
    role_v2     AS new_role_v2,
    partner_id,
    updated_at;

-- RETURNING 결과로 1건만 나와야 정상.
-- 0건 = 이메일 미존재 OR partner_id 있어서 차단됨.


-- ─────────────────────────────────────────────────────────────
-- STEP 3 : 변경 후 검증 (AFTER)
-- ─────────────────────────────────────────────────────────────
SELECT
    id,
    email,
    name,
    role,
    role_v2,
    partner_id,
    updated_at
FROM public.users
WHERE lower(email) = lower('ckwon2000@gmail.com');

-- 기대값:
--   role     = 'admin'
--   role_v2  = 'director'
--   partner_id = NULL


-- ─────────────────────────────────────────────────────────────
-- STEP 4 (선택) : 1~4그룹 디렉터 중 구분 필요 시
-- ─────────────────────────────────────────────────────────────
-- 권찬이 특정 그룹(예: 2그룹) 디렉터라면 아래 한 줄로 세분화:
--
--   UPDATE public.users
--      SET role_v2 = 'director_2'
--    WHERE lower(email) = lower('ckwon2000@gmail.com');
--
-- 옵션: 'director' / 'director_2' / 'director_3' / 'director_4'
-- 코드의 is_director(), guard_page allowed_roles는 4종 모두 통과.


-- ─────────────────────────────────────────────────────────────
-- 적용 후 사용자 동작
-- ─────────────────────────────────────────────────────────────
-- 1) 권찬 로그인 → 상단 메뉴에 🤝 파트너 / 👑 관리자 모두 노출
-- 2) 🤝 파트너 클릭 → agency_dashboard 정상 진입
-- 3) 📊 영업 파이프라인 진입 → 그래프 보기 4종 차트 확인 가능
-- 4) 본부 admin 권한 → 모든 본부 메뉴(통계·라이선스·고객사) 열람·관리 가능

-- 끝.
