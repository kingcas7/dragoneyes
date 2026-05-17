# DragonEyes 작업 백로그

> **정리일**: 2026-05-18
> **상태**: 다음 세션 인수인계 기준표
> **위치**: `~/dragoneyes/docs/DragonEyes_TODO_20260518.md`

---

## ✅ 완료 (2026-05-17~18 세션 — 운영 배포·push 완료)

- **P0-1** Step D — 영업 파이프라인 승인상태 분리 (approved/auto_approved 메인, pending/escalated 별도 섹션)
- **P0-2** E2E 테스트 — 등록·승인·거절·4-Layer 격리 전체 통과
- **P0-3** SQL/백업 정리 — 백업 파일 53→12, v1.6 스키마 pg_dump로 git 보존
- 부수 버그 3건 — 파트너 카드 권한 가드 / approval_requests 복귀 버튼 / 거절 처리(`changed_by` NOT NULL)
- 커밋: `5bfdab1` · `61b0d8f` · `66b90db` (전부 push 완료)

---

## 🔴 P1 — 다음 세션 우선

| # | 작업 | 규모 |
|---|------|------|
| 1 | **closed_lost 이력 표시** — 신규 등록 시 "과거 실주 이력 검토 필요" 안내 (DB 변경 없음, 등록 화면에만) | 소 |
| 2 | **엑셀 출력 에픽 6종** — 공통 헬퍼 1개 만들고 페이지별 부착 + `log_download` 감사로그 연동 | 대 |

엑셀 출력 6종:
1. 영업 파이프라인(opportunities) — 본부/파트너
2. 전체 파트너 명단 — 본부
3. 그룹별 전체 사용자(고객사/파트너사/총판/유관기관) — 본부
4. 총판 → 자기 대리점 + 고객
5. 대리점 → 자기 고객
6. 고객 → 자기 사용자

---

## 🟡 P2 — 정리·개선 + 인프라 조기 착수

| # | 작업 | 규모 |
|---|------|------|
| 3 | `approval_requests` — 대기 건 있을 때 하단 복귀 버튼 누락 | 소 |
| 4 | SQL 세트 phase 번호 중복 정리 (`docs/sql/` 0~6 vs `With Claude/DragonEyes System files` 1~11) | 중 |
| 5 | `opportunity_change_log`(트리거) ↔ `opportunity_status_log`(앱) 기능 중복 — 트리거 정리 검토 | 중 |
| 6 | **[묶음] 모니터링 성능개선 A단계 + v2.1 통계 페이지** — 아래 상세 | 대 |

### 6번 묶음 상세 (배치·이벤트 인프라 공유 → 반드시 함께 진행)

**A단계 — 모니터링 성능개선 인프라**
- 하드코딩 키워드 풀(`generate_recommend_keywords`) → `keyword_pool` DB 테이블화 (코드 수정 없이 키워드 추가/관리)
- `monitoring_events` 로깅 활성화 (현재 app.py 참조 0회 — 분석할 때마다 이벤트 기록)
- `learned_keywords`에 검수상태(pending/approved/rejected) + 효과점수 컬럼 추가

**v2.1 통계 페이지** (설계: `docs/v2.1_pending_additions.md` 9~87행)
- 홈 직속 메뉴 "📊 모니터링 통계", 권한별 범위
- 자정 일배치 — pg_cron 집계 + Railway Cron AI 인사이트
- KPI: 총분석/위험발견/조치완료/미조치 · 분석축: 시간·위험유형×플랫폼·Top키워드·신규학습후보·미조치우선순위
- 신규 테이블: monitoring_events / monitoring_daily_stats / daily_insights / batch_job_runs
- ※ 사용자 요구: "검색 섹터·검색 항목별 상세 통계" — 분석 축을 그 기준으로 확장·재정의할 것

---

## 🟢 P3 — 별도 스프린트 / v2.1

| # | 작업 |
|---|------|
| 7 | 음성 안내 시스템 — 시각장애인 접근성, WCAG 2.1 AA / Web Speech API (설계: `docs/v2.1_pending_additions.md` 96~178행). ※ 실제 시각장애인 베타 테스트 없이 출시 금지 |
| 8 | **모니터링 성능개선 B단계 (자율 가동)** — 일배치 키워드 마이닝 + 무효 키워드 decay + 학습 트리거 확대. A단계 완료 후 상시 백그라운드, 다른 개발과 병행 |
| 9 | 격리 백로그 — 총판 계층(`parent_partner_id`) · 유관기관(RELORG) 격리 · 영업기회 Re-assign UI |
| 10 | 라우팅 시스템 전면 리팩토링 (TODO 항목 J) |
| 11 | 보안 — Supabase publishable 키 전환 + Naver Client Secret 회전 (TODO 항목 M) |

---

## 🚦 출시 게이트 — 가동 직전 마지막 작업

| # | 작업 |
|---|------|
| 12 | **모니터링 성능개선 C단계** — 누적 학습 키워드 검수·튜닝, 오탐 제거, 탐지 임계값 조정 — **드래곤아이즈 가동 전 최종 작업** |

---

## 🔵 장기 — v2.1 컴플라이언스 (10만 사용자 트리거 시 발동)

PIA(개인정보 영향평가) · ISMS-P 인증 · 4-Layer 동의-권한 매핑 매트릭스 · RELORG 노출 PII 화이트리스트+감사로그 · CPO 외부 지정 검토

---

## 👀 관찰 항목

- **stale session** — 5/17 정다운 영업 파이프라인 0건 사례. 새 로그인으로 해소됨. 재발 시 세션 갱신 로직 조사
- **learned_keywords** — 테이블 존재 여부 + 학습 무음실패 검증 (`learn_keywords_from_report`가 예외를 `except: pass`로 삼킴)

## ❌ 보류 (재시도 금지)

- 관리자 페이지 챗봇 제거 — 5/17 다회 실패, 운영 영향 제로라 보류 확정. 백업 `app.py.backup_before_chatbot_remove_1706` 보존

---

## 📌 핵심 메모

- **모니터링 성능개선**은 단일 작업이 아니라 3단계: A(조기 인프라, P2) → B(상시 자율가동, P3) → C(출시 직전 검증, 출시 게이트). A·B를 일찍 시작할수록 학습 데이터가 쌓여 C 품질이 올라감.
- A단계와 v2.1 통계 페이지는 `monitoring_events` + 일배치 인프라를 공유 → P2 묶음(6번)으로 함께 진행.
- 현재 키워드 자가학습 골격은 이미 존재: 보고서(심각도 ≥3) → `learn_keywords_from_report` → `learned_keywords` 테이블 → `get_learned_keywords`로 추천 풀 재투입. 한계는 수동·반응형, 검수큐 없음, 효과측정 없음, 키워드 풀 하드코딩.
