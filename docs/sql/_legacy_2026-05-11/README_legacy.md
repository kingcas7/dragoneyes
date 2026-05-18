# DragonEyes v2.1 Phase 6~8 마이그레이션 가이드

## 📋 목적

비즈니스 모델을 정확히 반영한 데이터 구조 도입:

1. **partners** (영업 파트너스) + **customers** (모니터링 고객) 테이블 분리
2. **user_groups** 매핑 테이블로 6개 역할 명확화
3. 같은 법인이 양쪽에 등록 가능 (별도 ID, 별도 계약, 사업자번호로 추적)
4. 모든 대리점에 데모 모니터링 1seat 자동 부여
5. RLS 정책 정식화로 권한 격리

## 🎯 해결되는 문제

- ✅ 황철희가 본부 직원 + 다른 파트너 정보 노출되는 보안 이슈
- ✅ 정희영이 향후 모니터링 계약 추가 시 → "포유솔루션(모니터링)" 별도 등록 가능
- ✅ 로그인 후 user_profile 튕기는 라우팅 버그 (`get_user_home_page()`)
- ✅ 권한 라벨 매핑 버그 (정미옥 admin → "일반사용자")
- ✅ partners.user_id "미연결" 표시 문제 (user_groups로 대체)

## 📦 파일

```
phase6_tables.sql  — customers/user_groups 테이블 + partners 확장 + 함수 6개
phase7_seed.sql    — 기존 10명 user_groups 시딩 (검증 포함)
phase8_rls.sql     — RLS 정책 (8-A ~ 8-E, 단계별!)
README.md          — 이 파일
```

## ⚠️ 사전 체크리스트

- [ ] Phase 5 레거시 DROP은 **이후로 미룸** (이번 작업과 분리)
- [ ] Supabase Dashboard 백업 활성
- [ ] partners 현재 정책 백업: `SELECT * FROM pg_policies WHERE tablename='partners';`
- [ ] Streamlit 종료 가능한 시간

## 🚀 실행 순서

### 1️⃣ Phase 6: 테이블 생성 (안전, 10분)

Supabase SQL Editor에서 `phase6_tables.sql` 전체 실행.

**검증 (파일 끝부분 자동):**
- customers / user_groups 테이블 존재
- partners.demo_monitoring_seats / demo_seats_used 컬럼 추가
- user_groups 제약 4개 (UNIQUE + CHECK 3개)
- 함수 6개 (get_user_home_page 등)
- VIEW user_groups_resolved

### 2️⃣ Phase 7: 시딩 (안전, 5분)

`phase7_seed.sql` 전체 실행.

**검증:**
- 총 10행 INSERT
- 그룹별: hq_admin 4, hq_member 3, partner_admin 3
- 라우팅 함수 → 전원 partner_dashboard
- partners 데모 seats=1

❌ 실패 시: `DELETE FROM user_groups;` 로 롤백

### 3️⃣ Phase 8: RLS 정식화 (위험! 단계별)

⚠️ **한 번에 다 실행하지 말고 Step별로 끊어서 검증**

#### Step 8-A: partners 신규 정책 추가

```
8-A 블록만 복사 → 실행 → Streamlit 재시작 → 좋아요님 로그인 → partners 화면 정상 확인
```

화면 깨지면: 파일 내 "8-A 롤백" 실행.

#### Step 8-B: partners allow_all_temp 제거 (격리 시작)

⚠️ 가장 위험.

```
8-B 블록 실행 → 즉시 검증:
- 좋아요님: partners 2개 다 보임
- 정희영: 포유솔루션만
- 황철희: 오뚜기만 ← 핵심!
```

#### Step 8-C: users 격리

```
8-C 블록 → 검증:
- 황철희: 본인 1명만
- 정희영: 정희영+정다운 2명
- 좋아요님: 10명 다
```

#### Step 8-D: customers RLS (테이블 비어있어도 미리 적용)

```
8-D 블록 → 검증 (현재 customers 0개라 기능적 영향 없음)
```

#### Step 8-E: user_groups RLS

```
8-E 블록 → 검증:
- 좋아요님 로그인 정상
- 황철희: 본인 user_group만
```

## 🛡️ 긴급 롤백

좋아요님 본인이 로그인 안 되는 사태 발생 시 즉시 (phase8_rls.sql 끝부분):

```sql
BEGIN;
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_groups DISABLE ROW LEVEL SECURITY;
ALTER TABLE customers DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS partners_select_by_role ON partners;
DROP POLICY IF EXISTS partners_modify_hq_admin ON partners;
DROP POLICY IF EXISTS partners_update_hq_admin ON partners;
DROP POLICY IF EXISTS partners_delete_hq_admin ON partners;
CREATE POLICY allow_all_temp ON partners FOR ALL USING (true) WITH CHECK (true);
COMMIT;
```

→ 5/10 상태로 회귀.

## 📊 적용 후 예상 상태

| 사용자 | group_type | 보이는 화면 |
|---|---|---|
| 좋아요님/정미옥/김우주/박광남 | hq_admin | 전체 |
| 이성용/하민호/팀원3 | hq_member | 전체 (조회만) |
| 정희영/정다운 | partner_admin | 포유솔루션 + 본인 |
| 황철희 | partner_admin | 오뚜기 + 본인 |

## 📝 SQL 적용 후 별도 작업 (app.py)

DB만 바뀌어도 격리는 작동하지만, UI 완성도 위해 4가지 추가:

1. **권한 라벨 매핑 수정** (`get_user_groups_resolved()` 호출하도록)
2. **메뉴 분기** (`user_is_hq_staff()` 호출, 황철희에게 관리자 메뉴 숨김)
3. **홈페이지 라우팅** (`get_user_home_page()` 호출, user_profile 튕김 해결)
4. **데모 모드 토글** (partner_admin/member 화면에 🎬 데모 모드 토글 추가)

이 4개는 SQL 적용 후 별도 app.py 패치 단계로.

## 향후 추가 작업 (다음 주 이후)

- 파트너관리자 대시보드 8개 카드 기능 구현
- 데모 모니터링 UI 구현 (드래곤파더 챗봇 + 자동추천)
- customers 등록 UI 신설
- Phase 5 레거시 (agencies/agency_tenants) DROP
- partner_customers / licenses / 기타 테이블 RLS (Step 8-F)

## 작성 이력

- 2026-05-11 - 좋아요님과 8회 합의 후 최종안 작성
  - 3개 테이블 분리 확정
  - 6개 group_type 확정
  - 같은 법인 양쪽 등록 가능 (사업자번호 추적)
  - 대리점 자동 데모 1seat
  - 옵션 B (동일 로그인 토글 전환)
