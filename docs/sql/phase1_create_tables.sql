-- ═══════════════════════════════════════════════════════════════════
-- DragonEyes Migration: Phase 1 — 신규 테이블 생성
-- ═══════════════════════════════════════════════════════════════════
-- 실행 시점: phase0_backup.sql 검증 완료 후
-- 실행 위치: Supabase SQL Editor
-- 예상 소요 시간: 3~5분
-- 위험도: 중간 (CREATE TABLE이라 기존 데이터에 영향 없음, 단 ALTER가 있음)
-- 롤백: 본 파일 맨 아래 ROLLBACK 섹션 참조
-- ═══════════════════════════════════════════════════════════════════
-- ⚠️ 실행 전 확인:
--   1. phase0_backup.sql 완료 + 검증 통과
--   2. Supabase 자동 백업 한 번 더 실행
--   3. Streamlit 앱 일시 정지 (선택, 안전을 위해)
-- ═══════════════════════════════════════════════════════════════════

BEGIN;

-- ═══════════════════════════════════════════════════════════════════
-- Step 1: 공통 트리거 함수 (updated_at 자동 갱신)
-- ═══════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION public.update_updated_at_column() 
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════
-- Step 2: partners 테이블 (총판·대리점·유관기관 통합)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE public.partners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 기본 정보
    name TEXT NOT NULL,
    business_number TEXT UNIQUE,
    representative_name TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    
    -- 분류 (중복 가능)
    is_distributor BOOLEAN DEFAULT false,
    is_reseller BOOLEAN DEFAULT false,
    is_related_org BOOLEAN DEFAULT false,
    
    -- 계층
    parent_partner_id UUID REFERENCES public.partners(id),
    
    -- 채널
    business_channel TEXT NOT NULL,
    
    -- 3가지 계약 트랙
    has_sales_contract BOOLEAN DEFAULT false,
    has_customer_contract BOOLEAN DEFAULT false,
    has_org_admin_contract BOOLEAN DEFAULT false,
    
    sales_contract_doc_id UUID,
    customer_contract_doc_id UUID,
    org_admin_contract_doc_id UUID,
    
    sales_contract_active_from DATE,
    sales_contract_active_to DATE,
    customer_contract_active_from DATE,
    customer_contract_active_to DATE,
    org_admin_contract_active_from DATE,
    org_admin_contract_active_to DATE,
    
    -- 능력 토글 (계약에서 자동 파생)
    can_sell_license BOOLEAN GENERATED ALWAYS AS (
        has_sales_contract 
        AND sales_contract_active_from <= CURRENT_DATE 
        AND (sales_contract_active_to IS NULL OR sales_contract_active_to >= CURRENT_DATE)
    ) STORED,
    
    can_use_monitoring BOOLEAN GENERATED ALWAYS AS (
        has_customer_contract 
        AND customer_contract_active_from <= CURRENT_DATE 
        AND (customer_contract_active_to IS NULL OR customer_contract_active_to >= CURRENT_DATE)
    ) STORED,
    
    can_manage_disabled_users BOOLEAN GENERATED ALWAYS AS (
        has_org_admin_contract 
        AND org_admin_contract_active_from <= CURRENT_DATE 
        AND (org_admin_contract_active_to IS NULL OR org_admin_contract_active_to >= CURRENT_DATE)
    ) STORED,
    
    can_recruit_resellers BOOLEAN DEFAULT false,
    
    -- 상태
    partnership_status TEXT DEFAULT 'active',
    suspended_at TIMESTAMPTZ,
    terminated_at TIMESTAMPTZ,
    termination_reason TEXT,
    
    -- 마이그레이션 추적
    legacy_agency_id UUID,
    
    -- 메타
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 제약
    CONSTRAINT at_least_one_role CHECK (
        is_distributor OR is_reseller OR is_related_org
    ),
    CONSTRAINT distributor_no_parent CHECK (
        NOT is_distributor OR parent_partner_id IS NULL
    )
);

CREATE INDEX idx_partners_parent ON public.partners(parent_partner_id);
CREATE INDEX idx_partners_channel ON public.partners(business_channel);
CREATE INDEX idx_partners_status ON public.partners(partnership_status) 
    WHERE partnership_status = 'active';
CREATE INDEX idx_partners_legacy ON public.partners(legacy_agency_id) 
    WHERE legacy_agency_id IS NOT NULL;

CREATE TRIGGER update_partners_updated_at 
    BEFORE UPDATE ON public.partners
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ═══════════════════════════════════════════════════════════════════
-- Step 3: customers 테이블 (고객법인 마스터)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE public.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 기본 정보
    name TEXT NOT NULL,
    business_number TEXT UNIQUE,
    representative_name TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    industry_code TEXT,
    
    -- 영업 정보 (권한 격리 핵심)
    sold_by_partner_id UUID REFERENCES public.partners(id),
    parent_distributor_id UUID REFERENCES public.partners(id),
    business_channel TEXT NOT NULL,
    
    -- 직접고객 담당자 (Direct 케이스)
    direct_customer_manager_id UUID,  -- users(id) FK는 ALTER에서 추가
    
    -- 상태
    customer_status TEXT DEFAULT 'active',
    contract_signed_at TIMESTAMPTZ,
    churned_at TIMESTAMPTZ,
    churn_reason TEXT,
    
    -- 메타
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT direct_no_partner CHECK (
        (business_channel = 'direct' AND sold_by_partner_id IS NULL)
        OR business_channel != 'direct'
    )
);

CREATE INDEX idx_customers_sold_by ON public.customers(sold_by_partner_id);
CREATE INDEX idx_customers_distributor ON public.customers(parent_distributor_id);
CREATE INDEX idx_customers_status ON public.customers(customer_status);

CREATE TRIGGER update_customers_updated_at 
    BEFORE UPDATE ON public.customers
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- parent_distributor_id 자동 채움 트리거
CREATE OR REPLACE FUNCTION public.fill_parent_distributor() 
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.sold_by_partner_id IS NOT NULL THEN
        SELECT parent_partner_id INTO NEW.parent_distributor_id
        FROM public.partners 
        WHERE id = NEW.sold_by_partner_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_fill_parent_distributor
    BEFORE INSERT OR UPDATE OF sold_by_partner_id ON public.customers
    FOR EACH ROW EXECUTE FUNCTION public.fill_parent_distributor();

-- ═══════════════════════════════════════════════════════════════════
-- Step 4: users 테이블 확장
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE public.users 
    ADD COLUMN IF NOT EXISTS partner_id UUID REFERENCES public.partners(id),
    ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES public.customers(id),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb;
    -- preferences는 음성 안내 등 사용자 설정 저장용

CREATE INDEX IF NOT EXISTS idx_users_partner ON public.users(partner_id);
CREATE INDEX IF NOT EXISTS idx_users_customer ON public.users(customer_id);

-- updated_at 트리거 (이미 있으면 무시)
DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- customers의 direct_customer_manager_id FK 추가 (이제 users.id 참조 가능)
ALTER TABLE public.customers 
    ADD CONSTRAINT customers_direct_manager_fkey 
    FOREIGN KEY (direct_customer_manager_id) REFERENCES public.users(id);

-- ═══════════════════════════════════════════════════════════════════
-- Step 5: partner_customer_relations (N:M, 옵트인 기반)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE public.partner_customer_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID REFERENCES public.partners(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES public.customers(id) ON DELETE CASCADE,
    
    relationship_type TEXT NOT NULL,
    -- 'sales': 영업 관계
    -- 'related_org_assigned_by_customer': 고객사가 자발적 지정
    -- 'related_org_assigned_by_user': 사용자가 자발적 지정
    -- 'document_support': 서류 지원
    -- 'consulting': 컨설팅
    
    -- 옵트인 추적
    opted_in_by_user_id UUID REFERENCES public.users(id),
    opted_in_at TIMESTAMPTZ,
    opt_in_evidence TEXT,
    consent_record_id UUID,
    
    revoked_at TIMESTAMPTZ,
    revoke_reason TEXT,
    
    -- 액션 범위
    can_request_documents BOOLEAN DEFAULT true,
    can_view_monitoring_data BOOLEAN DEFAULT false,
    can_provide_support BOOLEAN DEFAULT true,
    
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    notes TEXT,
    
    UNIQUE (partner_id, customer_id, relationship_type)
);

CREATE INDEX idx_pcr_partner_active ON public.partner_customer_relations(partner_id) 
    WHERE revoked_at IS NULL;
CREATE INDEX idx_pcr_customer_active ON public.partner_customer_relations(customer_id) 
    WHERE revoked_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════
-- Step 6: hq_assignments + hq_staff_capabilities
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE public.hq_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_user_id UUID REFERENCES public.users(id),
    
    assigned_partner_id UUID REFERENCES public.partners(id),
    assigned_customer_id UUID REFERENCES public.customers(id),
    
    assignment_type TEXT NOT NULL,
    role TEXT DEFAULT 'primary',
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by_user_id UUID REFERENCES public.users(id),
    unassigned_at TIMESTAMPTZ,
    unassigned_reason TEXT,
    
    CONSTRAINT exactly_one_target CHECK (
        (assigned_partner_id IS NOT NULL)::int + 
        (assigned_customer_id IS NOT NULL)::int = 1
    )
);

CREATE INDEX idx_hqa_manager ON public.hq_assignments(manager_user_id) 
    WHERE unassigned_at IS NULL;
CREATE INDEX idx_hqa_partner ON public.hq_assignments(assigned_partner_id) 
    WHERE unassigned_at IS NULL;
CREATE INDEX idx_hqa_customer ON public.hq_assignments(assigned_customer_id) 
    WHERE unassigned_at IS NULL;

CREATE TABLE public.hq_staff_capabilities (
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    capability TEXT NOT NULL,
    -- 'director' | 'ops_review' | 'manage_channels' 
    -- | 'manage_direct_customers' | 'manage_related_orgs' | 'system_operator'
    
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by_user_id UUID REFERENCES public.users(id),
    revoked_at TIMESTAMPTZ,
    revoke_reason TEXT,
    
    PRIMARY KEY (user_id, capability)
);

CREATE INDEX idx_hqsc_active ON public.hq_staff_capabilities(user_id, capability) 
    WHERE revoked_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════
-- Step 7: contracts 테이블
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE public.contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    contract_type TEXT NOT NULL,
    -- 'partner_sales' | 'partner_customer' | 'partner_org_admin'
    -- | 'customer_main' | 'license_order'
    
    partner_id UUID REFERENCES public.partners(id),
    customer_id UUID REFERENCES public.customers(id),
    
    contract_number TEXT UNIQUE NOT NULL,
    signed_date DATE NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    contract_value NUMERIC,
    
    document_url TEXT NOT NULL,
    document_uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    document_uploaded_by UUID REFERENCES public.users(id),
    document_hash TEXT,
    
    verified_by_user_id UUID REFERENCES public.users(id),
    verified_at TIMESTAMPTZ,
    verification_notes TEXT,
    
    contract_status TEXT DEFAULT 'pending_verification',
    
    approval_workflow_id UUID,  -- approval_workflows FK는 나중에
    
    terminated_at TIMESTAMPTZ,
    termination_reason TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT exactly_one_party CHECK (
        (partner_id IS NOT NULL)::int + (customer_id IS NOT NULL)::int = 1
    )
);

CREATE INDEX idx_contracts_partner ON public.contracts(partner_id);
CREATE INDEX idx_contracts_customer ON public.contracts(customer_id);
CREATE INDEX idx_contracts_status ON public.contracts(contract_status);
CREATE INDEX idx_contracts_type ON public.contracts(contract_type);

-- ═══════════════════════════════════════════════════════════════════
-- Step 8: licenses 테이블 (토큰 라이선스)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE public.licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    
    -- 발주·수금
    ordered_to_partner_id UUID REFERENCES public.partners(id),
    forwarded_via_distributor_id UUID REFERENCES public.partners(id),
    
    -- 계약
    contract_id UUID REFERENCES public.contracts(id) NOT NULL,
    contract_type TEXT,
    
    -- 기간
    contract_start DATE NOT NULL,
    contract_end DATE NOT NULL,
    
    -- 토큰
    seats_purchased INTEGER NOT NULL,
    months_purchased INTEGER NOT NULL,
    total_user_months_purchased NUMERIC GENERATED ALWAYS AS 
        (seats_purchased * months_purchased) STORED,
    
    user_months_consumed NUMERIC DEFAULT 0,
    user_months_remaining NUMERIC GENERATED ALWAYS AS 
        (seats_purchased * months_purchased - user_months_consumed) STORED,
    
    -- 가격
    list_price NUMERIC,
    actual_price NUMERIC,
    paid_amount NUMERIC DEFAULT 0,
    payment_status TEXT DEFAULT 'pending',
    
    unit_price_per_user_month NUMERIC GENERATED ALWAYS AS (
        CASE WHEN seats_purchased * months_purchased > 0 
             THEN actual_price / (seats_purchased * months_purchased)
             ELSE 0 END
    ) STORED,
    
    -- 발급 상태
    issuance_status TEXT DEFAULT 'pending_contract',
    
    -- 갱신
    parent_license_id UUID REFERENCES public.licenses(id),
    carried_over_user_months NUMERIC DEFAULT 0,
    renewal_discount_applied NUMERIC DEFAULT 0,
    renewal_option_chosen TEXT,
    
    license_status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_licenses_customer ON public.licenses(customer_id);
CREATE INDEX idx_licenses_active ON public.licenses(license_status) 
    WHERE license_status = 'active';
CREATE INDEX idx_licenses_end ON public.licenses(contract_end);

-- ═══════════════════════════════════════════════════════════════════
-- Step 9: user_license_periods (사용자별 활성 기간)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE public.user_license_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_id UUID REFERENCES public.licenses(id) NOT NULL,
    user_id UUID REFERENCES public.users(id) NOT NULL,
    
    activated_at DATE NOT NULL,
    deactivated_at DATE,
    deactivation_reason TEXT,
    
    -- 월할 토큰 소비
    user_months_consumed NUMERIC GENERATED ALWAYS AS (
        CASE 
            WHEN deactivated_at IS NULL THEN
                EXTRACT(YEAR FROM CURRENT_DATE) * 12 + EXTRACT(MONTH FROM CURRENT_DATE)
                - EXTRACT(YEAR FROM activated_at) * 12 - EXTRACT(MONTH FROM activated_at)
                + 1
            ELSE
                EXTRACT(YEAR FROM deactivated_at) * 12 + EXTRACT(MONTH FROM deactivated_at)
                - EXTRACT(YEAR FROM activated_at) * 12 - EXTRACT(MONTH FROM activated_at)
                + 1
        END
    ) STORED,
    
    notes TEXT,
    created_by_user_id UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ulp_license ON public.user_license_periods(license_id);
CREATE INDEX idx_ulp_user ON public.user_license_periods(user_id);
CREATE INDEX idx_ulp_active ON public.user_license_periods(license_id) 
    WHERE deactivated_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════
-- Step 10: workspace_memberships
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE public.workspace_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) NOT NULL,
    
    partner_id UUID REFERENCES public.partners(id),
    customer_id UUID REFERENCES public.customers(id),
    
    role_in_workspace TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    left_at TIMESTAMPTZ,
    
    CONSTRAINT exactly_one_workspace CHECK (
        (partner_id IS NOT NULL)::int + (customer_id IS NOT NULL)::int = 1
    ),
    UNIQUE (user_id, partner_id, customer_id)
);

CREATE UNIQUE INDEX one_default_per_user 
    ON public.workspace_memberships(user_id) 
    WHERE is_default = true AND left_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════
-- Step 11: 승인 워크플로우 (3단 게이트)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE public.approval_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    target_type TEXT NOT NULL,
    target_id UUID NOT NULL,
    
    requested_by_user_id UUID REFERENCES public.users(id),
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    request_reason TEXT,
    
    final_status TEXT DEFAULT 'pending',
    completed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE public.approval_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES public.approval_workflows(id) ON DELETE CASCADE,
    
    step_order INT NOT NULL,
    step_role TEXT NOT NULL,
    -- 'ops_review' | 'director_approval' | 'executive_approval'
    
    reviewer_id UUID REFERENCES public.users(id),
    status TEXT DEFAULT 'pending',
    reviewed_at TIMESTAMPTZ,
    notes TEXT,
    
    activated_at TIMESTAMPTZ,
    
    UNIQUE (workflow_id, step_order)
);

CREATE INDEX idx_steps_workflow ON public.approval_steps(workflow_id);
CREATE INDEX idx_steps_pending ON public.approval_steps(step_role, status) 
    WHERE status = 'pending';

-- contracts.approval_workflow_id FK 추가
ALTER TABLE public.contracts 
    ADD CONSTRAINT contracts_approval_fkey 
    FOREIGN KEY (approval_workflow_id) REFERENCES public.approval_workflows(id);

CREATE TABLE public.approval_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id UUID REFERENCES public.approval_steps(id),
    user_id UUID REFERENCES public.users(id),
    user_email TEXT,
    
    action TEXT NOT NULL,
    snapshot JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

REVOKE UPDATE, DELETE ON public.approval_audit_log FROM PUBLIC;
REVOKE UPDATE, DELETE ON public.approval_audit_log FROM authenticated;

CREATE INDEX idx_audit_step ON public.approval_audit_log(step_id);
CREATE INDEX idx_audit_user ON public.approval_audit_log(user_id);

CREATE TABLE public.approval_policies (
    target_type TEXT PRIMARY KEY,
    required_steps TEXT[] NOT NULL,
    auto_approve_threshold NUMERIC,
    description TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO public.approval_policies (target_type, required_steps, description) VALUES
    ('license_issuance_large', 
     ARRAY['ops_review', 'director_approval', 'executive_approval'], 
     '대형 라이선스 발급 (1천만원 이상)'),
    ('license_issuance_small', 
     ARRAY['ops_review', 'director_approval'], 
     '소형 라이선스 발급'),
    ('license_user_modify', 
     ARRAY['ops_review'], 
     '라이선스 사용자 추가/제거'),
    ('partner_onboarding', 
     ARRAY['ops_review', 'director_approval', 'executive_approval'], 
     '파트너 신규 등록'),
    ('refund_or_termination', 
     ARRAY['ops_review', 'director_approval', 'executive_approval'], 
     '환불 또는 계약 해지'),
    ('token_settlement', 
     ARRAY['ops_review', 'director_approval'], 
     '토큰 정산');

-- ═══════════════════════════════════════════════════════════════════
-- Step 12: payment_records
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE public.payment_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_id UUID REFERENCES public.licenses(id),
    
    payment_stage TEXT NOT NULL,
    -- 'customer_to_partner' | 'reseller_to_distributor' | 'partner_to_hq'
    
    from_entity_type TEXT NOT NULL,
    from_entity_id UUID NOT NULL,
    to_entity_type TEXT NOT NULL,
    to_entity_id UUID NOT NULL,
    
    amount NUMERIC NOT NULL,
    currency TEXT DEFAULT 'KRW',
    
    paid_at TIMESTAMPTZ NOT NULL,
    payment_method TEXT,
    payment_reference TEXT,
    
    receipt_url TEXT,
    
    notes TEXT,
    created_by_user_id UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_license ON public.payment_records(license_id);
CREATE INDEX idx_payments_paid_at ON public.payment_records(paid_at);

COMMIT;

-- ═══════════════════════════════════════════════════════════════════
-- 검증 (별도 쿼리로 실행)
-- ═══════════════════════════════════════════════════════════════════

-- 신규 테이블 모두 생성됐는지
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = 'public' AND table_name = t.table_name) AS column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
  AND table_name IN (
    'partners', 'customers', 'partner_customer_relations',
    'hq_assignments', 'hq_staff_capabilities',
    'contracts', 'licenses', 'user_license_periods',
    'workspace_memberships',
    'approval_workflows', 'approval_steps', 'approval_audit_log', 'approval_policies',
    'payment_records'
  )
ORDER BY table_name;
-- 기대: 14개 row

-- users 테이블 신규 컬럼 확인
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'users'
  AND column_name IN ('partner_id', 'customer_id', 'updated_at', 'preferences');
-- 기대: 4 row

-- approval_policies 초기 데이터 확인
SELECT target_type, array_length(required_steps, 1) AS step_count, description
FROM public.approval_policies
ORDER BY target_type;
-- 기대: 6 row

-- ═══════════════════════════════════════════════════════════════════
-- 롤백 (필요 시)
-- ═══════════════════════════════════════════════════════════════════
-- 신규 테이블 모두 제거 + users 컬럼 원복
/*
BEGIN;

DROP TABLE IF EXISTS public.payment_records CASCADE;
DROP TABLE IF EXISTS public.approval_audit_log CASCADE;
DROP TABLE IF EXISTS public.approval_steps CASCADE;
DROP TABLE IF EXISTS public.approval_workflows CASCADE;
DROP TABLE IF EXISTS public.approval_policies CASCADE;
DROP TABLE IF EXISTS public.workspace_memberships CASCADE;
DROP TABLE IF EXISTS public.user_license_periods CASCADE;
DROP TABLE IF EXISTS public.licenses CASCADE;
DROP TABLE IF EXISTS public.contracts CASCADE;
DROP TABLE IF EXISTS public.hq_staff_capabilities CASCADE;
DROP TABLE IF EXISTS public.hq_assignments CASCADE;
DROP TABLE IF EXISTS public.partner_customer_relations CASCADE;
DROP TABLE IF EXISTS public.customers CASCADE;
DROP TABLE IF EXISTS public.partners CASCADE;

ALTER TABLE public.users 
    DROP COLUMN IF EXISTS partner_id,
    DROP COLUMN IF EXISTS customer_id,
    DROP COLUMN IF EXISTS preferences;
-- updated_at은 보존 (이미 5/10에 추가했고 사용 중이라)

DROP FUNCTION IF EXISTS public.fill_parent_distributor() CASCADE;

COMMIT;
*/

-- ═══════════════════════════════════════════════════════════════════
-- ✅ Phase 1 완료 후 다음 단계
-- ═══════════════════════════════════════════════════════════════════
-- 1. 위 검증 쿼리 모두 통과 확인 (14 + 4 + 6 = 정상)
-- 2. Streamlit 앱 재시작 → 에러 없는지 확인 (기존 기능 정상 작동)
-- 3. phase2_migrate_data.sql 실행 준비
