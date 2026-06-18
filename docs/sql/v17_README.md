# DragonEyes v1.7 — 캠페인 시스템 Phase 1 적용 가이드

## 🎯 목적
'온라인 유해컨텐츠 근절 캠페인' 신규 비즈니스 라인을 위한
DB 스키마 8단계 마이그레이션.

대상 사용자: **교육기관 / 학부모 / 학생** (3종)

---

## 📋 적용 순서 (반드시 순서대로)

| # | 파일 | 내용 | 예상 시간 |
|---|------|------|-----------|
| 1 | `v17_001_users_role_extend.sql` | users 테이블 확장 (10개 컬럼 + role_v2 3종 추가) | 10초 |
| 2 | `v17_002_institutions.sql` | institutions + institution_requests + pg_trgm | 20초 |
| 3 | `v17_003_parent_student.sql` | parent_student_links + 자녀 조회 함수 | 10초 |
| 4 | `v17_004_campaigns_materials.sql` | campaigns + materials + access + view_logs | 20초 |
| 5 | `v17_005_surveys.sql` | surveys + questions + responses + answers | 20초 |
| 6 | `v17_006_volunteer_credits.sql` | volunteer_credits + school_volunteer_batches | 15초 |
| 7 | `v17_007_payments.sql` | payment_providers + payments + contracts + subscriptions | 25초 |
| 8 | `v17_008_student_login_guard.sql` | 학생 모니터링 차단 함수 + view + 트리거 | 10초 |

**총 예상 시간 약 2분.**

---

## 🚀 Supabase 대시보드에서 실행하기

1. https://supabase.com/dashboard → 프로젝트 선택
2. 왼쪽 메뉴 → **SQL Editor** 클릭
3. **+ New query** 클릭
4. `v17_001_users_role_extend.sql` 파일을 텍스트 에디터로 열어 전체 복사
5. SQL Editor에 붙여넣기 → 우측 상단 **Run** 클릭
6. 마지막 SELECT의 결과가 **검증 표 기대값과 일치**하는지 확인
7. ✅ 일치하면 다음 파일(`v17_002_*`)로 진행
8. ❌ 에러 발생 시 즉시 멈추고 에러 메시지 공유 (안전을 위해)

---

## ✅ 적용 후 확인할 것들

### users 테이블 신규 컬럼 (총 10개)
- `institution_id` UUID
- `grade` SMALLINT
- `school_name` TEXT
- `birth_date` DATE
- `parent_consent_at` TIMESTAMPTZ
- `parent_consent_by` UUID
- `signup_source` TEXT
- `is_campaign_only` BOOLEAN (NOT NULL default FALSE)
- `notify_phone` TEXT
- `notify_sms_consent` BOOLEAN

### 신규 테이블 (총 14개)
1. `institutions` — 교육기관 마스터
2. `institution_requests` — 등록 신청 큐
3. `parent_student_links` — 학부모↔학생 매칭
4. `campaigns` — 연도별 캠페인
5. `campaign_materials` — 학습 자료
6. `material_access` — 열람 권한
7. `material_view_logs` — 시청 로그
8. `surveys` — 설문지
9. `survey_questions` — 문항
10. `survey_responses` — 응답 헤더
11. `survey_answers` — 개별 답변
12. `volunteer_credits` — 봉사 점수
13. `school_volunteer_batches` — 학교 일괄 발급
14. `payment_providers` — PG 마스터 (4종 기본 등록)
15. `payments` — 통합 결제 로그
16. `institution_contracts` — 기관 계약
17. `parent_subscriptions` — 학부모 연 1만원 구독

### 신규 함수 (총 6개)
- `_set_updated_at()` — updated_at 자동 갱신
- `_enforce_student_campaign_only()` — 학생 강제 is_campaign_only=TRUE
- `get_verified_children(parent_id)` — 학부모의 verified 자녀 목록
- `get_available_surveys_for_student(student_id)` — 학생용 활성 설문
- `get_student_volunteer_summary(student_id)` — 학생 누적 봉사 시간
- `has_active_parent_subscription(parent_id, year)` — 학부모 결제 여부
- `is_campaign_student(user_id)` — 학생 여부
- `can_access_monitoring(user_id)` — 모니터링 접근 가능 여부
- `can_access_monitoring_stats(user_id)` — 통계 접근 가능 여부

### 신규 view
- `v_user_access_summary` — 사용자별 접근 권한 요약

---

## 🔄 롤백

문제가 생기면 다음 SQL로 모두 제거:

```sql
-- ⚠️ 모든 캠페인 데이터 삭제됨 — 운영 데이터 있을 경우 절대 실행 금지!
DROP VIEW IF EXISTS public.v_user_access_summary CASCADE;
DROP FUNCTION IF EXISTS
    public.is_campaign_student,
    public.can_access_monitoring,
    public.can_access_monitoring_stats,
    public.get_verified_children,
    public.get_available_surveys_for_student,
    public.get_student_volunteer_summary,
    public.has_active_parent_subscription,
    public._enforce_student_campaign_only,
    public._set_updated_at CASCADE;

DROP TABLE IF EXISTS
    public.school_volunteer_batches,
    public.volunteer_credits,
    public.survey_answers,
    public.survey_responses,
    public.survey_questions,
    public.surveys,
    public.material_view_logs,
    public.material_access,
    public.campaign_materials,
    public.campaigns,
    public.parent_student_links,
    public.institution_requests,
    public.institution_contracts,
    public.parent_subscriptions,
    public.payments,
    public.payment_providers,
    public.institutions CASCADE;

ALTER TABLE public.users
    DROP COLUMN IF EXISTS institution_id,
    DROP COLUMN IF EXISTS grade,
    DROP COLUMN IF EXISTS school_name,
    DROP COLUMN IF EXISTS birth_date,
    DROP COLUMN IF EXISTS parent_consent_at,
    DROP COLUMN IF EXISTS parent_consent_by,
    DROP COLUMN IF EXISTS signup_source,
    DROP COLUMN IF EXISTS is_campaign_only,
    DROP COLUMN IF EXISTS notify_phone,
    DROP COLUMN IF EXISTS notify_sms_consent;
```

---

## 📊 정책 정리 (사용자 결정 반영)

| 항목 | 정책 |
|------|------|
| **학생** | 무료 / 모니터링 접근 차단 / 통계만 조회 |
| **학부모** | 연 1만원 (전체 유료 자료 무제한 + 자녀 동시 권한 + 다자녀 가능) |
| **교육기관** | 연단위 또는 일괄 계약 (커스텀 금액·기간) |
| **만 14세 미만 학생** | 학부모 사전 동의 필수 |
| **다운로드** | 모든 자료 view-only (storage_url 직접 노출 X) |
| **봉사 점수** | 자체 PDF / 1365 봉사포털 / 학교 일괄 3가지 발급 모드 |
| **설문** | 학교 커스텀 미등록 시 national만, 등록 시 학생이 선택 |
| **PG** | 토스/카카오/이니시스/네이버 4종 기본 등록 (모두 신고 전 비활성) |

---

## ▶ 다음 단계 (Phase 2)

Phase 1 적용 완료 후:
- **Phase 2: 로그인 페이지 재디자인** (모니터링 ↔ 캠페인 분기 UI)
- **Phase 3: 캠페인 홈 라우팅** (기관/학부모/학생 3카드)

진행 전 사용자님과 다시 검토.
