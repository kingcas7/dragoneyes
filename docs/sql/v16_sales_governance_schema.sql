-- ============================================================
-- DragonEyes 영업 거버넌스 v1.6 — 스키마 스냅샷
-- ============================================================
-- 추출일   : 2026-05-17
-- 출처     : 운영 Supabase (project xtqgxtdflemuphkzmzti, PostgreSQL 17.6)
-- 추출도구 : pg_dump 18.4 --schema-only --no-owner --no-privileges
--
-- ⚠️ 이 파일은 손으로 작성한 마이그레이션이 아니라, 운영 DB에서 역추출한
--    스키마 스냅샷입니다. v1.6 영업 거버넌스 작업(5/16~17)의 원본 마이그레이션
--    SQL이 보존되지 않아, 사후에 DB에서 복원해 git에 보존합니다.
--
-- 포함 객체:
--   테이블 8 : opportunities, opportunity_activities, opportunity_approval_log,
--              opportunity_change_log, opportunity_contacts,
--              opportunity_engagements, opportunity_status_log, approval_requests
--   뷰 1     : v_pending_approvals
--   + 인덱스 / 제약(PK·FK 30) / RLS 정책 / 트리거
--   + 트리거·정책용 함수 5 (아래 별도 섹션)
--
-- 주의:
--   - 함수/FK가 외부 테이블(users, partners, customers, licenses, contracts)을
--     참조합니다. 빈 DB에 재현 시 해당 테이블이 먼저 존재해야 합니다.
--   - psql 전용 \restrict / \unrestrict 지시문은 제거했습니다.
-- ============================================================


-- ════════════════════════════════════════════════════════════
-- [1] 트리거 / RLS 정책용 함수
-- ════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION public.auto_engage_parent_distributor()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_distributor_id UUID;
    v_partner_name TEXT;
BEGIN
    -- PRIMARY 또는 COLLAB만 캐스케이드 대상 (CASCADED 자신은 제외)
    IF NEW.engagement_type = 'CASCADED' THEN
        RETURN NEW;
    END IF;
    
    -- 새로 인게이지된 파트너가 IND-P인지 확인 (distributor_partners에 매핑 존재)
    SELECT dp.distributor_id, p.name 
    INTO v_distributor_id, v_partner_name
    FROM partners p
    LEFT JOIN distributor_partners dp ON dp.partner_id = p.id 
        AND dp.relationship_type = 'primary'
        AND dp.ended_at IS NULL
    WHERE p.id = NEW.partner_id;
    
    -- 상위 DIST가 있으면 매핑하는 distributor를 찾아서 자동 인게이지
    IF v_distributor_id IS NOT NULL THEN
        -- distributor에 매핑된 partners.id를 찾음 (총판도 partners 테이블에 한 행 가짐)
        INSERT INTO opportunity_engagements (
            opportunity_id, 
            partner_id, 
            engagement_type, 
            engaged_by, 
            reason
        )
        SELECT 
            NEW.opportunity_id,
            p.id,
            'CASCADED',
            NEW.engaged_by,
            '자동 캐스케이드: ' || v_partner_name || ' 인게이지에 따른 상위 총판 자동 추가'
        FROM partners p
        WHERE p.channel_type = 'DIST'
          AND EXISTS (
              SELECT 1 FROM distributors d 
              WHERE d.id = v_distributor_id 
                AND d.name = p.name  -- 또는 별도 매핑 컬럼 사용
          )
        ON CONFLICT DO NOTHING;
    END IF;
    
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.is_hq_user(p_user_id uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
AS $function$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM users
        WHERE id = p_user_id
          AND hq_position IS NOT NULL
          AND deleted_at IS NULL
    );
END;
$function$
;

CREATE OR REPLACE FUNCTION public.log_engagement_change()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO opportunity_change_log (
            opportunity_id, change_type, changed_by, 
            new_value, reason
        )
        VALUES (
            NEW.opportunity_id, 
            'partner_engaged', 
            NEW.engaged_by, 
            to_jsonb(NEW), 
            COALESCE(NEW.reason, '사유 미기재')
        );
    ELSIF TG_OP = 'UPDATE' AND OLD.unengaged_at IS NULL AND NEW.unengaged_at IS NOT NULL THEN
        INSERT INTO opportunity_change_log (
            opportunity_id, change_type, changed_by, 
            old_value, new_value, reason
        )
        VALUES (
            NEW.opportunity_id, 
            'partner_unengaged', 
            NEW.unengaged_by, 
            to_jsonb(OLD), 
            to_jsonb(NEW), 
            COALESCE(NEW.unengaged_reason, '해제 사유 미기재')
        );
    END IF;
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.log_opportunity_status_change()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO opportunity_change_log (
            opportunity_id, change_type, changed_by, 
            old_value, new_value, reason
        )
        VALUES (
            NEW.id,
            CASE 
                WHEN NEW.status = 'closed_won' THEN 'closed_won'
                WHEN NEW.status = 'closed_lost' THEN 'closed_lost'
                ELSE 'status_changed'
            END,
            auth.uid(),
            jsonb_build_object('status', OLD.status),
            jsonb_build_object('status', NEW.status),
            '상태 변경: ' || OLD.status || ' → ' || NEW.status
        );
    END IF;
    
    IF OLD.expected_amount IS DISTINCT FROM NEW.expected_amount THEN
        INSERT INTO opportunity_change_log (
            opportunity_id, change_type, changed_by,
            old_value, new_value, reason
        )
        VALUES (
            NEW.id,
            'amount_changed',
            auth.uid(),
            jsonb_build_object('amount', OLD.expected_amount),
            jsonb_build_object('amount', NEW.expected_amount),
            '예상 금액 변경'
        );
    END IF;
    
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;


-- ════════════════════════════════════════════════════════════
-- [2] 테이블 / 뷰 / 인덱스 / 제약 / 정책 (pg_dump 출력)
-- ════════════════════════════════════════════════════════════

--
-- PostgreSQL database dump
--


-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: approval_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.approval_requests (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    request_type text NOT NULL,
    requested_by uuid NOT NULL,
    related_partner_id uuid,
    related_customer_id uuid,
    related_license_id uuid,
    related_contract_id uuid,
    request_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    attached_document_url text,
    request_status text DEFAULT 'pending'::text,
    final_decision_at timestamp with time zone,
    final_decision_by uuid,
    final_decision_notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: opportunities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.opportunities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_name text NOT NULL,
    customer_business_reg text,
    customer_contact_name text,
    customer_contact_email text,
    customer_contact_phone text,
    origin_channel text NOT NULL,
    primary_owner text DEFAULT 'HQ'::text NOT NULL,
    expected_amount numeric(15,2),
    expected_close_date date,
    license_tier text,
    expected_seats integer,
    status text DEFAULT 'prospect'::text NOT NULL,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    closed_at timestamp with time zone,
    notes text,
    win_probability numeric(5,2) DEFAULT 0,
    assigned_sales_user_id uuid,
    customer_address text,
    customer_ceo_name text,
    customer_business_no text,
    customer_contact_title text,
    customer_fax text,
    business_field text,
    approval_status text DEFAULT 'pending'::text,
    approval_required boolean DEFAULT true,
    approved_by uuid,
    approved_by_name text,
    approved_at timestamp with time zone,
    approval_notes text,
    rejected_at timestamp with time zone,
    rejection_reason text,
    escalation_level integer DEFAULT 0,
    escalated_to uuid,
    escalated_to_name text,
    escalated_at timestamp with time zone,
    escalation_reason text,
    is_duplicate boolean DEFAULT false,
    duplicate_of uuid,
    duplicate_check_at timestamp with time zone,
    status_changed_at timestamp with time zone,
    status_changed_by uuid,
    status_changed_by_name text,
    assigned_partner_id uuid,
    assigning_distributor_id uuid,
    request_type text DEFAULT 'new'::text,
    CONSTRAINT chk_opp_amount CHECK (((expected_amount IS NULL) OR (expected_amount >= (0)::numeric))),
    CONSTRAINT chk_opp_origin CHECK ((origin_channel = ANY (ARRAY['드래곤아이즈다이렉트'::text, '총판'::text, '인다이렉트파트너'::text, '직접계약파트너'::text]))),
    CONSTRAINT chk_opp_owner CHECK ((primary_owner = ANY (ARRAY['HQ'::text, 'PARTNER'::text]))),
    CONSTRAINT chk_opp_seats CHECK (((expected_seats IS NULL) OR (expected_seats > 0))),
    CONSTRAINT chk_opp_status CHECK ((status = ANY (ARRAY['prospect'::text, 'qualified'::text, 'proposal'::text, 'negotiation'::text, 'contract'::text, 'closed_won'::text, 'closed_lost'::text]))),
    CONSTRAINT chk_opp_tier CHECK (((license_tier IS NULL) OR (license_tier = ANY (ARRAY['Standard'::text, 'Pro'::text, 'Enterprise'::text])))),
    CONSTRAINT chk_opp_win_prob CHECK (((win_probability >= (0)::numeric) AND (win_probability <= (100)::numeric))),
    CONSTRAINT opportunities_approval_status_check CHECK ((approval_status = ANY (ARRAY['auto_approved'::text, 'pending'::text, 'approved'::text, 'rejected'::text, 'escalated'::text]))),
    CONSTRAINT opportunities_request_type_check CHECK ((request_type = ANY (ARRAY['new'::text, 'renewal'::text, 'upsell'::text, 'duplicate_review'::text])))
);


--
-- Name: TABLE opportunities; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.opportunities IS 'Phase 7E: 영업 기회 마스터. pre-sale 단계 추적. post-sale은 partner_account_assignments';


--
-- Name: COLUMN opportunities.origin_channel; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.origin_channel IS 'DIR-S=본부 영업팀이 발굴 / DIST/IND-P/DIR-P=파트너가 자체 발굴';


--
-- Name: COLUMN opportunities.primary_owner; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.primary_owner IS 'HQ=본부 영업팀 주관 / PARTNER=파트너 주관';


--
-- Name: COLUMN opportunities.win_probability; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.win_probability IS 'Phase 7F: 영업사원 수기 입력 계약 확률 (0-100). Pipeline Forecast 가중치 계산용';


--
-- Name: COLUMN opportunities.assigned_sales_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.assigned_sales_user_id IS 'Phase 7F: 이 거래를 담당하는 영업사원';


--
-- Name: COLUMN opportunities.customer_address; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.customer_address IS '고객사 주소 (PO FROM 섹션)';


--
-- Name: COLUMN opportunities.customer_ceo_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.customer_ceo_name IS '고객사 대표이사';


--
-- Name: COLUMN opportunities.customer_business_no; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.customer_business_no IS '사업자등록번호 (XXX-XX-XXXXX)';


--
-- Name: COLUMN opportunities.customer_contact_title; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.customer_contact_title IS '담당자 직책';


--
-- Name: COLUMN opportunities.customer_fax; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.customer_fax IS 'FAX 번호';


--
-- Name: COLUMN opportunities.business_field; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.business_field IS '지원 사업 분야';


--
-- Name: COLUMN opportunities.assigned_partner_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.assigned_partner_id IS '영업 기회의 소속 파트너 (등록자가 파트너인 경우)';


--
-- Name: COLUMN opportunities.assigning_distributor_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.assigning_distributor_id IS '총판이 휘하 파트너에게 배당한 경우 추적용 (수동 핸드오프)';


--
-- Name: COLUMN opportunities.request_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunities.request_type IS '등록 요청 유형: new(신규고객) / renewal(재계약, 수량변동 가능) / upsell(기간중 좌석추가) / duplicate_review(중복검토 필요)';


--
-- Name: opportunity_activities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.opportunity_activities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    opportunity_id uuid NOT NULL,
    activity_type text NOT NULL,
    activity_date timestamp with time zone DEFAULT now() NOT NULL,
    title text NOT NULL,
    content text NOT NULL,
    next_action text,
    next_action_date date,
    author_id uuid,
    author_name text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone,
    CONSTRAINT opportunity_activities_activity_type_check CHECK ((activity_type = ANY (ARRAY['meeting'::text, 'call'::text, 'email'::text, 'visit'::text, 'proposal_sent'::text, 'contract_sent'::text, 'demo'::text, 'other'::text])))
);


--
-- Name: TABLE opportunity_activities; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.opportunity_activities IS '영업 활동 로그 (미팅/통화/이메일/방문/제안서/계약서/데모/기타)';


--
-- Name: COLUMN opportunity_activities.activity_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunity_activities.activity_type IS '활동 유형 (meeting/call/email/visit/proposal_sent/contract_sent/demo/other)';


--
-- Name: COLUMN opportunity_activities.next_action; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunity_activities.next_action IS '다음 액션 (예: 제안서 송부, 2차 미팅 일정 조율)';


--
-- Name: COLUMN opportunity_activities.next_action_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunity_activities.next_action_date IS '다음 액션 예정일';


--
-- Name: opportunity_approval_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.opportunity_approval_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    opportunity_id uuid NOT NULL,
    approval_type text NOT NULL,
    requested_by uuid,
    requested_by_name text,
    requested_by_role text,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    request_notes text,
    escalation_level integer DEFAULT 1,
    assigned_to uuid,
    assigned_to_name text,
    assigned_to_role text,
    action text,
    action_by uuid,
    action_by_name text,
    action_at timestamp with time zone,
    action_notes text,
    escalation_reason text,
    next_assignee uuid,
    next_assignee_name text,
    sla_target_hours integer DEFAULT 24,
    processing_duration_minutes integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    rejection_reason_code text,
    CONSTRAINT opportunity_approval_log_action_check CHECK ((action = ANY (ARRAY['approved'::text, 'rejected'::text, 'escalated'::text, 'pending'::text]))),
    CONSTRAINT opportunity_approval_log_approval_type_check CHECK ((approval_type = ANY (ARRAY['registration'::text, 'status_change'::text, 'duplicate_override'::text, 'rejection'::text]))),
    CONSTRAINT opportunity_approval_log_rejection_reason_code_check CHECK ((rejection_reason_code = ANY (ARRAY['duplicate'::text, 'direct_account'::text, 'unqualified'::text, 'territory_conflict'::text, 'pricing_concern'::text, 'other'::text])))
);


--
-- Name: COLUMN opportunity_approval_log.rejection_reason_code; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunity_approval_log.rejection_reason_code IS '거절 사유: duplicate/direct_account/unqualified/territory_conflict/pricing_concern/other';


--
-- Name: opportunity_change_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.opportunity_change_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    opportunity_id uuid NOT NULL,
    change_type text NOT NULL,
    changed_by uuid NOT NULL,
    changed_at timestamp with time zone DEFAULT now(),
    old_value jsonb,
    new_value jsonb,
    reason text NOT NULL,
    customer_request boolean DEFAULT false,
    CONSTRAINT chk_change_type CHECK ((change_type = ANY (ARRAY['created'::text, 'partner_engaged'::text, 'partner_unengaged'::text, 'partner_changed'::text, 'status_changed'::text, 'amount_changed'::text, 'customer_request_change'::text, 'closed_won'::text, 'closed_lost'::text])))
);


--
-- Name: TABLE opportunity_change_log; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.opportunity_change_log IS 'Phase 7E: 모든 영업 기회 변경 이력 감사 로그. append-only (UPDATE/DELETE 금지)';


--
-- Name: opportunity_contacts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.opportunity_contacts (
    id uuid NOT NULL,
    opportunity_id uuid NOT NULL,
    name text NOT NULL,
    title text,
    department text,
    role text,
    email text,
    phone text,
    notes text,
    is_primary boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    created_by uuid NOT NULL
);


--
-- Name: TABLE opportunity_contacts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.opportunity_contacts IS 'Phase 7F: 영업 기회별 고객 측 컨택. 한 거래에 여러 명, 외부 인물 자유 입력 가능';


--
-- Name: opportunity_engagements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.opportunity_engagements (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    opportunity_id uuid NOT NULL,
    partner_id uuid NOT NULL,
    engagement_type text NOT NULL,
    engaged_by uuid NOT NULL,
    engaged_at timestamp with time zone DEFAULT now(),
    reason text,
    unengaged_at timestamp with time zone,
    unengaged_by uuid,
    unengaged_reason text,
    CONSTRAINT chk_engagement_type CHECK ((engagement_type = ANY (ARRAY['PRIMARY'::text, 'CASCADED'::text, 'COLLAB'::text]))),
    CONSTRAINT chk_unengage_consistency CHECK ((((unengaged_at IS NULL) AND (unengaged_by IS NULL)) OR ((unengaged_at IS NOT NULL) AND (unengaged_by IS NOT NULL))))
);


--
-- Name: TABLE opportunity_engagements; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.opportunity_engagements IS 'Phase 7E: opportunity에 파트너가 인게이지된 매핑. 정보 격리의 핵심 — RLS가 이 테이블 기준으로 가시성 결정';


--
-- Name: COLUMN opportunity_engagements.engagement_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.opportunity_engagements.engagement_type IS 'PRIMARY=핸드오프 담당(수금권) / CASCADED=자동추가된 상위DIST / COLLAB=협업(수금권없음)';


--
-- Name: opportunity_status_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.opportunity_status_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    opportunity_id uuid NOT NULL,
    old_status text,
    new_status text NOT NULL,
    change_type text NOT NULL,
    changed_by uuid,
    changed_by_name text,
    changed_by_role text,
    change_reason text,
    requires_approval boolean DEFAULT false,
    approval_status text DEFAULT 'auto_approved'::text,
    approved_by uuid,
    approved_by_name text,
    approved_at timestamp with time zone,
    changed_at timestamp with time zone DEFAULT now() NOT NULL,
    ip_address inet,
    user_agent text,
    CONSTRAINT opportunity_status_log_approval_status_check CHECK ((approval_status = ANY (ARRAY['auto_approved'::text, 'pending'::text, 'approved'::text, 'rejected'::text]))),
    CONSTRAINT opportunity_status_log_change_type_check CHECK ((change_type = ANY (ARRAY['initial_create'::text, 'status_progress'::text, 'status_regress'::text, 'status_close'::text, 'admin_override'::text, 'auto_change'::text])))
);


--
-- Name: v_pending_approvals; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_pending_approvals AS
 SELECT o.id,
    o.customer_name,
    o.customer_business_no,
    o.license_tier,
    o.expected_seats,
    o.expected_amount,
    o.origin_channel,
    o.approval_status,
    o.is_duplicate,
    o.duplicate_of,
    o.escalation_level,
    o.created_at,
    o.created_by,
    u_creator.name AS creator_name,
    u_creator.role AS creator_role,
    u_creator.partner_id AS creator_partner_id,
    o.escalated_to,
    o.escalated_to_name,
    (EXTRACT(epoch FROM (now() - o.created_at)) / (3600)::numeric) AS hours_pending
   FROM (public.opportunities o
     LEFT JOIN public.users u_creator ON ((u_creator.id = o.created_by)))
  WHERE (o.approval_status = ANY (ARRAY['pending'::text, 'escalated'::text]))
  ORDER BY o.created_at;


--
-- Name: VIEW v_pending_approvals; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_pending_approvals IS '승인 대기 중인 영업 기회 (관리자 대시보드)';


--
-- Name: approval_requests approval_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.approval_requests
    ADD CONSTRAINT approval_requests_pkey PRIMARY KEY (id);


--
-- Name: opportunities opportunities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunities
    ADD CONSTRAINT opportunities_pkey PRIMARY KEY (id);


--
-- Name: opportunity_activities opportunity_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_activities
    ADD CONSTRAINT opportunity_activities_pkey PRIMARY KEY (id);


--
-- Name: opportunity_approval_log opportunity_approval_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_approval_log
    ADD CONSTRAINT opportunity_approval_log_pkey PRIMARY KEY (id);


--
-- Name: opportunity_change_log opportunity_change_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_change_log
    ADD CONSTRAINT opportunity_change_log_pkey PRIMARY KEY (id);


--
-- Name: opportunity_contacts opportunity_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_contacts
    ADD CONSTRAINT opportunity_contacts_pkey PRIMARY KEY (id);


--
-- Name: opportunity_engagements opportunity_engagements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_engagements
    ADD CONSTRAINT opportunity_engagements_pkey PRIMARY KEY (id);


--
-- Name: opportunity_status_log opportunity_status_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_status_log
    ADD CONSTRAINT opportunity_status_log_pkey PRIMARY KEY (id);


--
-- Name: idx_approval_log_assigned; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_approval_log_assigned ON public.opportunity_approval_log USING btree (assigned_to, action) WHERE (action = 'pending'::text);


--
-- Name: idx_approval_log_opp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_approval_log_opp ON public.opportunity_approval_log USING btree (opportunity_id);


--
-- Name: idx_approval_log_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_approval_log_pending ON public.opportunity_approval_log USING btree (action, escalation_level) WHERE (action = 'pending'::text);


--
-- Name: idx_ar_license; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ar_license ON public.approval_requests USING btree (related_license_id);


--
-- Name: idx_ar_partner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ar_partner ON public.approval_requests USING btree (related_partner_id);


--
-- Name: idx_ar_requested_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ar_requested_by ON public.approval_requests USING btree (requested_by);


--
-- Name: idx_ar_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ar_status ON public.approval_requests USING btree (request_status) WHERE (request_status = ANY (ARRAY['pending'::text, 'in_review'::text]));


--
-- Name: idx_ar_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ar_type ON public.approval_requests USING btree (request_type);


--
-- Name: idx_change_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_change_at ON public.opportunity_change_log USING btree (changed_at DESC);


--
-- Name: idx_change_opp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_change_opp ON public.opportunity_change_log USING btree (opportunity_id);


--
-- Name: idx_change_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_change_type ON public.opportunity_change_log USING btree (change_type);


--
-- Name: idx_contact_opp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contact_opp ON public.opportunity_contacts USING btree (opportunity_id);


--
-- Name: idx_contact_primary; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contact_primary ON public.opportunity_contacts USING btree (opportunity_id) WHERE (is_primary = true);


--
-- Name: idx_engage_opp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_engage_opp ON public.opportunity_engagements USING btree (opportunity_id);


--
-- Name: idx_engage_partner_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_engage_partner_active ON public.opportunity_engagements USING btree (partner_id) WHERE (unengaged_at IS NULL);


--
-- Name: idx_engagement_unique_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_engagement_unique_active ON public.opportunity_engagements USING btree (opportunity_id, partner_id, engagement_type) WHERE (unengaged_at IS NULL);


--
-- Name: idx_opp_activities_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opp_activities_date ON public.opportunity_activities USING btree (activity_date DESC);


--
-- Name: idx_opp_activities_opp_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opp_activities_opp_id ON public.opportunity_activities USING btree (opportunity_id);


--
-- Name: idx_opp_close_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opp_close_date ON public.opportunities USING btree (expected_close_date) WHERE (status <> ALL (ARRAY['closed_won'::text, 'closed_lost'::text]));


--
-- Name: idx_opp_origin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opp_origin ON public.opportunities USING btree (origin_channel);


--
-- Name: idx_opp_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opp_owner ON public.opportunities USING btree (created_by);


--
-- Name: idx_opp_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opp_status ON public.opportunities USING btree (status) WHERE (status <> ALL (ARRAY['closed_won'::text, 'closed_lost'::text]));


--
-- Name: idx_opps_approval_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opps_approval_status ON public.opportunities USING btree (approval_status) WHERE (approval_status = ANY (ARRAY['pending'::text, 'escalated'::text]));


--
-- Name: idx_opps_assigned_partner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opps_assigned_partner ON public.opportunities USING btree (assigned_partner_id) WHERE (assigned_partner_id IS NOT NULL);


--
-- Name: idx_opps_assigning_distributor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opps_assigning_distributor ON public.opportunities USING btree (assigning_distributor_id) WHERE (assigning_distributor_id IS NOT NULL);


--
-- Name: idx_opps_duplicate; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opps_duplicate ON public.opportunities USING btree (duplicate_of) WHERE (duplicate_of IS NOT NULL);


--
-- Name: idx_opps_request_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opps_request_type ON public.opportunities USING btree (request_type, approval_status) WHERE (approval_status = ANY (ARRAY['pending'::text, 'escalated'::text]));


--
-- Name: idx_status_log_opp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_status_log_opp ON public.opportunity_status_log USING btree (opportunity_id, changed_at DESC);


--
-- Name: idx_status_log_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_status_log_pending ON public.opportunity_status_log USING btree (approval_status) WHERE (approval_status = 'pending'::text);


--
-- Name: opportunity_engagements trg_cascade_distributor; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_cascade_distributor AFTER INSERT ON public.opportunity_engagements FOR EACH ROW EXECUTE FUNCTION public.auto_engage_parent_distributor();


--
-- Name: opportunity_engagements trg_log_engagement; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_log_engagement AFTER INSERT OR UPDATE ON public.opportunity_engagements FOR EACH ROW EXECUTE FUNCTION public.log_engagement_change();


--
-- Name: opportunities trg_log_opp_change; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_log_opp_change BEFORE UPDATE ON public.opportunities FOR EACH ROW EXECUTE FUNCTION public.log_opportunity_status_change();


--
-- Name: approval_requests update_approval_requests_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_approval_requests_updated_at BEFORE UPDATE ON public.approval_requests FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: approval_requests approval_requests_final_decision_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.approval_requests
    ADD CONSTRAINT approval_requests_final_decision_by_fkey FOREIGN KEY (final_decision_by) REFERENCES public.users(id);


--
-- Name: approval_requests approval_requests_related_contract_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.approval_requests
    ADD CONSTRAINT approval_requests_related_contract_id_fkey FOREIGN KEY (related_contract_id) REFERENCES public.contracts(id);


--
-- Name: approval_requests approval_requests_related_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.approval_requests
    ADD CONSTRAINT approval_requests_related_customer_id_fkey FOREIGN KEY (related_customer_id) REFERENCES public.customers(id);


--
-- Name: approval_requests approval_requests_related_license_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.approval_requests
    ADD CONSTRAINT approval_requests_related_license_id_fkey FOREIGN KEY (related_license_id) REFERENCES public.licenses(id);


--
-- Name: approval_requests approval_requests_related_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.approval_requests
    ADD CONSTRAINT approval_requests_related_partner_id_fkey FOREIGN KEY (related_partner_id) REFERENCES public.partners(id);


--
-- Name: approval_requests approval_requests_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.approval_requests
    ADD CONSTRAINT approval_requests_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES public.users(id);


--
-- Name: opportunities opportunities_assigned_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunities
    ADD CONSTRAINT opportunities_assigned_partner_id_fkey FOREIGN KEY (assigned_partner_id) REFERENCES public.partners(id) ON DELETE SET NULL;


--
-- Name: opportunities opportunities_assigned_sales_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunities
    ADD CONSTRAINT opportunities_assigned_sales_user_id_fkey FOREIGN KEY (assigned_sales_user_id) REFERENCES public.users(id);


--
-- Name: opportunities opportunities_assigning_distributor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunities
    ADD CONSTRAINT opportunities_assigning_distributor_id_fkey FOREIGN KEY (assigning_distributor_id) REFERENCES public.partners(id) ON DELETE SET NULL;


--
-- Name: opportunities opportunities_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunities
    ADD CONSTRAINT opportunities_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: opportunities opportunities_duplicate_of_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunities
    ADD CONSTRAINT opportunities_duplicate_of_fkey FOREIGN KEY (duplicate_of) REFERENCES public.opportunities(id) ON DELETE SET NULL;


--
-- Name: opportunity_activities opportunity_activities_opportunity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_activities
    ADD CONSTRAINT opportunity_activities_opportunity_id_fkey FOREIGN KEY (opportunity_id) REFERENCES public.opportunities(id) ON DELETE CASCADE;


--
-- Name: opportunity_approval_log opportunity_approval_log_opportunity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_approval_log
    ADD CONSTRAINT opportunity_approval_log_opportunity_id_fkey FOREIGN KEY (opportunity_id) REFERENCES public.opportunities(id) ON DELETE CASCADE;


--
-- Name: opportunity_change_log opportunity_change_log_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_change_log
    ADD CONSTRAINT opportunity_change_log_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES auth.users(id);


--
-- Name: opportunity_change_log opportunity_change_log_opportunity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_change_log
    ADD CONSTRAINT opportunity_change_log_opportunity_id_fkey FOREIGN KEY (opportunity_id) REFERENCES public.opportunities(id) ON DELETE CASCADE;


--
-- Name: opportunity_contacts opportunity_contacts_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_contacts
    ADD CONSTRAINT opportunity_contacts_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id);


--
-- Name: opportunity_contacts opportunity_contacts_opportunity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_contacts
    ADD CONSTRAINT opportunity_contacts_opportunity_id_fkey FOREIGN KEY (opportunity_id) REFERENCES public.opportunities(id) ON DELETE CASCADE;


--
-- Name: opportunity_engagements opportunity_engagements_engaged_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_engagements
    ADD CONSTRAINT opportunity_engagements_engaged_by_fkey FOREIGN KEY (engaged_by) REFERENCES auth.users(id);


--
-- Name: opportunity_engagements opportunity_engagements_opportunity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_engagements
    ADD CONSTRAINT opportunity_engagements_opportunity_id_fkey FOREIGN KEY (opportunity_id) REFERENCES public.opportunities(id) ON DELETE CASCADE;


--
-- Name: opportunity_engagements opportunity_engagements_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_engagements
    ADD CONSTRAINT opportunity_engagements_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public.partners(id);


--
-- Name: opportunity_engagements opportunity_engagements_unengaged_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_engagements
    ADD CONSTRAINT opportunity_engagements_unengaged_by_fkey FOREIGN KEY (unengaged_by) REFERENCES auth.users(id);


--
-- Name: opportunity_status_log opportunity_status_log_opportunity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opportunity_status_log
    ADD CONSTRAINT opportunity_status_log_opportunity_id_fkey FOREIGN KEY (opportunity_id) REFERENCES public.opportunities(id) ON DELETE CASCADE;


--
-- Name: opportunity_approval_log approval_log_all_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY approval_log_all_access ON public.opportunity_approval_log TO authenticated, anon USING (true) WITH CHECK (true);


--
-- Name: approval_requests; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.approval_requests ENABLE ROW LEVEL SECURITY;

--
-- Name: opportunity_change_log change_log_insert_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY change_log_insert_all ON public.opportunity_change_log FOR INSERT WITH CHECK (true);


--
-- Name: opportunity_change_log change_log_select_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY change_log_select_all ON public.opportunity_change_log FOR SELECT USING (true);


--
-- Name: opportunity_contacts contact_modify; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY contact_modify ON public.opportunity_contacts USING ((auth.uid() IS NOT NULL)) WITH CHECK ((auth.uid() IS NOT NULL));


--
-- Name: opportunity_contacts contacts_delete_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY contacts_delete_all ON public.opportunity_contacts FOR DELETE USING (true);


--
-- Name: opportunity_contacts contacts_insert_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY contacts_insert_all ON public.opportunity_contacts FOR INSERT WITH CHECK (true);


--
-- Name: opportunity_contacts contacts_select_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY contacts_select_all ON public.opportunity_contacts FOR SELECT USING (true);


--
-- Name: opportunity_contacts contacts_update_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY contacts_update_all ON public.opportunity_contacts FOR UPDATE USING (true) WITH CHECK (true);


--
-- Name: opportunity_engagements engagement_modify; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY engagement_modify ON public.opportunity_engagements USING (public.is_hq_user(auth.uid())) WITH CHECK (public.is_hq_user(auth.uid()));


--
-- Name: opportunity_engagements engagements_delete_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY engagements_delete_all ON public.opportunity_engagements FOR DELETE USING (true);


--
-- Name: opportunity_engagements engagements_insert_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY engagements_insert_all ON public.opportunity_engagements FOR INSERT WITH CHECK (true);


--
-- Name: opportunity_engagements engagements_select_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY engagements_select_all ON public.opportunity_engagements FOR SELECT USING (true);


--
-- Name: opportunity_engagements engagements_update_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY engagements_update_all ON public.opportunity_engagements FOR UPDATE USING (true) WITH CHECK (true);


--
-- Name: opportunity_activities opp_activities_delete_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY opp_activities_delete_all ON public.opportunity_activities FOR DELETE TO authenticated, anon USING (true);


--
-- Name: opportunity_activities opp_activities_insert_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY opp_activities_insert_all ON public.opportunity_activities FOR INSERT TO authenticated, anon WITH CHECK (true);


--
-- Name: opportunity_activities opp_activities_select_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY opp_activities_select_all ON public.opportunity_activities FOR SELECT TO authenticated, anon USING (true);


--
-- Name: opportunity_activities opp_activities_update_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY opp_activities_update_all ON public.opportunity_activities FOR UPDATE TO authenticated, anon USING (true) WITH CHECK (true);


--
-- Name: opportunities; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.opportunities ENABLE ROW LEVEL SECURITY;

--
-- Name: opportunities opportunities_delete_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY opportunities_delete_all ON public.opportunities FOR DELETE USING (true);


--
-- Name: opportunities opportunities_insert_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY opportunities_insert_all ON public.opportunities FOR INSERT TO authenticated, anon WITH CHECK (true);


--
-- Name: opportunities opportunities_select_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY opportunities_select_all ON public.opportunities FOR SELECT USING (true);


--
-- Name: opportunities opportunities_update_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY opportunities_update_all ON public.opportunities FOR UPDATE USING (true) WITH CHECK (true);


--
-- Name: opportunity_activities; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.opportunity_activities ENABLE ROW LEVEL SECURITY;

--
-- Name: opportunity_approval_log; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.opportunity_approval_log ENABLE ROW LEVEL SECURITY;

--
-- Name: opportunity_change_log; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.opportunity_change_log ENABLE ROW LEVEL SECURITY;

--
-- Name: opportunity_contacts; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.opportunity_contacts ENABLE ROW LEVEL SECURITY;

--
-- Name: opportunity_engagements; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.opportunity_engagements ENABLE ROW LEVEL SECURITY;

--
-- Name: opportunity_status_log; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.opportunity_status_log ENABLE ROW LEVEL SECURITY;

--
-- Name: opportunity_status_log status_log_all_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY status_log_all_access ON public.opportunity_status_log TO authenticated, anon USING (true) WITH CHECK (true);


--
-- PostgreSQL database dump complete
--


