# DragonEyes 작업 백로그

> **정리일**: 2026-05-18 (1~5 완료 반영)
> **상태**: 다음 세션 인수인계 기준표
> **위치**: `~/dragoneyes/docs/DragonEyes_TODO_20260518.md`

---

## ✅ 완료 (2026-05-17~18 세션 — 운영 배포·push 완료)

### P0 (5/17~18)
- **P0-1** Step D — 영업 파이프라인 승인상태 분리
- **P0-2** E2E 테스트 — 등록·승인·거절·4-Layer 격리 전체 통과
- **P0-3** SQL/백업 정리 — 백업 53→12, v1.6 스키마 pg_dump로 git 보존
- 부수 버그 3건 — 파트너 카드 권한 / 복귀 버튼 / 거절 처리(`changed_by`)
- 커밋 `5bfdab1` · `61b0d8f` · `66b90db` · `3dba8a2`

### 추천순서 1~5 (5/18)
- **1. closed_lost 이력 표시** — 신규 등록 시 "과거 실주 이력" 안내 · `7735f46`
- **2. 엑셀 출력 에픽 6종 + 파트너 영역** — `5ad1af0`·`bd3dde9`·`1f9b111`·`a70c63a`·`77e6550`
  - 공통 헬퍼 `render_excel_download()` + #1 영업 파이프라인 / #2 전체 파트너 명단 /
    #3·#6 사용자 명단(본부·파트너·고객 자동 스코핑) / #4 산하 대리점 / #5 담당 고객사
  - 추가: 파트너 정보(단일 파트너) · 담당자 관리(담당자 명단) 페이지 다운로드
- **3. approval_requests 복귀 버튼** — 대기 건 있을 때도 노출 · `698d827`
- **4. SQL phase 중복 정리** — With Claude SQL을 `docs/sql/_legacy_2026-05-11/`로 아카이브 · `ba8c755`
- **5. 트리거 중복 검토** — 검토 완료. **결론: 현행 유지** (트리거가 `updated_at`
  자동갱신 겸함 → drop 불가, 중복은 무해. v2.x 로깅 일원화 시 함께 정리)

---

## 🔴 다음 최우선 — #6 모니터링 성능개선 A + v2.1 통계 페이지 (대형 에픽)

> ⚠️ 단순 코딩 아님. 신규 테이블 4개 + 신규 페이지 + pg_cron/Railway Cron 인프라 +
> AI 연동. **설계(테이블 스키마·배치 구조·통계 항목)부터 잡는 전용 세션 필요.**

**A단계 — 모니터링 성능개선 인프라**
- 하드코딩 키워드 풀(`generate_recommend_keywords` 3576행) → `keyword_pool` DB 테이블화
- `monitoring_events` 로깅 활성화 (현재 app.py 참조 0회)
- `learned_keywords`에 검수상태(pending/approved/rejected) + 효과점수 컬럼 추가

**v2.1 통계 페이지** (설계: `docs/v2.1_pending_additions.md` 9~87행)
- 홈 직속 메뉴 "📊 모니터링 통계", 권한별 범위
- 자정 일배치 — pg_cron 집계 + Railway Cron AI 인사이트
- KPI: 총분석/위험발견/조치완료/미조치
- 신규 테이블: monitoring_events / monitoring_daily_stats / daily_insights / batch_job_runs
- ※ 사용자 요구: "검색 섹터·검색 항목별 상세 통계" — 분석 축을 그 기준으로 확장

**현행 키워드 시스템 조사 결과 (5/18, 다음 세션 참고)**
- 자가학습 골격 존재: 보고서(심각도≥3) → `learn_keywords_from_report`(3156행) →
  `learned_keywords` 테이블 → `get_learned_keywords`(3237행)로 추천 풀 재투입
- 한계 7가지: ①키워드 풀 하드코딩 ②학습이 수동·반응형 ③검수 큐 없음
  ④효과 측정 없음(use_count는 재학습 횟수일 뿐) ⑤죽은 키워드 정리 없음
  ⑥`monitoring_events` 미사용 ⑦`except: pass`로 학습 무음실패

---

## 🟢 P3 — 별도 스프린트 / v2.1

| # | 작업 |
|---|------|
| 7 | 음성 안내 시스템 — 시각장애인 접근성, WCAG 2.1 AA / Web Speech API (설계: `docs/v2.1_pending_additions.md` 96~178행). ※ 실제 시각장애인 베타 테스트 없이 출시 금지 |
| 8 | **모니터링 성능개선 B단계 (자율 가동)** — 일배치 키워드 마이닝 + decay + 학습 트리거 확대. A단계 후 상시 백그라운드 |
| 9 | 격리 백로그 — 총판 계층(`parent_partner_id`) · 유관기관(RELORG) 격리 · 영업기회 Re-assign UI |
| 10 | 라우팅 시스템 전면 리팩토링 (TODO 항목 J) |
| 11 | 보안 — Supabase publishable 키 전환 + Naver Client Secret 회전 (TODO 항목 M) |
| 13 | **stub 페이지 구현** — `support_request`(Support Request) · `license_status`(라이선스 현황) · `customer_management`(고객사 관리) 모두 "🚧 준비 중" 빈 페이지. 구현 시 엑셀 다운로드 함께 추가 ("모두 엑셀로" 방침) |

---

## 🚦 출시 게이트 — 가동 직전 마지막 작업

| # | 작업 |
|---|------|
| 12 | **모니터링 성능개선 C단계** — 누적 학습 키워드 검수·튜닝, 오탐 제거, 탐지 임계값 조정 — **드래곤아이즈 가동 전 최종 작업** |

---

## 🔵 장기 — v2.1 컴플라이언스 (10만 사용자 트리거 시 발동)

PIA · ISMS-P 인증 · 4-Layer 동의-권한 매핑 매트릭스 · RELORG 노출 PII 화이트리스트+감사로그 · CPO 외부 지정 검토

---

## 👀 관찰 항목

- **stale session** — 5/17 정다운 영업 파이프라인 0건 사례. 새 로그인으로 해소. 재발 시 세션 갱신 로직 조사
- **learned_keywords** — 테이블 존재 여부 DB 검증 + 학습 무음실패(`except: pass`) 검증 필요
- **레거시 SQL phase8~11** — `docs/sql/_legacy_2026-05-11/INDEX.md` 참조. 적용 여부 DB 검증 후 적용분은 정식 마이그레이션으로 승격 권장 (phase7은 적용 확정)

## ❌ 보류 (재시도 금지)

- 관리자 페이지 챗봇 제거 — 5/17 다회 실패, 운영 영향 제로라 보류 확정. 백업 `app.py.backup_before_chatbot_remove_1706` 보존

---

## 🧪 미완 — 로컬 테스트

5/18 작업분(closed_lost + 엑셀 6종 + 복귀 버튼)은 커밋·push됐으나 로컬 정밀 테스트 미완.
다음 세션 또는 운영 확인 시 점검 권장 (엑셀 #1 버튼 렌더만 시각 확인됨).

## 📌 핵심 메모

- **모니터링 성능개선**은 3단계: A(인프라) → B(상시 자율가동) → C(출시 직전 검증).
  A·B를 일찍 시작할수록 학습 데이터가 쌓여 C 품질이 올라감.
- A단계와 v2.1 통계 페이지는 `monitoring_events` + 일배치 인프라를 공유 → 묶음 진행.
