# DragonEyes Privacy Operations Manual v1

> **이 문서는 무엇인가?**
> 
> 이건 **인수인계 문서가 아닙니다**. 좋아요님(최승현)이 본부 임원으로서 **직접 운영하는 매뉴얼**입니다.  
> 보안 엔지니어 합류 전까지 이 문서대로 운영하시고, 합류 후에는 이 문서를 출발점으로 그분이 보완하실 수 있게 작성했습니다.
> 
> **사용법**:
> - 매주 월요일: 섹션 4 (일상 운영 체크리스트) 확인
> - 새 보호조치 시행 시: 섹션 3 매뉴얼 따라 실행 + 보호조치 이력 페이지에 기록
> - 사고 발생 시: 섹션 5 (사고 대응) 즉시 실행
> - 보안 엔지니어 합류 시: 섹션 6 (우선순위) 함께 검토
>
> **버전 정보**
> - 문서 버전: v1.0
> - 작성일: 2026-05-10
> - 작성자: 최승현 (4U Solution)
> - 위치: `~/dragoneyes/docs/DragonEyes_Privacy_Operations_v1.md`
> - 관련 문서: `DragonEyes_System_Design_v2.md`

---

## 목차

- [1. 현재 상태 — 우리가 이미 하고 있는 것](#1-현재-상태--우리가-이미-하고-있는-것)
- [2. 즉시 시행 — 오늘/이번주 P0](#2-즉시-시행--오늘이번주-p0)
- [3. 단계별 실행 매뉴얼](#3-단계별-실행-매뉴얼)
- [4. 일상 운영 체크리스트](#4-일상-운영-체크리스트)
- [5. 사고 대응 매뉴얼](#5-사고-대응-매뉴얼)
- [6. 보안 엔지니어 합류 시 우선순위](#6-보안-엔지니어-합류-시-우선순위)
- [부록 A: 실행 가능 SQL 모음](#부록-a-실행-가능-sql-모음)
- [부록 B: 컴플라이언스 매핑](#부록-b-컴플라이언스-매핑)

---

## 1. 현재 상태 — 우리가 이미 하고 있는 것

### 1.1 시행 완료 조치 (5/5 푸시 + 5/7 + 5/10 작업 기준)

이 목록은 **컴플라이언스 증빙용**입니다. 사고 발생 시 "당시 최선의 조치를 했다"는 근거가 됩니다.

#### 접근 통제

| # | 조치 | 시행일 | 증거 |
|---|---|---|---|
| 1 | Supabase Auth 기반 인증 | 시스템 도입 시 | Supabase 설정 |
| 2 | 역할 기반 접근 통제 (RBAC) | 시스템 도입 시 | users.role 컬럼 |
| 3 | 5-Layer 권한 필터 | 5/5 | commit d01dcc7 |
| 4 | agency_admin 권한 격리 버그 수정 | 5/7 | git log |
| 5 | Soft Delete 사용자 필터링 | 5/10 | app.py 5440번 줄 |
| 6 | 권한 라벨 명확화 (관리자/일반회원) | 5/7 | git log |

#### 보안 감사

| # | 조치 | 시행일 | 증거 |
|---|---|---|---|
| 7 | 다운로드 감사 로그 (7곳 + 14번째 admin 탭) | 5/5 | commit d01dcc7 |
| 8 | 보안 가드 3페이지 | 5/5 | commit d01dcc7 |

#### 데이터 무결성

| # | 조치 | 시행일 | 증거 |
|---|---|---|---|
| 9 | Soft Delete 정책 | 5/10 | users.deleted_at |
| 10 | Foreign Key 제약 (32개) | 시스템 도입 시 | DB 스키마 |
| 11 | Supabase RLS 재활성화 | 5/10 | SQL log |
| 12 | DB 정합성 정리 (analyzed_urls 232→6, learned_keywords) | 5/5 | SQL log |

#### 콘텐츠 보안 (NCMEC 표준)

| # | 조치 | 시행일 | 증거 |
|---|---|---|---|
| 13 | 키워드 거부 필터 | 5/5 | commit d01dcc7 |
| 14 | NCMEC 표준 자동추천 모니터링 | 5/5 | commit d01dcc7 |
| 15 | 자동 위험도 분류 검증 (일반 11/16, Roblox 25/27) | 5/6 | 모니터링 결과 |

#### 인프라 보안

| # | 조치 | 시행일 | 증거 |
|---|---|---|---|
| 16 | API 키 정기 회전 (YouTube, Anthropic) | 5/6 | Railway env |
| 17 | Supabase 자동 백업 | 시스템 도입 시 | Supabase Pro |
| 18 | HTTPS 전구간 적용 | 시스템 도입 시 | Streamlit + Supabase |
| 19 | Railway 환경변수 분리 | 시스템 도입 시 | Railway 설정 |

#### 개인정보 처리

| # | 조치 | 시행일 | 증거 |
|---|---|---|---|
| 20 | 이메일 동의 UI | 5/5 | commit d01dcc7 |
| 21 | 개인정보보호법 준수 설계 | 시스템 도입 시 | 시스템 전체 |

### 1.2 현재 미흡한 부분 (정직한 평가)

이 목록은 **자기 진단**입니다. 보완 계획은 섹션 2~3에서 다룹니다.

| # | 미흡 영역 | 영향 |
|---|---|---|
| M1 | 분리 동의 미구현 (체크박스 1개로 통합) | 개인정보보호법 위반 가능성 |
| M2 | 유관기관 제공 동의 별도 미수령 | 제17조 위반 가능성 |
| M3 | 민감정보 (장애정보) 명시 동의 미수령 | 제23조 위반 가능성 |
| M4 | 민감 컬럼 암호화 미적용 | 사고 시 정보 노출 |
| M5 | MFA 미적용 | 계정 탈취 위험 |
| M6 | 세션 타임아웃 미적용 | 무단 접근 위험 |
| M7 | 자동 삭제 정책 미적용 | 보존 기간 초과 데이터 누적 |
| M8 | 비정상 접근 탐지 미구현 | 사고 발생 시 늦은 인지 |

→ 이걸 한꺼번에 해결할 수는 없습니다. **섹션 2의 P0부터 순차 실행**하세요.

---

## 2. 즉시 시행 — 오늘/이번주 P0

### 2.1 오늘 할 것 (총 25분)

#### P0-1: service_role 키 코드 노출 점검 (10분)

```bash
cd ~/dragoneyes

# service_role 키가 코드에 박혀있는지 확인
grep -rn "service_role" --include="*.py" --include="*.js" --include="*.env*" .
grep -rn "SUPABASE_SERVICE_ROLE" --include="*.py" .

# .env 파일이 .gitignore에 있는지 확인
cat .gitignore | grep -E "\.env"

# git에 .env가 커밋된 적 있는지 확인 (위험)
git log --all --full-history -- .env 2>/dev/null
```

**기대 결과**:
- service_role 키는 환경변수에서만 읽음 (`os.environ.get("SUPABASE_SERVICE_ROLE_KEY")`)
- .env 파일은 git에서 제외됨

**문제 발견 시**:
- 키가 하드코딩 → 즉시 환경변수로 이전 + 키 회전
- .env가 git에 있음 → 즉시 키 회전 + git 히스토리에서 제거

#### P0-2: 백업 스키마 권한 잠금 (5분)

Supabase SQL Editor에서 실행:

```sql
-- 5/10 생성한 백업 스키마 보호
REVOKE ALL ON SCHEMA backup_20260510 FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA backup_20260510 FROM PUBLIC;

-- postgres 슈퍼유저만 접근 가능
GRANT USAGE ON SCHEMA backup_20260510 TO postgres;
GRANT SELECT ON ALL TABLES IN SCHEMA backup_20260510 TO postgres;

-- 검증
SELECT 
    schemaname,
    has_schema_privilege('authenticated', schemaname, 'USAGE') AS auth_can_use,
    has_schema_privilege('anon', schemaname, 'USAGE') AS anon_can_use
FROM pg_namespace
WHERE nspname LIKE 'backup_%';
-- 모두 false여야 정상
```

#### P0-3: Supabase MFA 활성화 (10분)

본부 임원(super_admin) 계정부터 적용:

1. Supabase Dashboard → Authentication → Multi-Factor Authentication
2. TOTP 활성화
3. 본인 계정에 인증앱 (Google Authenticator, Authy 등) 등록
4. 백업 코드 안전한 곳에 보관

→ Director, 운영팀 합류 시 동일 절차 적용 강제.

### 2.2 이번주 할 것

#### P0-4: 세션 타임아웃 코드 추가 (30분, 다음 작업일)

`app.py`에 추가:

```python
import streamlit as st
from datetime import datetime, timedelta

# 상수
SESSION_IDLE_TIMEOUT_MINUTES = 30   # 30분 무활동 시 로그아웃
ABSOLUTE_SESSION_HOURS = 8           # 8시간 후 재로그인 강제

def check_session_validity():
    """페이지 진입 시 첫 줄에 호출."""
    
    # 처음 로그인 시 시간 저장
    if 'login_time' not in st.session_state:
        st.session_state['login_time'] = datetime.now()
        st.session_state['last_activity'] = datetime.now()
        return
    
    now = datetime.now()
    
    # 무활동 체크
    idle_seconds = (now - st.session_state['last_activity']).total_seconds()
    if idle_seconds > SESSION_IDLE_TIMEOUT_MINUTES * 60:
        force_logout("30분 동안 활동이 없어 자동 로그아웃되었습니다.")
        return
    
    # 절대 시간 체크
    session_seconds = (now - st.session_state['login_time']).total_seconds()
    if session_seconds > ABSOLUTE_SESSION_HOURS * 3600:
        force_logout("보안을 위해 재로그인이 필요합니다.")
        return
    
    # 활동 시간 갱신
    st.session_state['last_activity'] = now

def force_logout(message: str):
    """세션 정리 + 로그인 페이지로."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.warning(message)
    st.rerun()
```

각 페이지 진입 시 첫 줄에 `check_session_validity()` 호출.

#### P0-5: 개인정보 보호조치 이력 페이지 신규 (2시간, 다음주)

상세 SQL은 부록 A 참조. 신규 페이지 한 개 추가하는 작업입니다.

---

## 3. 단계별 실행 매뉴얼

### 3.1 보호조치 이력 페이지 도입

#### Step 1: privacy_protection_activities 테이블 생성

```sql
BEGIN;

CREATE TABLE public.privacy_protection_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    activity_date DATE NOT NULL,
    activity_title TEXT NOT NULL,
    activity_category TEXT NOT NULL,
    -- 'access_control' | 'audit_logging' | 'encryption' 
    -- | 'authentication' | 'data_minimization' | 'consent_management'
    -- | 'incident_response' | 'vulnerability_patch' | 'policy_update'
    -- | 'training' | 'audit_inspection' | 'compliance_alignment'
    
    description TEXT NOT NULL,
    motivation TEXT,
    legal_basis TEXT,
    
    affected_systems TEXT[],
    affected_user_count INT,
    
    evidence_type TEXT,
    evidence_reference TEXT,
    evidence_url TEXT,
    
    implemented_by_user_id UUID REFERENCES users(id),
    implemented_by_name TEXT,
    implemented_by_role TEXT,
    
    verified_by_user_id UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    verification_method TEXT,
    verification_notes TEXT,
    
    activity_status TEXT DEFAULT 'completed',
    
    superseded_by_activity_id UUID REFERENCES privacy_protection_activities(id),
    related_incident_id UUID,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    severity_level TEXT,
    tags TEXT[]
);

CREATE INDEX idx_priv_act_date ON privacy_protection_activities(activity_date DESC);
CREATE INDEX idx_priv_act_category ON privacy_protection_activities(activity_category);
CREATE INDEX idx_priv_act_severity ON privacy_protection_activities(severity_level);
CREATE INDEX idx_priv_act_tags ON privacy_protection_activities USING gin(tags);

-- 본부 임원 + Director + 운영팀만 접근
ALTER TABLE privacy_protection_activities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "privacy_log_admin_only"
ON privacy_protection_activities
FOR ALL TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users u
        LEFT JOIN hq_staff_capabilities cap ON cap.user_id = u.id AND cap.revoked_at IS NULL
        WHERE u.email = auth.email()
          AND u.deleted_at IS NULL
          AND (
              u.role = 'super_admin'
              OR cap.capability IN ('director', 'ops_review')
          )
    )
);

-- append-only (수정·삭제 금지)
REVOKE UPDATE, DELETE ON privacy_protection_activities FROM PUBLIC;
REVOKE UPDATE, DELETE ON privacy_protection_activities FROM authenticated;

COMMIT;
```

#### Step 2: 기존 조치 21개 일괄 등록

```sql
-- 섹션 1.1의 모든 조치를 이 테이블에 등록
-- 향후 사고 시 컴플라이언스 증빙 자료가 됨

INSERT INTO privacy_protection_activities (
    activity_date, activity_title, activity_category,
    description, legal_basis,
    implemented_by_name, evidence_type, evidence_reference,
    severity_level, tags
) VALUES
('2026-05-05', '5-Layer 권한 필터 도입', 'access_control',
 'app.py 사용자 관리 페이지에 5-Layer 권한 필터 적용',
 '개인정보보호법 제29조 (안전성 확보 조치)',
 '최승현', 'commit_hash', 'd01dcc7',
 'high', ARRAY['권한필터', 'RBAC']),

('2026-05-05', '다운로드 감사 로그 (7곳 + admin 탭)', 'audit_logging',
 '민감 자료 다운로드 추적 시스템 구축',
 '개인정보보호법 제29조',
 '최승현', 'commit_hash', 'd01dcc7',
 'high', ARRAY['감사로그', '다운로드']),

-- ... 나머지 19개도 동일 패턴
('2026-05-10', 'user_documents RLS 재활성화', 'access_control',
 '5/7 데모용 비활성화 RLS 정책 재적용',
 '개인정보보호법 제29조',
 '최승현', 'sql_log', '2026-05-10 11:23',
 'high', ARRAY['RLS', '재활성화']);
```

#### Step 3: Streamlit 페이지 추가

`pages/14_개인정보_보호조치.py` 신규 생성:

```python
import streamlit as st
from datetime import datetime
from supabase_client import supabase
from auth_helpers import check_session_validity, get_current_user

check_session_validity()
user = get_current_user()

# 권한 검증 (DB RLS와 별개로 UI에서도 차단)
if not (
    user.role == 'super_admin' 
    or user.has_capability('director')
    or user.has_capability('ops_review')
):
    st.error("이 페이지는 본부 임원, Director, 운영팀만 접근 가능합니다.")
    st.stop()

st.title("🔒 개인정보 보호조치 이력")
st.caption("DragonEyes가 시행한 모든 개인정보 보호 조치 기록")

# 메트릭 카드
col1, col2, col3, col4 = st.columns(4)
total = supabase.table("privacy_protection_activities").select("id", count="exact").execute()
recent = supabase.table("privacy_protection_activities").select("id", count="exact") \
    .gte("activity_date", (datetime.now() - timedelta(days=30)).date()) \
    .execute()

with col1: st.metric("총 조치", total.count)
with col2: st.metric("최근 30일", recent.count)
with col3: st.metric("검증 대기", "...")
with col4: st.metric("법적 근거 매핑", "100%")

# 필터
category = st.selectbox("카테고리", 
    ["전체", "접근 통제", "감사 로그", "암호화", "인증", "사고 대응", "취약점 패치"])
search = st.text_input("제목·태그 검색")

# 신규 등록 버튼 (펼침)
with st.expander("+ 신규 보호조치 등록"):
    new_title = st.text_input("제목")
    new_date = st.date_input("시행일", datetime.now().date())
    new_category = st.selectbox("카테고리", [...])
    new_desc = st.text_area("설명")
    new_legal = st.text_input("법적 근거", "개인정보보호법 제29조")
    new_evidence = st.text_input("증거 (commit hash 등)")
    new_tags = st.text_input("태그 (쉼표 구분)")
    
    if st.button("등록"):
        supabase.table("privacy_protection_activities").insert({
            "activity_title": new_title,
            "activity_date": new_date.isoformat(),
            "activity_category": new_category,
            "description": new_desc,
            "legal_basis": new_legal,
            "evidence_reference": new_evidence,
            "tags": [t.strip() for t in new_tags.split(",") if t.strip()],
            "implemented_by_user_id": user.id,
            "implemented_by_name": user.name,
            "implemented_by_role": user.role
        }).execute()
        st.success("등록되었습니다.")
        st.rerun()

# 카드 리스트
records = supabase.table("privacy_protection_activities") \
    .select("*") \
    .order("activity_date", desc=True) \
    .limit(20).execute()

for r in records.data:
    with st.container(border=True):
        cols = st.columns([1, 6, 1])
        with cols[0]:
            st.caption(r['activity_category'])
            st.caption(r['activity_date'])
        with cols[1]:
            st.markdown(f"**{r['activity_title']}**")
            st.caption(r['description'])
            if r.get('legal_basis'):
                st.caption(f"📌 {r['legal_basis']}")
        with cols[2]:
            st.caption(r.get('implemented_by_name', '-'))
```

### 3.2 동의 시스템 도입 (4-Layer)

> ⚠️ 이 작업은 분량이 커서 **다음주 별도 일정**으로 진행하세요. 시스템 설계서 v2 마이그레이션 끝난 후.

#### 4-Layer 개요

| Layer | 동의 종류 | 시점 | 증거 강도 |
|---|---|---|---|
| 1 | 기본 가입 (수집·이용 + 민감정보) | 회원가입 | 체크박스 + IP + timestamp |
| 2 | 유관기관 매핑 (제3자 제공) | 사용자 자발 옵트인 | 약관 스냅샷 + 서명패드 |
| 3 | 민감정보 제공 (장애정보) | 서비스 활성화 | 명시적 동의 화면 + 서명 |
| 4 | 서류 작성 위임 (법률행위) | 위임 시 | 전자서명 (KISA) + 본인인증 |

상세 SQL은 부록 A 참조. UI는 시스템 설계서 섹션 7.2 참조.

#### 기존 사용자 재동의 캠페인

Layer 2~3 도입 시 **기존 사용자 전원에게 재동의 요청**이 필요할 수 있습니다.

```
1. 신규 약관 게시 (시행 30일 전 공지)
2. 사용자에게 이메일 + 시스템 알림
3. 다음 로그인 시 재동의 화면 강제 표시
4. 30일 내 미동의 사용자 → 서비스 일시 제한 안내
5. 90일 내 미동의 → 데이터 익명화 또는 삭제
```

이 캠페인은 **법무 자문 후** 진행하세요. 약관 본문이 법적 효력을 가져야 합니다.

---

## 4. 일상 운영 체크리스트

### 4.1 매일 (5분)

| 항목 | 확인 방법 |
|---|---|
| 비정상 로그인 시도 | Supabase Auth Dashboard → Logs |
| 대량 다운로드 | download_logs 테이블 최근 24시간 조회 |
| 시스템 에러 | Railway logs |

### 4.2 매주 월요일 (15분)

```sql
-- 1) 지난 주 다운로드 활동 요약
SELECT 
    DATE(created_at) AS date,
    COUNT(*) AS download_count,
    COUNT(DISTINCT user_id) AS unique_users
FROM download_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- 2) 신규 사용자 / 권한 변경
SELECT 
    email, name, role, partner_id, customer_id, created_at
FROM users
WHERE created_at >= NOW() - INTERVAL '7 days'
   OR updated_at >= NOW() - INTERVAL '7 days'
ORDER BY updated_at DESC;

-- 3) 보호조치 이력 등록 누락 점검
-- 지난 주 commit이 있는데 이력에 없으면 등록
```

### 4.3 매월 첫째주 (30분)

| 항목 | 작업 |
|---|---|
| 사용자 정리 | 휴면 90일+ 사용자 식별, 본인 확인 후 정리 |
| 권한 점검 | hq_assignments, hq_staff_capabilities 적정성 확인 |
| 동의 만료 점검 | consent_records.expires_at 만료 임박 사용자 알림 |
| 백업 검증 | Supabase 자동 백업 정상 여부 확인 |

### 4.4 분기별 (1일)

| 항목 | 작업 |
|---|---|
| API 키 회전 | YouTube, Anthropic, Supabase publishable, Naver |
| 보호조치 이력 점검 | 누락 항목 보강, 검증 |
| 컴플라이언스 정합성 | 새 법령·가이드라인 확인 |
| 외부 자문 (선택) | 변호사·CPO 자문 |

---

## 5. 사고 대응 매뉴얼

### 5.1 사고 유형별 대응

#### Type A: 데이터 노출 의심 (가장 심각)

```
1. [즉시] 의심 행위 차단
   - 의심 사용자 계정 일시 정지
   - 의심 IP 차단

2. [1시간 내] 영향 범위 평가
   - 어떤 데이터가 노출됐나?
   - 몇 명이 영향받았나?
   - 외부 유출 흔적이 있나?

3. [24시간 내] 신고 의무 이행
   - 개인정보보호위원회 신고
   - 영향받은 사용자에게 통지

4. [1주 내] 근본 원인 분석
   - 보호조치 이력 페이지에 사고 기록
   - 재발 방지 조치 시행

5. [1개월 내] 보고서 작성
   - 외부 보고용 사고 보고서
   - 보호조치 이력에 첨부
```

#### Type B: 계정 탈취

```
1. [즉시] 해당 계정 비밀번호 강제 변경
2. [즉시] 해당 계정의 최근 활동 추적
3. [1시간 내] 다른 사용자 영향 평가
4. [24시간 내] 본인 통지 + 보호조치 이력 등록
```

#### Type C: 권한 오용 (내부)

```
1. [즉시] 해당 사용자 권한 회수 (Soft Delete)
2. [1시간 내] 영향 범위 평가
3. [1일 내] 인사 조치 결정
4. [1주 내] 보호조치 이력에 기록 (익명 처리)
```

### 5.2 사고 시 보존해야 할 증거

```sql
-- 사고 의심 시 즉시 스냅샷
CREATE TABLE incident_snapshots.YYYYMMDD_incident_name AS
SELECT * FROM access_audit_log 
WHERE created_at >= [의심 시점 - 7일];

-- download_logs도 동일 패턴
-- approval_audit_log도 동일 패턴
```

### 5.3 신고 의무 (개인정보보호법 제34조)

| 사고 규모 | 신고 의무 | 시한 |
|---|---|---|
| 1만명 이상 노출 | 개인정보보호위원회 + 사용자 통지 | 72시간 내 |
| 그 외 | 사용자 통지 | 지체 없이 |
| 법 위반 발견 | 자진 신고 권장 | - |

---

## 6. 보안 엔지니어 합류 시 우선순위

### 6.1 첫 1주: 현황 파악

이 문서 + 시스템 설계서 v2 + 보호조치 이력 페이지를 함께 검토.

### 6.2 1개월 내 우선 보강

| # | 항목 | 사유 |
|---|---|---|
| 1 | pgcrypto + 민감 컬럼 암호화 (보호자 정보, 장애 정보) | 사고 시 정보 노출 방지 |
| 2 | 키 관리 시스템 (KMS) 도입 | 키 회전 자동화 |
| 3 | access_audit_log 자동 등록 | 모든 민감 데이터 접근 추적 |
| 4 | 비정상 접근 탐지 | 한 사용자가 1초에 100건 조회 등 |

### 6.3 3개월 내 보강

| # | 항목 |
|---|---|
| 5 | 보안 감사 외부 의뢰 |
| 6 | 개인정보 영향평가 (PIA) |
| 7 | 4-Layer 동의 시스템 본격 도입 (이미 시작했다면 검수) |
| 8 | 침투 테스트 (Pen-Test) |

### 6.4 6개월+

| # | 항목 |
|---|---|
| 9 | ISO 27001 인증 검토 |
| 10 | 서류 작성 대행 비즈니스 (Layer 4) 보안 인프라 |
| 11 | 전자서명 (KISA 인증) 통합 |

### 6.5 보안 엔지니어가 받을 자료 패키지

합류 첫날 다음을 전달:

1. 이 문서 (`DragonEyes_Privacy_Operations_v1.md`)
2. 시스템 설계서 (`DragonEyes_System_Design_v2.md`)
3. 보호조치 이력 페이지 (DB 데이터 직접 확인)
4. 현재 코드베이스 git access
5. Supabase Dashboard 접근 권한 (별도 계정)
6. Railway Dashboard 접근 권한
7. 미해결 보안 백로그 (시스템 설계서 부록 B.3)

---

## 부록 A: 실행 가능 SQL 모음

### A.1 consent_types 마스터 테이블

```sql
CREATE TABLE public.consent_types (
    id TEXT PRIMARY KEY,
    
    category TEXT NOT NULL,
    -- 'collection_use' | 'third_party_provision' | 'processing_delegation'
    -- | 'sensitive_info' | 'overseas_transfer' | 'marketing' | 'delegation_of_acts'
    
    title TEXT NOT NULL,
    legal_basis TEXT,
    is_required BOOLEAN NOT NULL,
    is_sensitive BOOLEAN DEFAULT false,
    
    data_items JSONB,
    purpose JSONB,
    retention_period TEXT,
    third_party_recipients JSONB,
    
    consent_text_template TEXT NOT NULL,
    minimum_age INT DEFAULT 14,
    
    version TEXT NOT NULL,
    effective_from DATE NOT NULL,
    superseded_by TEXT REFERENCES consent_types(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 초기 데이터
INSERT INTO consent_types (id, category, title, legal_basis, is_required, is_sensitive, version, effective_from, consent_text_template) VALUES
('collect_basic_v1', 'collection_use', 
 '필수: 개인정보 수집·이용 동의', 
 '개인정보보호법 제15조', true, false,
 '1.0', '2026-06-01', 
 '[수집 항목] 이름, 이메일, 전화번호 ...'),

('sensitive_disability_v1', 'sensitive_info',
 '필수: 장애 정보 처리 동의 (민감정보)',
 '개인정보보호법 제23조', true, true,
 '1.0', '2026-06-01',
 '[수집 항목] 장애유형, 장애등급 ...'),

('related_org_provision_v1', 'third_party_provision',
 '선택: 유관기관 제공 동의',
 '개인정보보호법 제17조', false, false,
 '1.0', '2026-06-01',
 '[제공 받는 자] 사용자가 지정한 유관기관 ...'),

('related_org_sensitive_v1', 'third_party_provision',
 '선택: 유관기관에 장애정보 제공',
 '개인정보보호법 제17조 + 제23조', false, true,
 '1.0', '2026-06-01',
 '[제공 항목] 장애유형, 장애등급 ...'),

('document_delegation_v1', 'delegation_of_acts',
 '선택: 서류 작성·제출 위임',
 '민법 제680조 (위임)', false, false,
 '1.0', '2026-06-01',
 '[위임 범위] 본인이 지정한 서류에 한함 ...');
```

### A.2 consent_records 트랜잭션 테이블

```sql
CREATE TABLE public.consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    consent_giver_user_id UUID REFERENCES users(id),
    consent_giver_role TEXT,
    
    consent_method_subject TEXT,
    -- 'self' | 'guardian' | 'legal_guardian'
    guardian_user_id UUID REFERENCES users(id),
    guardian_relationship TEXT,
    guardian_evidence_url TEXT,
    
    consent_type_id TEXT REFERENCES consent_types(id),
    
    target_partner_id UUID REFERENCES partners(id),
    target_customer_id UUID REFERENCES customers(id),
    target_external_org TEXT,
    
    consent_scope JSONB NOT NULL,
    consent_text_snapshot TEXT NOT NULL,
    consent_version TEXT NOT NULL,
    
    consented_at TIMESTAMPTZ DEFAULT NOW(),
    consent_method TEXT NOT NULL,
    -- 'web_checkbox' | 'web_signature' | 'electronic_signature'
    -- | 'paper_signed_scanned' | 'email_reply' | 'sms_otp'
    consent_evidence_url TEXT,
    
    ip_address INET,
    user_agent TEXT,
    device_fingerprint TEXT,
    
    revoked_at TIMESTAMPTZ,
    revoked_by_user_id UUID REFERENCES users(id),
    revoke_reason TEXT,
    revoke_method TEXT,
    
    expires_at TIMESTAMPTZ,
    
    renewed_from_consent_id UUID REFERENCES consent_records(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_consent_giver ON consent_records(consent_giver_user_id);
CREATE INDEX idx_consent_active ON consent_records(consent_type_id, consent_giver_user_id) 
    WHERE revoked_at IS NULL AND (expires_at IS NULL OR expires_at > NOW());
CREATE INDEX idx_consent_target_partner ON consent_records(target_partner_id) 
    WHERE revoked_at IS NULL;

REVOKE UPDATE, DELETE ON consent_records FROM PUBLIC;
REVOKE UPDATE, DELETE ON consent_records FROM authenticated;
```

### A.3 동의 검증 함수

```sql
CREATE OR REPLACE FUNCTION check_consent_active(
    p_user_id UUID,
    p_consent_type_id TEXT,
    p_target_partner_id UUID DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM consent_records
        WHERE consent_giver_user_id = p_user_id
          AND consent_type_id = p_consent_type_id
          AND (target_partner_id = p_target_partner_id OR p_target_partner_id IS NULL)
          AND revoked_at IS NULL
          AND (expires_at IS NULL OR expires_at > NOW())
    );
END;
$$ LANGUAGE plpgsql STABLE;
```

### A.4 위임 시스템 (서류 대행 비즈니스용)

```sql
CREATE TABLE public.document_delegations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    delegator_user_id UUID REFERENCES users(id),
    delegator_consent_record_id UUID REFERENCES consent_records(id),
    
    delegatee_partner_id UUID REFERENCES partners(id),
    delegatee_user_id UUID REFERENCES users(id),
    
    delegation_scope JSONB NOT NULL,
    -- {
    --   "document_types": ["고용장려금 신청서"],
    --   "submission_targets": ["한국장애인고용공단"],
    --   "max_documents_per_month": 5,
    --   "requires_user_review_before_submit": true
    -- }
    
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    
    electronic_signature_data TEXT NOT NULL,
    signature_certificate_info JSONB,
    signed_at TIMESTAMPTZ NOT NULL,
    
    delegation_document_url TEXT NOT NULL,
    document_hash TEXT NOT NULL,
    
    identity_verification_method TEXT NOT NULL,
    -- 'pass_app' | 'public_cert' | 'finance_cert' | 'notarized_paper'
    identity_verification_evidence_url TEXT,
    
    revoked_at TIMESTAMPTZ,
    revoke_reason TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE public.delegated_document_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delegation_id UUID REFERENCES document_delegations(id),
    
    action_type TEXT NOT NULL,
    -- 'created' | 'reviewed_by_user' | 'submitted' | 'rejected_by_authority'
    
    document_type TEXT,
    submission_target TEXT,
    
    user_reviewed_at TIMESTAMPTZ,
    user_review_method TEXT,
    
    performed_by_user_id UUID REFERENCES users(id),
    performed_at TIMESTAMPTZ DEFAULT NOW(),
    
    document_url TEXT,
    submission_receipt_url TEXT,
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

REVOKE UPDATE, DELETE ON document_delegations FROM PUBLIC;
REVOKE UPDATE, DELETE ON document_delegations FROM authenticated;
REVOKE UPDATE, DELETE ON delegated_document_actions FROM PUBLIC;
REVOKE UPDATE, DELETE ON delegated_document_actions FROM authenticated;
```

### A.5 access_audit_log

```sql
CREATE TABLE public.access_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id UUID REFERENCES users(id),
    user_email TEXT,
    user_role TEXT,
    
    accessed_at TIMESTAMPTZ DEFAULT NOW(),
    
    target_type TEXT,
    target_id UUID,
    accessed_columns TEXT[],
    
    action TEXT,
    query_hash TEXT,
    
    ip_address INET,
    user_agent TEXT,
    session_id TEXT,
    
    purpose TEXT,
    
    rows_affected INT,
    success BOOLEAN
);

CREATE INDEX idx_audit_user_time ON access_audit_log(user_id, accessed_at DESC);
CREATE INDEX idx_audit_target ON access_audit_log(target_type, target_id);
CREATE INDEX idx_audit_time ON access_audit_log(accessed_at DESC);

REVOKE UPDATE, DELETE ON access_audit_log FROM PUBLIC;
REVOKE UPDATE, DELETE ON access_audit_log FROM authenticated;
```

### A.6 데이터 보존 정책

```sql
CREATE TABLE public.data_retention_policies (
    target_type TEXT PRIMARY KEY,
    retention_days INT,
    deletion_method TEXT,  -- 'hard_delete' | 'anonymize' | 'archive' | 'retain_forever'
    legal_basis TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO data_retention_policies VALUES
    ('access_audit_log', 1825, 'archive', '개인정보보호법 5년'),
    ('user_resigned', 365, 'anonymize', '계약 종료 후 1년 익명화'),
    ('monitoring_data_personal', 1095, 'anonymize', '3년 후 개인식별 정보 제거'),
    ('analyzed_urls', NULL, 'retain_forever', '시스템 자산 (NCMEC 데이터셋)'),
    ('learned_keywords', NULL, 'retain_forever', '시스템 자산'),
    ('approval_workflows_completed', 2555, 'archive', '계약법 7년'),
    ('consent_records', 1825, 'archive', '개인정보보호법 5년 후 콜드');
```

---

## 부록 B: 컴플라이언스 매핑

### B.1 개인정보보호법 항목별 대응

| 법 조항 | 요구사항 | DragonEyes 대응 |
|---|---|---|
| 제15조 (수집·이용 동의) | 사전 동의 | Layer 1 동의 (consent_records) |
| 제17조 (제3자 제공) | 별도 동의 | Layer 2 동의 (유관기관 매핑) |
| 제22조 (마케팅) | 별도·선택 동의 | 추후 도입 |
| 제23조 (민감정보) | 명시 동의 | Layer 3 동의 (장애정보) |
| 제29조 (안전성 확보) | 기술·관리 조치 | 보호조치 이력 21건 |
| 제30조 (처리방침 공개) | 웹사이트 게시 | (별도 약관 페이지) |
| 제34조 (사고 신고) | 72시간 내 | 사고 대응 매뉴얼 (섹션 5) |

### B.2 NCMEC 표준 대응

| 항목 | 대응 |
|---|---|
| 자동 분류 시스템 | 조치 #14 |
| 위험도 등급 표준화 | 조치 #15 |
| 키워드 필터링 | 조치 #13 |
| 유해 콘텐츠 데이터셋 영구 보존 | data_retention_policies 'retain_forever' |

### B.3 향후 검토 컴플라이언스

| 표준 | 검토 시점 | 사유 |
|---|---|---|
| ISO 27001 | 출시 후 1년 | 정보보안 관리 시스템 |
| ISMS-P | 출시 전 | 정보보호·개인정보 통합 (한국) |
| GDPR | 해외 진출 시 | EU 개인정보 |
| HIPAA | 의료 데이터 도입 시 | 미국 의료 정보 (해당 시) |

---

## 변경 이력

| 버전 | 날짜 | 변경자 | 주요 내용 |
|---|---|---|---|
| v1.0 | 2026-05-10 | 최승현 | 최초 작성 (현재 상태 21건 + 4-Layer 동의 + 보호조치 이력 페이지) |

---

**문서 끝**

> 💡 **다음 액션 (오늘)**:
> 1. 섹션 2.1의 P0-1 (10분), P0-2 (5분), P0-3 (10분) 실행
> 2. 보호조치 이력 등록은 다음 작업일에 일괄 처리
> 3. 이 문서를 `~/dragoneyes/docs/`에 저장하고 git 커밋
