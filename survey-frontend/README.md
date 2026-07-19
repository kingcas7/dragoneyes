# 드래곤아이즈 캠페인 설문 — 정적 응답 페이지

수만 명 동시 사용을 위한 정적 HTML 응답 페이지입니다. Streamlit 본 앱과 분리되어
Vercel/Netlify 같은 정적 호스팅에 배포되며, Supabase REST RPC를 직접 호출합니다.

## 🏗️ 구조

```
[학생]  →  Streamlit (Railway)
              ↓ QR/링크 생성 (?token=...)
[응답자] →  정적 HTML (Vercel) ← 이 폴더
              ↓ Supabase JS SDK (anon)
[Supabase] →  RPC 함수 (SECURITY DEFINER)
              ↓
[DB]      →  external_survey_responses + token.response_count++
              ↓ 임계값 도달 시
[v17_018] →  봉사 인증서 자동 발급
```

## 📦 파일 구성

| 파일 | 역할 |
|----|----|
| `index.html` | 메인 페이지 (Tailwind CDN) |
| `style.css` | 추가 스타일 (한글 폰트·인쇄 차단) |
| `config.js` | Supabase URL + anon key (배포 시 채울 것) |
| `main.js` | Supabase RPC 호출 + 동적 렌더링 + 제출 로직 |
| `vercel.json` | Vercel 헤더·캐시·rewrite 설정 |

## 🚀 Vercel 배포

### 1) Supabase anon key 등록

`config.js` 파일 열어서 `SUPABASE_ANON_KEY` 채워주세요.
Supabase Dashboard → Settings → API → `anon` `public` 키 복사.

```js
window.DRAGONEYES_CONFIG = {
  SUPABASE_URL: "https://xtqgxtdflemuphkzmzti.supabase.co",
  SUPABASE_ANON_KEY: "eyJ..."  // ← 여기에 anon key
};
```

### 2) Vercel CLI로 배포

```bash
npm i -g vercel
cd survey-frontend
vercel        # 첫 배포 (프로젝트 생성)
vercel --prod # 운영 배포
```

또는 GitHub 연결:
- Vercel 대시보드 → New Project → kingcas7/dragoneyes 선택
- Root Directory: `survey-frontend`
- Framework: `Other` (정적)
- Build Command: 비워두기
- Output Directory: 비워두기

### 3) 도메인 (선택)

Vercel 대시보드 → Settings → Domains:
- 기본: `<project>.vercel.app`
- 커스텀: `survey.dragoneyes.co.kr` (DNS CNAME)

## 🔗 학생 dashboard 측 URL 변경

Streamlit `app.py`에서 학생 QR/링크 생성 시 사용하는 base URL을
Railway 환경변수 `SURVEY_FRONTEND_URL`로 분리:

```bash
# Railway → Variables
SURVEY_FRONTEND_URL=https://survey.dragoneyes.co.kr
```

미설정 시 Streamlit 페이지로 fallback (개발 환경).

## 🛡️ 보안 모델

- `anon` role은 테이블 직접 접근 X (RLS로 차단)
- `get_survey_by_token()`·`submit_external_response()` 두 함수만 호출 가능
- 두 함수는 `SECURITY DEFINER` 권한으로 토큰 검증 후 처리
- 60초 미만 제출은 `is_valid=false`로 무효 처리
- 같은 token + 응답자명 + 분 단위 중복 제출 차단

## 📊 응답 흐름

1. 응답자 URL 진입 → token 추출
2. `get_survey_by_token(token)` 호출
   - 토큰 검증, 배포자 정보, 26문항 반환
3. 배포자 정보 카드 자동 채우기
4. 응답자 정보 입력 (성명·나이·성별·거주지역)
5. 26문항 응답
6. `submit_external_response(...)` 호출
   - 응답 저장 + 카운트 증가
   - 임계값 도달 시 v17_018 트리거가 자동 인증서 발급
7. 완료 화면에 현재 진행률·임계값 표시

## 🧪 로컬 테스트

```bash
cd survey-frontend
python3 -m http.server 5500
# 브라우저: http://localhost:5500/?token=<유효한 토큰>
```

## ⚙️ Railway 멀티 인스턴스 (관리용)

응답 페이지는 정적이라 무한 확장 가능. Streamlit 본 앱(관리·로그인)은
Railway에서 멀티 인스턴스로 확장:

1. Railway → 프로젝트 Settings → Replicas: 2~4개
2. 로드 밸런서가 자동 분산
3. Supabase 연결 풀: 자동 처리 (현재 PgBouncer 6543 포트 권장)

비용: 인스턴스당 ~$5/월. 4개 = ~$20/월.
