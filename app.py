import streamlit as st
import anthropic
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from supabase import create_client
from datetime import datetime, date
import pandas as pd

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

st.set_page_config(
    page_title="드래곤아이 모니터링",
    page_icon="🐉",
    layout="wide"
)

# ── 세션 초기화 ──
if "user" not in st.session_state:
    st.session_state.user = None

# ── 로그인 함수 ──
def login(email, password):
    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if result.user:
            user_data = supabase.table("users").select("*").eq("email", email).execute()
            if user_data.data:
                st.session_state.user = user_data.data[0]
                return True, "로그인 성공"
            else:
                return False, "사용자 정보를 찾을 수 없습니다."
    except Exception as e:
        return False, f"로그인 실패: {str(e)}"
    return False, "로그인 실패"

# ── 보고서 저장 함수 ──
def save_report(content, result, severity, category, platform="manual"):
    try:
        supabase.table("reports").insert({
            "user_id": st.session_state.user["id"],
            "content": content,
            "result": result,
            "severity": severity,
            "category": category,
            "platform": platform
        }).execute()
        return True
    except Exception as e:
        st.error(f"저장 오류: {str(e)}")
        return False

# ── 심각도 추출 함수 ──
def extract_severity(text):
    for i in range(5, 0, -1):
        if f"심각도: {i}" in text or f"심각도:{i}" in text:
            return i
    return 0

def extract_category(text):
    for cat in ["그루밍", "성인", "부적절", "스팸", "안전"]:
        if cat in text:
            return cat
    return "미분류"

# ══════════════════════════════
# 로그인 화면
# ══════════════════════════════
if st.session_state.user is None:
    st.title("🐉 드래곤아이")
    st.subheader("내부 모니터링 시스템 로그인")
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")

        if st.button("로그인", use_container_width=True):
            if email and password:
                with st.spinner("로그인 중..."):
                    success, msg = login(email, password)
                if success:
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("이메일과 비밀번호를 입력해주세요.")

# ══════════════════════════════
# 메인 대시보드
# ══════════════════════════════
else:
    user = st.session_state.user
    is_admin = user.get("role") == "admin"

    # 상단 헤더
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("🐉 드래곤아이 모니터링 대시보드")
    with col2:
        # 오늘 보고서 수
        today = date.today().isoformat()
        today_reports = supabase.table("reports").select("id").eq("user_id", user["id"]).gte("created_at", today).execute()
        st.metric("📊 오늘 보고서", f"{len(today_reports.data)}건")
    with col3:
        if st.button("🚪 로그아웃"):
            st.session_state.user = None
            st.rerun()

    st.divider()

    # 탭 구성
    if is_admin:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📝 텍스트 분석",
            "🎬 유튜브 분석",
            "🔍 키워드 자동 탐색",
            "📈 내 성과",
            "👑 관리자 현황"
        ])
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 텍스트 분석",
            "🎬 유튜브 분석",
            "🔍 키워드 자동 탐색",
            "📈 내 성과"
        ])

    # ── 텍스트 분석 ──
    with tab1:
        st.subheader("텍스트 콘텐츠 분석")
        content = st.text_area("분석할 텍스트 입력", height=150)
        if st.button("분석 시작", key="text"):
            if content:
                with st.spinner("분석 중..."):
                    message = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1024,
                        messages=[{"role": "user", "content": f"""
아동 안전 모니터링 전문가로서 아래 콘텐츠를 분석해주세요.
콘텐츠: {content}
다음 형식으로 답해주세요:
심각도: 1~5 (1=안전, 5=매우위험)
분류: (스팸/부적절/성인/그루밍/안전 중 하나)
이유: (간단한 설명)
조치: (권고 조치)
"""}]
                    )
                result_text = message.content[0].text
                st.subheader("분석 결과")
                st.write(result_text)

                severity = extract_severity(result_text)
                category = extract_category(result_text)
                if save_report(content, result_text, severity, category):
                    st.success("📊 보고서가 저장됐습니다!")
            else:
                st.warning("텍스트를 입력해주세요.")

    # ── 유튜브 분석 ──
    with tab2:
        st.subheader("유튜브 영상 분석")
        url = st.text_input("유튜브 URL 입력")
        if st.button("분석 시작", key="youtube"):
            if url:
                try:
                    with st.spinner("유튜브 데이터 수집 중..."):
                        video_id = url.split("v=")[-1].split("&")[0]
                        video_response = youtube.videos().list(part="snippet", id=video_id).execute()
                        snippet = video_response["items"][0]["snippet"]
                        title = snippet["title"]
                        description = snippet.get("description", "")[:500]
                        tags = snippet.get("tags", [])
                        comments = []
                        try:
                            comment_response = youtube.commentThreads().list(
                                part="snippet", videoId=video_id, maxResults=50, order="relevance"
                            ).execute()
                            for item in comment_response.get("items", []):
                                text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                                comments.append(text)
                        except Exception:
                            comments = ["댓글 수집 불가"]
                        st.success(f"영상 제목: {title}")

                    with st.spinner("AI 분석 중..."):
                        analysis_text = f"영상 제목: {title}\n영상 설명: {description}\n태그: {', '.join(tags[:10])}\n댓글:\n{chr(10).join(comments[:20])}"
                        message = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=2048,
                            messages=[{"role": "user", "content": f"""
아동 안전 모니터링 전문가로서 아래 유튜브 영상을 분석해주세요.
{analysis_text}
다음 형식으로 답해주세요:
[영상 전체 분석]
심각도: 1~5
분류: (안전/스팸/부적절/성인/그루밍 중 하나)
이유: (설명)
조치: (권고 조치)
[위험 댓글 목록]
위험도 높은 댓글 최대 5개, 각각 심각도와 이유 설명. 없으면 "위험 댓글 없음"
"""}]
                        )
                    result_text = message.content[0].text
                    st.subheader("분석 결과")
                    st.write(result_text)

                    severity = extract_severity(result_text)
                    category = extract_category(result_text)
                    if save_report(url, result_text, severity, category, "youtube"):
                        st.success("📊 보고서가 저장됐습니다!")

                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")
            else:
                st.warning("유튜브 URL을 입력해주세요.")

    # ── 키워드 자동 탐색 ──
    with tab3:
        st.subheader("키워드 기반 자동 탐색")
        keyword = st.text_input("검색 키워드 (예: 초등학생 게임, 어린이 채팅)")
        max_results = st.slider("분석할 영상 수", min_value=5, max_value=20, value=10)

        if st.button("자동 탐색 시작", key="search"):
            if keyword:
                try:
                    with st.spinner(f"'{keyword}' 검색 중..."):
                        search_response = youtube.search().list(
                            part="snippet", q=keyword, type="video",
                            maxResults=max_results, relevanceLanguage="ko"
                        ).execute()
                        videos = []
                        for item in search_response.get("items", []):
                            vid = item["id"]["videoId"]
                            videos.append({
                                "id": vid,
                                "title": item["snippet"]["title"],
                                "description": item["snippet"].get("description", "")[:200],
                                "channel": item["snippet"]["channelTitle"],
                                "url": f"https://www.youtube.com/watch?v={vid}"
                            })

                    st.info(f"총 {len(videos)}개 영상 수집. AI 분석 시작...")
                    results = []
                    progress = st.progress(0)

                    for i, video in enumerate(videos):
                        with st.spinner(f"분석 중 ({i+1}/{len(videos)}): {video['title'][:30]}..."):
                            message = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=512,
                                messages=[{"role": "user", "content": f"""
아동 안전 모니터링 전문가로서 분석해주세요.
제목: {video['title']}
설명: {video['description']}
채널: {video['channel']}
반드시 아래 형식으로만:
심각도: (1~5)
분류: (안전/스팸/부적절/성인/그루밍)
이유: (한 줄)
"""}]
                            )
                            result_text = message.content[0].text
                            results.append({**video, "analysis": result_text})
                            severity = extract_severity(result_text)
                            category = extract_category(result_text)
                            save_report(video["url"], result_text, severity, category, "youtube_search")
                        progress.progress((i + 1) / len(videos))

                    st.success("분석 완료! 보고서 자동 저장됨 📊")
                    st.subheader("탐색 결과")
                    icons = {1: "✅", 2: "🟡", 3: "🟠", 4: "🔴", 5: "🚨"}
                    for r in results:
                        sev = extract_severity(r["analysis"])
                        icon = icons.get(sev, "❓")
                        with st.expander(f"{icon} {r['title']} — {r['channel']}"):
                            st.write(r["analysis"])
                            st.markdown(f"[유튜브에서 보기]({r['url']})")

                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")
            else:
                st.warning("키워드를 입력해주세요.")

    # ── 내 성과 ──
    with tab4:
        st.subheader(f"📈 {user['name']}님의 성과 현황")

        all_reports = supabase.table("reports").select("*").eq("user_id", user["id"]).execute()
        reports_data = all_reports.data

        if reports_data:
            df = pd.DataFrame(reports_data)
            df["created_at"] = pd.to_datetime(df["created_at"])
            df["month"] = df["created_at"].dt.strftime("%Y-%m")

            # 요약 지표
            col1, col2, col3, col4 = st.columns(4)
            today_count = len(df[df["created_at"].dt.date == date.today()])
            this_month = date.today().strftime("%Y-%m")
            month_count = len(df[df["month"] == this_month])
            total_count = len(df)
            target = user.get("monthly_target", 10)
            rate = min(int(month_count / target * 100), 100)

            col1.metric("오늘", f"{today_count}건")
            col2.metric("이번달", f"{month_count}건", f"목표 {target}건")
            col3.metric("달성률", f"{rate}%")
            col4.metric("누적 총계", f"{total_count}건")

            # 달성률 프로그레스바
            st.progress(rate / 100)
            if rate >= 100:
                st.success("🎉 이번달 목표 달성!")
            elif rate >= 70:
                st.info("💪 잘 하고 있어요! 조금만 더!")
            else:
                st.warning("📌 꾸준히 해봐요!")

            # 월별 추이
            st.subheader("월별 보고서 추이")
            monthly = df.groupby("month").size().reset_index(name="건수")
            st.bar_chart(monthly.set_index("month"))

            # 관리자 코멘트
            comments = supabase.table("comments").select("*").eq("user_id", user["id"]).order("created_at", desc=True).limit(3).execute()
            if comments.data:
                st.subheader("💬 관리자 코멘트")
                for c in comments.data:
                    st.info(f"📝 {c['content']}\n\n_{c['created_at'][:10]}_")
        else:
            st.info("아직 보고서가 없습니다. 분석을 시작해보세요!")

    # ── 관리자 현황 ──
    if is_admin:
        with tab5:
            st.subheader("👑 팀 전체 현황")

            all_users = supabase.table("users").select("*").execute()
            all_reports = supabase.table("reports").select("*").execute()

            if all_users.data and all_reports.data:
                df_r = pd.DataFrame(all_reports.data)
                df_r["created_at"] = pd.to_datetime(df_r["created_at"])
                this_month = date.today().strftime("%Y-%m")
                df_r["month"] = df_r["created_at"].dt.strftime("%Y-%m")

                st.subheader("이번달 팀원별 성과")
                summary = []
                for u in all_users.data:
                    user_reports = df_r[df_r["user_id"] == u["id"]]
                    month_reports = user_reports[user_reports["month"] == this_month]
                    today_reports = user_reports[user_reports["created_at"].dt.date == date.today()]
                    target = u.get("monthly_target", 10)
                    rate = min(int(len(month_reports) / target * 100), 100) if target > 0 else 0
                    summary.append({
                        "이름": u["name"],
                        "오늘": len(today_reports),
                        "이번달": len(month_reports),
                        "목표": target,
                        "달성률": f"{rate}%",
                        "누적": len(user_reports)
                    })

                st.dataframe(pd.DataFrame(summary), use_container_width=True)

                # 코멘트 작성
                st.subheader("💬 팀원에게 코멘트 남기기")
                target_user = st.selectbox("팀원 선택", [u["name"] for u in all_users.data])
                comment_text = st.text_area("코멘트 내용")
                if st.button("코멘트 전송"):
                    if comment_text:
                        target_user_data = next(u for u in all_users.data if u["name"] == target_user)
                        supabase.table("comments").insert({
                            "user_id": target_user_data["id"],
                            "admin_id": user["id"],
                            "content": comment_text
                        }).execute()
                        st.success(f"✅ {target_user}님께 코멘트를 전송했습니다!")
                    else:
                        st.warning("코멘트 내용을 입력해주세요.")
