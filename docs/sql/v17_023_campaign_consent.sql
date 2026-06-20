-- ============================================================
-- DragonEyes v1.7 — Phase 10 추가 (023)
-- 캠페인 사용 동의서 시스템 + 학생 보호자 정보 보강
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   :
--   모든 캠페인 사용자(학생/학부모/기관 admin)는 첫 로그인 시
--   '드래곤아이즈 온라인 유해컨텐츠 근절 캠페인 사이트 이용 동의서'에 동의해야 함.
--   - 모니터링 시스템 동의와 별도 (캠페인 전용)
--   - 약관 버전 업 시 자동 재동의 요청
--   - 학생은 보호자 정보(이름·전화·연락처·이메일·거주지) 필수 입력
--   - 학생은 자기 보호자 정보 수정 가능
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. users — 보호자 정보 컬럼 보강
-- ─────────────────────────────────────────────────────────────
-- guardian_name, guardian_phone 은 이미 존재
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS guardian_email TEXT;
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS guardian_contact TEXT;          -- 추가 연락처 (집/직장)
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS guardian_address TEXT;          -- 거주지 주소
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS guardian_updated_at TIMESTAMPTZ;
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS guardian_updated_by UUID
        REFERENCES public.users(id) ON DELETE SET NULL;

-- 캠페인 동의 추적 컬럼
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS campaign_terms_version TEXT;
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS campaign_terms_agreed_at TIMESTAMPTZ;


-- ─────────────────────────────────────────────────────────────
-- 2. campaign_terms_versions — 캠페인 약관 버전 관리
-- ─────────────────────────────────────────────────────────────
-- terms_of_service_versions(v17_022)와 별도 — 캠페인 사이트 전용 동의서
CREATE TABLE IF NOT EXISTS public.campaign_terms_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version         TEXT NOT NULL UNIQUE,                    -- 'v1.0', '2026-06-20' 등
    title           TEXT NOT NULL,
    body_md         TEXT NOT NULL,
    requires_guardian_info BOOLEAN NOT NULL DEFAULT FALSE,   -- 학생 동의 시 보호자 정보 필요 여부
    effective_from  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_by      UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ctv_active
    ON public.campaign_terms_versions(is_active, effective_from DESC);


-- ─────────────────────────────────────────────────────────────
-- 3. 초기 캠페인 약관 SEED (모니터링 약관 어댑테이션)
-- ─────────────────────────────────────────────────────────────
INSERT INTO public.campaign_terms_versions (version, title, body_md, requires_guardian_info, is_active)
VALUES (
    'v1.0',
    '드래곤아이즈 온라인 유해컨텐츠 근절 캠페인 사이트 이용 동의서',
'본 동의서는 드래곤아이즈가 운영하는 **온라인 유해컨텐츠 근절 캠페인 사이트** 이용에 관한 약관입니다. 캠페인 참여를 위해 아래 내용에 동의해주세요.

---

### 1. 캠페인 소개
1. 본 사이트는 (주)드래곤아이즈가 운영하는 **온라인 유해컨텐츠 근절 캠페인** 플랫폼입니다.
2. 학생·학부모·교육기관이 함께 참여하여 청소년의 온라인 안전 의식을 높이는 사회공헌 캠페인입니다.
3. 학습 자료(영상·PDF) 열람, 50문항 안전 설문 응시, 봉사활동 인증서 발급, 외부강사 강연, 만족도 조사 등을 제공합니다.

### 2. 회원의 권리와 의무
1. **학생**: 무료로 학습 자료·설문·봉사 점수 모두 이용 가능합니다.
2. **학부모**: 연 17,000원 결제 시 모든 유료 자료 무제한 + 자녀 전원 학습 권한이 부여됩니다.
3. **교육기관(학교)**: 사업자등록증/학교 인가증 등록·승인 후 학생 관리, 강연 신청, 인증서 조회가 가능합니다.
4. 모든 사용자는 본인의 라이선스를 타인과 공유하지 않으며, 실명 정보로 가입해야 합니다.

### 3. 개인정보 수집·이용
1. **수집 항목**: 이름, 이메일, 생년월일, 학교·학년, 휴대폰(선택), 결제 정보(PG사 처리)
2. **학생의 경우 추가 수집**: 보호자 이름·전화·연락처·이메일·거주지 주소 (개인정보보호법상 만 14세 미만 보호자 동의 의무)
3. **이용 목적**: 캠페인 서비스 제공, 봉사활동 인증서 발급, 학교별 통계 집계, 공지·만족도 조사 발송
4. **보유 기간**: 회원 탈퇴 시 즉시 파기 (결제 정보는 법정 보존 기간 5년)
5. **제3자 제공**: 원칙적으로 제공하지 않음. 다만 학교·교육청 등 상급기관에는 **개인정보 마스킹된 통계만** 공유합니다.

### 4. 봉사활동 인증서
1. 학년대별 설문 응답 임계값(초등 20/중학 30/고등 50명)을 달성하면 자동으로 인증서가 발급됩니다.
2. 인증서는 (주)드래곤아이즈 대표이사 직인이 찍힌 **표준 양식**과 학교장 날인란이 비어 있는 **학교 제출용** 두 가지로 출력 가능합니다.
3. 시리얼 번호로 진위 확인 가능하며, 재출력 횟수가 추적됩니다.

### 5. 결제 및 환불
1. 학부모 연 구독료는 17,000원이며 결제일부터 동년 12월 31일까지 유효합니다.
2. 환불 정책: 결제 후 7일 이내 자료 미열람 시 전액 환불, 이후에는 사용 비율에 따라 부분 환불 검토.
3. 환불 요청은 학부모 dashboard → 결제 내역 → 환불 요청 버튼으로 본부에 발송됩니다.

### 6. 학생 정보 보호 및 보호자 정보
1. 학생 개인정보는 **본교 교사**만 직접 열람 가능하며, 타 학교/상급기관에는 마스킹된 통계만 공유됩니다.
2. 만 14세 미만 학생은 보호자 동의 후 가입 가능합니다.
3. 학생은 자기 dashboard에서 **보호자 정보를 직접 수정**할 수 있습니다.

### 7. 공지 및 알림
1. 본부 admin 또는 학교 담당자가 발송한 공지를 사이트 내 공지 페이지와 등록 이메일로 받게 됩니다.
2. 구독 만료 30일/7일 전 알림이 자동 발송됩니다.

### 8. 약관 변경
1. 본 약관이 변경되면 모든 사용자는 다음 접속 시 재동의가 필요합니다.
2. 변경 내용은 공지로 사전 안내됩니다.

### 9. 책임 제한
1. 본 캠페인은 사회공헌 목적으로 운영되며, 학습 자료의 활용 결과에 대한 법적 책임은 사용자에게 있습니다.
2. 외부강사 강연은 학교와 협의 후 진행되며, 강연 내용에 대한 책임은 해당 강사에게 있습니다.

### 10. 분쟁 해결
1. 본 약관에 관한 분쟁은 (주)드래곤아이즈 본사 소재지 관할 법원에서 해결합니다.
2. 문의: support@dragoneyes.kr

---

**제정일**: 2026년 6월 20일
**시행일**: 2026년 6월 20일
**버전**: v1.0',
    TRUE,
    TRUE
)
ON CONFLICT (version) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 4. campaign_terms_acceptances — 사용자별 동의 이력
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.campaign_terms_acceptances (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    terms_version   TEXT NOT NULL,
    accepted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address      TEXT,
    user_agent      TEXT,
    -- 학생일 때 함께 저장된 보호자 정보 스냅샷 (수정 추적용)
    guardian_snapshot JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, terms_version)
);

CREATE INDEX IF NOT EXISTS idx_cta_user    ON public.campaign_terms_acceptances(user_id);
CREATE INDEX IF NOT EXISTS idx_cta_version ON public.campaign_terms_acceptances(terms_version);


-- ─────────────────────────────────────────────────────────────
-- 5. 현재 활성 약관 + 사용자 동의 필요 여부
-- ─────────────────────────────────────────────────────────────
-- 반환:
--   needs_consent BOOLEAN — 동의 필요 (재동의 포함)
--   current_version TEXT  — 현재 활성 약관 버전
--   user_version TEXT     — 사용자가 마지막 동의한 버전
--   requires_guardian BOOLEAN — 현재 약관이 보호자 정보 요구하는지
CREATE OR REPLACE FUNCTION public.check_campaign_consent(p_user_id UUID)
RETURNS TABLE (
    needs_consent BOOLEAN,
    current_version TEXT,
    user_version TEXT,
    requires_guardian BOOLEAN,
    is_student BOOLEAN
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_active_ver TEXT;
    v_active_req_guardian BOOLEAN;
    v_user_ver TEXT;
    v_role TEXT;
BEGIN
    SELECT version, requires_guardian_info
      INTO v_active_ver, v_active_req_guardian
      FROM public.campaign_terms_versions
     WHERE is_active = TRUE
     ORDER BY effective_from DESC
     LIMIT 1;

    IF v_active_ver IS NULL THEN
        needs_consent := FALSE;
        current_version := NULL;
        user_version := NULL;
        requires_guardian := FALSE;
        is_student := FALSE;
        RETURN NEXT; RETURN;
    END IF;

    SELECT campaign_terms_version, role_v2
      INTO v_user_ver, v_role
      FROM public.users WHERE id = p_user_id;

    needs_consent     := (v_user_ver IS DISTINCT FROM v_active_ver);
    current_version   := v_active_ver;
    user_version      := v_user_ver;
    requires_guardian := v_active_req_guardian;
    is_student        := (v_role = 'student');
    RETURN NEXT;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 6. 동의 처리 함수 (학생: 보호자 정보 함께)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.accept_campaign_terms(
    p_user_id          UUID,
    p_terms_version    TEXT,
    p_guardian_name    TEXT DEFAULT NULL,
    p_guardian_phone   TEXT DEFAULT NULL,
    p_guardian_contact TEXT DEFAULT NULL,
    p_guardian_email   TEXT DEFAULT NULL,
    p_guardian_address TEXT DEFAULT NULL,
    p_ip               TEXT DEFAULT NULL,
    p_user_agent       TEXT DEFAULT NULL
) RETURNS BOOLEAN LANGUAGE plpgsql AS $$
DECLARE
    v_role TEXT;
    v_snapshot JSONB;
BEGIN
    SELECT role_v2 INTO v_role FROM public.users WHERE id = p_user_id;
    IF v_role IS NULL THEN RETURN FALSE; END IF;

    -- 학생일 때 보호자 정보 5종 필수
    IF v_role = 'student' THEN
        IF p_guardian_name IS NULL OR p_guardian_name = ''
           OR p_guardian_phone IS NULL OR p_guardian_phone = ''
           OR p_guardian_email IS NULL OR p_guardian_email = ''
           OR p_guardian_address IS NULL OR p_guardian_address = ''
        THEN
            RAISE EXCEPTION '학생은 보호자 정보(이름·전화·이메일·거주지)가 필수입니다';
        END IF;

        v_snapshot := jsonb_build_object(
            'name',    p_guardian_name,
            'phone',   p_guardian_phone,
            'contact', p_guardian_contact,
            'email',   p_guardian_email,
            'address', p_guardian_address
        );

        UPDATE public.users
           SET guardian_name    = p_guardian_name,
               guardian_phone   = p_guardian_phone,
               guardian_contact = p_guardian_contact,
               guardian_email   = p_guardian_email,
               guardian_address = p_guardian_address,
               guardian_updated_at = NOW(),
               guardian_updated_by = p_user_id
         WHERE id = p_user_id;
    END IF;

    -- users 컬럼 갱신
    UPDATE public.users
       SET campaign_terms_version = p_terms_version,
           campaign_terms_agreed_at = NOW()
     WHERE id = p_user_id;

    -- 동의 이력 INSERT (재동의 시 update)
    INSERT INTO public.campaign_terms_acceptances (
        user_id, terms_version, ip_address, user_agent, guardian_snapshot
    ) VALUES (
        p_user_id, p_terms_version, p_ip, p_user_agent, v_snapshot
    )
    ON CONFLICT (user_id, terms_version) DO UPDATE
    SET accepted_at = NOW(),
        guardian_snapshot = COALESCE(EXCLUDED.guardian_snapshot, public.campaign_terms_acceptances.guardian_snapshot);

    RETURN TRUE;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 7. 학생이 자기 보호자 정보 수정 (재동의 없이)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.update_my_guardian_info(
    p_user_id          UUID,
    p_guardian_name    TEXT,
    p_guardian_phone   TEXT,
    p_guardian_contact TEXT,
    p_guardian_email   TEXT,
    p_guardian_address TEXT
) RETURNS BOOLEAN LANGUAGE plpgsql AS $$
DECLARE
    v_role TEXT;
BEGIN
    SELECT role_v2 INTO v_role FROM public.users WHERE id = p_user_id;
    IF v_role <> 'student' THEN
        RAISE EXCEPTION '학생만 자기 보호자 정보를 수정할 수 있습니다';
    END IF;

    IF COALESCE(p_guardian_name,'') = ''
       OR COALESCE(p_guardian_phone,'') = ''
       OR COALESCE(p_guardian_email,'') = ''
       OR COALESCE(p_guardian_address,'') = ''
    THEN
        RAISE EXCEPTION '보호자 정보(이름·전화·이메일·거주지)는 필수입니다';
    END IF;

    UPDATE public.users
       SET guardian_name    = p_guardian_name,
           guardian_phone   = p_guardian_phone,
           guardian_contact = p_guardian_contact,
           guardian_email   = p_guardian_email,
           guardian_address = p_guardian_address,
           guardian_updated_at = NOW(),
           guardian_updated_by = p_user_id
     WHERE id = p_user_id;

    RETURN TRUE;
END;
$$;


-- ─────────────────────────────────────────────────────────────
-- 8. 보호자 정보 조회 (본인 + 학교 교사 — 마스킹 정책은 v17_016)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_my_guardian_info(p_user_id UUID)
RETURNS TABLE (
    guardian_name TEXT, guardian_phone TEXT, guardian_contact TEXT,
    guardian_email TEXT, guardian_address TEXT,
    guardian_updated_at TIMESTAMPTZ
) LANGUAGE SQL STABLE AS $$
    SELECT guardian_name, guardian_phone, guardian_contact,
           guardian_email, guardian_address, guardian_updated_at
      FROM public.users
     WHERE id = p_user_id;
$$;


-- ─────────────────────────────────────────────────────────────
-- 9. 트리거 (updated_at)
-- ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_ctv_updated_at ON public.campaign_terms_versions;
CREATE TRIGGER trg_ctv_updated_at
    BEFORE UPDATE ON public.campaign_terms_versions
    FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT column_name FROM information_schema.columns
 WHERE table_schema='public' AND table_name='users'
   AND column_name IN (
       'guardian_email','guardian_contact','guardian_address',
       'guardian_updated_at','guardian_updated_by',
       'campaign_terms_version','campaign_terms_agreed_at')
 ORDER BY column_name;
-- 기대: 7행

SELECT version, requires_guardian_info, is_active
  FROM public.campaign_terms_versions;
-- 기대: v1.0 | true | true

SELECT 'campaign_terms_versions' AS tbl, COUNT(*) AS rows FROM public.campaign_terms_versions
UNION ALL
SELECT 'campaign_terms_acceptances', COUNT(*) FROM public.campaign_terms_acceptances;
-- 기대: 1행 / 0행

SELECT routine_name FROM information_schema.routines
 WHERE routine_schema='public'
   AND routine_name IN (
       'check_campaign_consent','accept_campaign_terms',
       'update_my_guardian_info','get_my_guardian_info')
 ORDER BY routine_name;
-- 기대: 4행

-- 끝.
