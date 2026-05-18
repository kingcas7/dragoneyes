-- ============================================================
-- DragonEyes v2.1 Phase 6: 신규 테이블 및 컬럼
-- ============================================================
-- 작성일: 2026-05-11
-- 작성자: 좋아요님 (최승현)
--
-- 핵심 변경:
--   1. customers 테이블 신설 (모니터링 서비스 고객)
--   2. partners 테이블에 demo_monitoring_seats 컬럼 추가
--   3. user_groups 매핑 테이블 신설 (6개 group_type)
--   4. 헬퍼 VIEW + 함수
--
-- 비즈니스 모델:
--   - partners = 영업/협력 파트너스 (대리점, 유관기관) - 라이선스 사용 X
--   - customers = 모니터링 서비스 고객 - 라이선스 사용 O
--   - 같은 법인이 양쪽 등록 가능 (별도 계약, 별도 user_id)
--   - 모든 대리점은 데모용 모니터링 1seat 자동 부여 (영업/시연용)
--
-- group_type 6종:
--   hq_admin        : 본부 관리자 (정미옥/좋아요님/김우주/박광남)
--   hq_member       : 본부 일반 직원 (이성용/하민호/팀원3)
--   partner_admin   : partners 소속 관리자 (정희영/정다운/황철희)
--   partner_member  : partners 소속 일반 직원
--   customer_admin  : customers 소속 관리자
--   monitoring_user : 장애인 등 모니터링 전용 사용자
-- ============================================================

BEGIN;

-- ============================================
-- 1. partners 테이블 확장
-- ============================================

ALTER TABLE partners ADD COLUMN IF NOT EXISTS 
    demo_monitoring_seats INT NOT NULL DEFAULT 1;

ALTER TABLE partners ADD COLUMN IF NOT EXISTS 
    demo_seats_used INT NOT NULL DEFAULT 0;

COMMENT ON COLUMN partners.demo_monitoring_seats IS 
    '영업/시연용 모니터링 권한 수. 기본 1개, 본부 승인으로 증가 가능.';

COMMENT ON COLUMN partners.demo_seats_used IS 
    '실제 사용 중인 데모 seat 수. demo_monitoring_seats를 초과할 수 없음.';

ALTER TABLE partners ADD CONSTRAINT chk_demo_seats_not_exceeded
    CHECK (demo_seats_used <= demo_monitoring_seats);

-- ============================================
-- 2. customers 테이블 신설 (모니터링 고객)
-- ============================================

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 표시명 (괄호로 계약 구분: "포유솔루션 (모니터링)")
    display_name TEXT NOT NULL,
    
    -- 법인 정보 (같은 사업자번호가 partners에도 있을 수 있음)
    legal_name TEXT NOT NULL,
    business_number TEXT NOT NULL,
    representative_name TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    
    -- 계약 정보
    contract_number TEXT,
    contract_label TEXT,  -- 괄호 안에 표시될 라벨 (예: "모니터링")
    contract_start DATE,
    contract_end DATE,
    contract_status TEXT NOT NULL DEFAULT 'pilot'
        CHECK (contract_status IN ('pilot', 'active', 'paused', 'terminated')),
    
    -- 라이선스/사용자 한도
    license_count INT NOT NULL DEFAULT 0,
    monitoring_user_limit INT,
    monitoring_users_count INT NOT NULL DEFAULT 0,
    
    -- 영업 라인 추적 (어느 대리점이 영업했는지)
    sold_by_partner_id UUID REFERENCES partners(id),
    
    -- Soft delete
    deleted_at TIMESTAMPTZ,
    
    -- 감사
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES users(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- 같은 사업자번호 + 같은 contract_label 중복 방지
    -- (포유솔루션 모니터링 계약 1개만 허용. 추가 계약은 label 달리해서 등록)
    UNIQUE (business_number, contract_label)
);

COMMENT ON TABLE customers IS 
    '모니터링 서비스 고객사. partners와 별개 테이블. 같은 법인이 양쪽 등록 가능.';

CREATE INDEX idx_customers_business_number ON customers(business_number);
CREATE INDEX idx_customers_status ON customers(contract_status);
CREATE INDEX idx_customers_sold_by ON customers(sold_by_partner_id);
CREATE INDEX idx_customers_not_deleted ON customers(id) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 3. user_groups 매핑 테이블 신설
-- ============================================

CREATE TABLE IF NOT EXISTS user_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 역할 종류 (6종)
    group_type TEXT NOT NULL CHECK (group_type IN (
        'hq_admin',
        'hq_member',
        'partner_admin',
        'partner_member',
        'customer_admin',
        'monitoring_user'
    )),
    
    -- 소속 정보 (group_type에 따라 정확히 하나만 채워짐)
    partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    
    -- 활성 상태
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- 감사
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES users(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- ⭐ 핵심 제약: 한 user_id = 한 group_type (활성 상태에서)
    -- 다중 역할 필요 시 별도 user_id 발급 (옵션 2)
    UNIQUE (user_id)
);

COMMENT ON TABLE user_groups IS 
    '사용자-역할 매핑. 한 user_id는 정확히 하나의 group_type만 보유.';

-- ============================================
-- 4. 제약 조건: group_type별 참조 검증
-- ============================================

ALTER TABLE user_groups
    ADD CONSTRAINT chk_partner_required CHECK (
        (group_type IN ('partner_admin', 'partner_member') 
         AND partner_id IS NOT NULL AND customer_id IS NULL)
        OR group_type NOT IN ('partner_admin', 'partner_member')
    );

ALTER TABLE user_groups
    ADD CONSTRAINT chk_customer_required CHECK (
        (group_type IN ('customer_admin', 'monitoring_user') 
         AND customer_id IS NOT NULL AND partner_id IS NULL)
        OR group_type NOT IN ('customer_admin', 'monitoring_user')
    );

ALTER TABLE user_groups
    ADD CONSTRAINT chk_hq_no_refs CHECK (
        (group_type IN ('hq_admin', 'hq_member') 
         AND partner_id IS NULL AND customer_id IS NULL)
        OR group_type NOT IN ('hq_admin', 'hq_member')
    );

-- ============================================
-- 5. 인덱스
-- ============================================

CREATE INDEX idx_user_groups_user_id 
    ON user_groups(user_id) WHERE is_active = TRUE;

CREATE INDEX idx_user_groups_partner 
    ON user_groups(partner_id) WHERE partner_id IS NOT NULL;

CREATE INDEX idx_user_groups_customer 
    ON user_groups(customer_id) WHERE customer_id IS NOT NULL;

CREATE INDEX idx_user_groups_type 
    ON user_groups(group_type);

-- ============================================
-- 6. updated_at 자동 갱신
-- ============================================

CREATE TRIGGER trg_user_groups_updated_at
    BEFORE UPDATE ON user_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 7. 헬퍼 VIEW: user_groups_resolved
-- ============================================
-- 매번 JOIN 안 해도 한 줄로 조회

CREATE OR REPLACE VIEW user_groups_resolved AS
SELECT 
    ug.id,
    ug.user_id,
    u.email,
    u.name AS user_name,
    u.status AS user_status,
    ug.group_type,
    -- admin/member/monitoring 편의 컬럼
    CASE 
        WHEN ug.group_type LIKE '%_admin' THEN 'admin'
        WHEN ug.group_type LIKE '%_member' THEN 'member'
        WHEN ug.group_type = 'monitoring_user' THEN 'monitoring'
    END AS role_level,
    -- 큰 카테고리 (hq/partner/customer)
    CASE 
        WHEN ug.group_type IN ('hq_admin', 'hq_member') THEN 'hq'
        WHEN ug.group_type IN ('partner_admin', 'partner_member') THEN 'partner'
        WHEN ug.group_type IN ('customer_admin', 'monitoring_user') THEN 'customer'
    END AS group_category,
    ug.is_active,
    -- 파트너 정보
    ug.partner_id,
    p.name AS partner_name,
    p.business_number AS partner_business_number,
    p.is_distributor,
    p.is_reseller,
    p.is_related_org,
    p.demo_monitoring_seats,
    -- 고객사 정보
    ug.customer_id,
    c.display_name AS customer_display_name,
    c.legal_name AS customer_legal_name,
    c.business_number AS customer_business_number,
    c.contract_status,
    ug.created_at,
    ug.updated_at
FROM user_groups ug
JOIN users u ON u.id = ug.user_id
LEFT JOIN partners p ON p.id = ug.partner_id
LEFT JOIN customers c ON c.id = ug.customer_id
WHERE ug.is_active = TRUE;

COMMENT ON VIEW user_groups_resolved IS 
    '활성 사용자-역할 매핑 조회용 VIEW.';

-- ============================================
-- 8. 헬퍼 함수: get_user_home_page(user_id)
-- ============================================
-- 옵션 B 반영: partner_admin/member도 데모 모니터링 가능하지만 홈은 파트너 대시보드

CREATE OR REPLACE FUNCTION get_user_home_page(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
    v_group_type TEXT;
BEGIN
    SELECT group_type INTO v_group_type
    FROM user_groups
    WHERE user_id = p_user_id AND is_active = TRUE
    LIMIT 1;
    
    -- 그룹이 없으면 기본값
    IF v_group_type IS NULL THEN
        RETURN 'partner_dashboard';
    END IF;
    
    -- monitoring_user만 모니터링 홈, 나머지는 파트너 대시보드
    IF v_group_type = 'monitoring_user' THEN
        RETURN 'monitoring_home';
    ELSE
        RETURN 'partner_dashboard';
    END IF;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_user_home_page(UUID) IS 
    '로그인 직후 홈페이지 결정. monitoring_user → monitoring_home, 그 외 → partner_dashboard.';

-- ============================================
-- 9. 헬퍼 함수: user_has_group_type, user_is_hq_staff
-- ============================================

CREATE OR REPLACE FUNCTION user_has_group_type(p_user_id UUID, p_group_type TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_groups
        WHERE user_id = p_user_id 
          AND group_type = p_group_type
          AND is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION user_is_hq_staff(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_groups
        WHERE user_id = p_user_id 
          AND group_type IN ('hq_admin', 'hq_member')
          AND is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION user_is_hq_admin(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_groups
        WHERE user_id = p_user_id 
          AND group_type = 'hq_admin'
          AND is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- 본인이 속한 partner_id 반환 (NULL 가능)
CREATE OR REPLACE FUNCTION user_partner_id(p_user_id UUID)
RETURNS UUID AS $$
DECLARE
    v_partner_id UUID;
BEGIN
    SELECT partner_id INTO v_partner_id
    FROM user_groups
    WHERE user_id = p_user_id 
      AND group_type IN ('partner_admin', 'partner_member')
      AND is_active = TRUE
    LIMIT 1;
    
    RETURN v_partner_id;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- 본인이 속한 customer_id 반환 (NULL 가능)
CREATE OR REPLACE FUNCTION user_customer_id(p_user_id UUID)
RETURNS UUID AS $$
DECLARE
    v_customer_id UUID;
BEGIN
    SELECT customer_id INTO v_customer_id
    FROM user_groups
    WHERE user_id = p_user_id 
      AND group_type IN ('customer_admin', 'monitoring_user')
      AND is_active = TRUE
    LIMIT 1;
    
    RETURN v_customer_id;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ============================================
-- 10. 검증 쿼리
-- ============================================

-- 테이블 2개 신설 확인
SELECT 
    table_name,
    EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = t) AS exists
FROM (VALUES ('customers'), ('user_groups')) AS x(t)
CROSS JOIN LATERAL (SELECT t AS table_name) y;

-- partners 컬럼 추가 확인
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'partners' 
  AND column_name IN ('demo_monitoring_seats', 'demo_seats_used');

-- user_groups 제약 4개 확인
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'user_groups'::regclass
ORDER BY contype, conname;

-- 함수 5개 확인
SELECT proname FROM pg_proc 
WHERE proname IN (
    'get_user_home_page', 
    'user_has_group_type', 
    'user_is_hq_staff',
    'user_is_hq_admin',
    'user_partner_id',
    'user_customer_id'
)
ORDER BY proname;

-- VIEW 확인
SELECT table_name FROM information_schema.views 
WHERE table_name = 'user_groups_resolved';

COMMIT;

-- ============================================
-- 롤백 SQL
-- ============================================
-- BEGIN;
-- DROP FUNCTION IF EXISTS user_customer_id(UUID);
-- DROP FUNCTION IF EXISTS user_partner_id(UUID);
-- DROP FUNCTION IF EXISTS user_is_hq_admin(UUID);
-- DROP FUNCTION IF EXISTS user_is_hq_staff(UUID);
-- DROP FUNCTION IF EXISTS user_has_group_type(UUID, TEXT);
-- DROP FUNCTION IF EXISTS get_user_home_page(UUID);
-- DROP VIEW IF EXISTS user_groups_resolved;
-- DROP TABLE IF EXISTS user_groups CASCADE;
-- DROP TABLE IF EXISTS customers CASCADE;
-- ALTER TABLE partners DROP COLUMN IF EXISTS demo_seats_used;
-- ALTER TABLE partners DROP COLUMN IF EXISTS demo_monitoring_seats;
-- COMMIT;
