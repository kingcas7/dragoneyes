# DragonEyes 작업 To-Do (2026-05-15 ~)

## 📅 작성: 2026-05-14 12:52 (5/14 오전 세션 마감, 커밋 78adbac)

---

## ✅ 5/14 완료 사항 (커밋 78adbac, +550줄)

### 산출물
- PO 양식 v2 5종 (Tier1/2/3-100/200/500)
- 회사 정보 푸터 + 범용 명칭

### 시스템 통합
- COMPANY_INFO 상수 (드래곤아이즈㈜)
- 사이트 푸터 다국어 변경 (ko/en/ja, 법인 공식 톤)

### DB 스키마 (Phase 5-4)
- tenants +10 컬럼
- partners +4 컬럼
- license_requests +2 컬럼
- license_request_users 신규 테이블

### UI 구현
- partner_info 페이지 본격 구현 (130줄)
- 시장 확장 시스템 (BUSINESS_FIELDS 7 + REGULATORY_AUTHORITIES 60+)
- 동적 selectbox + "기타" 입력 (form 밖 배치)

---

## 🔥 P0 — 다음 세션 즉시 진행

### A. 동의 항목 6가지 본문에 회사 정보 반영
- "DragonEyes" → "드래곤아이즈(주)"
- 사업자등록번호 + 분쟁 관할 조항
- 예상 시간: 30~45분

### B. customer_management 페이지 확장 (Step D-2)
- tenants 신규 컬럼 입력/수정 폼
- 권한별 분기 (파트너 admin + 본부 superadmin)
- 예상 시간: 1~1.5시간

### C. AI 파서 — .xlsx PO 양식 업로드 → 자동 INSERT
- 4단계 분할 (UI/파서/미리보기/INSERT)
- 5개 Tier 인식
- 예상 시간: 2~3시간 (단독 세션)

---

## 🟡 P1 — 시장 확장 후속

### D. related_organizations 테이블 신설
### E. regulatory_authorities 동적 시스템
### F. Phase 4 라이선스 확인서 PDF

---

## 🟢 P2 — Upgrade 플랜 (10/30 데드라인)

### G. Supabase Data API 정책 변경 대응
- 데드라인: 2026-10-30 (5.5개월 여유)
- 변경: public 스키마 새 테이블에 명시적 GRANT 필수
- 영향: 기존 14개 테이블 영향 없음, 새 테이블만 적용
- 작업: 모든 테이블 GRANT 점검 + SQL 파일 표준 템플릿 업데이트
- 9월 말까지 마무리 권장

### H. 카드 UX 개선 (streamlit-extras)
### I. 외부 사용자 안내 (황철희/정희영 카톡)

---

## 🔵 P3 — 별도 스프린트

### J. 라우팅 시스템 전면 리팩토링
### K. v2.1 음성 안내 (WCAG 2.1 AA)
### L. v2.1 모니터링 통계 페이지
### M. 보안 (Supabase publishable + Naver Client Secret 회전)

---

## 📊 5/14 현황

- app.py: 9504줄
- DB 테이블: 14개 + license_request_users
- 활성 사용자: 10명 (본부 7 + 포유솔루션 2 + 오뚜기 1)
- 파트너: 2 (포유솔루션 active, 오뚜기 pilot)
- Git: 커밋 78adbac, main 동기화 완료

---

## 📌 다음 세션 시작 명령어

\`\`\`bash
cd ~/dragoneyes && nohup streamlit run app.py > /tmp/streamlit.log 2>&1 &
git log --oneline -5
ls -lh app.py.backup_* | tail -3
\`\`\`
