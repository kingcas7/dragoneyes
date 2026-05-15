-- ════════════════════════════════════════════════════════════════
-- Phase 6: 라이선스 생애주기 관리 시스템 (License Lifecycle Management)
-- 작성: 2026-05-14 14:37
-- 목적: 카탈로그 + 발주 명세 + 보유 라이선스 3-Tier 구조
-- ════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────
-- 1. catalog_items (마스터 카탈로그)
--    본부가 관리하는 판매 가능 품목
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS catalog_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_code TEXT UNIQUE NOT NULL,           -- 'LIC-STD', 'LIC-PRO' 등
    item_name TEXT NOT NULL,                  -- 'DragonEyes 라이선스 (Standard)'
    category TEXT NOT NULL,                   -- 'license' / 'service' / 'addon'
    default_unit_price INT NOT NULL DEFAULT 0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_catalog_items_active ON catalog_items(is_active, sort_order);
CREATE INDEX IF NOT EXISTS idx_catalog_items_category ON catalog_items(category);

COMMENT ON TABLE catalog_items IS 'DragonEyes 판매 가능 품목 카탈로그 (본부 관리)';
COMMENT ON COLUMN catalog_items.item_code IS '품목 코드 (LIC-STD, LIC-PRO 등 변경 불가 식별자)';
COMMENT ON COLUMN catalog_items.category IS 'license/service/addon';

-- 시드 데이터
INSERT INTO catalog_items (item_code, item_name, category, default_unit_price, description, sort_order)
VALUES
    ('LIC-STD', 'DragonEyes 라이선스 (Standard)', 'license', 300000, '월 단위 사용자 라이선스, 기본 모니터링 기능', 1),
    ('LIC-PRO', 'DragonEyes 라이선스 (Pro)', 'license', 500000, '월 단위 사용자 라이선스, 고급 AI 분석 포함', 2),
    ('LIC-ENT', 'DragonEyes 라이선스 (Enterprise)', 'license', 800000, '월 단위 사용자 라이선스, 전체 기능 + 우선 지원', 3),
    ('SVC-CONSULT', '컨설팅 서비스', 'service', 100000, '시간당 전문 컨설팅', 10),
    ('SVC-SETUP', '초기 셋업 비용', 'service', 1000000, '일시불 셋업 및 온보딩', 11),
    ('SVC-TRAIN', '사용자 교육', 'service', 500000, '1회 교육 (관리자 + 사용자)', 12)
ON CONFLICT (item_code) DO NOTHING;

-- ────────────────────────────────────────────────────────────────
-- 2. license_request_items (발주 명세)
--    신청서당 N개의 발주 라인
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS license_request_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES license_requests(id) ON DELETE CASCADE,
    catalog_item_id UUID REFERENCES catalog_items(id),  -- NULL이면 직접 입력 (기타)
    
    -- 발주 명세 (단가 × 수량 × 기간 = 금액)
    item_name_snapshot TEXT NOT NULL,         -- 발주 당시 품목명 (catalog 변경되어도 보존)
    item_code_snapshot TEXT,                  -- 발주 당시 품목 코드
    unit_price INT NOT NULL DEFAULT 0,        -- 단가 (원/단위)
    quantity INT NOT NULL DEFAULT 1,          -- 수량 (사용자 수 또는 횟수)
    period_months INT NOT NULL DEFAULT 1,     -- 라이선스 기간 (개월) — service면 1
    amount INT NOT NULL DEFAULT 0,            -- 금액 = unit_price × quantity × period_months
    
    line_order INT DEFAULT 0,                 -- 발주서 내 라인 순서
    remark TEXT,                              -- 비고
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_request_items_request ON license_request_items(request_id, line_order);

COMMENT ON TABLE license_request_items IS '라이선스 신청서별 발주 명세 (PO 양식 ③ 영역)';
COMMENT ON COLUMN license_request_items.item_name_snapshot IS '발주 당시 품목명 스냅샷 (catalog 변경되어도 보존)';
COMMENT ON COLUMN license_request_items.amount IS '단가 × 수량 × 기간';

-- ────────────────────────────────────────────────────────────────
-- 3. tenant_licenses (보유 라이선스)
--    업체별 현재 활성 라이선스
--    좋아요님 비전: 추가/갱신/축소 가능
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenant_licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- 라이선스 정보
    catalog_item_id UUID REFERENCES catalog_items(id),
    item_code_snapshot TEXT NOT NULL,
    item_name_snapshot TEXT NOT NULL,
    
    -- 라이선스 수량/기간
    licensed_quantity INT NOT NULL DEFAULT 0,    -- 현재 보유 사용자 수
    unit_price INT NOT NULL DEFAULT 0,
    
    -- 라이선스 기간
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    
    -- 상태
    status TEXT NOT NULL DEFAULT 'active',    -- active/expired/cancelled/suspended
    
    -- 추적
    source_request_id UUID REFERENCES license_requests(id),    -- 최초 발급 신청서
    last_renewal_request_id UUID REFERENCES license_requests(id), -- 최근 갱신 신청서
    
    -- 알림
    expiry_notification_sent BOOLEAN DEFAULT FALSE,    -- 만료 30일 전 알림 발송 여부
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenant_licenses_tenant ON tenant_licenses(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_tenant_licenses_expiry ON tenant_licenses(end_date, status);

COMMENT ON TABLE tenant_licenses IS '업체별 보유 라이선스 (활성/만료/취소 추적)';
COMMENT ON COLUMN tenant_licenses.status IS 'active=사용중, expired=만료, cancelled=취소, suspended=일시중지';
COMMENT ON COLUMN tenant_licenses.licensed_quantity IS '현재 보유 사용자 수 (추가/축소 시 변경)';

-- ────────────────────────────────────────────────────────────────
-- updated_at 자동 갱신 트리거 (catalog_items, tenant_licenses)
-- ────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS catalog_items_updated_at ON catalog_items;
CREATE TRIGGER catalog_items_updated_at
    BEFORE UPDATE ON catalog_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS tenant_licenses_updated_at ON tenant_licenses;
CREATE TRIGGER tenant_licenses_updated_at
    BEFORE UPDATE ON tenant_licenses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ────────────────────────────────────────────────────────────────
-- 권한 (P2 Supabase 정책 변경 대비, 5/30~)
-- ────────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE ON public.catalog_items TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.catalog_items TO service_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.license_request_items TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.license_request_items TO service_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.tenant_licenses TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.tenant_licenses TO service_role;

-- ────────────────────────────────────────────────────────────────
-- 검증 쿼리
-- ────────────────────────────────────────────────────────────────
SELECT 
    'catalog_items' as table_name,
    COUNT(*) as row_count
FROM catalog_items
UNION ALL
SELECT 'license_request_items', COUNT(*) FROM license_request_items
UNION ALL
SELECT 'tenant_licenses', COUNT(*) FROM tenant_licenses;

-- catalog 시드 확인
SELECT item_code, item_name, category, default_unit_price 
FROM catalog_items 
ORDER BY sort_order;
