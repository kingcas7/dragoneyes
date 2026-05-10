# DragonEyes 마이그레이션 SQL 실행 가이드

> **다음주 실행을 위한 가이드** — 좋아요님이 순서대로 따라하시면 됩니다.

## 📂 파일 구성

```
sql/
├── phase0_backup.sql           # 1~2분, 백업 스키마 생성
├── phase1_create_tables.sql    # 3~5분, 14개 신규 테이블 생성
└── phase2_migrate_data.sql     # 1~3분, agencies → partners 데이터 복사
```

## 🎯 실행 순서

### 0단계: 사전 준비 (10분)

1. **Supabase Dashboard에서 자동 백업 한 번 더 실행**
   - Database → Backups → Manual Backup
2. **Streamlit 앱 일시 정지** (선택, 안전을 위해)
   ```bash
   # 좋아요님 로컬에서
   lsof -ti:8501 | xargs kill -9
   ```
3. **현재 시스템 상태 스크린샷** (롤백 시 비교용)
   - 사용자 수, agency 수, 다른 데이터 카운트

### 1단계: phase0_backup.sql (5분)

1. 파일 열기
2. **`YYYYMMDD`를 실제 날짜로 변경** (예: `20260517`)
   - 8군데에 있어요 — 모두 같은 날짜로
   - VS Code 또는 텍스트 에디터의 "찾아 바꾸기" 사용
3. Supabase SQL Editor에 복사
4. 메인 BEGIN/COMMIT 블록 먼저 실행 (Run)
5. 검증 쿼리 별도로 실행
6. **모든 검증 통과 확인 후** 다음 단계

### 2단계: phase1_create_tables.sql (10분)

1. Supabase SQL Editor에 복사
2. 메인 BEGIN/COMMIT 블록 실행
3. 검증 쿼리 별도 실행
4. **기대 결과**:
   - 14개 신규 테이블 생성됨
   - users 테이블에 4개 컬럼 추가됨
   - approval_policies에 6개 row 들어감
5. **Streamlit 앱 재시작 → 기존 기능 정상 작동 확인**

### 3단계: phase2_migrate_data.sql (10분)

1. **사전 점검 쿼리 먼저 실행** (READ ONLY)
   - 활성 agencies 수, agency_id 있는 사용자 수 확인
2. 메인 BEGIN/COMMIT 블록 실행
3. 검증 쿼리 별도 실행
4. **모든 검증 통과 확인** (특히 ⓐ ⓑ ⓒ)
5. **Streamlit 앱 재시작 → 기존 기능 정상 작동 확인**

### 4단계: 수동 후속 작업 (30분~1시간)

좋아요님이 직접 결정해야 할 것:

1. **총판 분류**: 어느 agency가 총판이었는지 — 좋아요님만 아심
2. **유관기관 분류**: 어느 agency가 유관기관이었는지
3. **본부 직원 capabilities 등록**: Director, ops_review 권한 부여

→ phase2 파일 맨 아래 "수동 후속 작업" 섹션의 SQL 예시 참고

## 🚨 문제 발생 시

### 어떤 단계에서 에러가 나면

1. **에러 메시지 그대로 보고** (스크린샷)
2. **다음 단계 진행 금지**
3. 이 디렉토리의 메모와 함께 Claude에게 문의

### 롤백이 필요하면

각 파일 맨 아래에 ROLLBACK 섹션이 있습니다:
- Phase 2 롤백: 데이터만 되돌림 (테이블 유지)
- Phase 1 롤백: 신규 테이블 모두 제거
- Phase 0 롤백: 백업 스키마 제거 (위험, 보통 유지)

## ✅ 완료 후

- [ ] Phase 0 검증 통과
- [ ] Phase 1 검증 통과 + Streamlit 정상
- [ ] Phase 2 검증 통과 + Streamlit 정상
- [ ] 수동 후속 작업 (총판/유관기관 분류)
- [ ] 본부 직원 capabilities 등록
- [ ] Git 커밋 (마이그레이션 시점 기록)
- [ ] 보호조치 이력에 등록 (privacy_protection_activities)

다음 단계: **Phase 3 (코드 듀얼 리드)** — app.py 수정 작업으로 별도 진행
