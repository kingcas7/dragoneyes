-- ============================================================
-- DragonEyes v2.1 Phase 7: 기존 10명 user_groups 시딩
-- ============================================================
-- 사전 조건: phase6_tables.sql 실행 완료
-- 시딩 결과: 총 10행 INSERT
--
-- 매핑:
--   본부 admin 4명 → hq_admin
--   본부 member 3명 → hq_member
--   포유솔루션 2명 (정희영/정다운) → partner_admin (partners 참조)
--   오뚜기 1명 (황철희) → partner_admin (partners 참조)
--
-- 현재 customers 테이블은 비어있음 (모니터링 계약 체결 시 별도 추가)
-- ============================================================

BEGIN;

-- ============================================
-- 사전 검증
-- ============================================

-- 사용자 10명 존재 확인
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM users
    WHERE email IN (
        'miok479@nate.com', 'kingcas7@gmail.com', 
        'kimwouldyou@naver.com', 'toast1234@naver.com',
        'bigboy616@naver.com', 'haminho83@naver.com', 'jojic3000@gmail.com',
        'wjdheeyoung@naver.com', 'long8282@gmail.com',
        'rapid1120@daum.net'
    );
    
    IF v_count != 10 THEN
        RAISE EXCEPTION '예상한 10명 중 %명만 존재. 시딩 중단.', v_count;
    END IF;
END $$;

-- partners 2개 존재 확인
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM partners
    WHERE business_number = '821-81-02627'
       OR name = '오뚜기직업재활센터';
    
    IF v_count != 2 THEN
        RAISE EXCEPTION '예상한 파트너 2개 중 %개만 존재. 시딩 중단.', v_count;
    END IF;
END $$;

-- ============================================
-- 1. 본부 admin 4명 시딩
-- ============================================
INSERT INTO user_groups (user_id, group_type, created_by)
SELECT 
    id, 
    'hq_admin', 
    (SELECT id FROM users WHERE email = 'kingcas7@gmail.com')
FROM users 
WHERE email IN (
    'miok479@nate.com',
    'kingcas7@gmail.com',
    'kimwouldyou@naver.com',
    'toast1234@naver.com'
);

-- ============================================
-- 2. 본부 member 3명 시딩
-- ============================================
INSERT INTO user_groups (user_id, group_type, created_by)
SELECT 
    id, 
    'hq_member', 
    (SELECT id FROM users WHERE email = 'kingcas7@gmail.com')
FROM users 
WHERE email IN (
    'bigboy616@naver.com',
    'haminho83@naver.com',
    'jojic3000@gmail.com'
);

-- ============================================
-- 3. 포유솔루션 2명 (partner_admin) 시딩
-- ============================================
INSERT INTO user_groups (user_id, group_type, partner_id, created_by)
SELECT 
    u.id, 
    'partner_admin', 
    p.id, 
    (SELECT id FROM users WHERE email = 'kingcas7@gmail.com')
FROM users u
CROSS JOIN partners p
WHERE u.email IN ('wjdheeyoung@naver.com', 'long8282@gmail.com')
  AND p.business_number = '821-81-02627';

-- ============================================
-- 4. 오뚜기 황철희 (partner_admin) 시딩
-- ============================================
INSERT INTO user_groups (user_id, group_type, partner_id, created_by)
SELECT 
    u.id, 
    'partner_admin', 
    p.id, 
    (SELECT id FROM users WHERE email = 'kingcas7@gmail.com')
FROM users u
CROSS JOIN partners p
WHERE u.email = 'rapid1120@daum.net'
  AND p.name = '오뚜기직업재활센터';

-- ============================================
-- 검증 1: 총 10행
-- ============================================
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count FROM user_groups;
    
    IF v_count != 10 THEN
        RAISE EXCEPTION '시딩 결과 %행. 예상 10행. 롤백 필요.', v_count;
    END IF;
    
    RAISE NOTICE '✅ 시딩 성공: 10행 INSERT 완료';
END $$;

-- ============================================
-- 검증 2: 그룹별 분포
-- ============================================
SELECT 
    group_type, 
    COUNT(*) AS user_count
FROM user_groups
GROUP BY group_type
ORDER BY group_type;
-- 예상:
--   hq_admin       : 4
--   hq_member      : 3
--   partner_admin  : 3

-- ============================================
-- 검증 3: 전체 매핑 (VIEW 사용)
-- ============================================
SELECT 
    email, 
    user_name, 
    group_type, 
    group_category, 
    role_level,
    partner_name
FROM user_groups_resolved
ORDER BY group_category, role_level DESC, user_name;

-- ============================================
-- 검증 4: 라우팅 함수 동작
-- ============================================
SELECT 
    u.email, 
    u.name,
    get_user_home_page(u.id) AS home_page,
    user_is_hq_staff(u.id) AS is_hq,
    user_is_hq_admin(u.id) AS is_hq_admin,
    user_partner_id(u.id) AS partner_id,
    user_customer_id(u.id) AS customer_id
FROM users u
WHERE u.email IN (
    'kingcas7@gmail.com',     -- HQ admin → partner_dashboard, is_hq=true
    'bigboy616@naver.com',    -- HQ member → partner_dashboard, is_hq=true
    'wjdheeyoung@naver.com',  -- Partner admin → partner_dashboard, partner_id set
    'rapid1120@daum.net'      -- Partner admin (오뚜기) → partner_dashboard
)
ORDER BY u.email;

-- ============================================
-- 검증 5: partners 데모 권한 확인
-- ============================================
SELECT 
    name, 
    business_number,
    is_distributor,
    is_reseller,
    demo_monitoring_seats,
    demo_seats_used
FROM partners
WHERE name IN ('포유솔루션 주식회사', '오뚜기직업재활센터')
ORDER BY name;
-- 예상: 두 파트너 모두 demo_monitoring_seats=1, demo_seats_used=0

COMMIT;

-- ============================================
-- 롤백 SQL
-- ============================================
-- BEGIN;
-- DELETE FROM user_groups;
-- COMMIT;
