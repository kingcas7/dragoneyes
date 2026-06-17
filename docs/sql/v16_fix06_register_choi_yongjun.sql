-- ============================================================
-- DragonEyes v1.6 — Fix 06 (단순화 버전 — 치환 불필요)
-- 신규 사용자 등록: 최용준 (포유솔루션 모니터링 직원)
-- ============================================================
-- 적용일 : 2026-06-10
--
-- [사용 방법]
--   STEP 0 (Dashboard): Authentication → Users → Add User 만 수행
--                       Email: dragonjuny02@gmail.com / Auto Confirm ✅
--                       임시 비밀번호는 본인에게 별도 전달
--   STEP 1 (SQL): 아래 SQL을 통째로 복사 → 실행 끝
--                 (auth uuid / tenant_id 자동 조회 — 치환 불필요)
--   STEP 2 (검증): 마지막 SELECT로 등록 결과 확인
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- (선택) 사전 확인 — 포유솔루션과 auth 사용자가 있는지
-- ─────────────────────────────────────────────────────────────
SELECT
    '포유솔루션 tenant 후보' AS what,
    id::text AS id_or_uuid,
    name     AS info
FROM public.customers
WHERE name LIKE '%포유%' OR name LIKE '%4U%'
UNION ALL
SELECT
    'Auth 사용자' AS what,
    id::text AS id_or_uuid,
    email    AS info
FROM auth.users
WHERE lower(email) = lower('dragonjuny02@gmail.com');

--   결과:
--     · '포유솔루션 tenant 후보' 행 1건 이상 보여야 함 (없으면 customers 등록 필요)
--     · 'Auth 사용자' 행 1건 — Dashboard STEP 0이 끝났는지 확인


-- ─────────────────────────────────────────────────────────────
-- INSERT — auth uuid / tenant_id 자동 조회 (한 번에 실행)
-- ─────────────────────────────────────────────────────────────
INSERT INTO public.users (
    id,
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
)
SELECT
    au.id,                                       -- auth.users.id 자동 조회
    'dragonjuny02@gmail.com',
    '최용준',
    '010-7114-7930',
    (
        SELECT id
        FROM public.customers
        WHERE name LIKE '%포유%' OR name LIKE '%4U%'
        ORDER BY created_at ASC
        LIMIT 1
    ),                                            -- 포유솔루션 tenant_id 자동 조회
    NULL,
    'user',
    'user',
    FALSE,
    '최승현',
    '010-6294-5937',
    10,
    jsonb_build_object(
        'voice_guide_enabled', false,
        'voice_speed', 1.0,
        'voice_lang', 'ko-KR',
        'dictation_enabled', false,
        'guardian_email', 'kingcas7@gmail.com'
    ),
    NOW(),
    NOW()
FROM auth.users au
WHERE lower(au.email) = lower('dragonjuny02@gmail.com')
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

--   RETURNING 결과로 1건 반환되면 성공.
--   0건 = STEP 0 (Dashboard Auth 사용자 등록) 미완료 → 먼저 수행 후 재실행.


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT
    u.id,
    u.email,
    u.name,
    u.phone,
    u.role,
    u.role_v2,
    u.tenant_id,
    c.name AS tenant_name,
    u.partner_id,
    u.is_tenant_admin,
    u.guardian_name,
    u.guardian_phone,
    u.preferences ->> 'guardian_email' AS guardian_email,
    u.monthly_target,
    u.created_at
FROM public.users u
LEFT JOIN public.customers c ON c.id = u.tenant_id
WHERE lower(u.email) = lower('dragonjuny02@gmail.com');

-- 기대값:
--   role            = 'user'
--   role_v2         = 'user'
--   tenant_name     = '포유솔루션' (또는 (주)포유솔루션)
--   partner_id      = NULL
--   is_tenant_admin = false
--   guardian_name   = '최승현'
--   guardian_phone  = '010-6294-5937'
--   guardian_email  = 'kingcas7@gmail.com'
