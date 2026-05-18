-- ═══════════════════════════════════════════════════════════════
-- DragonEyes Phase 1: 신규 테이블 생성 (System Design v2)
-- ═══════════════════════════════════════════════════════════════
-- 작성일: 2026-05-10
-- 목적: agencies/agency_tenants 기반 단순 구조 → partners/customers 분리 다층 구조 전환
-- 실행 환경: Supabase SQL Editor (PostgreSQL 15+)
-- 안전성: 트랜잭션 + 멱등성(IF NOT EXISTS) + 검증 쿼리 포함
-- 
-- 변경 사항:
--   1. partners 테이블 신설 (32 컬럼) - 3가지 계약 트랙 토글 지원
--   2. customer_organizations 테이블 신설 - tenants와 별개의 고객사 정보
--   3. partner_customers 매핑 테이블 신설 - N:M 관계
--   4. license_pools 신설 - 토큰 라이선스 (월할+현재형 소비)
--   5. workspaces 신설 - URL /w/{id}/... 구조
--   6. approval_steps + approval_policies - 3단 승인 게이트
--   7. hq_staff_capabilities - 본부 7역할 정의
--   8. token_consumption_logs - 라이선스 소비 추적
--   9. contract_documents - 모든 본부 라이선스 계약서 첨부 필수
--   10. license_renewals - 갱신 시 옵션A 할인 / 옵션B 연장
--   11. seat_changes - 좌석 추가/제거 이력
--   12. partner_tenant_assignments - 파트너↔테넌트 배정
--   13. notifications_v2 - 알림 시스템 확장
--   14. audit_logs_v2 - 감사 로그 확장
--   + users 테이블 4 컬럼 추가 (partner_id, customer_id, updated_at, preferences)
--   + partners_with_status VIEW
-- ═══════════════════════════════════════════════════════════════

BEGIN;

-- ───────────────────────────────────────────────────────────────
-- 1. partners 테이블 (32 컬럼)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.partners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 기본 정보
    name TEXT NOT NULL,
    business_number TEXT,
    representative_name TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    
    -- 3가지 계약 트랙 토글 (System Design v2 결정 ②)
    is_distributor BOOLEAN DEFAULT FALSE,  -- 총판
    is_reseller BOOLEAN DEFAULT FALSE,     -- 대리점 (sales contract)
    is_related_org BOOLEAN DEFAULT FALSE,  -- 유관기관 (org_admin contract)
    
    -- 부모-자식 관계 (총판 산하 대리점)
    parent_partner_id UUID REFERENCES public.partners(id) ON DELETE SET NULL,
    
    -- 비즈니스 채널
    business_channel TEXT DEFAULT 'direct_partnership',
    
    -- 계약 보유 플래그
    has_sales_contract BOOLEAN DEFAULT FALSE,
    has_customer_contract BOOLEAN DEFAULT FALSE,
    has_org_admin_contract BOOLEAN DEFAULT FALSE,
    
    -- 계약서 문서 ID (contract_documents.id 참조)
    sales_contract_doc_id UUID,
    customer_contract_doc_id UUID,
    org_admin_contract_doc_id UUID,
    
    -- 계약 활성 기간
    sales_contract_active_from DATE,
    sales_contract_active_to DATE,
    customer_contract_active_from DATE,
    customer_contract_active_to DATE,
    org_admin_contract_active_from DATE,
    org_admin_contract_active_to DATE,
    
    -- 영업 권한
    can_recruit_resellers BOOLEAN DEFAULT FALSE,
    
    -- 상태 관리
    partnership_status TEXT DEFAULT 'active',  -- active, pilot, suspended, terminated
    suspended_at TIMESTAMPTZ,
    terminated_at TIMESTAMPTZ,
    termination_reason TEXT,
    
    -- 레거시 매핑 (Phase 5에서 사용)
    legacy_agency_id UUID,
    
    -- 타임스탬프
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partners_business_number ON public.partners(business_number);
CREATE INDEX IF NOT EXISTS idx_partners_parent ON public.partners(parent_partner_id);
CREATE INDEX IF NOT EXISTS idx_partners_status ON public.partners(partnership_status);
CREATE INDEX IF NOT EXISTS idx_partners_legacy ON public.partners(legacy_agency_id);

-- ───────────────────────────────────────────────────────────────
-- 2. customer_organizations (고객사 정보 - tenants와 분리)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.customer_organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    business_number TEXT,
    representative_name TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    industry TEXT,
    employee_count INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customer_orgs_business ON public.customer_organizations(business_number);

-- ───────────────────────────────────────────────────────────────
-- 3. partner_customers (N:M 매핑) - 파트너 ↔ 테넌트
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.partner_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES public.partners(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    relationship_type TEXT DEFAULT 'sales',  -- sales, customer, org_admin
    is_opt_in BOOLEAN DEFAULT TRUE,  -- 유관기관 매핑은 옵트인
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    UNIQUE(partner_id, tenant_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_partner_customers_partner ON public.partner_customers(partner_id);
CREATE INDEX IF NOT EXISTS idx_partner_customers_tenant ON public.partner_customers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_partner_customers_type ON public.partner_customers(relationship_type);

-- ───────────────────────────────────────────────────────────────
-- 4. license_pools (토큰 라이선스 - 월할+현재형 소비)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.license_pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    license_plan TEXT NOT NULL,  -- basic, pro, enterprise
    
    -- 발급 단위
    total_seats INTEGER NOT NULL,
    used_seats INTEGER DEFAULT 0,
    
    -- 토큰 풀 (월할)
    monthly_token_quota BIGINT NOT NULL,
    consumed_tokens BIGINT DEFAULT 0,
    
    -- 1차/2차 송금 추적
    ordered_to UUID REFERENCES public.partners(id) ON DELETE SET NULL,  -- 1차 수금
    paid_to UUID REFERENCES public.partners(id) ON DELETE SET NULL,     -- 1차 수금 (=ordered_to)
    forwarded_via_distributor_id UUID REFERENCES public.partners(id) ON DELETE SET NULL,  -- 2단 송금
    
    -- 계약 기간
    license_start DATE NOT NULL,
    license_end DATE NOT NULL,
    
    -- 갱신 옵션
    renewal_option TEXT,  -- A_discount, B_extension
    last_renewed_at TIMESTAMPTZ,
    
    -- 상태
    status TEXT DEFAULT 'active',  -- active, expired, suspended
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_license_pools_tenant ON public.license_pools(tenant_id);
CREATE INDEX IF NOT EXISTS idx_license_pools_status ON public.license_pools(status);
CREATE INDEX IF NOT EXISTS idx_license_pools_dates ON public.license_pools(license_start, license_end);

-- ───────────────────────────────────────────────────────────────
-- 5. workspaces (URL /w/{id}/... 구조)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,  -- URL용 슬러그
    name TEXT NOT NULL,
    workspace_type TEXT NOT NULL,  -- hq, partner, customer, org_admin
    partner_id UUID REFERENCES public.partners(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (partner_id IS NOT NULL OR tenant_id IS NOT NULL OR workspace_type = 'hq')
);

CREATE INDEX IF NOT EXISTS idx_workspaces_slug ON public.workspaces(slug);
CREATE INDEX IF NOT EXISTS idx_workspaces_type ON public.workspaces(workspace_type);

-- ───────────────────────────────────────────────────────────────
-- 6. approval_steps + approval_policies (3단 승인 게이트)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.approval_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_name TEXT UNIQUE NOT NULL,
    target_resource TEXT NOT NULL,  -- license_pool, partner, contract, etc
    total_steps INTEGER NOT NULL,
    step_definitions JSONB NOT NULL,  -- [{step:1, approver_role:"operations"}, ...]
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.approval_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES public.approval_policies(id) ON DELETE CASCADE,
    target_id UUID NOT NULL,  -- 승인 대상 (license_pool.id 등)
    target_type TEXT NOT NULL,
    
    step_number INTEGER NOT NULL,
    approver_role TEXT NOT NULL,  -- operations, director, executive
    approver_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    
    status TEXT DEFAULT 'pending',  -- pending, approved, rejected
    decision_note TEXT,
    decided_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(policy_id, target_id, step_number)
);

CREATE INDEX IF NOT EXISTS idx_approval_steps_target ON public.approval_steps(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_approval_steps_status ON public.approval_steps(status);

-- 기본 정책 6 row 삽입
INSERT INTO public.approval_policies (policy_name, target_resource, total_steps, step_definitions, description) VALUES
('license_pool_creation', 'license_pool', 3, 
 '[{"step":1,"approver_role":"operations","label":"운영팀 검토"},{"step":2,"approver_role":"director","label":"Director 승인"},{"step":3,"approver_role":"executive","label":"임원 결재"}]',
 '라이선스 발급 3단 승인'),
('partner_creation', 'partner', 3,
 '[{"step":1,"approver_role":"operations","label":"운영팀 검토"},{"step":2,"approver_role":"director","label":"Director 승인"},{"step":3,"approver_role":"executive","label":"임원 결재"}]',
 '신규 파트너 등록 3단 승인'),
('contract_signing', 'contract_documents', 3,
 '[{"step":1,"approver_role":"operations","label":"운영팀 검토"},{"step":2,"approver_role":"director","label":"Director 승인"},{"step":3,"approver_role":"executive","label":"임원 결재"}]',
 '계약서 체결 3단 승인'),
('license_renewal', 'license_pool', 2,
 '[{"step":1,"approver_role":"operations","label":"운영팀 검토"},{"step":2,"approver_role":"director","label":"Director 승인"}]',
 '라이선스 갱신 2단 승인'),
('seat_change', 'license_pool', 1,
 '[{"step":1,"approver_role":"operations","label":"운영팀 검토"}]',
 '좌석 추가/제거 1단 승인'),
('partner_termination', 'partner', 3,
 '[{"step":1,"approver_role":"operations","label":"운영팀 검토"},{"step":2,"approver_role":"director","label":"Director 승인"},{"step":3,"approver_role":"executive","label":"임원 결재"}]',
 '파트너 해지 3단 승인')
ON CONFLICT (policy_name) DO NOTHING;

-- ───────────────────────────────────────────────────────────────
-- 7. hq_staff_capabilities (본부 7역할)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.hq_staff_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role_category TEXT NOT NULL,  -- executive, director, operations, channel_manager, direct_customer, related_org, support
    can_approve_step INTEGER,  -- 1, 2, 3 (승인 가능 단계)
    can_create_partners BOOLEAN DEFAULT FALSE,
    can_manage_customers BOOLEAN DEFAULT FALSE,
    can_view_finance BOOLEAN DEFAULT FALSE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    notes TEXT,
    UNIQUE(user_id, role_category)
);

CREATE INDEX IF NOT EXISTS idx_hq_staff_user ON public.hq_staff_capabilities(user_id);
CREATE INDEX IF NOT EXISTS idx_hq_staff_role ON public.hq_staff_capabilities(role_category);

-- ───────────────────────────────────────────────────────────────
-- 8. token_consumption_logs
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.token_consumption_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_pool_id UUID NOT NULL REFERENCES public.license_pools(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    tokens_consumed BIGINT NOT NULL,
    operation_type TEXT,  -- chat, analysis, recommendation, etc
    metadata JSONB,
    consumed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_token_logs_pool ON public.token_consumption_logs(license_pool_id);
CREATE INDEX IF NOT EXISTS idx_token_logs_user ON public.token_consumption_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_token_logs_date ON public.token_consumption_logs(consumed_at);

-- ───────────────────────────────────────────────────────────────
-- 9. contract_documents (모든 본부 라이선스 계약서 첨부 필수)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.contract_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_type TEXT NOT NULL,  -- sales, customer, org_admin, license
    partner_id UUID REFERENCES public.partners(id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE SET NULL,
    license_pool_id UUID REFERENCES public.license_pools(id) ON DELETE SET NULL,
    
    document_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    mime_type TEXT,
    
    signed_at DATE,
    expires_at DATE,
    
    uploaded_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contracts_partner ON public.contract_documents(partner_id);
CREATE INDEX IF NOT EXISTS idx_contracts_tenant ON public.contract_documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_contracts_type ON public.contract_documents(contract_type);

-- partners 테이블의 contract_doc_id FK 추가
ALTER TABLE public.partners 
    DROP CONSTRAINT IF EXISTS fk_partners_sales_contract,
    DROP CONSTRAINT IF EXISTS fk_partners_customer_contract,
    DROP CONSTRAINT IF EXISTS fk_partners_org_admin_contract;

ALTER TABLE public.partners
    ADD CONSTRAINT fk_partners_sales_contract 
        FOREIGN KEY (sales_contract_doc_id) REFERENCES public.contract_documents(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_partners_customer_contract 
        FOREIGN KEY (customer_contract_doc_id) REFERENCES public.contract_documents(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_partners_org_admin_contract 
        FOREIGN KEY (org_admin_contract_doc_id) REFERENCES public.contract_documents(id) ON DELETE SET NULL;

-- ───────────────────────────────────────────────────────────────
-- 10. license_renewals (갱신 시 옵션A 할인 / 옵션B 연장)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.license_renewals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_pool_id UUID NOT NULL REFERENCES public.license_pools(id) ON DELETE CASCADE,
    
    renewal_option TEXT NOT NULL,  -- A_discount, B_extension
    
    -- 옵션 A: 할인
    discount_rate DECIMAL(5,2),
    
    -- 옵션 B: 연장
    extension_months INTEGER,
    
    previous_end_date DATE,
    new_end_date DATE,
    
    chosen_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    chosen_at TIMESTAMPTZ DEFAULT NOW(),
    
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_renewals_pool ON public.license_renewals(license_pool_id);

-- ───────────────────────────────────────────────────────────────
-- 11. seat_changes (좌석 추가/제거 이력)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.seat_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_pool_id UUID NOT NULL REFERENCES public.license_pools(id) ON DELETE CASCADE,
    
    change_type TEXT NOT NULL,  -- add, remove
    seats_changed INTEGER NOT NULL,
    
    previous_total INTEGER,
    new_total INTEGER,
    
    -- 종료일 맞춤 정산
    prorated_amount DECIMAL(12,2),
    
    requested_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    approved_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_seat_changes_pool ON public.seat_changes(license_pool_id);

-- ───────────────────────────────────────────────────────────────
-- 12. partner_tenant_assignments (파트너↔테넌트 영업 배정)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.partner_tenant_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES public.partners(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    
    assignment_type TEXT DEFAULT 'sales_lead',  -- sales_lead, support, maintenance
    is_primary BOOLEAN DEFAULT FALSE,
    
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    
    notes TEXT,
    UNIQUE(partner_id, tenant_id, assignment_type)
);

CREATE INDEX IF NOT EXISTS idx_assignments_partner ON public.partner_tenant_assignments(partner_id);
CREATE INDEX IF NOT EXISTS idx_assignments_tenant ON public.partner_tenant_assignments(tenant_id);

-- ───────────────────────────────────────────────────────────────
-- 13. notifications_v2 (알림 시스템 확장)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.notifications_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    recipient_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    
    notification_type TEXT NOT NULL,  -- approval_request, task, announcement, system, etc
    priority TEXT DEFAULT 'normal',  -- low, normal, high, urgent
    
    title TEXT NOT NULL,
    body TEXT,
    
    source_type TEXT,  -- approval_steps, tasks, announcements, etc
    source_id UUID,
    target_page TEXT,  -- 클릭 시 이동할 페이지
    
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    
    expires_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notif_v2_recipient ON public.notifications_v2(recipient_id);
CREATE INDEX IF NOT EXISTS idx_notif_v2_unread ON public.notifications_v2(recipient_id, is_read) WHERE is_read = FALSE;
CREATE INDEX IF NOT EXISTS idx_notif_v2_type ON public.notifications_v2(notification_type);

-- ───────────────────────────────────────────────────────────────
-- 14. audit_logs_v2 (감사 로그 확장)
-- ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.audit_logs_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    actor_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    actor_role TEXT,
    
    action_type TEXT NOT NULL,  -- create, update, delete, approve, reject, etc
    target_type TEXT NOT NULL,  -- partner, tenant, license_pool, etc
    target_id UUID,
    
    before_data JSONB,
    after_data JSONB,
    
    ip_address TEXT,
    user_agent TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_v2_actor ON public.audit_logs_v2(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_v2_target ON public.audit_logs_v2(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_audit_v2_date ON public.audit_logs_v2(created_at);

-- ═══════════════════════════════════════════════════════════════
-- users 테이블 4컬럼 확장
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE public.users 
    ADD COLUMN IF NOT EXISTS partner_id UUID REFERENCES public.partners(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES public.customer_organizations(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_users_partner ON public.users(partner_id);
CREATE INDEX IF NOT EXISTS idx_users_customer ON public.users(customer_id);

-- ═══════════════════════════════════════════════════════════════
-- 트리거: updated_at 자동 갱신
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 각 테이블에 트리거 적용
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN 
        SELECT unnest(ARRAY['partners', 'customer_organizations', 'license_pools', 
                            'workspaces', 'users'])
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS update_%s_updated_at ON public.%I', t, t);
        EXECUTE format('CREATE TRIGGER update_%s_updated_at 
                        BEFORE UPDATE ON public.%I 
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()', t, t);
    END LOOP;
END $$;

-- ═══════════════════════════════════════════════════════════════
-- VIEW: partners_with_status (운영 편의용)
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW public.partners_with_status AS
SELECT 
    p.*,
    -- 계약 활성 여부 계산
    (p.has_sales_contract 
     AND CURRENT_DATE BETWEEN COALESCE(p.sales_contract_active_from, CURRENT_DATE) 
                          AND COALESCE(p.sales_contract_active_to, CURRENT_DATE + 1)) AS can_sell,
    (p.has_customer_contract 
     AND CURRENT_DATE BETWEEN COALESCE(p.customer_contract_active_from, CURRENT_DATE) 
                          AND COALESCE(p.customer_contract_active_to, CURRENT_DATE + 1)) AS can_consult,
    (p.has_org_admin_contract 
     AND CURRENT_DATE BETWEEN COALESCE(p.org_admin_contract_active_from, CURRENT_DATE) 
                          AND COALESCE(p.org_admin_contract_active_to, CURRENT_DATE + 1)) AS can_admin_orgs,
    -- 통계
    (SELECT COUNT(*) FROM public.partner_customers pc WHERE pc.partner_id = p.id) AS customer_count,
    (SELECT COUNT(*) FROM public.users u WHERE u.partner_id = p.id) AS user_count
FROM public.partners p;

-- ═══════════════════════════════════════════════════════════════
-- 검증 쿼리 (실행 후 확인용)
-- ═══════════════════════════════════════════════════════════════
DO $$
DECLARE
    table_count INTEGER;
    policy_count INTEGER;
BEGIN
    -- 14개 테이블 + users 컬럼 확인
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public' 
      AND table_name IN (
          'partners', 'customer_organizations', 'partner_customers',
          'license_pools', 'workspaces', 'approval_steps', 'approval_policies',
          'hq_staff_capabilities', 'token_consumption_logs', 'contract_documents',
          'license_renewals', 'seat_changes', 'partner_tenant_assignments',
          'notifications_v2', 'audit_logs_v2'
      );
    
    SELECT COUNT(*) INTO policy_count FROM public.approval_policies;
    
    RAISE NOTICE '✅ Phase 1 완료';
    RAISE NOTICE '   신규 테이블 생성: % / 15개', table_count;
    RAISE NOTICE '   기본 승인 정책: % rows', policy_count;
    
    IF table_count < 15 THEN
        RAISE WARNING '⚠️ 일부 테이블 생성 누락. 확인 필요.';
    END IF;
END $$;

COMMIT;

-- ═══════════════════════════════════════════════════════════════
-- 롤백 SQL (필요 시 별도 실행)
-- ═══════════════════════════════════════════════════════════════
-- 주의: 운영 데이터 손실 위험. 백업 후 실행.
/*
BEGIN;

-- users 컬럼 제거
ALTER TABLE public.users 
    DROP COLUMN IF EXISTS partner_id,
    DROP COLUMN IF EXISTS customer_id,
    DROP COLUMN IF EXISTS preferences;
-- updated_at은 유지 (다른 곳에서 사용 가능)

-- VIEW 삭제
DROP VIEW IF EXISTS public.partners_with_status;

-- 테이블 역순 삭제 (FK 의존성)
DROP TABLE IF EXISTS public.audit_logs_v2 CASCADE;
DROP TABLE IF EXISTS public.notifications_v2 CASCADE;
DROP TABLE IF EXISTS public.partner_tenant_assignments CASCADE;
DROP TABLE IF EXISTS public.seat_changes CASCADE;
DROP TABLE IF EXISTS public.license_renewals CASCADE;
DROP TABLE IF EXISTS public.contract_documents CASCADE;
DROP TABLE IF EXISTS public.token_consumption_logs CASCADE;
DROP TABLE IF EXISTS public.hq_staff_capabilities CASCADE;
DROP TABLE IF EXISTS public.approval_steps CASCADE;
DROP TABLE IF EXISTS public.approval_policies CASCADE;
DROP TABLE IF EXISTS public.workspaces CASCADE;
DROP TABLE IF EXISTS public.license_pools CASCADE;
DROP TABLE IF EXISTS public.partner_customers CASCADE;
DROP TABLE IF EXISTS public.customer_organizations CASCADE;
DROP TABLE IF EXISTS public.partners CASCADE;

-- 트리거 함수 (다른 테이블에서 사용 중일 수 있음 - 신중히)
-- DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

COMMIT;
*/
