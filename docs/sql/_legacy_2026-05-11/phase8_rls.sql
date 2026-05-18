-- ============================================================
-- DragonEyes v2.1 Phase 8: RLS 정책 정식화
-- ============================================================
-- ⚠️ 위험! 단계별 적용 + 각 단계 후 Streamlit 로그인 검증 필수
--
-- 사전 조건:
--   - phase6_tables.sql 실행 완료
--   - phase7_seed.sql 실행 완료 (10행 시딩)
--
-- 단계:
--   8-A: partners RLS 신규 정책 추가 (allow_all_temp 유지)
--   8-B: partners allow_all_temp 제거 (격리 시작!)
--   8-C: users 테이블 격리
--   8-D: customers 테이블 RLS
--   8-E: user_groups 자체 RLS
--   8-F: partner_customers / licenses 등 나머지 테이블 (별도 SQL)
-- ============================================================


-- ============================================================
-- ⛔ Step 8-A: partners 신규 정책 추가
-- ============================================================
-- 적용 후 즉시 좋아요님 로그인 테스트
-- 화면 깨지면 즉시 8-A 롤백

BEGIN;

DROP POLICY IF EXISTS partners_select_by_role ON partners;
CREATE POLICY partners_select_by_role ON partners FOR SELECT
USING (
    -- HQ 직원은 전체 조회
    user_is_hq_staff(auth.uid())
    OR
    -- 파트너 소속 직원은 본인 파트너만
    id = user_partner_id(auth.uid())
);

DROP POLICY IF EXISTS partners_modify_hq_admin ON partners;
CREATE POLICY partners_modify_hq_admin ON partners FOR INSERT
WITH CHECK (user_is_hq_admin(auth.uid()));

DROP POLICY IF EXISTS partners_update_hq_admin ON partners;
CREATE POLICY partners_update_hq_admin ON partners FOR UPDATE
USING (user_is_hq_admin(auth.uid()))
WITH CHECK (user_is_hq_admin(auth.uid()));

DROP POLICY IF EXISTS partners_delete_hq_admin ON partners;
CREATE POLICY partners_delete_hq_admin ON partners FOR DELETE
USING (user_is_hq_admin(auth.uid()));

COMMIT;

-- ★★★ 검증 8-A ★★★
-- 1) Streamlit 재시작
-- 2) 좋아요님 로그인 → partners 화면에서 2개 보이는지
-- 3) 정상이면 8-B 진행, 비정상이면 아래 롤백

-- 8-A 롤백:
-- BEGIN;
-- DROP POLICY IF EXISTS partners_select_by_role ON partners;
-- DROP POLICY IF EXISTS partners_modify_hq_admin ON partners;
-- DROP POLICY IF EXISTS partners_update_hq_admin ON partners;
-- DROP POLICY IF EXISTS partners_delete_hq_admin ON partners;
-- COMMIT;


-- ============================================================
-- ⛔ Step 8-B: partners allow_all_temp 제거 (격리 시작!)
-- ============================================================
-- 가장 위험한 단계. 적용 직후 검증.

BEGIN;

DROP POLICY IF EXISTS allow_all_temp ON partners;

COMMIT;

-- ★★★ 검증 8-B (필수!) ★★★
-- 1) 좋아요님 로그인 → partners 2개 다 보이는지 (포유솔루션 + 오뚜기)
-- 2) 정희영 로그인 → partners 1개만 (포유솔루션만)
-- 3) 황철희 로그인 → partners 1개만 (오뚜기만)
-- 4) 황철희가 포유솔루션 안 보여야 정상!

-- 8-B 롤백 (allow_all_temp 복구):
-- BEGIN;
-- CREATE POLICY allow_all_temp ON partners FOR ALL USING (true) WITH CHECK (true);
-- COMMIT;


-- ============================================================
-- ⛔ Step 8-C: users 테이블 격리
-- ============================================================
-- 황철희가 본부 직원 10명 다 보는 문제 해결

BEGIN;

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_select_by_role ON users;
CREATE POLICY users_select_by_role ON users FOR SELECT
USING (
    -- 본인은 항상
    id = auth.uid()
    OR
    -- HQ 직원은 전체
    user_is_hq_staff(auth.uid())
    OR
    -- 파트너 admin은 같은 파트너 소속 사용자만
    EXISTS (
        SELECT 1 
        FROM user_groups my_ug
        JOIN user_groups target_ug ON target_ug.user_id = users.id
        WHERE my_ug.user_id = auth.uid()
          AND my_ug.group_type = 'partner_admin'
          AND my_ug.is_active = TRUE
          AND target_ug.is_active = TRUE
          AND target_ug.partner_id = my_ug.partner_id
    )
    OR
    -- 고객사 admin은 같은 고객사 소속 사용자만
    EXISTS (
        SELECT 1 
        FROM user_groups my_ug
        JOIN user_groups target_ug ON target_ug.user_id = users.id
        WHERE my_ug.user_id = auth.uid()
          AND my_ug.group_type = 'customer_admin'
          AND my_ug.is_active = TRUE
          AND target_ug.is_active = TRUE
          AND target_ug.customer_id = my_ug.customer_id
    )
);

DROP POLICY IF EXISTS users_update_self_or_hq_admin ON users;
CREATE POLICY users_update_self_or_hq_admin ON users FOR UPDATE
USING (
    id = auth.uid()
    OR user_is_hq_admin(auth.uid())
)
WITH CHECK (
    id = auth.uid()
    OR user_is_hq_admin(auth.uid())
);

DROP POLICY IF EXISTS users_insert_hq_admin ON users;
CREATE POLICY users_insert_hq_admin ON users FOR INSERT
WITH CHECK (user_is_hq_admin(auth.uid()));

DROP POLICY IF EXISTS users_delete_hq_admin ON users;
CREATE POLICY users_delete_hq_admin ON users FOR DELETE
USING (user_is_hq_admin(auth.uid()));

COMMIT;

-- ★★★ 검증 8-C ★★★
-- 1) 황철희 로그인 → 사용자 화면에서 본인 1명만
-- 2) 정희영 로그인 → 정희영 + 정다운 2명
-- 3) 좋아요님 로그인 → 10명 다

-- 8-C 롤백:
-- BEGIN;
-- DROP POLICY IF EXISTS users_select_by_role ON users;
-- DROP POLICY IF EXISTS users_update_self_or_hq_admin ON users;
-- DROP POLICY IF EXISTS users_insert_hq_admin ON users;
-- DROP POLICY IF EXISTS users_delete_hq_admin ON users;
-- ALTER TABLE users DISABLE ROW LEVEL SECURITY;
-- COMMIT;


-- ============================================================
-- ⛔ Step 8-D: customers 테이블 RLS
-- ============================================================
-- 현재 customers는 빈 테이블이지만 미리 정책 적용

BEGIN;

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS customers_select_by_role ON customers;
CREATE POLICY customers_select_by_role ON customers FOR SELECT
USING (
    -- 본인이 admin 또는 monitoring user인 customers만
    id = user_customer_id(auth.uid())
    OR
    -- HQ 직원은 전체
    user_is_hq_staff(auth.uid())
    OR
    -- 영업한 대리점은 자기가 판 customers 조회 가능
    (
        sold_by_partner_id = user_partner_id(auth.uid())
        AND user_partner_id(auth.uid()) IS NOT NULL
    )
);

DROP POLICY IF EXISTS customers_modify_hq_admin ON customers;
CREATE POLICY customers_modify_hq_admin ON customers FOR INSERT
WITH CHECK (user_is_hq_admin(auth.uid()));

DROP POLICY IF EXISTS customers_update_hq_admin ON customers;
CREATE POLICY customers_update_hq_admin ON customers FOR UPDATE
USING (user_is_hq_admin(auth.uid()))
WITH CHECK (user_is_hq_admin(auth.uid()));

DROP POLICY IF EXISTS customers_delete_hq_admin ON customers;
CREATE POLICY customers_delete_hq_admin ON customers FOR DELETE
USING (user_is_hq_admin(auth.uid()));

COMMIT;


-- ============================================================
-- ⛔ Step 8-E: user_groups 자체 RLS
-- ============================================================
-- ⚠️ 함수가 user_groups 읽으므로 SECURITY DEFINER가 핵심
-- (phase6에서 이미 SECURITY DEFINER 설정함)

BEGIN;

ALTER TABLE user_groups ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_groups_select ON user_groups;
CREATE POLICY user_groups_select ON user_groups FOR SELECT
USING (
    user_id = auth.uid()
    OR user_is_hq_staff(auth.uid())
);

DROP POLICY IF EXISTS user_groups_modify ON user_groups;
CREATE POLICY user_groups_modify ON user_groups FOR INSERT
WITH CHECK (user_is_hq_admin(auth.uid()));

DROP POLICY IF EXISTS user_groups_update ON user_groups;
CREATE POLICY user_groups_update ON user_groups FOR UPDATE
USING (user_is_hq_admin(auth.uid()))
WITH CHECK (user_is_hq_admin(auth.uid()));

DROP POLICY IF EXISTS user_groups_delete ON user_groups;
CREATE POLICY user_groups_delete ON user_groups FOR DELETE
USING (user_is_hq_admin(auth.uid()));

COMMIT;

-- ★★★ 검증 8-E ★★★
-- 1) 좋아요님 로그인 정상
-- 2) 황철희 로그인 → 본인 user_group만 보이는지

-- 8-E 롤백:
-- BEGIN;
-- ALTER TABLE user_groups DISABLE ROW LEVEL SECURITY;
-- DROP POLICY IF EXISTS user_groups_select ON user_groups;
-- DROP POLICY IF EXISTS user_groups_modify ON user_groups;
-- DROP POLICY IF EXISTS user_groups_update ON user_groups;
-- DROP POLICY IF EXISTS user_groups_delete ON user_groups;
-- COMMIT;


-- ============================================================
-- 🔴 긴급 전체 롤백 (모든 단계 무효화)
-- ============================================================
-- 좋아요님 본인 로그인 안 되는 사태 발생 시 즉시 실행:

-- BEGIN;
-- ALTER TABLE users DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_groups DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE customers DISABLE ROW LEVEL SECURITY;
-- DROP POLICY IF EXISTS partners_select_by_role ON partners;
-- DROP POLICY IF EXISTS partners_modify_hq_admin ON partners;
-- DROP POLICY IF EXISTS partners_update_hq_admin ON partners;
-- DROP POLICY IF EXISTS partners_delete_hq_admin ON partners;
-- CREATE POLICY allow_all_temp ON partners FOR ALL USING (true) WITH CHECK (true);
-- COMMIT;
