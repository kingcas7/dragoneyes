# DragonEyes System Design v2

> **버전 정보**
> - 문서 버전: v2.0
> - 작성일: 2026-05-10
> - 작성자: 최승현 (4U Solution)
> - 상태: Draft → 다음주 검토 후 Approved
> - 이 문서의 위치: `~/dragoneyes/docs/DragonEyes_System_Design_v2.md`
> - 보안·개인정보 운영은 별도 문서 참조: `DragonEyes_Privacy_Operations_v1.md`

---

## 목차

- [0. 메타 정보](#0-메타-정보)
- [1. 비즈니스 모델](#1-비즈니스-모델)
- [2. 데이터 모델](#2-데이터-모델)
- [3. 토큰 라이선스 회계](#3-토큰-라이선스-회계)
- [4. 권한 격리 매트릭스](#4-권한-격리-매트릭스)
- [5. 마이그레이션 단계](#5-마이그레이션-단계)
- [6. UI / Workspace 모델](#6-ui--workspace-모델)
- [7. 보안 & 개인정보보호 (요약)](#7-보안--개인정보보호-요약)
- [부록 A: 전체 SQL 스키마](#부록-a-전체-sql-스키마)
- [부록 B: 미해결 항목 + Phase 2 백로그](#부록-b-미해결-항목--phase-2-백로그)

---

## 0. 메타 정보

### 0.1 문서 목적

이 문서는 DragonEyes 시스템의 v2 업그레이드 청사진입니다. 다음 작업의 기반이 됩니다:
- 다음 주 partners 테이블 마이그레이션
- 코드 레벨 `agency_id` → `partner_id` 전환
- UI 메뉴 재편 (위탁대시보드 → Workspace 모델)
- 토큰 라이선스 시스템 도입

### 0.2 v1 → v2 주요 변경점

| 영역 | v1 | v2 |
|---|---|---|
| 파트너 관리 | `agencies` 단일 테이블 | `partners` 통합 (총판·대리점·유관기관) |
| 고객 관리 | 사용자 안에 분산 | `customers` 별도 마스터 테이블 |
| 라이선스 모델 | 정액 | **토큰 (user-months)** |
| 권한 모델 | role 단일 | role + capabilities + assignments |
| 승인 워크플로우 | 단순 | **3단 게이트** (운영팀 → Director → 임원) |
| UI 모델 | 통합 화면 | **Workspace 격리** |
| 동의 관리 | 체크박스 1개 | **4-Layer 분리 동의** |

### 0.3 결정자 및 책임자

- **시스템 설계 결정**: 최승현
- **보안 정책 결정**: 최승현 (보안 엔지니어 합류 전까지)
- **법무 검토**: 외부 자문 (예정)
- **개인정보 보호책임자**: 최승현 (대표 겸임)

### 0.4 관련 문서

- `DragonEyes_Privacy_Operations_v1.md` — 보안·개인정보 운영 매뉴얼
- 5/10 인계 문서 — 개발 컨텍스트
- `app.py` — 현재 코드베이스
- Supabase Dashboard — 현재 DB 스키마

---

## 1. 비즈니스 모델

### 1.1 채널 구조

DragonEyes는 4U Solution의 SaaS 모니터링 플랫폼이며, 다음 채널로 영업합니다:

```
DragonEyes 본부 (4U Solution)
│
├── [A] Direct Business — 본부가 직접 고객 영업
│       └── 고객법인
│
└── [B] Indirect Business — 채널 영업
        │
        ├── [B-1] 총판 (Distributor)
        │       └── 산하 대리점 → 고객법인
        │           발주 흐름: 대리점 → 총판 → 본부
        │
        └── [B-2] 직접 계약 대리점 (총판 미경유)
                └── 고객법인
                    발주 흐름: 대리점 → 본부
```

### 1.2 본부 내부 조직

본부는 7가지 역할로 구성됩니다:

| 역할 | 책임 | 권한 범위 |
|---|---|---|
| 본부 임원 (super_admin) | 회사 전체 책임, 최종 승인 | 모든 데이터·작업 |
| Director (영업총괄) | 영업 결과 책임, 2차 승인 | 영업·계약 관련 모든 데이터 |
| 운영팀 (ops_team) | 절차·규정 준수, 1차 검토 | 모든 계약·라이선스 요청 |
| 채널 매니저 | 담당 총판·대리점 관리 | 자기 담당 파트너 + 그들의 고객 |
| 직접고객 담당 | Direct 계약 고객 관리 | 자기 담당 고객만 |
| 유관기관 담당 | 유관기관 3트랙 관리 | 자기 담당 유관기관 |
| 운영 담당 | 시스템·고객 지원 | 시스템 운영 |

### 1.3 파트너의 다중 역할 (3가지 계약 트랙)

파트너는 단일 종류가 아니라 **계약 트랙의 조합**으로 정의됩니다:

| 트랙 | 계약 | 권한 | 과금 |
|---|---|---|---|
| ① 영업 | 파트너 계약 | 라이선스 판매 | 수수료/마진 |
| ② 자체 사용 | 고객 계약 | 자체 모니터링 운영 | 라이선스 비용 |
| ③ 유관기관 권한 | 유관기관 계약 | 사용자 지원·관리 (옵트인 기반) | 별도 과금 |

한 파트너가 1~3개 트랙을 동시 보유할 수 있습니다.

### 1.4 유관기관의 특수성

유관기관은 다음 3가지 역할을 조합할 수 있습니다:

1. **영업 가능** (트랙 ①): 본부 승인으로 라이선스 판매 권한 획득
2. **자체 사용** (트랙 ②): 본부와 직접 고객 계약 체결
3. **사용자 지원** (트랙 ③): 옵트인된 고객·사용자에 대해 서류 요청·지원

**중요**: 유관기관이 사용자 데이터에 접근하려면 **고객사 또는 사용자가 자발적으로 "내 소속 유관기관"을 지정**해야 합니다 (옵트인 모델). 유관기관이 일방적으로 "이 사용자 관리할게"가 아닙니다.

### 1.5 발주·수금 흐름

원칙: **"발주받은 사람이 곧 1차 수금자"**

| 케이스 | 발주처 | 1차 수금 | 본부 송금 |
|---|---|---|---|
| 본부 직접 영업 | 본부 | 본부 | - |
| 직접계약 대리점 | 대리점 | 대리점 | 대리점 → 본부 |
| 총판 산하 대리점 | 대리점 | 대리점 | 대리점 → 총판 → 본부 |
| 유관기관 영업 | 유관기관 | 유관기관 | 유관기관 → (총판 또는) 본부 |

**모든 본부 발급 라이선스는 계약서 첨부 필수**입니다 (투명성 확보).

### 1.6 승인 워크플로우 (3단 게이트)

모든 중요 액션은 다음 게이트를 통과해야 합니다:

```
요청 발생 → [운영팀 검토 (1차)] → [Director 승인 (2차, 영업 책임)] → [본부 임원 승인 (최종)]
                ↑                       ↑                              ↑
            절차·규정              영업 결과 책임                회사 전략·재무
```

DB 레벨 CHECK 제약으로 운영팀 통과 없이 상위 단계 승인이 불가능하게 강제됩니다.

### 1.7 결재 정책 (요청 종류별 필요 단계)

| 액션 | 필요 단계 | 사유 |
|---|---|---|
| 라이선스 발급 (대형) | 운영팀 → Director → 임원 | 매출 영향 큼 |
| 라이선스 발급 (소형) | 운영팀 → Director | 임원까지는 과함 |
| 라이선스 사용자 추가/제거 | 운영팀만 | 일상 운영 |
| 파트너 신규 등록 | 운영팀 → Director → 임원 | 채널 정책 |
| 환불·계약 해지 | 운영팀 → Director → 임원 | 손실 영향 |
| 토큰 정산 | 운영팀 → Director | 회계 영향 |

이 정책은 `approval_policies` 테이블로 관리되며 운영하면서 조정 가능합니다.

---

## 2. 데이터 모델

### 2.1 핵심 테이블 개요

v2에서 신규 또는 변경되는 테이블:

| 테이블 | 상태 | 설명 |
|---|---|---|
| `partners` | 🆕 신규 | 총판·대리점·유관기관 통합 |
| `customers` | 🆕 신규 | 고객법인 마스터 |
| `partner_customer_relations` | 🆕 신규 | N:M 관계 (유관기관 매핑 등) |
| `hq_assignments` | 🆕 신규 | 본부 직원 ↔ 외부 entity 담당 배정 |
| `hq_staff_capabilities` | 🆕 신규 | 본부 직원 세부 권한 |
| `contracts` | 🆕 신규 | 모든 계약서 마스터 |
| `licenses` | 🆕 신규 | 토큰 라이선스 |
| `user_license_periods` | 🆕 신규 | 사용자별 라이선스 활성 기간 |
| `approval_workflows` | 🆕 신규 | 승인 워크플로우 마스터 |
| `approval_steps` | 🆕 신규 | 승인 단계 (동적 N단) |
| `approval_audit_log` | 🆕 신규 | 결재 감사 로그 |
| `approval_policies` | 🆕 신규 | 결재 정책 |
| `workspace_memberships` | 🆕 신규 | Workspace 멤버십 |
| `payment_records` | 🆕 신규 | 결제 기록 |
| `users` | ✏️ 변경 | partner_id, customer_id, updated_at 추가 |
| `agencies` | 🗑️ 폐기 | partners로 마이그레이션 후 제거 |

보안·동의 관련 테이블은 `DragonEyes_Privacy_Operations_v1.md`에서 다룹니다.

### 2.2 partners 테이블

```sql
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
    
    -- 계층 (총판 ← 대리점)
    parent_partner_id UUID REFERENCES public.partners(id),
    
    -- 채널
    business_channel TEXT NOT NULL,
    -- 'direct' | 'via_distributor' | 'reseller_direct' | 'related_org'
    
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
    
    -- 파트너십 상태
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
```

### 2.3 customers 테이블

```sql
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
    
    -- 영업 정보 (권한 격리의 핵심)
    sold_by_partner_id UUID REFERENCES public.partners(id),
    parent_distributor_id UUID REFERENCES public.partners(id),
    business_channel TEXT NOT NULL,  -- 'direct' | 'via_partner'
    
    -- 직접고객 담당자 (Direct 케이스만)
    direct_customer_manager_id UUID REFERENCES public.users(id),
    
    -- 고객 상태
    customer_status TEXT DEFAULT 'active',  -- 'prospect' | 'active' | 'churned'
    contract_signed_at TIMESTAMPTZ,
    churned_at TIMESTAMPTZ,
    churn_reason TEXT,
    
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
```

### 2.4 partner_customer_relations (N:M)

유관기관 매핑은 사용자/고객의 옵트인이 필요합니다.

```sql
CREATE TABLE public.partner_customer_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID REFERENCES public.partners(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES public.customers(id) ON DELETE CASCADE,
    
    relationship_type TEXT NOT NULL,
    -- 'sales': 영업 관계
    -- 'related_org_assigned_by_customer': 고객사가 자발적으로 지정
    -- 'related_org_assigned_by_user': 사용자(장애인)가 자발적으로 지정
    -- 'document_support': 서류 지원
    -- 'consulting': 컨설팅
    
    -- 옵트인 추적 (개인정보보호법 대응)
    opted_in_by_user_id UUID REFERENCES public.users(id),
    opted_in_at TIMESTAMPTZ,
    opt_in_evidence TEXT,
    consent_record_id UUID,  -- consent_records FK (Privacy 문서 참조)
    
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

CREATE INDEX idx_pcr_partner ON public.partner_customer_relations(partner_id) 
    WHERE revoked_at IS NULL;
CREATE INDEX idx_pcr_customer ON public.partner_customer_relations(customer_id) 
    WHERE revoked_at IS NULL;
```

### 2.5 hq_assignments 테이블

본부 직원이 어떤 외부 entity를 담당하는지 관리합니다.

```sql
CREATE TABLE public.hq_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_user_id UUID REFERENCES public.users(id),
    
    -- 담당 대상 (둘 중 하나만)
    assigned_partner_id UUID REFERENCES public.partners(id),
    assigned_customer_id UUID REFERENCES public.customers(id),
    
    assignment_type TEXT NOT NULL,
    -- 'channel_mgr_distributor' | 'channel_mgr_reseller'
    -- | 'direct_customer_mgr' | 'related_org_mgr'
    
    role TEXT DEFAULT 'primary',  -- 'primary' | 'secondary' | 'backup'
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by_user_id UUID REFERENCES public.users(id),
    unassigned_at TIMESTAMPTZ,
    unassigned_reason TEXT,
    
    CONSTRAINT exactly_one_target CHECK (
        (assigned_partner_id IS NOT NULL)::int + 
        (assigned_customer_id IS NOT NULL)::int = 1
    )
);

CREATE INDEX idx_hq_assignments_manager ON public.hq_assignments(manager_user_id) 
    WHERE unassigned_at IS NULL;
CREATE INDEX idx_hq_assignments_partner ON public.hq_assignments(assigned_partner_id) 
    WHERE unassigned_at IS NULL;
CREATE INDEX idx_hq_assignments_customer ON public.hq_assignments(assigned_customer_id) 
    WHERE unassigned_at IS NULL;
```

### 2.6 hq_staff_capabilities 테이블

본부 직원의 세부 권한을 관리합니다 (한 직원 다중 역할 가능).

```sql
CREATE TABLE public.hq_staff_capabilities (
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    capability TEXT NOT NULL,
    -- 'director'                : Director 권한
    -- 'ops_review'              : 운영팀 검토 권한
    -- 'manage_channels'         : 채널 매니저
    -- 'manage_direct_customers' : 직접고객 담당
    -- 'manage_related_orgs'     : 유관기관 담당
    -- 'system_operator'         : 시스템 운영
    
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by_user_id UUID REFERENCES public.users(id),
    revoked_at TIMESTAMPTZ,
    revoke_reason TEXT,
    
    PRIMARY KEY (user_id, capability)
);
```

### 2.7 contracts 테이블

모든 계약서를 통합 관리합니다.

```sql
CREATE TABLE public.contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    contract_type TEXT NOT NULL,
    -- 'partner_sales': 파트너 영업 계약
    -- 'partner_customer': 파트너 자체사용 계약  
    -- 'partner_org_admin': 유관기관 권한 계약
    -- 'customer_main': 고객 본 계약
    -- 'license_order': 라이선스 발주 계약
    
    -- 계약 당사자
    partner_id UUID REFERENCES public.partners(id),
    customer_id UUID REFERENCES public.customers(id),
    
    -- 계약 정보
    contract_number TEXT UNIQUE NOT NULL,
    signed_date DATE NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    contract_value NUMERIC,
    
    -- 문서
    document_url TEXT NOT NULL,
    document_uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    document_uploaded_by UUID REFERENCES public.users(id),
    document_hash TEXT,  -- SHA-256
    
    -- 검증
    verified_by_user_id UUID REFERENCES public.users(id),
    verified_at TIMESTAMPTZ,
    verification_notes TEXT,
    
    -- 상태
    contract_status TEXT DEFAULT 'pending_verification',
    -- 'pending_verification' | 'active' | 'expired' | 'terminated'
    
    -- 승인 워크플로우 연결
    approval_workflow_id UUID,
    
    -- 종료
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
```

### 2.8 시나리오별 데이터 패턴 검증

5가지 케이스에 어떤 row가 들어가는지:

#### 케이스 A: 본부가 직접 고객 영업

```
partners:                       (없음)
customers:                       
  ├── id: c001
  ├── name: "고객A"
  ├── sold_by_partner_id: NULL
  ├── business_channel: 'direct'
  └── direct_customer_manager_id: 박직원
hq_assignments:                  
  ├── manager_user_id: 박직원
  ├── assigned_customer_id: c001
  └── assignment_type: 'direct_customer_mgr'
```

#### 케이스 B: 직접계약 대리점이 영업

```
partners:                        
  ├── id: p001
  ├── name: "대리점B"
  ├── is_reseller: true
  ├── parent_partner_id: NULL
  ├── business_channel: 'reseller_direct'
  └── has_sales_contract: true
customers:                       
  ├── sold_by_partner_id: p001
  └── business_channel: 'via_partner'
hq_assignments:                  
  ├── assigned_partner_id: p001
  └── assignment_type: 'channel_mgr_reseller'
```

#### 케이스 C: 총판 산하 대리점이 영업

```
partners:                        
  ├── 총판T (id: p100, is_distributor: true)
  └── 대리점D (id: p101, is_reseller: true, parent_partner_id: p100)
customers:                       
  ├── sold_by_partner_id: p101
  ├── parent_distributor_id: p100  (트리거로 자동 채움)
  └── business_channel: 'via_partner'
hq_assignments:                  
  ├── assigned_partner_id: p100  (총판 단위로 매니저 배정)
  └── assignment_type: 'channel_mgr_distributor'
```

#### 케이스 D: 유관기관이 영업 (트랙 ① 보유)

```
partners:                        
  ├── id: p200
  ├── name: "유관기관O"
  ├── is_related_org: true
  ├── has_sales_contract: true     (트랙 ① 활성)
  ├── has_customer_contract: false
  ├── has_org_admin_contract: false
  └── business_channel: 'related_org'
customers:                       
  ├── sold_by_partner_id: p200
  └── business_channel: 'via_partner'
hq_assignments:                  
  ├── assigned_partner_id: p200
  └── assignment_type: 'related_org_mgr'
```

#### 케이스 E: 유관기관이 사용자 지원 + 영업 (트랙 ① + ③)

```
partners:                        
  ├── id: p300
  ├── name: "유관기관P"
  ├── is_related_org: true
  ├── has_sales_contract: true     (트랙 ①)
  └── has_org_admin_contract: true (트랙 ③)
customers:                       
  └── (다른 고객들, sold_by_partner_id: p300 또는 다른 파트너)
partner_customer_relations:      
  ├── partner_id: p300
  ├── customer_id: c500 (사용자가 자발 지정)
  ├── relationship_type: 'related_org_assigned_by_user'
  ├── opted_in_by_user_id: 사용자
  └── consent_record_id: 동의 기록
hq_assignments:                  
  ├── assigned_partner_id: p300
  └── assignment_type: 'related_org_mgr'
```

**중요**: 유관기관은 자기 자신을 customer로 두지 않습니다. 유관기관이 모니터링 서비스를 자체 사용하려면 별도 customer row가 필요하고, 이 경우엔 `has_customer_contract`로 트랙 ②를 추가합니다.

---

## 3. 토큰 라이선스 회계

### 3.1 핵심 개념

**토큰 = user-months** (좌석 × 개월 수)

```
일반 SaaS:    5명 × 12개월 = 5명이 12개월 내내 사용 (잔여 시 손실)
DragonEyes:   5명 × 12개월 = 60 user-months 토큰 (월할 정산)
              ↓
              중간에 휴직/퇴사 시 미사용 토큰 절약
              ↓
              갱신 시 고객 선택:
              ├── 옵션 A: 다음 라이선스 할인
              └── 옵션 B: 다음 라이선스 기간 연장
```

**합리성 근거**: 장애인 고용은 변동성이 큽니다 (질병/입원/휴직 빈번). 일반 SaaS의 정액제는 미사용 기간만큼 비용 손실이 발생하지만, 토큰 모델은 이를 방지합니다.

### 3.2 4가지 핵심 결정사항

| # | 결정 | 사유 |
|---|---|---|
| Q1 | **월할 계산** | 일할 대비 단순, 영업·청구 표준화 |
| Q2 | **현재형 소비** | 실제 사용한 만큼만 누적, 휴직 시 자동 정산 |
| Q3 | **갱신 시 고객 선택** (옵션 A/B) | UI 토글로 제공, DB는 둘 다 지원 |
| Q4 | **좌석 추가 자유** | 종료일 맞춰 토큰 할당, 갱신 시 일괄 관리 |

### 3.3 licenses 테이블

```sql
CREATE TABLE public.licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    
    -- 발주·수금 라인
    ordered_to_partner_id UUID REFERENCES public.partners(id),     
    -- NULL이면 본부 직접
    forwarded_via_distributor_id UUID REFERENCES public.partners(id),
    
    -- 계약
    contract_id UUID REFERENCES public.contracts(id) NOT NULL,
    contract_type TEXT,  -- '1year' | '2year' | 'custom'
    
    -- 기간
    contract_start DATE NOT NULL,
    contract_end DATE NOT NULL,
    
    -- 토큰 (핵심)
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
    payment_status TEXT DEFAULT 'pending',  -- 'pending' | 'partial' | 'paid'
    
    -- 단가 (할인·이월 계산용)
    unit_price_per_user_month NUMERIC GENERATED ALWAYS AS (
        CASE WHEN seats_purchased * months_purchased > 0 
             THEN actual_price / (seats_purchased * months_purchased)
             ELSE 0 END
    ) STORED,
    
    -- 발급 상태
    issuance_status TEXT DEFAULT 'pending_contract',
    -- 'pending_contract' | 'pending_ops' | 'pending_director' 
    -- | 'pending_executive' | 'issued' | 'rejected'
    
    -- 갱신 추적
    parent_license_id UUID REFERENCES public.licenses(id),
    carried_over_user_months NUMERIC DEFAULT 0,
    renewal_discount_applied NUMERIC DEFAULT 0,
    renewal_option_chosen TEXT,  -- 'discount' | 'extension' | NULL
    
    license_status TEXT DEFAULT 'active',  -- 'active' | 'expired' | 'terminated'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_licenses_customer ON public.licenses(customer_id);
CREATE INDEX idx_licenses_status ON public.licenses(license_status) 
    WHERE license_status = 'active';
CREATE INDEX idx_licenses_end ON public.licenses(contract_end);
```

### 3.4 user_license_periods 테이블

```sql
CREATE TABLE public.user_license_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_id UUID REFERENCES public.licenses(id) NOT NULL,
    user_id UUID REFERENCES public.users(id) NOT NULL,
    
    -- 활성 기간
    activated_at DATE NOT NULL,
    deactivated_at DATE,
    deactivation_reason TEXT,
    -- 'resigned' | 'leave' | 'transferred' | 'license_end' | 'manual'
    
    -- 토큰 소비량 (월할 자동 계산)
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
```

### 3.5 종료일 맞춤 활성화 함수

신규 사용자 추가 시 라이선스 종료일에 맞춰 자동 정산하는 함수:

```sql
CREATE OR REPLACE FUNCTION activate_user_with_license_end(
    p_license_id UUID,
    p_user_id UUID,
    p_activate_from DATE DEFAULT CURRENT_DATE
) RETURNS UUID AS $$
DECLARE
    v_license_end DATE;
    v_remaining NUMERIC;
    v_required NUMERIC;
    v_period_id UUID;
BEGIN
    -- 라이선스 정보 조회
    SELECT contract_end, user_months_remaining 
    INTO v_license_end, v_remaining
    FROM licenses WHERE id = p_license_id AND license_status = 'active';
    
    IF v_license_end IS NULL THEN
        RAISE EXCEPTION 'License % not found or not active', p_license_id;
    END IF;
    
    -- 필요 토큰 계산 (월할)
    v_required := EXTRACT(YEAR FROM v_license_end) * 12 
                + EXTRACT(MONTH FROM v_license_end)
                - EXTRACT(YEAR FROM p_activate_from) * 12 
                - EXTRACT(MONTH FROM p_activate_from)
                + 1;
    
    -- 잔여 부족 시 경고 (차단 아님 — 좌석 추가 자유 정책)
    IF v_remaining < v_required THEN
        RAISE WARNING 'License token shortage: need %, have %. Consider adding tokens.', 
            v_required, v_remaining;
    END IF;
    
    -- 활성화 (deactivated_at은 라이선스 종료일로 미리 설정 — 일관 관리)
    INSERT INTO user_license_periods (
        license_id, user_id, activated_at, deactivated_at
    )
    VALUES (
        p_license_id, p_user_id, p_activate_from, v_license_end
    )
    RETURNING id INTO v_period_id;
    
    RETURN v_period_id;
END;
$$ LANGUAGE plpgsql;
```

### 3.6 토큰 정산 시뮬레이션

```
시나리오: 5명 × 12개월 = 60 user-months 라이선스
계약 기간: 2024-01-01 ~ 2024-12-31
단가: 100,000원 / user-month (총 600만원)

타임라인:
─────────────────────────────────────────────
2024-01-01: 김씨, 이씨, 박씨, 최씨, 정씨 활성화 (5명)
2024-06-15: 이씨 휴직 (deactivated_at = 2024-06-15)
2024-08-31: 최씨 퇴사 (deactivated_at = 2024-08-31)
2024-12-31: 라이선스 종료
─────────────────────────────────────────────

토큰 소비 계산 (월할):
- 김씨: 1월~12월 = 12 user-months
- 이씨: 1월~6월  = 6 user-months
- 박씨: 1월~12월 = 12 user-months
- 최씨: 1월~8월  = 8 user-months
- 정씨: 1월~12월 = 12 user-months

총 소비 = 12 + 6 + 12 + 8 + 12 = 50 user-months
구매   = 60 user-months
절약   = 10 user-months (16.7%)
절약 금액 = 10 × 100,000 = 1,000,000원
─────────────────────────────────────────────

갱신 시 옵션:
옵션 A (할인): 다음 라이선스 결제액에서 100만원 할인
옵션 B (연장): 다음 라이선스 기간 16.7% 연장
              5명 × 12개월 → 5명 × 14개월
```

### 3.7 갱신 처리 SQL

```sql
CREATE OR REPLACE FUNCTION renew_license(
    p_old_license_id UUID,
    p_new_seats INTEGER,
    p_new_months INTEGER,
    p_new_price NUMERIC,
    p_renewal_option TEXT  -- 'discount' | 'extension'
) RETURNS UUID AS $$
DECLARE
    v_old_record RECORD;
    v_savings NUMERIC;
    v_new_license_id UUID;
    v_unit_price NUMERIC;
BEGIN
    -- 이전 라이선스 정보
    SELECT * INTO v_old_record 
    FROM licenses WHERE id = p_old_license_id;
    
    -- 절약 토큰 계산
    v_savings := v_old_record.user_months_remaining;
    v_unit_price := v_old_record.unit_price_per_user_month;
    
    -- 새 라이선스 생성
    IF p_renewal_option = 'discount' THEN
        INSERT INTO licenses (
            customer_id, parent_license_id,
            seats_purchased, months_purchased,
            actual_price, list_price,
            renewal_discount_applied, renewal_option_chosen,
            contract_start, contract_end
        ) VALUES (
            v_old_record.customer_id, p_old_license_id,
            p_new_seats, p_new_months,
            p_new_price - (v_savings * v_unit_price),  -- 할인 적용
            p_new_price,
            v_savings * v_unit_price,
            'discount',
            v_old_record.contract_end + INTERVAL '1 day',
            v_old_record.contract_end + INTERVAL '1 day' + (p_new_months || ' months')::INTERVAL
        ) RETURNING id INTO v_new_license_id;
        
    ELSIF p_renewal_option = 'extension' THEN
        INSERT INTO licenses (
            customer_id, parent_license_id,
            seats_purchased, months_purchased,
            actual_price, list_price,
            carried_over_user_months, renewal_option_chosen,
            contract_start, contract_end
        ) VALUES (
            v_old_record.customer_id, p_old_license_id,
            p_new_seats, p_new_months,
            p_new_price, p_new_price,
            v_savings,
            'extension',
            v_old_record.contract_end + INTERVAL '1 day',
            -- 기간 연장 = 기본 기간 + (절약토큰 / 좌석수) 개월
            v_old_record.contract_end + INTERVAL '1 day' 
                + (p_new_months || ' months')::INTERVAL
                + ((v_savings / p_new_seats) || ' months')::INTERVAL
        ) RETURNING id INTO v_new_license_id;
    END IF;
    
    -- 이전 라이선스 만료 처리
    UPDATE licenses 
    SET license_status = 'expired'
    WHERE id = p_old_license_id;
    
    RETURN v_new_license_id;
END;
$$ LANGUAGE plpgsql;
```

---

## 4. 권한 격리 매트릭스

### 4.1 역할 정의 (최종)

| 역할 코드 | 한글명 | role 컬럼 | 추가 식별 |
|---|---|---|---|
| `super_admin` | 본부 임원 | `super_admin` | - |
| `director` | Director (영업총괄) | `hq_staff` | `hq_staff_capabilities = 'director'` |
| `ops_team` | 운영팀 | `hq_staff` | `capabilities = 'ops_review'` |
| `channel_mgr` | 채널 매니저 | `hq_staff` | `capabilities = 'manage_channels'` |
| `direct_cust_mgr` | 직접고객 담당 | `hq_staff` | `capabilities = 'manage_direct_customers'` |
| `related_org_mgr` | 유관기관 담당 | `hq_staff` | `capabilities = 'manage_related_orgs'` |
| `partner_admin` | 파트너 관리자 | `partner_admin` | `partner_id` 보유 |
| `partner_user` | 파트너 사용자 | `partner_user` | `partner_id` 보유 |
| `customer_admin` | 고객 관리자 | `customer_admin` | `customer_id` 보유 |
| `customer_user` | 고객 일반사용자 | `customer_user` | `customer_id` 보유 |

### 4.2 권한 매트릭스

R = 조회, W = 쓰기, A = 승인, '-' = 권한 없음

| 리소스 | 임원 | Director | 운영팀 | 채널매니저 | 직접고객담당 | 유관기관담당 | 파트너관리자 | 파트너사용자 | 고객관리자 | 고객사용자 |
|---|---|---|---|---|---|---|---|---|---|---|
| **partners** | RWA | RW | RW | R(담당) | - | R(담당) | R(자기) | - | - | - |
| **customers** | RWA | RW | RW | R(담당) | RW(담당) | R(매핑) | R(자기영업) | R(자기영업) | R(자기) | - |
| **users** | RWA | RW | RW | R(담당) | R(담당) | R(매핑) | R(자기) | R(자기) | R(자기) | R(자기) |
| **licenses** | RWA | RWA | RW | R(담당) | R(담당) | R(매핑) | R(자기영업) | - | R(자기) | - |
| **contracts** | RWA | RWA | RWA | R(담당) | R(담당) | R(담당) | R(자기) | - | R(자기) | - |
| **approval_workflows** | A(최종) | A(2차) | A(1차) | R(자기제출) | R(자기제출) | R(자기제출) | R(자기제출) | - | - | - |
| **monitoring_data** | RW | R | R | - | - | R(매핑+옵트인) | - | - | RW(자기) | RW(자기) |
| **payment_records** | RWA | RW | RW | R(담당) | R(담당) | R(담당) | RW(자기수금) | - | R(자기납부) | - |

### 4.3 RLS 정책 4가지 빈출 패턴

#### 패턴 1: 본부 직원 (모든 데이터 조회)

```sql
CREATE POLICY "hq_staff_read_all" ON some_table
FOR SELECT TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users u
        WHERE u.email = auth.email()
          AND u.deleted_at IS NULL
          AND u.role IN ('super_admin', 'hq_staff')
    )
);
```

#### 패턴 2: 채널 매니저 / 직접고객담당 / 유관기관담당 (자기 담당만)

```sql
CREATE POLICY "hq_assigned_partner_read" ON customers
FOR SELECT TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM hq_assignments h
        JOIN users u ON u.id = h.manager_user_id
        WHERE u.email = auth.email()
          AND u.deleted_at IS NULL
          AND h.unassigned_at IS NULL
          AND (
              h.assigned_partner_id = customers.sold_by_partner_id
              OR h.assigned_partner_id = customers.parent_distributor_id
              OR h.assigned_customer_id = customers.id
          )
    )
);
```

#### 패턴 3: 파트너 관리자·사용자 (자기 파트너 영역)

```sql
CREATE POLICY "partner_admin_own_customers" ON customers
FOR SELECT TO authenticated
USING (
    customers.sold_by_partner_id IN (
        SELECT u.partner_id FROM users u
        WHERE u.email = auth.email() 
          AND u.deleted_at IS NULL
          AND u.role IN ('partner_admin', 'partner_user')
    )
);

-- 총판은 자기 + 산하 대리점의 고객까지
CREATE POLICY "distributor_includes_resellers" ON customers
FOR SELECT TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users u
        JOIN partners p ON p.id = u.partner_id
        WHERE u.email = auth.email()
          AND u.deleted_at IS NULL
          AND p.is_distributor = true
          AND (
              customers.sold_by_partner_id = p.id
              OR customers.parent_distributor_id = p.id
          )
    )
);
```

#### 패턴 4: 유관기관 (옵트인된 매핑만)

```sql
CREATE POLICY "related_org_opted_in" ON customers
FOR SELECT TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM partner_customer_relations pcr
        JOIN users u ON u.partner_id = pcr.partner_id
        WHERE u.email = auth.email()
          AND u.deleted_at IS NULL
          AND pcr.customer_id = customers.id
          AND pcr.relationship_type IN (
              'related_org_assigned_by_customer', 
              'related_org_assigned_by_user'
          )
          AND pcr.revoked_at IS NULL
    )
);
```

### 4.4 권한 검증 헬퍼 함수

앱 코드에서 자주 쓸 검증 함수들:

```sql
-- 사용자가 본부 직원인지
CREATE OR REPLACE FUNCTION is_hq_staff(p_email TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM users 
        WHERE email = p_email 
          AND deleted_at IS NULL
          AND role IN ('super_admin', 'hq_staff')
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- 본부 직원이 특정 capability 보유 중인지
CREATE OR REPLACE FUNCTION has_capability(p_email TEXT, p_capability TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM users u
        JOIN hq_staff_capabilities cap ON cap.user_id = u.id
        WHERE u.email = p_email
          AND u.deleted_at IS NULL
          AND cap.capability = p_capability
          AND cap.revoked_at IS NULL
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- 사용자가 특정 파트너의 데이터에 접근 가능한지
CREATE OR REPLACE FUNCTION can_access_partner(p_email TEXT, p_partner_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN (
        is_hq_staff(p_email)
        OR EXISTS (
            SELECT 1 FROM users WHERE email = p_email AND partner_id = p_partner_id
        )
        OR EXISTS (
            SELECT 1 FROM hq_assignments h
            JOIN users u ON u.id = h.manager_user_id
            WHERE u.email = p_email AND h.assigned_partner_id = p_partner_id
                  AND h.unassigned_at IS NULL
        )
    );
END;
$$ LANGUAGE plpgsql STABLE;
```

---

## 5. 마이그레이션 단계

### 5.1 무중단 5단계 전략

```
Phase 0: 백업 + 준비          (오늘 — 5/10)
Phase 1: 신규 테이블 생성     (Day 1)
Phase 2: 데이터 복사          (Day 2)
Phase 3: 코드 듀얼 리드       (Day 3-7)
Phase 4: 코드 단일 라이트     (Day 8-14)
Phase 5: 레거시 컬럼 삭제     (Day 15+)
```

### 5.2 Phase 0: 백업

```sql
-- ═══════════════════════════════════════════════════════════
-- Phase 0: 백업 (Supabase SQL Editor)
-- ═══════════════════════════════════════════════════════════

-- 1) Supabase 자동 백업 확인 (Dashboard에서)

-- 2) 수동 SQL 백업 스키마 생성
CREATE SCHEMA IF NOT EXISTS backup_20260510;

-- 3) 영향 받는 모든 테이블 백업
CREATE TABLE backup_20260510.agencies AS SELECT * FROM public.agencies;
CREATE TABLE backup_20260510.users AS SELECT * FROM public.users;
CREATE TABLE backup_20260510.user_documents AS SELECT * FROM public.user_documents;
-- (필요 시 추가)

-- 4) 백업 스키마 권한 잠금 (보안)
REVOKE ALL ON SCHEMA backup_20260510 FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA backup_20260510 FROM PUBLIC;
-- 본부 임원만 접근 가능하게 별도 정책 적용 (Privacy 문서 참조)

-- 5) 백업 검증
SELECT 
    'agencies' AS tbl, COUNT(*) AS cnt FROM backup_20260510.agencies
UNION ALL
SELECT 'users', COUNT(*) FROM backup_20260510.users;
```

### 5.3 Phase 1: 신규 테이블 생성

```sql
BEGIN;

-- 섹션 2의 모든 CREATE TABLE 실행
-- (partners, customers, partner_customer_relations, hq_assignments, ...)

-- users 테이블 확장
ALTER TABLE public.users 
    ADD COLUMN IF NOT EXISTS partner_id UUID REFERENCES public.partners(id),
    ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES public.customers(id),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 동일 트리거를 partners, customers에도 적용
CREATE TRIGGER update_partners_updated_at 
    BEFORE UPDATE ON public.partners
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at 
    BEFORE UPDATE ON public.customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 검증
SELECT 
    table_name, 
    COUNT(*) AS column_count 
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name IN ('partners', 'customers', 'licenses', 'hq_assignments')
GROUP BY table_name;

COMMIT;
```

### 5.4 Phase 2: agencies → partners 데이터 복사

```sql
BEGIN;

-- 1) agencies 데이터를 partners로 복사
INSERT INTO public.partners (
    id, name, business_number, representative_name, 
    address, phone, email,
    is_distributor, is_reseller, is_related_org,
    business_channel,
    has_sales_contract,
    legacy_agency_id,
    created_at
)
SELECT 
    gen_random_uuid(),
    a.name,
    a.business_number,
    a.representative_name,
    a.address,
    a.phone,
    a.email,
    -- 기존 agencies는 일단 모두 직접계약 대리점으로
    false,                          -- is_distributor
    true,                           -- is_reseller
    false,                          -- is_related_org
    'reseller_direct',              -- 나중에 수동 분류
    true,                           -- has_sales_contract
    a.id,                           -- legacy_agency_id (롤백 추적)
    a.created_at
FROM public.agencies a
WHERE a.deleted_at IS NULL;

-- 2) users.partner_id 채우기
UPDATE public.users u
SET partner_id = p.id
FROM public.partners p
WHERE p.legacy_agency_id = u.agency_id
  AND u.partner_id IS NULL;

-- 3) 검증: 복사 누락 확인
SELECT 
    'agencies (active)' AS source, 
    COUNT(*) AS cnt 
FROM agencies WHERE deleted_at IS NULL
UNION ALL
SELECT 
    'partners (from legacy)', 
    COUNT(*) 
FROM partners WHERE legacy_agency_id IS NOT NULL;

-- 4) users.partner_id 채워진 비율 확인
SELECT 
    COUNT(*) FILTER (WHERE partner_id IS NOT NULL) AS migrated,
    COUNT(*) FILTER (WHERE agency_id IS NOT NULL) AS had_agency,
    COUNT(*) AS total
FROM users WHERE deleted_at IS NULL;

COMMIT;
```

### 5.5 Phase 3: 코드 듀얼 리드

```python
# app.py 헬퍼 함수 추가
def get_partner_id_for_user(user_email: str) -> Optional[UUID]:
    """
    Phase 3 듀얼 리드: partner_id 우선, 없으면 agency_id로 fallback.
    Phase 4부터는 partner_id만 사용하므로 이 함수 제거.
    """
    user = supabase.table("users") \
        .select("partner_id, agency_id") \
        .eq("email", user_email) \
        .single() \
        .execute()
    
    if not user.data:
        return None
    
    # 우선 partner_id 사용
    if user.data.get("partner_id"):
        return user.data["partner_id"]
    
    # Fallback: agency_id로 partner 찾기
    if user.data.get("agency_id"):
        partner = supabase.table("partners") \
            .select("id") \
            .eq("legacy_agency_id", user.data["agency_id"]) \
            .single() \
            .execute()
        return partner.data["id"] if partner.data else None
    
    return None
```

### 5.6 Phase 4: 단일 라이트

```python
# app.py — 모든 신규 코드는 partner_id만 사용
# grep 'agency_id' 후 모두 변경 확인

# 변경 대상:
# - 모든 INSERT/UPDATE 쿼리
# - 모든 함수 시그니처
# - 모든 RLS 정책 (Phase 1에서 이미 완료)
```

### 5.7 Phase 5: 레거시 컬럼 삭제

```sql
-- 1) 의존성 확인
SELECT 
    tc.table_name, tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE kcu.column_name = 'agency_id' 
  AND tc.table_schema = 'public';

-- 2) 모든 레거시 코드 제거 확인 (grep agency_id)

-- 3) 컬럼 삭제
BEGIN;

ALTER TABLE public.users DROP COLUMN IF EXISTS agency_id;

-- agencies 테이블도 폐기 (백업은 backup_20260510에 보존)
DROP TABLE IF EXISTS public.agencies CASCADE;

COMMIT;
```

### 5.8 마이그레이션 위험 매트릭스

| 단계 | 위험 | 영향도 | 완화 방법 |
|---|---|---|---|
| Phase 1 | 테이블 충돌 | 중 | `IF NOT EXISTS`, 트랜잭션 |
| Phase 2 | 데이터 누락 | 큼 | COUNT 비교, legacy_agency_id 추적 |
| Phase 2 | 트리거 미동작 | 중 | parent_distributor_id 자동 채움 트리거 검증 |
| Phase 3 | 듀얼 리드 버그 | 큼 | 헬퍼 함수 추상화, 단위 테스트 |
| Phase 4 | grep 누락 | 큼 | `git grep agency_id` 결과 0건 확인 |
| Phase 5 | 외래키 의존 | 매우 큼 | DROP 전 의존성 확인 SQL 실행 |

### 5.9 롤백 계획

각 Phase별 롤백 절차:

```sql
-- Phase 1 롤백: 신규 테이블 삭제
BEGIN;
DROP TABLE IF EXISTS public.user_license_periods CASCADE;
DROP TABLE IF EXISTS public.licenses CASCADE;
DROP TABLE IF EXISTS public.approval_steps CASCADE;
-- (나머지 신규 테이블)
ALTER TABLE public.users DROP COLUMN IF EXISTS partner_id;
ALTER TABLE public.users DROP COLUMN IF EXISTS customer_id;
ROLLBACK; -- 또는 COMMIT (실제 적용)

-- Phase 2 롤백: 데이터만 제거 (구조는 유지)
DELETE FROM partners WHERE legacy_agency_id IS NOT NULL;
UPDATE users SET partner_id = NULL WHERE partner_id IS NOT NULL;

-- Phase 5 롤백: agencies 복원
CREATE TABLE public.agencies AS 
    SELECT * FROM backup_20260510.agencies;
ALTER TABLE public.users ADD COLUMN agency_id UUID REFERENCES agencies(id);
UPDATE users u SET agency_id = p.legacy_agency_id 
    FROM partners p WHERE u.partner_id = p.id;
```

---

## 6. UI / Workspace 모델

### 6.1 Workspace 패턴 도입 이유

기존 SaaS의 함정: "권한 격리는 됐는데 UX는 모두가 같은 시스템을 보는 것처럼" 보임.

이로 인해:
- 1번 총판 대리점이 다른 총판 대리점 흔적을 보면 심리적 부담
- "내 일"이라는 소속감 부족
- 영업 자유도 저하

**Workspace 모델의 효과**: 마치 자기만 위한 시스템처럼 느끼게 만들어 직관적·자율적 업무 처리 가능.

### 6.2 URL 구조

```
[기존]
/partners
/customers
/licenses

[신규 — Workspace 기반]
/w/{workspace_id}/dashboard           # 내 워크스페이스 홈
/w/{workspace_id}/customers           # 내 워크스페이스의 고객만
/w/{workspace_id}/licenses            # 내 워크스페이스의 라이선스만
/w/{workspace_id}/reports/sales       # 내 워크스페이스 영업보고
```

URL에 `workspace_id`가 박혀있으면 **다른 워크스페이스로의 우발적 접근이 원천 차단**됩니다.

### 6.3 workspace_memberships 테이블

```sql
CREATE TABLE public.workspace_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) NOT NULL,
    
    -- 워크스페이스 (둘 중 하나)
    partner_id UUID REFERENCES public.partners(id),
    customer_id UUID REFERENCES public.customers(id),
    
    -- 워크스페이스 내 역할
    role_in_workspace TEXT NOT NULL,
    -- 'admin' | 'manager' | 'member' | 'viewer'
    
    -- 기본 워크스페이스 (로그인 시 첫 화면)
    is_default BOOLEAN DEFAULT false,
    
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    left_at TIMESTAMPTZ,
    
    CONSTRAINT exactly_one_workspace CHECK (
        (partner_id IS NOT NULL)::int + (customer_id IS NOT NULL)::int = 1
    ),
    UNIQUE (user_id, partner_id, customer_id)
);

-- 한 사용자에 기본 워크스페이스는 단 1개
CREATE UNIQUE INDEX one_default_per_user 
    ON workspace_memberships(user_id) 
    WHERE is_default = true AND left_at IS NULL;
```

### 6.4 Workspace Resolver

```python
def resolve_user_workspaces(user_id: UUID) -> List[Workspace]:
    """
    로그인 시 사용자가 속한 모든 워크스페이스 결정.
    """
    user = get_user(user_id)
    workspaces = []
    
    # 1) 본부 직원
    if user.role in ('super_admin', 'hq_staff'):
        workspaces.append(Workspace(
            type='hq',
            id='hq',
            name='DragonEyes 본부',
            icon='🏢',
            home_page='hq_dashboard'
        ))
    
    # 2) 파트너 멤버십
    memberships = supabase.table("workspace_memberships") \
        .select("*, partners(*)") \
        .eq("user_id", user_id) \
        .is_("left_at", "null") \
        .execute()
    
    for m in memberships.data:
        if m['partner_id']:
            partner = m['partners']
            ws_type = (
                'distributor' if partner['is_distributor'] else
                'reseller' if partner['is_reseller'] else
                'related_org'
            )
            workspaces.append(Workspace(
                type=ws_type,
                id=partner['id'],
                name=partner['name'],
                icon='🏛️' if partner['is_distributor'] else 
                     '🏪' if partner['is_reseller'] else '🏥',
                home_page=f'{ws_type}_dashboard',
                is_default=m['is_default']
            ))
        elif m['customer_id']:
            workspaces.append(Workspace(
                type='customer',
                id=m['customer_id'],
                name=m['customers']['name'],
                icon='🏢',
                home_page='customer_dashboard',
                is_default=m['is_default']
            ))
    
    return workspaces
```

### 6.5 사이드바 디자인 원칙

```
┌─────────────────────────────────┐
│ 🔄 [위드루트 (대리점)] ▾        │  ← 워크스페이스 스위처 (드롭다운)
│ 소속: 1번 총판                   │  ← 부모 컨텍스트 표시
│ ─────────────────────────       │
│ 📊 대시보드                      │
│ 👥 내 고객 (12)                  │  ← "내" 강조 + 카운트 배지
│ 📄 내 라이선스 (8)               │
│ 💬 내 영업보고                   │
│ 📁 내 문서함                     │
│ ❓ 도움 요청 (→ 1번 총판/본부)    │  ← 부모에게만 가는 1:1 채널
│ ─────────────────────────       │
│ ⚙️ 설정                          │
└─────────────────────────────────┘
```

핵심 UX 원칙:

| 원칙 | 적용 |
|---|---|
| 언어 톤 | "전체 고객" → "내 고객" |
| 즉시 가시성 | 카운트 배지 ("내 고객 (12)") |
| 부모 컨텍스트 | 대리점 화면에 "소속: 1번 총판" 항상 표시 |
| 도움 요청 채널 | 자기 부모(총판/본부)에게만 가는 1:1 |
| 대시보드 = 자기 KPI | 영업 목표 달성률, 갱신 임박 등만 |

### 6.6 페이지별 역할 분기 (의사코드)

```python
def render_partners_page():
    role = get_user_role()
    workspace = get_current_workspace()
    
    if role == 'super_admin' or has_capability('hq_admin'):
        # 본부 → 전체 partners 테이블
        render_full_partner_table()
        render_create_partner_button()
        
    elif has_capability('manage_channels'):
        # 채널 매니저 → 자기가 배정된 총판/대리점만
        partners = get_assigned_partners(user_id, type=['distributor', 'reseller'])
        render_partner_cards(partners)
        
    elif has_capability('manage_related_orgs'):
        # 유관기관 담당 → 자기가 배정된 유관기관만
        partners = get_assigned_partners(user_id, type=['related_org'])
        render_partner_cards(partners)
        
    elif role == 'partner_admin':
        # 파트너 관리자 → 자기 파트너 정보만
        my_partner = get_partner(workspace.id)
        render_partner_detail(my_partner)
        
        # 총판인 경우 산하 대리점도
        if my_partner.is_distributor:
            render_child_resellers(my_partner.id)
    
    else:
        st.error("권한이 없습니다")
```

### 6.7 신규 메뉴 구조

```
[ 기존 메뉴 ]              [ 신규 메뉴 (Workspace 기반) ]
─────────────────         ────────────────────────────
🏠 홈                       🏠 홈
📊 위탁대시보드      →       👥 Partners (역할별 분기)
👤 사용자 관리              📋 Customers
📑 보고서                   📄 Licenses
⚙️ 설정                     📊 모니터링
                           📁 문서 관리 (계약서)
                           ✅ 승인 (결재 워크플로우)
                           👤 사용자 관리
                           📑 보고서
                           ⚙️ 설정
                           🔒 개인정보 보호조치 (본부 임원/Director/운영팀만)
```

### 6.8 역할별 메뉴 노출 매트릭스

| 메뉴 | 임원 | Director | 운영팀 | 채널매니저 | 직접고객담당 | 유관기관담당 | 파트너관리자 | 고객관리자 |
|---|---|---|---|---|---|---|---|---|
| 홈 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Partners | ✅ | ✅ | ✅ | ✅(담당) | - | ✅(담당) | ✅(자기) | - |
| Customers | ✅ | ✅ | ✅ | ✅(담당) | ✅(담당) | ✅(매핑) | ✅(자기영업) | ✅(자기) |
| Licenses | ✅ | ✅ | ✅ | ✅ | ✅ | ✅(매핑) | ✅(자기) | ✅(자기) |
| 모니터링 | ✅ | ✅ | ✅ | - | - | ✅(옵트인) | - | ✅ |
| 문서 관리 | ✅ | ✅ | ✅ | ✅(담당) | ✅(담당) | ✅(담당) | ✅(자기) | ✅(자기) |
| 승인 | ✅ | ✅ | ✅ | 제출 | 제출 | 제출 | 제출 | - |
| 사용자 관리 | ✅ | ✅ | ✅ | - | - | - | ✅(자기) | ✅(자기) |
| 보고서 | ✅ | ✅ | ✅ | ✅(범위) | ✅(범위) | ✅(범위) | ✅(자기) | - |
| 설정 | ✅ | ✅ | - | - | - | - | ✅(자기) | ✅(자기) |
| 보호조치 이력 | ✅ | ✅ | ✅ | - | - | - | - | - |

---

## 7. 보안 & 개인정보보호 (요약)

> ⚠️ **상세 내용은 별도 문서 참조**: `DragonEyes_Privacy_Operations_v1.md`
> 
> 이 섹션은 시스템 설계 관점의 보안 요소만 요약합니다. 실제 운영 매뉴얼·체크리스트·SQL 실행 가이드는 별도 문서에 있습니다.

### 7.1 시스템 설계에 박힌 보안 요소

| 영역 | 설계 요소 | 위치 |
|---|---|---|
| 접근 통제 | RLS 정책 (4가지 패턴) | 섹션 4 |
| 권한 격리 | Workspace 모델 (URL 레벨) | 섹션 6 |
| 책임 추적 | 3단 승인 게이트 + audit log | 섹션 1.6 |
| 무결성 | append-only 테이블 (audit, consent) | 별도 문서 |
| 컴플라이언스 | 4-Layer 분리 동의 | 별도 문서 |
| 회수 가능성 | Soft Delete + revoke 메커니즘 | 전체 |

### 7.2 4-Layer 동의 모델 (개요)

| Layer | 동의 종류 | 법적 근거 | 시점 |
|---|---|---|---|
| 1 | 기본 가입 (수집·이용 + 민감정보) | 개인정보보호법 제15조, 제23조 | 회원가입 |
| 2 | 유관기관 매핑 (제3자 제공) | 제17조 | 옵트인 시 |
| 3 | 민감정보 제공 (장애정보) | 제17조 + 제23조 | 서비스 활성화 |
| 4 | 서류 작성 위임 (법률행위) | 민법 제680조 | 위임 시 (전자서명 필수) |

상세 SQL·UI·운영 절차는 `DragonEyes_Privacy_Operations_v1.md` 참조.

### 7.3 개인정보 보호조치 이력 페이지

**페이지명**: 개인정보 보호조치 이력  
**접근 권한**: 본부 임원 + Director + 운영팀  
**핵심 기능**:
- 날짜별 보호조치 카드 뷰
- 카테고리·태그 검색
- 법적 근거 자동 매핑
- 증거 (commit hash, SQL log) 자동 연결
- append-only (수정·삭제 불가)
- 자동 등록 + 수동 보강 하이브리드

**관련 테이블**: `privacy_protection_activities` (Privacy 문서 섹션 3 참조)

### 7.4 비즈니스 확장 대비 — 서류 작성 대행

향후 비즈니스 확장 방향: 유관기관이 장애인 관련 서류를 사용자 대신 작성·제출.

이 비즈니스에 필요한 추가 인프라:
- 전자서명 시스템 (KISA 인증)
- 위임장 PDF 생성·해시 보관
- 본인 검토 단계 (in-app/email/SMS)
- 공공기관 제출 추적

상세 설계는 Privacy 문서 섹션 4 (Layer 4) 및 Phase 2 백로그 참조.

---

## 부록 A: 전체 SQL 스키마

이 부록은 Phase 1에서 실행할 모든 CREATE 문을 한 곳에 모은 것입니다. 실제 실행 시 BEGIN/COMMIT으로 감싸세요.

### A.1 의존성 순서

```
1. partners (자기 참조 FK 있음)
2. customers (partners FK)
3. partner_customer_relations (둘 다 FK)
4. contracts (둘 다 FK)
5. licenses (customers, contracts FK)
6. user_license_periods (licenses, users FK)
7. hq_assignments (users, partners, customers FK)
8. hq_staff_capabilities (users FK)
9. workspace_memberships (users, partners, customers FK)
10. approval_workflows + approval_steps + approval_audit_log
11. approval_policies
12. payment_records
```

### A.2 모든 CREATE 문 (참조용)

> 위 섹션 2~6에서 정의한 모든 테이블의 SQL은 이미 본문에 포함되어 있습니다. 실제 마이그레이션 시:
> 
> 1. 섹션 2.2 ~ 2.7의 CREATE TABLE을 순서대로 실행
> 2. 섹션 3.3 ~ 3.4의 licenses, user_license_periods CREATE 실행
> 3. 섹션 6.3의 workspace_memberships CREATE 실행
> 4. 아래 추가 테이블 (approval, payment) 실행

### A.3 approval_workflows + approval_steps

```sql
CREATE TABLE public.approval_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    target_type TEXT NOT NULL,
    -- 'license_issuance' | 'contract_registration'
    -- | 'partner_onboarding' | 'license_modification'
    -- | 'token_settlement' | 'refund'
    target_id UUID NOT NULL,
    
    -- 요청자
    requested_by_user_id UUID REFERENCES public.users(id),
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    request_reason TEXT,
    
    -- 최종 상태
    final_status TEXT DEFAULT 'pending',
    -- 'pending' | 'approved' | 'rejected' | 'cancelled'
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
    -- 'pending' | 'approved' | 'rejected' | 'needs_info'
    reviewed_at TIMESTAMPTZ,
    notes TEXT,
    
    activated_at TIMESTAMPTZ,
    
    UNIQUE (workflow_id, step_order)
);

CREATE INDEX idx_approval_steps_workflow ON public.approval_steps(workflow_id);
CREATE INDEX idx_approval_steps_pending ON public.approval_steps(step_role, status) 
    WHERE status = 'pending';
```

### A.4 approval_audit_log

```sql
CREATE TABLE public.approval_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id UUID REFERENCES public.approval_steps(id),
    user_id UUID REFERENCES public.users(id),
    user_email TEXT,  -- 사용자 삭제되어도 보존
    
    action TEXT NOT NULL,
    -- 'viewed' | 'commented' | 'approved' | 'rejected' | 'requested_info'
    
    snapshot JSONB,  -- 결재 시점 데이터 스냅샷
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- append-only
REVOKE UPDATE, DELETE ON public.approval_audit_log FROM PUBLIC;
REVOKE UPDATE, DELETE ON public.approval_audit_log FROM authenticated;

CREATE INDEX idx_approval_audit_step ON public.approval_audit_log(step_id);
CREATE INDEX idx_approval_audit_user ON public.approval_audit_log(user_id);
```

### A.5 approval_policies

```sql
CREATE TABLE public.approval_policies (
    target_type TEXT PRIMARY KEY,
    required_steps TEXT[] NOT NULL,
    -- 예: ['ops_review', 'director_approval', 'executive_approval']
    
    auto_approve_threshold NUMERIC,
    -- 예: 1000000 (백만원 이하면 auto-approve)
    
    description TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 초기 정책 삽입
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
```

### A.6 payment_records

```sql
CREATE TABLE public.payment_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_id UUID REFERENCES public.licenses(id),
    
    -- 결제 흐름
    payment_stage TEXT NOT NULL,
    -- 'customer_to_partner' : 고객이 파트너에게 1차 입금
    -- 'reseller_to_distributor' : 대리점이 총판에게 송금
    -- 'partner_to_hq' : 파트너가 본부에 최종 송금
    
    from_entity_type TEXT NOT NULL,  -- 'customer' | 'partner' | 'hq'
    from_entity_id UUID NOT NULL,
    to_entity_type TEXT NOT NULL,
    to_entity_id UUID NOT NULL,
    
    amount NUMERIC NOT NULL,
    currency TEXT DEFAULT 'KRW',
    
    paid_at TIMESTAMPTZ NOT NULL,
    payment_method TEXT,  -- 'bank_transfer' | 'card' | 'other'
    payment_reference TEXT,  -- 송금 확인번호
    
    -- 증빙
    receipt_url TEXT,
    
    notes TEXT,
    created_by_user_id UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_license ON public.payment_records(license_id);
CREATE INDEX idx_payments_paid_at ON public.payment_records(paid_at);
```

### A.7 자동 트리거: customers.parent_distributor_id 자동 채움

```sql
CREATE OR REPLACE FUNCTION fill_parent_distributor() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.sold_by_partner_id IS NOT NULL THEN
        SELECT parent_partner_id INTO NEW.parent_distributor_id
        FROM partners 
        WHERE id = NEW.sold_by_partner_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_fill_parent_distributor
    BEFORE INSERT OR UPDATE OF sold_by_partner_id ON public.customers
    FOR EACH ROW EXECUTE FUNCTION fill_parent_distributor();
```

### A.8 자동 트리거: 워크스페이스 자동 생성

사용자가 partner_id 또는 customer_id를 받으면 자동으로 workspace_memberships에 추가:

```sql
CREATE OR REPLACE FUNCTION auto_create_workspace_membership() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.partner_id IS NOT NULL AND 
       (OLD IS NULL OR OLD.partner_id IS DISTINCT FROM NEW.partner_id) THEN
        INSERT INTO workspace_memberships (
            user_id, partner_id, role_in_workspace, is_default
        ) VALUES (
            NEW.id, NEW.partner_id, 
            CASE NEW.role 
                WHEN 'partner_admin' THEN 'admin'
                ELSE 'member'
            END,
            true
        ) ON CONFLICT DO NOTHING;
    END IF;
    
    IF NEW.customer_id IS NOT NULL AND 
       (OLD IS NULL OR OLD.customer_id IS DISTINCT FROM NEW.customer_id) THEN
        INSERT INTO workspace_memberships (
            user_id, customer_id, role_in_workspace, is_default
        ) VALUES (
            NEW.id, NEW.customer_id,
            CASE NEW.role
                WHEN 'customer_admin' THEN 'admin'
                ELSE 'member'
            END,
            true
        ) ON CONFLICT DO NOTHING;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_workspace_on_user_change
    AFTER INSERT OR UPDATE OF partner_id, customer_id ON public.users
    FOR EACH ROW EXECUTE FUNCTION auto_create_workspace_membership();
```

---

## 부록 B: 미해결 항목 + Phase 2 백로그

### B.1 오늘 결정된 사항

| # | 결정 | 근거 |
|---|---|---|
| 1 | partners ≠ customers, 별도 테이블 | RLS 격리 단순화 |
| 2 | partners는 3가지 계약 트랙 토글 | 유관기관 다중역할 |
| 3 | 본부 7가지 역할 | 책임 분산 |
| 4 | 단일 hq_assignments 테이블 | 한 직원 다중 담당 |
| 5 | 3단 승인 게이트 | 책임 매트릭스 |
| 6 | approval_steps 동적 단계 | 영업총괄 추가 시 무중단 확장 |
| 7 | 토큰 = 월할 계산 + 현재형 소비 | 단순·표준 |
| 8 | 갱신 시 고객이 옵션 A/B 선택 | UX 우선 |
| 9 | 좌석 추가 자유 + 종료일 맞춤 | 일관 관리 |
| 10 | partners ↔ customers는 N:M | 유관기관 다중 고객 관리 |
| 11 | 유관기관 매핑은 옵트인 (사용자 자발) | 개인정보보호법 제17조 |
| 12 | Workspace 모델 (URL `/w/{id}/...`) | 직관적 업무 처리 |
| 13 | ordered_to = paid_to (1차 수금자) | 자금 흐름 단순화 |
| 14 | 모든 본부 라이선스 = 계약서 첨부 필수 | 투명성 |

### B.2 Phase 2 백로그 (시스템 확장)

| # | 항목 | 우선순위 | 비고 |
|---|---|---|---|
| 1 | 서류 작성 대행 시스템 (Layer 4 동의) | P1 | 비즈니스 확장 |
| 2 | 전자서명 (KISA 인증) | P1 | Layer 4 prerequisites |
| 3 | 공공기관 API 연동 | P2 | 서류 자동 제출 |
| 4 | 영업총괄 추가 (조직 확장 시) | P2 | approval_steps row 추가 |
| 5 | 자동 갱신 알림 (라이선스 종료 30일 전) | P1 | UX |
| 6 | 토큰 정산 보고서 자동 생성 | P1 | 회계 |
| 7 | 파트너별 매출 대시보드 | P2 | 영업 분석 |
| 8 | 모바일 반응형 개선 | P2 | UX |

### B.3 Phase 2 백로그 (보안)

> 보안 엔지니어 합류 후 우선 다룰 항목들. 상세는 `DragonEyes_Privacy_Operations_v1.md` 참조.

| # | 항목 | 우선순위 |
|---|---|---|
| S1 | pgcrypto 활성화 + 민감 컬럼 암호화 | P1 |
| S2 | 키 관리 시스템 (KMS) 도입 | P1 |
| S3 | 비정상 접근 탐지 시스템 | P2 |
| S4 | 보안 감사 외부 의뢰 | P0 (출시 전) |
| S5 | 개인정보 영향평가 (PIA) | P0 (출시 전) |
| S6 | 침투 테스트 | P2 |
| S7 | ISO 27001 인증 검토 | P3 |

### B.4 즉시 조치 P0 (오늘/이번주)

| # | 항목 | 소요 시간 | 담당 |
|---|---|---|---|
| 1 | service_role 키 코드 노출 점검 | 10분 | 최승현 |
| 2 | 백업 스키마 권한 잠금 | 5분 | 최승현 |
| 3 | Supabase MFA 활성화 (super_admin) | 20분 | 최승현 |
| 4 | 세션 타임아웃 코드 추가 | 30분 | 최승현 |
| 5 | 보호조치 이력 페이지 신규 | 2시간 | 다음주 |

### B.5 의존성 그래프

```
다음주 작업 의존성:
─────────────────────────────────────────
[1] Phase 0 (백업)
        ↓
[2] Phase 1 (테이블 생성)
        ↓
[3] Phase 2 (데이터 복사)
        ├── [3a] customers 데이터 (수동)
        └── [3b] contracts 데이터 (수동, 위드루트 등)
        ↓
[4] UI 명칭 변경 (위탁대시보드 → Partners)
        ↓
[5] Phase 3 (코드 듀얼 리드)
        ↓
[6] Workspace UI 도입
        ↓
[7] Phase 4 (단일 라이트)
        ↓
[8] Phase 5 (레거시 컬럼 삭제)
```

### B.6 의사결정 보류 항목

다음주 추가 결정 필요:

| 항목 | 결정 시점 | 영향 범위 |
|---|---|---|
| 결재 정책 자동 라우팅 임계값 (대형/소형 기준) | 다음주 | approval_policies |
| 라이선스 갱신 알림 기간 (30/60/90일) | 다음주 | UX |
| 파트너 등급 시스템 (Gold/Silver) | Phase 2 | partners 테이블 |
| 다국어 지원 (영어) | Phase 2 | 전체 UI |

---

## 변경 이력

| 버전 | 날짜 | 변경자 | 주요 내용 |
|---|---|---|---|
| v2.0 | 2026-05-10 | 최승현 | 최초 작성 (Direct/Indirect, 토큰, Workspace, 3단 승인, 4-Layer 동의) |

---

**문서 끝**
