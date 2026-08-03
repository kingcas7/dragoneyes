# NCP 이전 체크리스트 (B안: 앱 + 셀프호스팅 Supabase)
> 작성 2026-08-04 · 교육청/공공 계약으로 "국내 클라우드" 요구가 확정되면 이 문서대로 실행.
> 예상 총 기간: **2~3주 (실작업 7~10일 + 리허설·검증)** · 목표 월 비용: 15~40만 원대

## 0. 사전 확인 (계약 단계 — 착수 전 필수)
- [ ] 기관 요구 수준 서면 확인: ①데이터 국내 소재 ②국내 CSP ③CSAP 인증 — ①이면 이전 불필요(현 Supabase=AWS 서울), ③이면 NCP 공공기관용(gov-ncloud)으로 이 문서 C안 확장
- [ ] 개인정보 처리방침 개정 항목 도출: 처리 위탁(Supabase Inc·Railway → 네이버클라우드/자체 호스팅) 변경 고지
- [ ] NICE 본인인증·토스페이먼츠 콜백 URL 변경 신청 리드타임 확인 (수일 소요 가능)

## 1. NCP 인프라 준비 (0.5일)
- [ ] 계정·결제 등록, VPC + Subnet + ACG(방화벽: 80/443/22만 오픈)
- [ ] 서버: 시작은 1대 통합(4vCPU/16GB, SSD 100GB↑) — 트래픽 증가 시 app/db 분리
- [ ] 공인 IP, Object Storage 버킷(백업·스토리지 백엔드용)
- [ ] DNS 준비: portal.dragoneyes.co.kr TTL을 이전 1주 전에 300초로 하향

## 2. 셀프호스팅 Supabase 구축 (1~2일)
- [ ] github.com/supabase/supabase → /docker 의 docker-compose 사용 (버전 태그 고정!)
- [ ] 신규 시크릿 발급: JWT_SECRET, ANON_KEY, SERVICE_ROLE_KEY (기존 키와 다름 — 앱 .env 교체 대상)
- [ ] GoTrue(Auth) SMTP = Resend 연결 (비밀번호 재설정 메일)
- [ ] Storage 백엔드: NCP Object Storage(S3 호환) 연결 권장 (로컬 볼륨보다 백업 유리)
- [ ] HTTPS: caddy 또는 nginx + Let's Encrypt

## 3. 데이터 이전 (1~2일 + 리허설 1회)
- [ ] DB 본체: `pg_dump`(Supabase 커넥션 스트링) → 신규 Postgres restore — 확장(pgcrypto 등)·시퀀스·트리거·RLS 정책 포함 여부 확인
- [ ] **Auth 사용자: auth 스키마 포함 덤프 — 비밀번호 해시가 그대로 이전되어 사용자 재설정 불필요** (검증 필수: 테스트 계정 3종으로 기존 비밀번호 로그인)
- [ ] Storage 파일: 버킷 4종(Documents / user-documents / license-documents / app-data) 전량 복사 스크립트
- [ ] ⚠️ **최대 함정: DB에 저장된 서명 URL(attachment_url 등)은 구 도메인이라 전부 무효화됨** → campaign_learning_materials 등 URL 보유 테이블 전수 조사 후 신규 서명 URL 일괄 재발급 스크립트 실행
- [ ] 리허설: 위 전 과정을 스테이징에서 1회 왕복 후 소요 시간 기록

## 4. 앱 이전 (0.5일)
- [ ] 기존 Dockerfile 그대로 빌드·기동 (코드 수정 불필요가 원칙)
- [ ] .env 교체: SUPABASE_URL / SUPABASE_KEY / SUPABASE_SERVICE_ROLE_KEY → 셀프호스팅 값
- [ ] 외부 API 스모크: YouTube·Anthropic·Resend·카카오다음검색
- [ ] 재유통 지문(app-data 버킷)·학습자료 다운로드 작동 확인

## 5. 검증 (2~3일)
- [ ] 기능: 로그인(기존 비번) → 탐색 → 분석 → 보고서 제출 → 히스토리 복귀 → 관제 통계 → 캠페인(학습자료 열람·설문·봉사인증) → 음성 접근성
- [ ] 권한: 요원/관리자/파트너/캠페인 계정별 화면 분리 확인 (RLS 이전 검증)
- [ ] 부하: 동시 30 세션 시나리오
- [ ] 백업 체계: pg_dump 일일 cron + Object Storage 업로드 + **복구 리허설 1회**

## 6. 컷오버 (반나절 · 야간 권장)
- [ ] 사전 공지(작성 중 데이터 손실 방지) → 쓰기 중지 → 최종 델타 덤프·복원
- [ ] DNS 전환 → 24시간 모니터링
- [ ] 롤백 플랜: DNS 원복만으로 복귀 가능하게 Railway·구 Supabase를 **2주간 유지**

## 7. 이전 후 (1~2주 내)
- [ ] Railway·Supabase 구독 해지 (2~4주 유예 후)
- [ ] 개인정보처리방침 개정 게시, NICE·토스 콜백 URL 전환 확인
- [ ] NCP 비용 알림 설정, 월 비용 실측 기록

## 리스크 요약
| 리스크 | 대응 |
|---|---|
| 서명 URL 전면 무효화 | 3단계 URL 재발급 스크립트 — 리허설에서 검증 |
| Auth 해시 이전 실패 | 최후수단: 전 사용자 비밀번호 재설정 메일 (Resend) |
| 셀프호스팅 Supabase 운영 부담 | 버전 고정 + 월 1회 계획 업데이트, 백업 자동화 |
| CSAP 요구로 격상 | gov-ncloud 리전 재견적 (비용 약 1.5배) + 보안 요건 별도 정리 |
