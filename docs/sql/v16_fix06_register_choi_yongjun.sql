-- ============================================================
-- DragonEyes v1.6 — Fix 06
-- 신규 사용자 등록: 최용준 (포유솔루션 모니터링 직원)
-- ============================================================
-- 적용일 : 2026-06-10
-- 적용처 : 운영 Supabase (project xtqgxtdflemuphkzmzti)
--
-- [등록 정보]
--   이름   : 최용준
--   이메일 : dragonjuny02@gmail.com
--   연락처 : 010-7114-7930
--   소속   : 포유솔루션 (tenant)
--   권한   : user (모니터링만, 관리자 권한 없음)
--   보호자 : 최승현
--   보호자 연락처 : 010-6294-5937
--   보호자 이메일 : kingcas7@gmail.com
--
-- [실행 순서]
--   1. Supabase Dashboard에서 Auth 사용자 먼저 추가 (아래 STEP 0 안내)
--   2. STEP 1: 포유솔루션 tenant_id 조회
--   3. STEP 2: Auth user id 조회
--   4. STEP 3: public.users INSERT
--   5. STEP 4: 검증
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- STEP 0 (Dashboard 작업) : Supabase Auth 사용자 추가
-- ─────────────────────────────────────────────────────────────
--   Supabase Dashboard → Authentication → Users → Add User
--     · Email          : dragonjuny02@gmail.com
--     · Password       : (임시 비밀번호 — 최용준에게 별도 전달)
--     · Auto Confirm   : ✅ 체크 (이메일 확인 생략, 즉시 로그인 가능)
--   생성 후 사용자 카드의 User UID(uuid)를 복사해두면 빠릅니다.
--
--   ⚠️ 비밀번호는 별도 안전한 채널(예: 카카오톡, SMS)로 전달.
--      최초 로그인 후 본인이 user_profile에서 변경 권장.


-- ─────────────────────────────────────────────────────────────
-- STEP 1 : 포유솔루션 tenant_id 조회
-- ─────────────────────────────────────────────────────────────
--   포유솔루션 customer/tenant 레코드 확인. 가장 유력한 행 1건 사용.
SELECT
    id            AS tenant_id,
    name          AS tenant_name,
    business_number,
    created_at
FROM public.customers
WHERE name LIKE '%포유%'
   OR name LIKE '%4U%'
   OR name LIKE '%(주)포유솔루션%'
ORDER BY created_at ASC
LIMIT 5;

--   ⚠️ 위에서 정확한 포유솔루션 행의 tenant_id를 복사해 STEP 3에 붙여넣기.
--   (customers 테이블이 없거나 다른 이름이면 supabase 인스턴스의 실제 테이블명 사용)


-- ─────────────────────────────────────────────────────────────
-- STEP 2 : 방금 생성한 Auth 사용자 UID 조회
-- ─────────────────────────────────────────────────────────────
SELECT
    id    AS auth_user_id,
    email,
    created_at,
    last_sign_in_at,
    email_confirmed_at
FROM auth.users
WHERE lower(email) = lower('dragonjuny02@gmail.com');

--   ⚠️ id(uuid)를 복사해 STEP 3에 붙여넣기.


-- ─────────────────────────────────────────────────────────────
-- STEP 3 : public.users INSERT
-- ─────────────────────────────────────────────────────────────
--   아래 :auth_uid, :tenant_uid 를 STEP 1, 2 결과로 치환 후 실행.
--   Supabase SQL Editor는 변수 치환이 없으니 직접 문자열 교체.
--
--   예) 'AUTH_USER_ID_HERE' → 'a1b2c3d4-e5f6-...' (STEP 2 결과)
--        'TENANT_ID_HERE'    → 'p1q2r3s4-...'     (STEP 1 결과)
--
INSERT INTO public.users (
    id,                  -- auth.users.id 와 동일 (uuid)
    email,
    name,
    phone,
    tenant_id,
    partner_id,
    role,
    role_v2,
    is_tenant_admin,
    guardian_name,
    guardian_phone,
    monthly_target,
    preferences,
    created_at,
    updated_at
) VALUES (
    'AUTH_USER_ID_HERE',                  -- ⚠️ STEP 2의 auth user id 붙여넣기
    'dragonjuny02@gmail.com',
    '최용준',
    '010-7114-7930',
    'TENANT_ID_HERE',                     -- ⚠️ STEP 1의 포유솔루션 tenant_id 붙여넣기
    NULL,                                  -- 본부 또는 파트너 직원이 아니므로 NULL
    'user',                                -- 일반 사용자 (모니터링만)
    'user',                                -- role_v2 도 일반 user
    FALSE,                                 -- 테넌트 관리자 아님
    '최승현',                              -- 보호자 이름
    '010-6294-5937',                       -- 보호자 연락처
    10,                                    -- 월간 목표 (기본 10건)
    jsonb_build_object(
        'voice_guide_enabled', false,
        'voice_speed', 1.0,
        'voice_lang', 'ko-KR',
        'dictation_enabled', false,
        'guardian_email', 'kingcas7@gmail.com'   -- 보호자 이메일은 preferences JSONB에 보존
    ),
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    email          = EXCLUDED.email,
    name           = EXCLUDED.name,
    phone          = EXCLUDED.phone,
    tenant_id      = EXCLUDED.tenant_id,
    role           = EXCLUDED.role,
    role_v2        = EXCLUDED.role_v2,
    guardian_name  = EXCLUDED.guardian_name,
    guardian_phone = EXCLUDED.guardian_phone,
    preferences    = EXCLUDED.preferences,
    updated_at     = NOW()
RETURNING id, email, name, role, role_v2, tenant_id, guardian_name, guardian_phone;


-- ─────────────────────────────────────────────────────────────
-- STEP 4 : 등록 검증
-- ─────────────────────────────────────────────────────────────
SELECT
    u.id,
    u.email,
    u.name,
    u.phone,
    u.role,
    u.role_v2,
    u.tenant_id,
    c.name                       AS tenant_name,
    u.partner_id,
    u.is_tenant_admin,
    u.guardian_name,
    u.guardian_phone,
    u.preferences ->> 'guardian_email' AS guardian_email_in_prefs,
    u.monthly_target,
    u.created_at
FROM public.users u
LEFT JOIN public.customers c ON c.id = u.tenant_id
WHERE lower(u.email) = lower('dragonjuny02@gmail.com');

-- 기대 결과:
--   role            = 'user'
--   role_v2         = 'user'
--   tenant_id       = 포유솔루션의 customer id
--   tenant_name     = '포유솔루션' (또는 (주)포유솔루션)
--   partner_id      = NULL
--   is_tenant_admin = false
--   guardian_*      = 최승현 / 010-6294-5937
--   guardian_email_in_prefs = kingcas7@gmail.com


-- ─────────────────────────────────────────────────────────────
-- 등록 후 최용준 사용자 동작
-- ─────────────────────────────────────────────────────────────
-- 1) 임시 비밀번호로 로그인 → home_landing 또는 home 진입
-- 2) 일반 사용자 권한 (관리자/파트너 메뉴 없음)
-- 3) 사용 가능 메뉴: 텍스트분석·유튜브분석·키워드탐색·네이버탐색·디스코드탐색·
--                   탐색 히스토리·보고서 목록·내 성과·드래곤파더·공지사항
-- 4) 음성 안내 / 받아쓰기 토글 가능 (시각장애인 친화)

-- 끝.
