import streamlit as st
import anthropic
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from supabase import create_client
from datetime import date, datetime, timedelta
import pandas as pd

import requests
load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
def get_naver_keys():
    cid = os.getenv("NAVER_CLIENT_ID", "")
    sec = os.getenv("NAVER_CLIENT_SECRET", "")
    if not cid:
        try: cid = st.secrets.get("NAVER_CLIENT_ID", "")
        except: pass
    if not sec:
        try: sec = st.secrets.get("NAVER_CLIENT_SECRET", "")
        except: pass
    return cid, sec
NAVER_CLIENT_ID, NAVER_CLIENT_SECRET = get_naver_keys()

st.set_page_config(page_title="DragonEyes / 드래곤아이즈", page_icon="🐉", layout="wide")

# ── 모바일 반응형 CSS ──
st.markdown("""
<style>
/* 모바일 기본 (768px 이하) */
@media (max-width: 768px) {

    /* 전체 여백 축소 */
    .block-container {
        padding: 0.5rem 0.5rem !important;
        max-width: 100% !important;
    }

    /* 컬럼을 모바일에서 세로로 */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* 버튼 크게 */
    button[kind="primary"], button[kind="secondary"] {
        font-size: 1rem !important;
        padding: 0.6rem 0.8rem !important;
        min-height: 2.8rem !important;
        width: 100% !important;
    }

    /* 입력창 크게 */
    input, textarea, select {
        font-size: 1rem !important;
        min-height: 2.5rem !important;
    }

    /* 탭 글자 작게 (탭이 많아서) */
    button[data-baseweb="tab"] {
        font-size: 0.7rem !important;
        padding: 0.3rem 0.3rem !important;
    }

    /* 메트릭 카드 */
    [data-testid="metric-container"] {
        padding: 0.3rem !important;
    }

    /* 사이드바 숨김 */
    [data-testid="stSidebar"] {
        display: none !important;
    }

    /* 헤더 폰트 */
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1rem !important; }

    /* 테이블 스크롤 */
    [data-testid="stDataFrame"] {
        overflow-x: auto !important;
    }

    /* 채팅창 높이 축소 */
    [data-testid="stVerticalBlockBorderWrapper"] {
        min-height: auto !important;
    }

    /* 드래곤파더 채팅 높이 모바일 조정 */
    div[style*="height: 320px"] {
        height: 200px !important;
    }
}

/* 태블릿 (768px ~ 1024px) */
@media (min-width: 769px) and (max-width: 1024px) {
    .block-container {
        padding: 1rem !important;
    }
    button[data-baseweb="tab"] {
        font-size: 0.8rem !important;
        padding: 0.4rem 0.4rem !important;
    }
}

/* 데스크탑 전체 컴팩트 */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 0.4rem !important;
}
h1 { font-size: 1.5rem !important; margin: 0 !important; }
h2 { font-size: 1.1rem !important; margin: 0 !important; }
h3 { font-size: 0.95rem !important; margin: 0 !important; }
hr { margin: 0.25rem 0 !important; }

[data-testid="metric-container"] {
    padding: 0.15rem 0.25rem !important;
}
[data-testid="metric-container"] label {
    font-size: 0.72rem !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.1rem !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.68rem !important;
}
[data-testid="stHeading"] {
    margin: 0.1rem 0 !important;
}
[data-testid="stVerticalBlock"] > div {
    gap: 0.25rem !important;
}
[data-testid="stHorizontalBlock"] {
    gap: 0.4rem !important;
    align-items: center !important;
}
[data-testid="stProgressBar"] {
    margin: 0.15rem 0 !important;
}
button[kind="secondary"] {
    padding: 0.25rem 0.4rem !important;
    font-size: 0.82rem !important;
}
p { margin-bottom: 0.2rem !important; }
</style>
""", unsafe_allow_html=True)

DAILY_DRAGON_LIMIT = 5
MONTHLY_DRAGON_LIMIT = 20

# 대화형 AI 제한
CHAT_DAILY_LIMIT = 40
CHAT_WEEKLY_LIMIT = 100
CHAT_MONTHLY_LIMIT = 400

# ══════════════════════════════
# 역할 레이블 매핑 (중앙 관리)
# ══════════════════════════════
ROLE_LABELS = {
    "superadmin":     "👑 전체 관리자",
    # 1그룹
    "group_leader":   "🔱 제1 그룹장",
    "director":       "🎯 1그룹 디렉터",
    # 2그룹
    "group_leader_2": "🔱 제2 그룹장",
    "director_2":     "🎯 2그룹 디렉터",
    # 3그룹
    "group_leader_3": "🔱 제3 그룹장",
    "director_3":     "🎯 3그룹 디렉터",
    # 4그룹
    "group_leader_4": "🔱 제4 그룹장",
    "director_4":     "🎯 4그룹 디렉터",
    # 공통
    "team_leader":    "👔 팀장",
    "user":           "👤 일반사용자",
    "admin":          "⚙️ 관리자",
}

ROLE_ICONS = {
    "superadmin":     "👑",
    "group_leader":   "🔱",
    "group_leader_2": "🔱",
    "group_leader_3": "🔱",
    "group_leader_4": "🔱",
    "director":       "🎯",
    "director_2":     "🎯",
    "director_3":     "🎯",
    "director_4":     "🎯",
    "team_leader":    "👔",
    "user":           "👤",
    "admin":          "⚙️",
}

def role_label(role_v2):
    return ROLE_LABELS.get(role_v2, "👤 일반사용자")

def role_icon(role_v2):
    return ROLE_ICONS.get(role_v2, "👤")

# ══════════════════════════════
# 다국어 딕셔너리
# ══════════════════════════════
LANG = {
    "ko": {
        "app_title":"🐉 드래곤아이즈 모니터링","this_month":"📅 이번달","home":"🏠 홈",
        "write_report":"📋 보고서 작성","logout":"🚪 로그아웃","prev":"◀ 이전으로",
        "submit":"✅ 보고서 제출","cancel":"❌ 취소","detail":"상세보기","delete":"🗑️ 삭제",
        "save":"💾 수정 저장","close":"닫기","total":"총","unit_reports":"건","unit_times":"회",
        "login_title":"🐉 드래곤아이즈","login_sub":"내부 모니터링 시스템 로그인",
        "email":"이메일","password":"비밀번호","login_btn":"로그인","login_ok":"로그인 성공",
        "login_fail":"로그인 실패","login_warn":"이메일과 비밀번호를 입력해주세요.",
        "no_user":"사용자 정보를 찾을 수 없습니다.",
        "greeting":"👋 안녕하세요, {}님!","month_report":"📅 이번달 보고서","goal":"목표 {}건",
        "achievement":"🎯 달성률","dragon_token":"🐉 드래곤 토큰","token_remain":"{}회 남음",
        "pending_list":"건 대기중","shortcut":"📌 바로가기",
        "assigned_pending":"⚠️ 내게 배정된 미작성 목록 ({}건)",
        "tab_text":"📝 텍스트 분석","tab_youtube":"🎬 유튜브 분석","tab_keyword":"🔍 키워드 탐색",
        "tab_dragon":"🐉 드래곤아이즈 추천","tab_history":"📜 탐색 히스토리",
        "tab_reports":"📁 보고서 목록","tab_stats":"📈 내 성과","tab_admin":"👑 관리자",
        "text_title":"텍스트 콘텐츠 분석","text_input":"분석할 텍스트 입력",
        "analyze_start":"분석 시작","analyzing":"분석 중...","result_title":"분석 결과",
        "to_report":"📋 보고서로 작성하기","enter_text":"텍스트를 입력해주세요.",
        "yt_title":"유튜브 영상 분석","yt_url":"유튜브 URL 입력","yt_collecting":"데이터 수집 중...",
        "yt_analyzing":"AI 분석 중...","yt_open":"▶️ 유튜브에서 보기","enter_url":"URL을 입력해주세요.",
        "kw_title":"키워드 기반 자동 탐색","kw_input":"검색 키워드","kw_count":"분석할 영상 수",
        "kw_start":"자동 탐색 시작","kw_searching":"'{}' 검색 중...","kw_skipped":"⏭️ 이미 분석한 영상 {}개 제외됨",
        "kw_no_new":"새로운 영상이 없습니다. 다른 키워드를 시도해보세요.",
        "kw_analyzing":"새 영상 {}개 분석 시작...","kw_done":"완료! {}개 분석됨",
        "kw_results":"탐색 결과 ({}개)","kw_clear":"🗑️ 검색 결과 초기화","enter_keyword":"키워드를 입력해주세요.",
        "dragon_title":"🐉 드래곤아이즈 추천 모니터링 리스트",
        "dragon_caption":"AI가 플랫폼별 위험 키워드를 자동 생성하고 유튜브를 탐색합니다. 이미 분석한 영상은 자동 제외됩니다.",
        "dragon_used":"이번달 사용","dragon_today":"오늘 사용","dragon_remain":"남은 월간 횟수",
        "dragon_monthly_limit":"이번달 추천 한도에 도달했습니다. 관리자에게 추가 토큰을 요청하세요.",
        "dragon_daily_limit":"오늘 추천 한도({}회)에 도달했습니다. 내일 다시 사용 가능합니다.",
        "dragon_general":"🐉 일반 추천","dragon_roblox":"🎮 Roblox 추천","dragon_minecraft":"⛏️ Minecraft 추천",
        "dragon_kw_gen":"{} 위험 키워드 생성 중...","dragon_kw_done":"키워드 {}개 생성됨!",
        "dragon_kw_fail":"키워드 생성 실패. 다시 시도해주세요.","dragon_scanning":"'{}' 탐색 중... ({}/{})",
        "dragon_complete":"완료! {} — {}개 중 주의 필요 {}개 발견",
        "dragon_risky":"🚨 주의 필요 ({}개)","dragon_safe":"✅ 안전 판정 ({}개)","dragon_clear":"🗑️ 추천 결과 초기화",
        "sort":"정렬","sort_sev_high":"심각도 높은순","sort_sev_low":"심각도 낮은순",
        "sort_newest":"최신순","sort_oldest":"오래된순",
        "report_title":"📋 보고서 작성","platform":"플랫폼","severity":"심각도","category":"분류",
        "content_url":"콘텐츠 내용 또는 URL","memo":"추가 메모 (선택)","memo_placeholder":"직접 판단한 내용, 특이사항 등",
        "ai_result":"🤖 AI 분석 결과 보기","yt_open_video":"▶️ 유튜브에서 영상 열기",
        "enter_content":"콘텐츠 내용을 입력해주세요.","report_detail":"보고서 상세보기",
        "written_by":"작성자","written_at":"작성일","updated_at":"수정일",
        "content":"**콘텐츠 내용**","analysis":"**분석 결과**","edit_report":"✏️ 보고서 수정",
        "edit_sev":"심각도 수정","edit_cat":"분류 수정","edit_result":"분석 결과 수정",
        "edit_saved":"✅ 수정됐습니다!","delete_report":"🗑️ 이 보고서 삭제",
        "report_list":"📁 보고서 목록","filter_sev":"심각도 필터","filter_cat":"분류 필터",
        "filter_writer":"작성자 필터","all":"전체","no_reports":"아직 보고서가 없습니다.",
        "sev_1":"1—안전","sev_2":"2—낮은위험","sev_3":"3—중간위험","sev_4":"4—높은위험","sev_5":"5—매우위험",
        "cat_safe":"안전","cat_spam":"스팸","cat_bad":"부적절","cat_adult":"성인","cat_groom":"그루밍","cat_unclassified":"미분류",
        "plat_yt":"YouTube","plat_rb":"Roblox","plat_mc":"Minecraft","plat_etc":"기타",
        "history_title":"📜 탐색 히스토리","history_caption":"지금까지 분석된 영상 목록 (최대 1000개)",
        "filter_type":"탐색 유형","filter_reported":"보고서 여부","reported":"작성됨","not_reported":"미작성",
        "after_date":"날짜 이후","assignee":"담당","unassigned":"미배정","write_btn":"📋 작성",
        "stats_title":"📈 {}님의 성과 현황","stat_month":"이번달","stat_rate":"달성률",
        "stat_total":"누적 총계","stat_target":"이번달 목표","goal_achieved":"🎉 이번달 목표 달성!",
        "goal_good":"💪 잘 하고 있어요!","goal_keep":"📌 꾸준히 해봐요!","admin_comment":"💬 관리자 코멘트",
        "admin_title":"👑 관리자 대시보드","admin_team":"📊 팀 현황","admin_assign":"🎯 목록 배정",
        "admin_token":"🪙 토큰 관리","admin_email":"📧 수신자 관리","admin_log":"📨 발송 이력",
        "send_comment":"코멘트 전송","select_member":"팀원 선택","comment_content":"코멘트 내용",
        "comment_sent":"✅ {}님께 전송됐습니다!","comment_empty":"코멘트 내용을 입력해주세요.",
        "email_bulk":"📧 선택 보고서 일괄 이메일 발송","email_recipient":"수신자 선택","email_subject":"제목",
        "email_memo":"추가 메모 (선택)","email_send":"📧 선택된 수신자에게 일괄 발송 (UI 미리보기)",
        "email_preview":"📄 발송 미리보기","email_no_rec":"등록된 수신자가 없습니다. 관리자 탭에서 수신자를 추가하세요.",
        "email_single":"📧 발송","email_sent_ok":"✅ {}에게 발송 예정으로 저장됨",
        "new_recipient":"**새 수신자 등록**","rec_name":"이름 / 기관명","rec_email":"이메일","rec_type":"유형",
        "rec_memo":"메모 (선택)","rec_add":"➕ 수신자 등록","rec_added":"✅ {} 등록됨!",
        "rec_list":"등록된 수신자 목록","rec_active":"✅ 활성","rec_inactive":"❌ 비활성",
        "deactivate":"❌ 비활성화","activate":"✅ 활성화",
        "save_error":"저장 오류: {}","delete_error":"삭제 오류: {}","error":"오류: {}","no_url":"URL을 입력해주세요.",
    },
    "en": {
        "app_title":"🐉 DragonEyes Monitoring","this_month":"📅 This Month","home":"🏠 Home",
        "write_report":"📋 Write Report","logout":"🚪 Logout","prev":"◀ Back",
        "submit":"✅ Submit Report","cancel":"❌ Cancel","detail":"View Detail","delete":"🗑️ Delete",
        "save":"💾 Save Changes","close":"Close","total":"Total","unit_reports":" reports","unit_times":" times",
        "login_title":"🐉 DragonEyes","login_sub":"Internal Monitoring System Login",
        "email":"Email","password":"Password","login_btn":"Login","login_ok":"Login successful",
        "login_fail":"Login failed","login_warn":"Please enter email and password.","no_user":"User not found.",
        "greeting":"👋 Welcome, {}!","month_report":"📅 Monthly Reports","goal":"Goal: {}",
        "achievement":"🎯 Achievement","dragon_token":"🐉 Dragon Tokens","token_remain":"{} remaining",
        "pending_list":" pending","shortcut":"📌 Quick Access","assigned_pending":"⚠️ My Assigned Pending List ({} items)",
        "tab_text":"📝 Text Analysis","tab_youtube":"🎬 YouTube Analysis","tab_keyword":"🔍 Keyword Search",
        "tab_dragon":"🐉 DragonEyes Picks","tab_history":"📜 Search History",
        "tab_reports":"📁 Reports","tab_stats":"📈 My Stats","tab_admin":"👑 Admin",
        "text_title":"Text Content Analysis","text_input":"Enter text to analyze",
        "analyze_start":"Start Analysis","analyzing":"Analyzing...","result_title":"Analysis Result",
        "to_report":"📋 Create Report","enter_text":"Please enter text.",
        "yt_title":"YouTube Video Analysis","yt_url":"Enter YouTube URL","yt_collecting":"Collecting data...",
        "yt_analyzing":"AI analyzing...","yt_open":"▶️ Watch on YouTube","enter_url":"Please enter a URL.",
        "kw_title":"Keyword-based Auto Search","kw_input":"Search keyword","kw_count":"Number of videos",
        "kw_start":"Start Search","kw_searching":"Searching '{}'...","kw_skipped":"⏭️ {} already-analyzed videos excluded",
        "kw_no_new":"No new videos. Try a different keyword.","kw_analyzing":"Analyzing {} new videos...",
        "kw_done":"Done! {} analyzed","kw_results":"Search Results ({})","kw_clear":"🗑️ Clear Results",
        "enter_keyword":"Please enter a keyword.",
        "dragon_title":"🐉 DragonEyes Recommended Monitoring List",
        "dragon_caption":"AI auto-generates risk keywords and searches YouTube. Already-analyzed videos are excluded.",
        "dragon_used":"Used This Month","dragon_today":"Used Today","dragon_remain":"Monthly Remaining",
        "dragon_monthly_limit":"Monthly limit reached. Ask admin for more tokens.",
        "dragon_daily_limit":"Daily limit ({} times) reached. Try again tomorrow.",
        "dragon_general":"🐉 General Picks","dragon_roblox":"🎮 Roblox Picks","dragon_minecraft":"⛏️ Minecraft Picks",
        "dragon_kw_gen":"Generating {} risk keywords...","dragon_kw_done":"{} keywords generated!",
        "dragon_kw_fail":"Keyword generation failed.","dragon_scanning":"Scanning '{}' ... ({}/{})",
        "dragon_complete":"Done! {} — {} found, {} need attention",
        "dragon_risky":"🚨 Needs Attention ({})","dragon_safe":"✅ Safe ({})","dragon_clear":"🗑️ Clear Results",
        "sort":"Sort","sort_sev_high":"Severity: High → Low","sort_sev_low":"Severity: Low → High",
        "sort_newest":"Newest First","sort_oldest":"Oldest First",
        "report_title":"📋 Write Report","platform":"Platform","severity":"Severity","category":"Category",
        "content_url":"Content or URL","memo":"Additional Memo (optional)","memo_placeholder":"Your judgment, special notes, etc.",
        "ai_result":"🤖 View AI Analysis","yt_open_video":"▶️ Watch on YouTube",
        "enter_content":"Please enter content.","report_detail":"Report Detail",
        "written_by":"Author","written_at":"Created","updated_at":"Updated",
        "content":"**Content**","analysis":"**Analysis Result**","edit_report":"✏️ Edit Report",
        "edit_sev":"Edit Severity","edit_cat":"Edit Category","edit_result":"Edit Analysis",
        "edit_saved":"✅ Saved!","delete_report":"🗑️ Delete This Report",
        "report_list":"📁 Reports","filter_sev":"Severity Filter","filter_cat":"Category Filter",
        "filter_writer":"Author Filter","all":"All","no_reports":"No reports yet.",
        "sev_1":"1—Safe","sev_2":"2—Low Risk","sev_3":"3—Medium Risk","sev_4":"4—High Risk","sev_5":"5—Critical",
        "cat_safe":"Safe","cat_spam":"Spam","cat_bad":"Inappropriate","cat_adult":"Adult","cat_groom":"Grooming","cat_unclassified":"Unclassified",
        "plat_yt":"YouTube","plat_rb":"Roblox","plat_mc":"Minecraft","plat_etc":"Other",
        "history_title":"📜 Search History","history_caption":"All analyzed videos (up to 1,000)",
        "filter_type":"Search Type","filter_reported":"Report Status","reported":"Reported","not_reported":"Not Reported",
        "after_date":"After Date","assignee":"Assignee","unassigned":"Unassigned","write_btn":"📋 Write",
        "stats_title":"📈 {}'s Performance","stat_month":"This Month","stat_rate":"Achievement",
        "stat_total":"Total","stat_target":"Monthly Target","goal_achieved":"🎉 Monthly goal achieved!",
        "goal_good":"💪 Doing great!","goal_keep":"📌 Keep going!","admin_comment":"💬 Admin Comments",
        "admin_title":"👑 Admin Dashboard","admin_team":"📊 Team Overview","admin_assign":"🎯 Assign Tasks",
        "admin_token":"🪙 Token Management","admin_email":"📧 Recipients","admin_log":"📨 Send Log",
        "send_comment":"Send Comment","select_member":"Select Member","comment_content":"Comment",
        "comment_sent":"✅ Sent to {}!","comment_empty":"Please enter a comment.",
        "email_bulk":"📧 Bulk Email Selected Reports","email_recipient":"Select Recipients","email_subject":"Subject",
        "email_memo":"Additional Memo (optional)","email_send":"📧 Send to Selected Recipients (Preview)",
        "email_preview":"📄 Send Preview","email_no_rec":"No recipients. Add them in the Admin tab.",
        "email_single":"📧 Send","email_sent_ok":"✅ Queued for delivery to {}",
        "new_recipient":"**Add New Recipient**","rec_name":"Name / Organization","rec_email":"Email","rec_type":"Type",
        "rec_memo":"Memo (optional)","rec_add":"➕ Add Recipient","rec_added":"✅ {} added!",
        "rec_list":"Registered Recipients","rec_active":"✅ Active","rec_inactive":"❌ Inactive",
        "deactivate":"❌ Deactivate","activate":"✅ Activate",
        "save_error":"Save error: {}","delete_error":"Delete error: {}","error":"Error: {}","no_url":"Please enter a URL.",
    },
    "ja": {
        "app_title":"🐉 ドラゴンアイズ モニタリング","this_month":"📅 今月","home":"🏠 ホーム",
        "write_report":"📋 レポート作成","logout":"🚪 ログアウト","prev":"◀ 戻る",
        "submit":"✅ レポート提出","cancel":"❌ キャンセル","detail":"詳細を見る","delete":"🗑️ 削除",
        "save":"💾 変更を保存","close":"閉じる","total":"合計","unit_reports":"件","unit_times":"回",
        "login_title":"🐉 ドラゴンアイズ","login_sub":"内部モニタリングシステム ログイン",
        "email":"メールアドレス","password":"パスワード","login_btn":"ログイン","login_ok":"ログイン成功",
        "login_fail":"ログイン失敗","login_warn":"メールとパスワードを入力してください。","no_user":"ユーザー情報が見つかりません。",
        "greeting":"👋 こんにちは、{}さん！","month_report":"📅 今月のレポート","goal":"目標 {}件",
        "achievement":"🎯 達成率","dragon_token":"🐉 ドラゴントークン","token_remain":"残り{}回",
        "pending_list":"件 未処理","shortcut":"📌 クイックアクセス","assigned_pending":"⚠️ 担当未作成リスト（{}件）",
        "tab_text":"📝 テキスト分析","tab_youtube":"🎬 YouTube分析","tab_keyword":"🔍 キーワード検索",
        "tab_dragon":"🐉 ドラゴンアイズ推薦","tab_history":"📜 検索履歴",
        "tab_reports":"📁 レポート一覧","tab_stats":"📈 マイ実績","tab_admin":"👑 管理者",
        "text_title":"テキストコンテンツ分析","text_input":"分析するテキストを入力",
        "analyze_start":"分析開始","analyzing":"分析中...","result_title":"分析結果",
        "to_report":"📋 レポートとして作成","enter_text":"テキストを入力してください。",
        "yt_title":"YouTube動画分析","yt_url":"YouTube URLを入力","yt_collecting":"データ収集中...",
        "yt_analyzing":"AI分析中...","yt_open":"▶️ YouTubeで見る","enter_url":"URLを入力してください。",
        "kw_title":"キーワード自動検索","kw_input":"検索キーワード","kw_count":"分析する動画数",
        "kw_start":"自動検索開始","kw_searching":"「{}」を検索中...","kw_skipped":"⏭️ 分析済み{}件を除外",
        "kw_no_new":"新しい動画がありません。別のキーワードを試してください。",
        "kw_analyzing":"新規{}件の分析開始...","kw_done":"完了！{}件分析済み",
        "kw_results":"検索結果（{}件）","kw_clear":"🗑️ 結果をクリア","enter_keyword":"キーワードを入力してください。",
        "dragon_title":"🐉 ドラゴンアイズ推薦モニタリングリスト",
        "dragon_caption":"AIがプラットフォーム別のリスクキーワードを自動生成しYouTubeを検索します。分析済み動画は自動除外。",
        "dragon_used":"今月使用","dragon_today":"本日使用","dragon_remain":"月間残り",
        "dragon_monthly_limit":"今月の上限に達しました。管理者に追加トークンを申請してください。",
        "dragon_daily_limit":"本日の上限（{}回）に達しました。明日また使用できます。",
        "dragon_general":"🐉 一般推薦","dragon_roblox":"🎮 Roblox推薦","dragon_minecraft":"⛏️ Minecraft推薦",
        "dragon_kw_gen":"{} リスクキーワード生成中...","dragon_kw_done":"{}個のキーワードを生成しました！",
        "dragon_kw_fail":"キーワード生成に失敗しました。","dragon_scanning":"「{}」を検索中... ({}/{})",
        "dragon_complete":"完了！{} — {}件中 要注意{}件発見",
        "dragon_risky":"🚨 要注意（{}件）","dragon_safe":"✅ 安全判定（{}件）","dragon_clear":"🗑️ 結果をクリア",
        "sort":"並び替え","sort_sev_high":"深刻度：高い順","sort_sev_low":"深刻度：低い順",
        "sort_newest":"新しい順","sort_oldest":"古い順",
        "report_title":"📋 レポート作成","platform":"プラットフォーム","severity":"深刻度","category":"分類",
        "content_url":"コンテンツ内容またはURL","memo":"追加メモ（任意）","memo_placeholder":"直接の判断、特記事項など",
        "ai_result":"🤖 AI分析結果を見る","yt_open_video":"▶️ YouTubeで動画を開く",
        "enter_content":"コンテンツ内容を入力してください。","report_detail":"レポート詳細",
        "written_by":"作成者","written_at":"作成日","updated_at":"更新日",
        "content":"**コンテンツ内容**","analysis":"**分析結果**","edit_report":"✏️ レポート編集",
        "edit_sev":"深刻度を変更","edit_cat":"分類を変更","edit_result":"分析結果を編集",
        "edit_saved":"✅ 保存しました！","delete_report":"🗑️ このレポートを削除",
        "report_list":"📁 レポート一覧","filter_sev":"深刻度フィルター","filter_cat":"分類フィルター",
        "filter_writer":"作成者フィルター","all":"すべて","no_reports":"まだレポートがありません。",
        "sev_1":"1—安全","sev_2":"2—低リスク","sev_3":"3—中リスク","sev_4":"4—高リスク","sev_5":"5—重大",
        "cat_safe":"安全","cat_spam":"スパム","cat_bad":"不適切","cat_adult":"成人向け","cat_groom":"グルーミング","cat_unclassified":"未分類",
        "plat_yt":"YouTube","plat_rb":"Roblox","plat_mc":"Minecraft","plat_etc":"その他",
        "history_title":"📜 検索履歴","history_caption":"分析済み動画一覧（最大1,000件）",
        "filter_type":"検索タイプ","filter_reported":"レポート状況","reported":"作成済み","not_reported":"未作成",
        "after_date":"日付以降","assignee":"担当者","unassigned":"未割り当て","write_btn":"📋 作成",
        "stats_title":"📈 {}さんの実績","stat_month":"今月","stat_rate":"達成率",
        "stat_total":"累計","stat_target":"今月の目標","goal_achieved":"🎉 今月の目標達成！",
        "goal_good":"💪 よくできています！","goal_keep":"📌 継続しましょう！","admin_comment":"💬 管理者コメント",
        "admin_title":"👑 管理者ダッシュボード","admin_team":"📊 チーム状況","admin_assign":"🎯 タスク割り当て",
        "admin_token":"🪙 トークン管理","admin_email":"📧 受信者管理","admin_log":"📨 送信履歴",
        "send_comment":"コメント送信","select_member":"メンバーを選択","comment_content":"コメント内容",
        "comment_sent":"✅ {}さんへ送信しました！","comment_empty":"コメントを入力してください。",
        "email_bulk":"📧 選択レポート一括メール送信","email_recipient":"受信者を選択","email_subject":"件名",
        "email_memo":"追加メモ（任意）","email_send":"📧 選択した受信者へ一括送信（プレビュー）",
        "email_preview":"📄 送信プレビュー","email_no_rec":"受信者が登録されていません。管理者タブで追加してください。",
        "email_single":"📧 送信","email_sent_ok":"✅ {}へ送信予定として保存されました",
        "new_recipient":"**新規受信者登録**","rec_name":"名前 / 機関名","rec_email":"メールアドレス","rec_type":"種別",
        "rec_memo":"メモ（任意）","rec_add":"➕ 受信者を登録","rec_added":"✅ {}を登録しました！",
        "rec_list":"登録済み受信者一覧","rec_active":"✅ 有効","rec_inactive":"❌ 無効",
        "deactivate":"❌ 無効化","activate":"✅ 有効化",
        "save_error":"保存エラー: {}","delete_error":"削除エラー: {}","error":"エラー: {}","no_url":"URLを入力してください。",
    }
}

def t(key, *args):
    lang = st.session_state.get("lang", "ko")
    text = LANG.get(lang, LANG["ko"]).get(key, LANG["ko"].get(key, key))
    if args:
        try: return text.format(*args)
        except: return text
    return text

defaults = {
    "user": None,
    "access_token": None,
    "report_count": 0,
    "lang": "ko",
    "current_page": "home_landing",
    "prev_page": "home_landing",
    "active_tab": 0,
    "prefill_content": "",
    "prefill_result": "",
    "prefill_severity": 1,
    "prefill_category": "안전",
    "prefill_platform": "YouTube",
    "selected_report": None,
    "search_results": [],
    "recommend_results": [],
    "chat_history": [],
    "dragon_fullscreen": False,
    "contact_hq_recipient": "kingcas7@gmail.com",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── 새로고침 세션 복원 ──
params = st.query_params
if "token" in params and st.session_state.user is None:
    try:
        token = params["token"]
        result = supabase.auth.get_user(token)
        if result.user:
            ud = supabase.table("users").select("*").eq("email", result.user.email).execute()
            if ud.data:
                st.session_state.user = ud.data[0]
                st.session_state.access_token = token
                this_month = date.today().strftime("%Y-%m")
                res = supabase.table("reports").select("id").eq("user_id", ud.data[0]["id"]).gte("created_at", f"{this_month}-01").execute()
                st.session_state.report_count = len(res.data)
                st.session_state.current_page = "home_landing"
    except Exception:
        st.query_params.clear()

# ══════════════════════════════
# 조직 관리 헬퍼 함수
# ══════════════════════════════

def get_user_role(user):
    """역할 반환: superadmin > group_leader > director > team_leader > user"""
    return user.get("role_v2") or ("admin" if user.get("role") == "admin" else "user")

def is_superadmin(user):
    return get_user_role(user) == "superadmin"

def is_director(user):
    return get_user_role(user) in (
        "superadmin",
        "group_leader", "group_leader_2", "group_leader_3", "group_leader_4",
        "director", "director_2", "director_3", "director_4",
    )

def is_team_leader(user):
    return get_user_role(user) in (
        "superadmin",
        "group_leader", "group_leader_2", "group_leader_3", "group_leader_4",
        "director", "director_2", "director_3", "director_4",
        "team_leader",
    )

def can_approve(user, target_user=None):
    role = get_user_role(user)
    if role in ("superadmin", "group_leader", "director"):
        return True
    if role == "team_leader":
        if target_user is None:
            return True
        return target_user.get("team_id") == user.get("team_id")
    return False

def get_all_users():
    try:
        return supabase.table("users").select("*").execute().data or []
    except:
        return []

def get_all_teams():
    try:
        return supabase.table("teams").select("*").execute().data or []
    except:
        return []

def get_team_members(team_id):
    try:
        return supabase.table("users").select("*").eq("team_id", team_id).execute().data or []
    except:
        return []

def get_unread_announcements(user_id):
    try:
        all_ann = supabase.table("announcements").select("id").eq("is_deleted", False).execute().data or []
        read_ids = [r["announcement_id"] for r in (supabase.table("announcement_reads").select("announcement_id").eq("user_id", user_id).execute().data or [])]
        return [a for a in all_ann if a["id"] not in read_ids]
    except:
        return []

def mark_announcement_read(announcement_id, user_id):
    try:
        supabase.table("announcement_reads").upsert({
            "announcement_id": announcement_id,
            "user_id": user_id,
        }).execute()
    except:
        pass

def get_pending_leaves(user_id, role):
    try:
        if role in ("superadmin", "group_leader", "group_leader_2", "group_leader_3", "group_leader_4", "director", "director_2", "director_3", "director_4"):
            return supabase.table("leave_requests").select("*").eq("status", "pending").order("created_at", desc=True).execute().data or []
        elif role == "team_leader":
            team_members = supabase.table("users").select("id").eq("team_id", supabase.table("users").select("team_id").eq("id", user_id).execute().data[0].get("team_id")).execute().data or []
            member_ids = [m["id"] for m in team_members]
            if member_ids:
                return supabase.table("leave_requests").select("*").in_("user_id", member_ids).eq("status", "pending").order("created_at", desc=True).execute().data or []
        return []
    except:
        return []

# ══════════════════════════════
# 헬퍼 함수
# ══════════════════════════════
def get_month_count(user_id):
    this_month = date.today().strftime("%Y-%m")
    res = supabase.table("reports").select("id").eq("user_id", user_id).gte("created_at", f"{this_month}-01").execute()
    return len(res.data)

def login(email, password):
    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if result.user:
            ud = supabase.table("users").select("*").eq("email", email).execute()
            if ud.data:
                st.session_state.user = ud.data[0]
                st.session_state.access_token = result.session.access_token
                st.session_state.report_count = get_month_count(ud.data[0]["id"])
                st.query_params["token"] = result.session.access_token
                return True, "로그인 성공"
            return False, "사용자 정보를 찾을 수 없습니다."
    except Exception as e:
        return False, f"로그인 실패: {str(e)}"
    return False, "로그인 실패"

def is_weekday():
    return True

def get_chat_token_info(user_id):
    ym = date.today().strftime("%Y-%m")
    res = supabase.table("chat_tokens").select("*").eq("user_id", user_id).eq("year_month", ym).execute()
    if res.data:
        return res.data[0]
    supabase.table("chat_tokens").insert({
        "user_id": user_id, "year_month": ym,
        "used_count": 0, "extra_tokens": 0
    }).execute()
    return {"used_count": 0, "extra_tokens": 0}

def get_chat_today_count(user_id):
    today = date.today().isoformat()
    res = supabase.table("chat_logs").select("id").eq("user_id", user_id).gte("created_at", today).execute()
    return len(res.data)

def get_chat_week_count(user_id):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    res = supabase.table("chat_logs").select("id").eq("user_id", user_id).gte("created_at", monday.isoformat()).execute()
    return len(res.data)

def can_use_chat(user_id):
    if not is_weekday():
        return {"ok": False, "reason": "weekend"}
    info = get_chat_token_info(user_id)
    monthly_limit = CHAT_MONTHLY_LIMIT + info.get("extra_tokens", 0)
    monthly_used = info["used_count"]
    today_used = get_chat_today_count(user_id)
    week_used = get_chat_week_count(user_id)
    if monthly_used >= monthly_limit:
        return {"ok": False, "reason": "monthly", "monthly_used": monthly_used, "monthly_limit": monthly_limit, "today_used": today_used, "week_used": week_used}
    if week_used >= CHAT_WEEKLY_LIMIT:
        return {"ok": False, "reason": "weekly", "monthly_used": monthly_used, "monthly_limit": monthly_limit, "today_used": today_used, "week_used": week_used}
    if today_used >= CHAT_DAILY_LIMIT:
        return {"ok": False, "reason": "daily", "monthly_used": monthly_used, "monthly_limit": monthly_limit, "today_used": today_used, "week_used": week_used}
    return {
        "ok": True, "reason": None,
        "monthly_used": monthly_used, "monthly_limit": monthly_limit,
        "monthly_remaining": monthly_limit - monthly_used,
        "today_used": today_used, "today_remaining": CHAT_DAILY_LIMIT - today_used,
        "week_used": week_used, "week_remaining": CHAT_WEEKLY_LIMIT - week_used,
    }

def use_chat_token(user_id):
    ym = date.today().strftime("%Y-%m")
    info = get_chat_token_info(user_id)
    supabase.table("chat_tokens").update({
        "used_count": info["used_count"] + 1,
        "updated_at": datetime.now().isoformat()
    }).eq("user_id", user_id).eq("year_month", ym).execute()

def add_chat_extra_tokens(user_id, amount):
    ym = date.today().strftime("%Y-%m")
    info = get_chat_token_info(user_id)
    supabase.table("chat_tokens").update({
        "extra_tokens": info.get("extra_tokens", 0) + amount,
        "updated_at": datetime.now().isoformat()
    }).eq("user_id", user_id).eq("year_month", ym).execute()

def chat_with_ai(messages_history, user_message, lang="ko"):
    system_prompt = {
        "ko": """당신은 Dragon J Holdings의 드래곤파더입니다. DragonEyes 팀의 든든한 AI 동반자입니다.
아동 온라인 안전, 그루밍 패턴, 보고서 작성 등 업무 질문은 물론, 일상 대화, 고민 상담, 잡담, 유머, 퀴즈 등 어떤 주제든 자유롭게 대화할 수 있습니다.
최신 정보가 필요한 질문(최근 뉴스, 최신 트렌드, 새로운 법령 등)은 웹 검색을 활용해 답변하세요.
팀원들이 즐겁고 편안하게 일할 수 있도록 친근하고 따뜻하게 대화해주세요.""",
        "en": """You are DragonFather, the friendly AI companion of Dragon J Holdings DragonEyes team.
You can help with child safety work, grooming patterns, and reports — but also chat freely about anything: daily life, jokes, trivia, advice, or casual conversation.
For questions requiring up-to-date information (recent news, trends, new laws), use web search to provide accurate answers.
Be warm, fun, and supportive. Help the team enjoy their work.""",
        "ja": """あなたはDragon J Holdings DragonEyesチームの頼れるAIコンパニオン、ドラゴンファーザーです。
子どもの安全業務はもちろん、日常会話、悩み相談、雑談、ユーモア、クイズなど、どんな話題でも自由に話せます。
最新情報が必要な質問はウェブ検索を活用して回答してください。
チームメンバーが楽しく快適に仕事できるよう、親しみやすく温かく接してください。"""
    }

    tools = [{"type": "web_search_20250305", "name": "web_search"}]
    recent = messages_history[-6:] if len(messages_history) > 6 else messages_history
    recent.append({"role": "user", "content": user_message[:300]})

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt.get(lang, system_prompt["ko"]),
        tools=tools,
        messages=recent
    )

    response_text = ""
    for block in msg.content:
        if hasattr(block, "text"):
            response_text += block.text
    return response_text if response_text else "답변을 생성하지 못했습니다."

def translate_to_english(text):
    if not text or len(text.strip()) < 5:
        return ""
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=1024,
            messages=[{"role": "user", "content": f"""Translate the following text to English accurately and concisely.
Keep technical terms, severity levels, and category names in English.
Return only the translated text without any explanation.

Text to translate:
{text}"""}]
        )
        return msg.content[0].text.strip()
    except Exception:
        return ""

def save_report(content, result, severity, category, platform="manual"):
    try:
        saved_search = list(st.session_state.search_results)
        saved_recommend = list(st.session_state.recommend_results)

        lang = st.session_state.get("lang", "ko")
        result_en = ""
        content_en = ""
        if lang in ("ko", "ja"):
            with st.spinner("🌐 영어 번역 중..." if lang == "ko" else "🌐 英語に翻訳中..."):
                result_en = translate_to_english(result)
                if content and "youtube.com" not in content:
                    content_en = translate_to_english(content)

        supabase.table("reports").insert({
            "user_id": st.session_state.user["id"],
            "content": content,
            "result": result,
            "severity": severity,
            "category": category,
            "platform": platform,
            "result_en": result_en,
            "content_en": content_en,
        }).execute()
        if "youtube.com" in content:
            supabase.table("analyzed_urls").update({"reported": True}).eq("url", content).execute()
        st.session_state.report_count = get_month_count(st.session_state.user["id"])
        st.session_state.search_results = saved_search
        st.session_state.recommend_results = saved_recommend
        return True
    except Exception as e:
        st.error(t("save_error", str(e)))
        return False

def delete_report(report_id):
    try:
        supabase.table("reports").delete().eq("id", report_id).execute()
        st.session_state.report_count = get_month_count(st.session_state.user["id"])
        return True
    except Exception as e:
        st.error(f"삭제 오류: {str(e)}")
        return False

def get_analyzed_urls():
    try:
        res = supabase.table("analyzed_urls").select("url").execute()
        return set(r["url"] for r in res.data)
    except Exception:
        return set()

def mark_url_analyzed(url, title="", search_type="keyword", assigned_to=None):
    try:
        data = {
            "url": url,
            "title": title,
            "search_type": search_type,
            "assigned_to": assigned_to,
            "assigned_at": datetime.now().isoformat() if assigned_to else None,
        }
        supabase.table("analyzed_urls").upsert(data).execute()
        all_urls = supabase.table("analyzed_urls").select("id").order("analyzed_at", desc=False).execute()
        if len(all_urls.data) > 1000:
            old_ids = [r["id"] for r in all_urls.data[:len(all_urls.data)-1000]]
            for oid in old_ids:
                supabase.table("analyzed_urls").delete().eq("id", oid).execute()
    except Exception:
        pass

def get_token_info(user_id):
    ym = date.today().strftime("%Y-%m")
    res = supabase.table("dragon_tokens").select("*").eq("user_id", user_id).eq("year_month", ym).execute()
    if res.data:
        return res.data[0]
    supabase.table("dragon_tokens").insert({
        "user_id": user_id,
        "year_month": ym,
        "used_count": 0,
        "extra_tokens": 0
    }).execute()
    return {"used_count": 0, "extra_tokens": 0}

def get_today_dragon_count(user_id):
    today = date.today().isoformat()
    res = supabase.table("analyzed_urls").select("id").eq("assigned_to", user_id).gte("analyzed_at", today).in_("search_type", ["dragon_general","dragon_roblox","dragon_minecraft"]).execute()
    return len(res.data)

def use_dragon_token(user_id):
    ym = date.today().strftime("%Y-%m")
    info = get_token_info(user_id)
    supabase.table("dragon_tokens").update({
        "used_count": info["used_count"] + 1,
        "updated_at": datetime.now().isoformat()
    }).eq("user_id", user_id).eq("year_month", ym).execute()

def add_extra_tokens(user_id, amount):
    ym = date.today().strftime("%Y-%m")
    info = get_token_info(user_id)
    supabase.table("dragon_tokens").update({
        "extra_tokens": info.get("extra_tokens", 0) + amount,
        "updated_at": datetime.now().isoformat()
    }).eq("user_id", user_id).eq("year_month", ym).execute()

def can_use_dragon(user_id):
    info = get_token_info(user_id)
    used = info["used_count"]
    extra = info.get("extra_tokens", 0)
    monthly_limit = MONTHLY_DRAGON_LIMIT + extra
    today_used = get_today_dragon_count(user_id)
    return {
        "ok": used < monthly_limit and today_used < DAILY_DRAGON_LIMIT,
        "used": used,
        "monthly_limit": monthly_limit,
        "today_used": today_used,
        "daily_limit": DAILY_DRAGON_LIMIT,
        "monthly_remaining": monthly_limit - used,
        "daily_remaining": DAILY_DRAGON_LIMIT - today_used,
    }

def extract_severity(text):
    for i in range(5, 0, -1):
        if f"심각도: {i}" in text or f"심각도:{i}" in text:
            return i
    return 1

def extract_category(text):
    for cat in ["섹스토션", "폭력유도", "그루밍", "성인", "부적절", "스팸", "안전"]:
        if cat in text:
            return cat
    return "미분류"

def sev_icon(s):
    return {1:"✅", 2:"🟡", 3:"🟠", 4:"🔴", 5:"🚨"}.get(s, "❓")

GUIDELINE_BADGE_FULL = """
<div style="
    background: linear-gradient(135deg, #0a1628 0%, #0d1f3c 100%);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 12px 18px;
    margin: 8px 0 14px 0;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
">
    <span style="color:#94a3b8; font-size:0.72rem; font-weight:600; letter-spacing:0.08em; margin-right:4px; white-space:nowrap;">
        🛡️ 국제기관 가이드라인 준수
    </span>
    <span style="background:linear-gradient(135deg,#1a3a5c,#0e2a4a);border:1px solid #2563eb55;color:#60a5fa;font-size:0.68rem;font-weight:700;padding:4px 10px;border-radius:20px;letter-spacing:0.03em;white-space:nowrap;">🇺🇸 NCMEC 가이드라인 준수</span>
    <span style="background:linear-gradient(135deg,#1a3a5c,#0e2a4a);border:1px solid #7c3aed55;color:#a78bfa;font-size:0.68rem;font-weight:700;padding:4px 10px;border-radius:20px;letter-spacing:0.03em;white-space:nowrap;">🌍 WeProtect Global Alliance 기준 적용</span>
    <span style="background:linear-gradient(135deg,#1a3a5c,#0e2a4a);border:1px solid #059669aa;color:#34d399;font-size:0.68rem;font-weight:700;padding:4px 10px;border-radius:20px;letter-spacing:0.03em;white-space:nowrap;">🇬🇧 IWF 글로벌 기준 참고</span>
    <span style="background:linear-gradient(135deg,#1a3a5c,#0e2a4a);border:1px solid #d9770655;color:#fb923c;font-size:0.68rem;font-weight:700;padding:4px 10px;border-radius:20px;letter-spacing:0.03em;white-space:nowrap;">⚙️ Tech Coalition Developer Good Practices 준수</span>
</div>
"""

def search_type_label(st_val):
    return {
        "dragon_general": "🐉 일반추천",
        "dragon_roblox":  "🎮 Roblox추천",
        "dragon_minecraft":"⛏️ Minecraft추천",
        "keyword":        "🔍 키워드탐색",
    }.get(st_val, st_val)

def go_to(page, from_tab=None):
    st.session_state.prev_page = st.session_state.current_page
    st.session_state.prev_tab = st.session_state.get("active_tab", 0)
    if from_tab is not None:
        st.session_state.active_tab = from_tab
    st.session_state.current_page = page

def go_back():
    st.session_state.current_page = st.session_state.prev_page
    st.session_state.active_tab = st.session_state.get("prev_tab", 0)
    st.session_state.prev_page = "home"

def go_home():
    st.session_state.current_page = "home_landing"
    st.session_state.prev_page = "home_landing"
    st.session_state.selected_report = None

def open_report_form(content="", result="", severity=1, category="안전", platform="YouTube", from_tab=None):
    st.session_state.prefill_content = content
    st.session_state.prefill_result = result
    st.session_state.prefill_severity = severity
    st.session_state.prefill_category = category
    st.session_state.prefill_platform = platform
    go_to("report_form", from_tab)

def parse_keywords(text):
    keywords = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line and line[0].isdigit():
            line = line.lstrip("0123456789.-) ").strip()
        if line and len(line) > 1:
            keywords.append(line)
    return keywords[:10]

def generate_recommend_keywords(platform="general"):
    import random
    keyword_pools = {
        "general": [
            "미성년자 채팅 만남", "초등학생 온라인 만남", "청소년 개인방송",
            "어린이 랜덤채팅", "중학생 SNS 만남", "10대 화상채팅",
            "미성년자 조건만남", "청소년 섹스토션 피해", "어린이 딥페이크 피해",
            "청소년 사진 협박", "10대 영상통화 위험", "어린이 온라인 성범죄",
            "미성년자 그루밍", "초등학생 유해 콘텐츠", "청소년 사이버성폭력",
        ],
        "gambling": [
            "청소년 불법도박 사이트", "초등학생 온라인도박", "미성년자 스포츠토토",
            "청소년 파워볼 사이트", "중학생 도박 빠짐", "10대 온라인카지노",
            "청소년 달팽이게임", "사다리게임 미성년자", "로하이 초등학생",
            "소셜그래프 청소년", "청소년 홀짝게임", "미성년자 바카라",
            "청소년 도박 알바", "학생 대리베팅 모집", "미성년자 총판 모집",
            "청소년 도박자금 빌려줌", "학생 도박빚 협박", "10대 도박 사기",
        ],
        "roblox": [
            "로블록스 미성년자 만남", "로블록스 이상한 사람 신고", "로블록스 성인 접근",
            "로블록스 개인정보 요구", "로블록스 실제 만남 유도", "로블록스 어린이 위험",
            "로블록스 디스코드 유도", "로블록스 카카오톡 알려달라", "로블록스 사진 요구",
            "로블록스 나이 속임", "로블록스 선물 조건", "로블록스 협박 피해",
            "로블록스 성인 게임", "어린이 로블록스 성범죄", "로블록스 그루밍 피해",
        ],
        "minecraft": [
            "마인크래프트 미성년자 만남", "마인크래프트 이상한 서버 신고", "마인크래프트 성인 접근",
            "마인크래프트 개인정보 요구", "마인크래프트 실제 만남", "마인크래프트 어린이 위험",
            "마인크래프트 디스코드 유도", "마인크래프트 카카오톡 알려달라", "마인크래프트 사진 요구",
            "마인크래프트 나이 속임", "마인크래프트 선물 조건", "마인크래프트 협박",
            "마인크래프트 성인 서버", "어린이 마인크래프트 성범죄", "마인크래프트 그루밍",
        ],
    }
    pool = keyword_pools.get(platform, keyword_pools["general"])
    return random.sample(pool, min(10, len(pool)))

def search_and_analyze(keyword, max_results=5, analyzed_urls=None, search_type="keyword", assigned_to=None):
    if analyzed_urls is None:
        analyzed_urls = set()

    sr = youtube.search().list(
        part="snippet", q=keyword, type="video",
        maxResults=max_results + 10,
        relevanceLanguage="ko",
        order="date",
        regionCode="KR",
        safeSearch="none"
    ).execute()

    results = []
    for item in sr.get("items", []):
        if len(results) >= max_results:
            break
        vid = item["id"]["videoId"]
        url = f"https://www.youtube.com/watch?v={vid}"
        if url in analyzed_urls:
            continue
        title = item["snippet"]["title"]
        desc = item["snippet"].get("description", "")[:300]
        channel = item["snippet"]["channelTitle"]
        published = item["snippet"].get("publishedAt", "")[:10]

        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=400,
            messages=[{"role": "user", "content": f"""아동 온라인 안전 모니터링 전문가로서 다음 유튜브 영상이 아동에게 위험한지 분석해주세요.

제목: {title}
채널: {channel}
업로드일: {published}
설명: {desc}

다음 기준으로 위험도를 판단하세요:
- 어린이/청소년을 대상으로 접근하거나 유인하는 내용
- 무료 아이템/선물/게임 혜택으로 미성년자를 유혹하는 내용
- 개인정보 요구, 외부 플랫폼(디스코드/카카오톡 등)으로 이동 유도
- 사진/영상 협박, 딥페이크 피해 관련 내용
- 위험한 챌린지, 자해 유도 내용

반드시 아래 형식으로만 답변하세요:
심각도: (1~5)
분류: (안전/스팸/부적절/성인/그루밍/섹스토션/폭력유도)
위험신호: (발견된 위험 패턴, 없으면 "없음")
이유: (한 줄 요약)"""}]
        )
        rt = msg.content[0].text
        sev = extract_severity(rt)
        cat = extract_category(rt)

        if search_type in ["dragon_general", "dragon_roblox", "dragon_minecraft"]:
            if sev < 3 or cat in ["안전", "스팸"]:
                analyzed_urls.add(url)
                mark_url_analyzed(url, title, search_type, assigned_to)
                continue

        mark_url_analyzed(url, title, search_type, assigned_to)
        results.append({
            "id": vid, "title": title, "channel": channel,
            "url": url, "keyword": keyword, "analysis": rt,
            "severity": sev, "category": cat, "search_type": search_type,
            "published": published
        })
        analyzed_urls.add(url)
    return results

# ══════════════════════════════
# 로그인 화면
# ══════════════════════════════
if st.session_state.user is None:
    lc1, lc2, lc3, lc4 = st.columns([6,1,1,1])
    st.markdown("""
    <style>
    button[key="login_flag_ko"] p, button[key="login_flag_en"] p, button[key="login_flag_ja"] p {
        font-size: 2.2rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    with lc2:
        if st.button("🇰🇷", help="한국어", key="login_flag_ko"): st.session_state.lang = "ko"; st.rerun()
    with lc3:
        if st.button("🇺🇸", help="English", key="login_flag_en"): st.session_state.lang = "en"; st.rerun()
    with lc4:
        if st.button("🇯🇵", help="日本語", key="login_flag_ja"): st.session_state.lang = "ja"; st.rerun()

    st.title(t("login_title"))
    st.subheader(t("login_sub"))
    st.divider()
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        email = st.text_input(t("email"))
        password = st.text_input(t("password"), type="password")
        if st.button(t("login_btn"), use_container_width=True):
            if email and password:
                with st.spinner(t("analyzing")):
                    ok, msg = login(email, password)
                if ok:
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning(t("login_warn"))

# ══════════════════════════════
# 메인 앱
# ══════════════════════════════
else:
    user = st.session_state.user
    is_admin = user.get("role") == "admin" or user.get("role_v2") in (
        "superadmin",
        "group_leader", "group_leader_2", "group_leader_3", "group_leader_4",
        "director", "director_2", "director_3", "director_4",
    )
    user_role = get_user_role(user)
    is_super = is_superadmin(user)
    is_dir   = is_director(user)
    is_lead  = is_team_leader(user)
    is_high  = is_dir

    page = st.session_state.current_page

    # ── 미확인 공지 팝업 ──
    unread_ann = get_unread_announcements(user["id"])
    if unread_ann and "ann_popup_shown" not in st.session_state:
        st.session_state.ann_popup_shown = True
        latest = supabase.table("announcements").select("*").eq("id", unread_ann[0]["id"]).execute().data
        if latest:
            ann = latest[0]
            type_color = {"notice": "🔵", "work_order": "🟠", "urgent": "🚨"}.get(ann["type"], "📢")
            type_label = {"notice": "공지사항", "work_order": "업무지시", "urgent": "긴급공지"}.get(ann["type"], "공지")
            with st.container(border=True):
                st.markdown(f"### {type_color} {type_label}")
                st.markdown(f"**{ann['title']}**")
                st.markdown(ann["content"])
                st.caption(f"발송일: {str(ann.get('created_at',''))[:10]}")
                if st.button("✅ 확인", key="ann_popup_confirm"):
                    mark_announcement_read(ann["id"], user["id"])
                    st.session_state.pop("ann_popup_shown", None)
                    st.rerun()

    # ── 상단 헤더 ──
    _show_admin_btn = is_admin or is_super
    try:
        _unread_cnt = len(get_unread_announcements(user["id"]))
    except:
        _unread_cnt = 0
    _notice_label = f"📢 공지 🔴{_unread_cnt}" if _unread_cnt > 0 else "📢 공지"

    st.markdown("""
    <style>
    /* 헤더 버튼 박스 제거 — 텍스트만 표시 */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0.25rem 0.3rem !important;
        font-size: 1.0rem !important;
        color: #94a3b8 !important;
        transition: color 0.2s;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        background: transparent !important;
        color: #f1f5f9 !important;
        border: none !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] p {
        font-size: 1.0rem !important;
        padding: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if _show_admin_btn:
        h1, hf, h_work, h6, h7, h_notice, h_admin, h_profile, h8 = st.columns([2.2, 1.5, 0.7, 0.65, 0.75, 0.72, 0.8, 0.85, 0.65])
    else:
        h1, hf, h_work, h6, h7, h_notice, h_profile, h8 = st.columns([2.2, 1.5, 0.7, 0.65, 0.75, 0.72, 0.85, 0.65])

    with h1:
        title_text = t("app_title").replace("🐉 ", "").replace("🐉 ", "")
        st.markdown(f'<div style="font-size:1.6rem; font-weight:700; display:flex; align-items:center; gap:6px; margin:0; padding:4px 0">🐉 {title_text}</div>', unsafe_allow_html=True)
    with hf:
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            if st.button("🇰🇷", use_container_width=True, key="flag_ko", help="한국어"):
                st.session_state.lang = "ko"; st.rerun()
        with fc2:
            if st.button("🇺🇸", use_container_width=True, key="flag_en", help="English"):
                st.session_state.lang = "en"; st.rerun()
        with fc3:
            if st.button("🇯🇵", use_container_width=True, key="flag_ja", help="日本語"):
                st.session_state.lang = "ja"; st.rerun()
    with h_work:
        if st.button("💼 일하기", use_container_width=True, key="hdr_work_btn"):
            go_to("work_page"); st.rerun()
    with h6:
        if st.button("🏠 홈", use_container_width=True):
            go_home(); st.rerun()
    with h7:
        if st.button("📋 작성", use_container_width=True):
            open_report_form(from_tab=st.session_state.active_tab); st.rerun()
    with h_notice:
        if st.button(_notice_label, use_container_width=True, key="hdr_notice_btn"):
            st.session_state.current_page = "home"
            st.session_state.active_tab = 98
            st.rerun()
    if _show_admin_btn:
        with h_admin:
            if st.button("👑 관리자", use_container_width=True, key="hdr_admin_btn"):
                st.session_state.current_page = "home"
                st.session_state.active_tab = 99
                st.rerun()
    with h_profile:
        if st.button("👤 사용자", use_container_width=True, key="hdr_profile_btn"):
            go_to("user_profile"); st.rerun()
    with h8:
        if st.button("🚪", use_container_width=True, help="로그아웃"):
            st.query_params.clear()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    st.divider()

    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
        border-left: 5px solid #e94560;
        border-radius: 8px;
        padding: 0.5rem 1.2rem;
        margin-bottom: 0.3rem;
        color: white;
        font-size: 0.88rem;
        line-height: 1.5;
    ">
        🛡️ <strong>이 곳은 온라인 유해 컨텐츠를 모니터링하는 Claude 기반의 Agent AI 드래곤파더와 함께 작업하는 곳입니다.</strong><br>
        어린이 아동학대, 그루밍, 성폭력, 도박 등과 관련한 다양한 불법 컨텐츠를 감시합니다.
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════
    # 보고서 작성 페이지
    # ══════════════════════════════
    if page == "report_form":
        col_back, col_title = st.columns([1,5])
        with col_back:
            if st.button(t("prev")):
                go_back(); st.rerun()
        with col_title:
            st.subheader(t("report_title"))
            st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)
        with st.container(border=True):
            rc1, rc2 = st.columns(2)
            with rc1:
                pl = [t("plat_yt"), t("plat_rb"), t("plat_mc"), t("plat_etc")]
                pidx = 0
                report_platform = st.selectbox(t("platform"), pl, index=pidx)
                report_severity = st.selectbox(t("severity"), [1,2,3,4,5],
                    index=st.session_state.prefill_severity-1,
                    format_func=lambda x: t(f"sev_{x}"))
            with rc2:
                cl = [t("cat_safe"), t("cat_spam"), t("cat_bad"), t("cat_adult"), t("cat_groom")]
                report_category = st.selectbox(t("category"), cl)
            report_content = st.text_area(t("content_url"), value=st.session_state.prefill_content, height=100)
            report_memo = st.text_area(t("memo"), height=80, placeholder=t("memo_placeholder"))
            if st.session_state.prefill_result:
                with st.expander(t("ai_result")):
                    st.write(st.session_state.prefill_result)
            if report_content and "youtube.com" in report_content:
                st.markdown(f"[{t('yt_open_video')}]({report_content})")
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button(t("submit"), use_container_width=True, type="primary"):
                    if report_content:
                        final = st.session_state.prefill_result or f"[{t('cat_safe')}]\n{t('category')}: {report_category}\n{t('severity')}: {report_severity}"
                        if report_memo:
                            final += f"\n\n[{t('memo')}]\n{report_memo}"
                        if save_report(report_content, final, report_severity, report_category, report_platform.lower()):
                            prev = st.session_state.prev_page
                            st.session_state.prefill_content = ""
                            st.session_state.prefill_result = ""
                            st.session_state.current_page = prev
                            st.rerun()
                    else:
                        st.warning(t("enter_content"))
            with bc2:
                if st.button(t("cancel"), use_container_width=True):
                    go_back(); st.rerun()

    # ══════════════════════════════
    # 보고서 상세 페이지
    # ══════════════════════════════
    elif page == "report_detail":
        r = st.session_state.selected_report
        can_edit = is_admin or r.get("user_id") == user["id"]

        col_back, col_title = st.columns([1,5])
        with col_back:
            if st.button(t("prev")):
                go_back(); st.rerun()
        with col_title:
            sev = r.get("severity",0)
            st.subheader(f"{sev_icon(sev)} {t('report_detail')}")

        all_users_cache = supabase.table("users").select("id,name").execute()
        umap_cache = {u["id"]: u["name"] for u in (all_users_cache.data or [])}
        author_name = umap_cache.get(r.get("user_id",""), "?")

        with st.container(border=True):
            d1,d2,d3,d4 = st.columns(4)
            d1.metric(t("severity"), f"{sev_icon(sev)} {sev}")
            d2.metric(t("category"), r.get("category","-"))
            d3.metric(t("platform"), r.get("platform","-"))
            d4.metric(t("written_by"), author_name)
            st.caption(f"{t('written_at')}: {str(r.get('created_at',''))[:16]}" +
                      (f"  |  {t('updated_at')}: {str(r.get('updated_at',''))[:16]}" if r.get('updated_at') else ""))
            st.divider()
            st.markdown(t("content"))
            cv = r.get("content","")
            if "youtube.com" in cv:
                st.markdown(f"[{t('yt_open')}]({cv})")
            else:
                st.write(cv)
            st.divider()
            st.markdown(t("analysis"))
            result_en = r.get("result_en", "")
            lang = st.session_state.get("lang", "ko")
            orig_flag = "🇰🇷" if lang == "ko" else ("🇯🇵" if lang == "ja" else "🇺🇸")

            if result_en:
                rc1, rc2 = st.columns(2)
                with rc1:
                    st.markdown(f"**{orig_flag} 원문 / 原文**")
                    st.info(r.get("result",""))
                with rc2:
                    st.markdown("**🇺🇸 English**")
                    st.info(result_en)
            else:
                st.write(r.get("result",""))
                if st.button("🌐 영어로 번역 / Translate to English", key="translate_btn"):
                    with st.spinner("🌐 번역 중..."):
                        new_result_en = translate_to_english(r.get("result",""))
                        new_content_en = ""
                        if r.get("content","") and "youtube.com" not in r.get("content",""):
                            new_content_en = translate_to_english(r.get("content",""))
                        try:
                            supabase.table("reports").update({
                                "result_en": new_result_en,
                                "content_en": new_content_en,
                            }).eq("id", r["id"]).execute()
                            st.session_state.selected_report["result_en"] = new_result_en
                            st.session_state.selected_report["content_en"] = new_content_en
                            st.success("✅ 번역 완료!")
                            st.rerun()
                        except Exception as e:
                            st.error(t("save_error", str(e)))

            if can_edit:
                st.divider()
                with st.expander(t("edit_report")):
                    edit_sev = st.selectbox(t("edit_sev"), [1,2,3,4,5],
                        index=r.get("severity",1)-1,
                        format_func=lambda x: t(f"sev_{x}"), key="edit_sev")
                    cats = [t("cat_safe"), t("cat_spam"), t("cat_bad"), t("cat_adult"), t("cat_groom")]
                    edit_cat = st.selectbox(t("edit_cat"), cats, key="edit_cat")
                    edit_result = st.text_area(t("edit_result"), value=r.get("result",""), height=150, key="edit_result")
                    if st.button(t("save"), type="primary"):
                        try:
                            supabase.table("reports").update({
                                "severity": edit_sev, "category": edit_cat, "result": edit_result,
                                "updated_at": datetime.now().isoformat(), "updated_by": user["id"]
                            }).eq("id", r["id"]).execute()
                            st.session_state.selected_report["severity"] = edit_sev
                            st.session_state.selected_report["category"] = edit_cat
                            st.session_state.selected_report["result"] = edit_result
                            st.success(t("edit_saved")); st.rerun()
                        except Exception as e:
                            st.error(t("save_error", str(e)))
                if st.button(t("delete_report"), type="secondary"):
                    if delete_report(r["id"]):
                        go_back(); st.rerun()

    # ══════════════════════════════
    # 드래곤파더 전체화면 페이지
    # ══════════════════════════════
    elif page == "dragon_chat":
        lang = st.session_state.get("lang", "ko")
        col_back, col_title = st.columns([1, 5])
        with col_back:
            if st.button("◀ 홈으로"):
                go_home(); st.rerun()
        with col_title:
            st.subheader("🐲 드래곤파더 — 전체화면 대화")
            st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)

        chat_info = can_use_chat(user["id"])
        ci1, ci2, ci3 = st.columns(3)
        ci1.metric("오늘", f"{chat_info.get('today_used',0)}/{CHAT_DAILY_LIMIT}턴")
        ci2.metric("이번주", f"{chat_info.get('week_used',0)}/{CHAT_WEEKLY_LIMIT}턴")
        ci3.metric("이번달", f"{chat_info.get('monthly_used',0)}/{chat_info.get('monthly_limit', CHAT_MONTHLY_LIMIT)}턴")

        chat_box = st.container(height=550)
        with chat_box:
            if not st.session_state.chat_history:
                st.caption("💡 예: '이 댓글이 그루밍 패턴인지 분석해줘'")
                st.caption("💡 예: '보고서 작성할 때 주의사항은?'")
                st.caption("💡 예: 'Roblox에서 흔한 위험 패턴은?'")
                st.caption("💡 예: '오늘 점심 뭐 먹을까?' '농담 해줘' 등 자유롭게!")
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    with st.chat_message("user"):
                        st.write(msg["content"])
                else:
                    with st.chat_message("assistant", avatar="🐲"):
                        st.write(msg["content"])

        if not chat_info["ok"]:
            reason = chat_info.get("reason")
            if reason == "daily": st.warning(f"오늘 한도({CHAT_DAILY_LIMIT}턴) 도달")
            elif reason == "weekly": st.warning(f"이번 주 한도({CHAT_WEEKLY_LIMIT}턴) 도달")
            elif reason == "monthly": st.warning("이번 달 한도 도달. 관리자에게 추가 요청하세요.")

        ic1, ic2 = st.columns([6, 1])
        with ic1:
            fs_input = st.chat_input(
                "드래곤파더에게 뭐든 물어보세요... (300자)" if chat_info["ok"] else "사용 불가",
                max_chars=300, disabled=not chat_info["ok"], key="dragon_fs_input"
            )
        with ic2:
            if st.button("🗑️", help="대화 초기화", key="clear_fs"):
                st.session_state.chat_history = []; st.rerun()

        if fs_input and chat_info["ok"]:
            st.session_state.chat_history.append({"role": "user", "content": fs_input})
            with st.spinner("🐲 드래곤파더가 답변 중..."):
                try:
                    api_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history[:-1]]
                    response = chat_with_ai(api_history, fs_input, lang)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    supabase.table("chat_logs").insert({"user_id": user["id"], "message": fs_input, "response": response, "tokens_used": 1}).execute()
                    use_chat_token(user["id"])
                    st.rerun()
                except Exception as e:
                    st.session_state.chat_history.pop()
                    st.error(f"오류: {str(e)}")

    # ══════════════════════════════
    # 💼 일하기 페이지 (기존 홈 랜딩 내용)
    # ══════════════════════════════
    elif page == "work_page":
        lang = st.session_state.get("lang", "ko")
        col_back, col_title = st.columns([1, 5])
        with col_back:
            if st.button("◀ 홈으로"):
                go_home(); st.rerun()
        with col_title:
            st.subheader(f"💼 일하기 — {t('greeting', user['name'])}")

        st.divider()
        token_info = can_use_dragon(user["id"])
        all_my = supabase.table("reports").select("id,severity,created_at").eq("user_id", user["id"]).execute()
        df_my = pd.DataFrame(all_my.data) if all_my.data else pd.DataFrame()
        this_month = date.today().strftime("%Y-%m")
        month_cnt = len(df_my[df_my["created_at"].str[:7] == this_month]) if not df_my.empty else 0
        target = user.get("monthly_target", 10)
        rate = min(int(month_cnt / target * 100), 100) if target > 0 else 0
        history_cnt = len(st.session_state.search_results) + len(st.session_state.recommend_results)

        st.markdown(f"""
        <div style="display:flex; gap:8px; margin:4px 0;">
            <div style="flex:1; background:linear-gradient(135deg,#0ea5e9,#06b6d4); border-radius:8px; padding:6px 10px; text-align:center; box-shadow:0 2px 8px rgba(14,165,233,0.35);">
                <div style="font-size:0.68rem; color:#e0f7ff;">{t('month_report')}</div>
                <div style="font-size:1.1rem; font-weight:700; color:#ffffff;">{month_cnt}{t('unit_reports')}</div>
                <div style="font-size:0.62rem; color:#bae6fd;">↑ {t('goal', target)}</div>
            </div>
            <div style="flex:1; background:linear-gradient(135deg,#10b981,#34d399); border-radius:8px; padding:6px 10px; text-align:center; box-shadow:0 2px 8px rgba(16,185,129,0.35);">
                <div style="font-size:0.68rem; color:#d1fae5;">{t('achievement')}</div>
                <div style="font-size:1.1rem; font-weight:700; color:#ffffff;">{rate}%</div>
                <div style="font-size:0.62rem; color:#a7f3d0;">목표 {target}건</div>
            </div>
            <div style="flex:1; background:linear-gradient(135deg,#f59e0b,#fbbf24); border-radius:8px; padding:6px 10px; text-align:center; box-shadow:0 2px 8px rgba(245,158,11,0.35);">
                <div style="font-size:0.68rem; color:#fef3c7;">{t('dragon_token')}</div>
                <div style="font-size:1.1rem; font-weight:700; color:#ffffff;">{token_info['monthly_remaining']}</div>
                <div style="font-size:0.62rem; color:#fde68a;">회 남음</div>
            </div>
            <div style="flex:1; background:linear-gradient(135deg,#ec4899,#f472b6); border-radius:8px; padding:6px 10px; text-align:center; box-shadow:0 2px 8px rgba(236,72,153,0.35);">
                <div style="font-size:0.68rem; color:#fce7f3;">탐색 히스토리</div>
                <div style="font-size:1.1rem; font-weight:700; color:#ffffff;">{history_cnt}건</div>
                <div style="font-size:0.62rem; color:#fbcfe8;">대기중</div>
            </div>
        </div>
        <div style="background:#334155; border-radius:4px; height:6px; margin:4px 0;">
            <div style="background:#22c55e; width:{rate}%; height:6px; border-radius:4px;"></div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown('<div style="font-size:0.8rem; font-weight:600; color:#94a3b8; margin-bottom:4px;">🚀 바로가기</div>', unsafe_allow_html=True)
        if st.button("🐉 드래곤아이즈 모니터링 자동 추천 리스트 생성", use_container_width=True, type="primary"):
            st.session_state.current_page = "home"
            st.session_state.active_tab = 3
            st.rerun()
        gb1, gb2, gb3 = st.columns(3)
        with gb1:
            if st.button(t("tab_text"), use_container_width=True):
                st.session_state.current_page = "home"; st.rerun()
        with gb2:
            if st.button(t("tab_youtube"), use_container_width=True):
                st.session_state.current_page = "home"; st.rerun()
        with gb3:
            if st.button(t("tab_reports"), use_container_width=True):
                st.session_state.current_page = "home"; st.rerun()

        assigned = supabase.table("analyzed_urls").select("*").eq("assigned_to", user["id"]).eq("reported", False).order("analyzed_at", desc=True).limit(5).execute()
        if assigned.data:
            st.divider()
            st.subheader(t("assigned_pending", len(assigned.data)))
            for d in assigned.data:
                ac1, ac2 = st.columns([5,1])
                with ac1:
                    st.caption(f"{search_type_label(d.get('search_type',''))} | {str(d.get('analyzed_at',''))[:10]} | {d.get('title','')[:50]}")
                with ac2:
                    if st.button(t("write_btn"), key=f"work_rep_{d['id']}"):
                        open_report_form(d["url"], "", 1, "안전", "YouTube", from_tab=4)
                        st.session_state.current_page = "report_form"; st.rerun()

        # 역할별 팀 현황
        _role = get_user_role(user)
        this_month = date.today().strftime("%Y-%m")

        if _role in ("superadmin", "group_leader", "group_leader_2", "group_leader_3", "group_leader_4", "director", "director_2", "director_3", "director_4"):
            st.divider()
            st.markdown("### 📊 팀별 업무 현황")
            try:
                all_teams_dash = supabase.table("teams").select("*").execute().data or []
                all_users_dash = supabase.table("users").select("*").execute().data or []
                all_reports_dash = supabase.table("reports").select("user_id,created_at").execute().data or []
                umap_dash = {u["id"]: u for u in all_users_dash}
                if all_teams_dash:
                    for team in all_teams_dash:
                        members = [u for u in all_users_dash if u.get("team_id") == team["id"]]
                        leader = umap_dash.get(team.get("leader_id",""), {})
                        with st.expander(f"🏢 **{team['name']}** | 팀장: {leader.get('name','미지정')} | 팀원: {len(members)}명", expanded=True):
                            if members:
                                cols_header = st.columns([2.5, 1, 1, 1, 1])
                                cols_header[0].markdown("**이름**")
                                cols_header[1].markdown("**이번달**")
                                cols_header[2].markdown("**목표**")
                                cols_header[3].markdown("**달성률**")
                                cols_header[4].markdown("**누적**")
                                for m in members:
                                    m_reports = [r for r in all_reports_dash if r["user_id"] == m["id"]]
                                    m_month = len([r for r in m_reports if r["created_at"][:7] == this_month])
                                    m_total = len(m_reports)
                                    m_target = m.get("monthly_target", 10)
                                    m_rate = min(int(m_month/m_target*100), 100) if m_target > 0 else 0
                                    r_icon = role_icon(m.get("role_v2","user"))
                                    rate_color = "#22c55e" if m_rate >= 100 else ("#f59e0b" if m_rate >= 50 else "#ef4444")
                                    cols = st.columns([2.5, 1, 1, 1, 1])
                                    cols[0].write(f"{r_icon} {m['name']}")
                                    cols[1].write(f"{m_month}건")
                                    cols[2].write(f"{m_target}건")
                                    cols[3].markdown(f"<span style='color:{rate_color};font-weight:700'>{m_rate}%</span>", unsafe_allow_html=True)
                                    cols[4].write(f"{m_total}건")
                            else:
                                st.caption("팀원 없음")
                else:
                    st.info("생성된 팀이 없습니다.")
                no_team = [u for u in all_users_dash if not u.get("team_id")]
                if no_team:
                    with st.expander(f"👥 **팀 미배정** | {len(no_team)}명"):
                        for u in no_team:
                            u_reports = [r for r in all_reports_dash if r["user_id"] == u["id"]]
                            u_month = len([r for r in u_reports if r["created_at"][:7] == this_month])
                            r_icon = role_icon(u.get("role_v2","user"))
                            st.caption(f"{r_icon} {u['name']} ({u.get('email','')}) | 이번달 {u_month}건")
            except Exception as e:
                st.warning(f"팀 현황 불러오기 실패: {str(e)}")

        elif _role == "team_leader":
            st.divider()
            st.markdown("### 👥 내 팀 현황")
            try:
                my_team_id = user.get("team_id")
                if my_team_id:
                    team_members = supabase.table("users").select("*").eq("team_id", my_team_id).execute().data or []
                    all_reports_team = supabase.table("reports").select("user_id,created_at").execute().data or []
                    if team_members:
                        cols_h = st.columns([2.5, 1, 1, 1, 1])
                        cols_h[0].markdown("**이름**"); cols_h[1].markdown("**이번달**")
                        cols_h[2].markdown("**목표**"); cols_h[3].markdown("**달성률**"); cols_h[4].markdown("**누적**")
                        for m in team_members:
                            m_reports = [r for r in all_reports_team if r["user_id"] == m["id"]]
                            m_month = len([r for r in m_reports if r["created_at"][:7] == this_month])
                            m_total = len(m_reports)
                            m_target = m.get("monthly_target", 10)
                            m_rate = min(int(m_month/m_target*100), 100) if m_target > 0 else 0
                            is_me = "⭐ " if m["id"] == user["id"] else ""
                            rate_color = "#22c55e" if m_rate >= 100 else ("#f59e0b" if m_rate >= 50 else "#ef4444")
                            cols = st.columns([2.5, 1, 1, 1, 1])
                            cols[0].write(f"{is_me}{m['name']}")
                            cols[1].write(f"{m_month}건")
                            cols[2].write(f"{m_target}건")
                            cols[3].markdown(f"<span style='color:{rate_color};font-weight:700'>{m_rate}%</span>", unsafe_allow_html=True)
                            cols[4].write(f"{m_total}건")
                    else:
                        st.info("팀원이 없습니다.")
                else:
                    st.info("배정된 팀이 없습니다.")
            except Exception as e:
                st.warning(f"팀 현황 불러오기 실패: {str(e)}")

    # ══════════════════════════════
    # 👤 사용자 정보 페이지
    # ══════════════════════════════
    elif page == "user_profile":
        import io
        col_back, col_title = st.columns([1, 5])
        with col_back:
            if st.button("◀ 홈으로"):
                go_home(); st.rerun()
        with col_title:
            st.subheader("👤 사용자 정보")

        st.divider()

        # ── 내 정보 조회/수정 ──
        with st.container(border=True):
            st.markdown("### 📋 내 정보")
            pc1, pc2 = st.columns(2)
            with pc1:
                st.text_input("이름", value=user.get("name",""), disabled=True)
                st.text_input("이메일", value=user.get("email",""), disabled=True)
                st.text_input("소속 팀", value=user.get("team_id","미배정"), disabled=True)
                st.text_input("역할", value=role_label(user.get("role_v2","user")), disabled=True)
            with pc2:
                new_phone = st.text_input("📱 연락처 (휴대폰)", value=user.get("phone",""), placeholder="010-0000-0000")
                new_birth = st.text_input("🎂 생년월일", value=user.get("birthdate",""), placeholder="1990-01-01")
                new_addr = st.text_input("🏠 주소", value=user.get("address",""), placeholder="서울시 ...")
                new_emergency = st.text_input("🆘 비상연락처", value=user.get("emergency_contact",""), placeholder="관계 / 010-0000-0000")

            if st.button("💾 정보 저장", type="primary", use_container_width=True):
                try:
                    supabase.table("users").update({
                        "phone": new_phone,
                        "birthdate": new_birth,
                        "address": new_addr,
                        "emergency_contact": new_emergency,
                        "profile_updated_at": datetime.now().isoformat(),
                    }).eq("id", user["id"]).execute()
                    # 세션 업데이트
                    st.session_state.user["phone"] = new_phone
                    st.session_state.user["birthdate"] = new_birth
                    st.session_state.user["address"] = new_addr
                    st.session_state.user["emergency_contact"] = new_emergency
                    st.success("✅ 정보가 저장됐습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 오류: {str(e)}")

        st.divider()

        # ── 비밀번호 변경 ──
        with st.container(border=True):
            st.markdown("### 🔐 비밀번호 변경")
            pw1 = st.text_input("새 비밀번호", type="password", key="pw_new")
            pw2 = st.text_input("새 비밀번호 확인", type="password", key="pw_confirm")
            if st.button("🔐 비밀번호 변경", use_container_width=True):
                if not pw1:
                    st.warning("새 비밀번호를 입력해주세요.")
                elif pw1 != pw2:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif len(pw1) < 6:
                    st.warning("비밀번호는 6자 이상이어야 합니다.")
                else:
                    try:
                        supabase.auth.update_user({"password": pw1})
                        st.success("✅ 비밀번호가 변경됐습니다!")
                    except Exception as e:
                        st.error(f"변경 오류: {str(e)}")

        st.divider()

        # ── 본사에 연락하기 ──
        with st.container(border=True):
            st.markdown("### 📩 본사에 연락하기")
            st.caption(f"수신: {st.session_state.contact_hq_recipient}")
            contact_subject = st.text_input("제목", placeholder="문의 제목을 입력해주세요")
            contact_body = st.text_area("내용", height=120, placeholder="문의 내용을 입력해주세요")
            if st.button("📩 본사에 전송", type="primary", use_container_width=True):
                if contact_subject and contact_body:
                    try:
                        supabase.table("hq_messages").insert({
                            "from_user_id": user["id"],
                            "from_name": user["name"],
                            "from_email": user.get("email",""),
                            "subject": contact_subject,
                            "body": contact_body,
                            "recipient": st.session_state.contact_hq_recipient,
                        }).execute()
                        st.success("✅ 본사에 메시지가 전송됐습니다!")
                    except Exception as e:
                        st.error(f"전송 오류: {str(e)}")
                else:
                    st.warning("제목과 내용을 모두 입력해주세요.")

        # ── 디렉터 이상: 전체 사용자 정보 엑셀 출력 ──
        if is_dir:
            st.divider()
            with st.container(border=True):
                st.markdown("### 📊 전체 직원 정보 관리 (디렉터 이상)")
                try:
                    all_users_prof = supabase.table("users").select("*").order("name").execute().data or []
                    all_teams_prof = supabase.table("teams").select("*").execute().data or []
                    team_map = {t["id"]: t["name"] for t in all_teams_prof}

                    # 테이블 미리보기
                    preview_data = []
                    for u in all_users_prof:
                        preview_data.append({
                            "이름": u.get("name",""),
                            "이메일": u.get("email",""),
                            "역할": role_label(u.get("role_v2","user")),
                            "소속팀": team_map.get(u.get("team_id",""), "미배정"),
                            "연락처": u.get("phone",""),
                            "생년월일": u.get("birthdate",""),
                            "주소": u.get("address",""),
                            "비상연락처": u.get("emergency_contact",""),
                            "정보수정일": str(u.get("profile_updated_at",""))[:10],
                        })
                    df_prof = pd.DataFrame(preview_data)
                    st.dataframe(df_prof, use_container_width=True)

                    # 엑셀 다운로드
                    excel_buf = io.BytesIO()
                    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                        df_prof.to_excel(writer, index=False, sheet_name="직원정보")
                    excel_buf.seek(0)
                    st.download_button(
                        label="📥 전체 직원 정보 엑셀 다운로드",
                        data=excel_buf,
                        file_name=f"DragonEyes_직원정보_{date.today().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary",
                    )
                except Exception as e:
                    st.error(f"직원 정보 불러오기 오류: {str(e)}")

    # ══════════════════════════════
    # 홈 랜딩 페이지 (심플 버전)
    # ══════════════════════════════
    elif page == "home_landing":
        lang = st.session_state.get("lang", "ko")

        # 메인 2컬럼 레이아웃 — 드래곤파더 왼쪽, 통계+모니터링 오른쪽
        left_col, right_col = st.columns([1, 1])

        # ── 왼쪽: 드래곤파더 ──
        with left_col:
            st.markdown("""
            <style>
            div[data-testid="stVerticalBlock"]:has(> div > div > #dragonfather_anchor) {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                border: 1px solid #e94560;
                border-radius: 12px;
                box-shadow: 0 4px 24px rgba(233,69,96,0.35), 0 0 40px rgba(15,52,96,0.5);
                padding: 1rem 1rem 0.5rem 1rem;
            }
            </style>
            """, unsafe_allow_html=True)
            st.markdown('<span id="dragonfather_anchor"></span>', unsafe_allow_html=True)

            chat_info = can_use_chat(user["id"])
            da1, da2 = st.columns([3, 2])
            with da1:
                st.markdown('''
                <div style="display:flex; flex-direction:column; justify-content:center; height:100%; padding-top:4px;">
                    <div style="font-size:1.4rem; font-weight:700; color:#16a34a; line-height:1.2;">🐲 드래곤파더</div>
                    <div style="font-size:0.85rem; color:#4ade80; margin-top:2px;">✨ Agent AI 드래곤파더</div>
                </div>
                ''', unsafe_allow_html=True)
            with da2:
                st.markdown("<div style='padding-top:6px;'>", unsafe_allow_html=True)
                if st.button("🐲 큰 화면에서 대화하기", key="dragon_fs_btn", use_container_width=True):
                    go_to("dragon_chat"); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            today_u = chat_info.get('today_used',0)
            week_u = chat_info.get('week_used',0)
            month_u = chat_info.get('monthly_used',0)
            month_lim = chat_info.get('monthly_limit', CHAT_MONTHLY_LIMIT)
            st.markdown(f"""
            <div style="margin:2px 0 4px 0;">
                <div style="display:flex; gap:8px; align-items:center;">
                    <div style="text-align:center; padding:4px 8px; background:linear-gradient(135deg,#3b82f6,#6366f1); border-radius:8px; flex:1;">
                        <div style="font-size:0.58rem; color:#e0e7ff;">오늘</div>
                        <div style="font-size:0.85rem; font-weight:700; color:#ffffff;">{today_u}/{CHAT_DAILY_LIMIT}</div>
                    </div>
                    <div style="text-align:center; padding:4px 8px; background:linear-gradient(135deg,#6366f1,#8b5cf6); border-radius:8px; flex:1;">
                        <div style="font-size:0.58rem; color:#ede9fe;">이번주</div>
                        <div style="font-size:0.85rem; font-weight:700; color:#ffffff;">{week_u}/{CHAT_WEEKLY_LIMIT}</div>
                    </div>
                    <div style="text-align:center; padding:4px 8px; background:linear-gradient(135deg,#8b5cf6,#a855f7); border-radius:8px; flex:1;">
                        <div style="font-size:0.58rem; color:#fae8ff;">이번달</div>
                        <div style="font-size:0.85rem; font-weight:700; color:#ffffff;">{month_u}/{month_lim}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 미확인 공지
            try:
                recent_ann = supabase.table("announcements").select("*").eq("is_deleted", False).order("created_at", desc=True).limit(3).execute().data or []
                my_reads_home = [r["announcement_id"] for r in (supabase.table("announcement_reads").select("announcement_id").eq("user_id", user["id"]).execute().data or [])]
                unread_home = [a for a in recent_ann if a["id"] not in my_reads_home]
                if unread_home:
                    ann_icon_map = {"notice":"🔵","work_order":"🟠","urgent":"🚨"}
                    for ann_h in unread_home[:2]:
                        icon_h = ann_icon_map.get(ann_h["type"],"📢")
                        ann_date_h = str(ann_h.get("created_at",""))[:10]
                        st.markdown(f"""
                        <div style="background:linear-gradient(90deg,rgba(233,69,96,0.15),rgba(15,52,96,0.3));
                            border-left:3px solid #e94560; border-radius:6px;
                            padding:5px 10px; margin:3px 0; font-size:0.8rem;">
                            {icon_h} <strong style="color:#f1f5f9;">{ann_h['title']}</strong>
                            <span style="color:#94a3b8; margin-left:6px; font-size:0.72rem;">{ann_date_h}</span>
                            <span style="background:#e94560; color:white; border-radius:4px; padding:1px 5px; font-size:0.65rem; margin-left:4px;">미확인</span>
                        </div>
                        """, unsafe_allow_html=True)
            except:
                pass

            chat_box = st.container(height=340)
            with chat_box:
                if not st.session_state.chat_history:
                    st.caption("💡 예: '이 댓글이 그루밍 패턴인지 분석해줘'")
                    st.caption("💡 예: '보고서 작성할 때 주의사항은?'")
                    st.caption("💡 예: 'Roblox에서 흔한 위험 패턴은?'")
                for msg in st.session_state.chat_history[-10:]:
                    if msg["role"] == "user":
                        with st.chat_message("user"):
                            st.write(msg["content"])
                    else:
                        with st.chat_message("assistant", avatar="🐲"):
                            st.write(msg["content"])

            if not chat_info["ok"]:
                reason = chat_info.get("reason")
                if reason == "daily": st.warning(f"오늘 한도({CHAT_DAILY_LIMIT}턴) 도달")
                elif reason == "weekly": st.warning(f"이번 주 한도({CHAT_WEEKLY_LIMIT}턴) 도달")
                elif reason == "monthly": st.warning("이번 달 한도 도달.")

            ic1, ic2 = st.columns([5, 1])
            with ic1:
                home_input = st.chat_input(
                    "드래곤파더에게 질문하세요... (300자)" if chat_info["ok"] else "사용 불가",
                    max_chars=300, disabled=not chat_info["ok"], key="home_chat_input"
                )
            with ic2:
                if st.button("🗑️", help="대화 초기화", key="clear_chat_home"):
                    st.session_state.chat_history = []; st.rerun()

            if home_input and chat_info["ok"]:
                st.session_state.chat_history.append({"role": "user", "content": home_input})
                with st.spinner("🐲 드래곤파더가 답변 중..."):
                    try:
                        api_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history[:-1]]
                        response = chat_with_ai(api_history, home_input, lang)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        supabase.table("chat_logs").insert({"user_id": user["id"], "message": home_input, "response": response, "tokens_used": 1}).execute()
                        use_chat_token(user["id"])
                        st.rerun()
                    except Exception as e:
                        st.session_state.chat_history.pop()
                        st.error(f"오류: {str(e)}")

        # ── 오른쪽: 통계 (상단) + 모니터링 버튼 (하단) ──
        with right_col:

            # ① 통계 — 맨 위에 바짝
            st.markdown('<div style="font-size:0.82rem; font-weight:600; color:#94a3b8; margin-bottom:4px; padding-left:16px;">📊 통계 & 현황</div>', unsafe_allow_html=True)
            try:
                all_my_home = supabase.table("reports").select("id,severity,created_at").eq("user_id", user["id"]).execute()
                df_home = pd.DataFrame(all_my_home.data) if all_my_home.data else pd.DataFrame()
                this_month = date.today().strftime("%Y-%m")
                month_cnt_h = len(df_home[df_home["created_at"].str[:7] == this_month]) if not df_home.empty else 0
                target_h = user.get("monthly_target", 10)
                rate_h = min(int(month_cnt_h / target_h * 100), 100) if target_h > 0 else 0
                token_info_h = can_use_dragon(user["id"])

                # 숫자 크기 20% 축소 + 왼쪽 여백 추가
                st.markdown(f"""
                <div style="display:flex; gap:12px; padding:0 8px 0 16px; margin-bottom:4px;">
                    <div style="flex:1; background:#1e293b; border-radius:8px; padding:10px 14px;">
                        <div style="font-size:0.7rem; color:#94a3b8; margin-bottom:2px;">📅 이번달</div>
                        <div style="font-size:1.5rem; font-weight:700; color:#38bdf8; line-height:1.1;">{month_cnt_h}건</div>
                        <div style="font-size:0.65rem; color:#4ade80;">↑ 목표 {target_h}건</div>
                    </div>
                    <div style="flex:1; background:#1e293b; border-radius:8px; padding:10px 14px;">
                        <div style="font-size:0.7rem; color:#94a3b8; margin-bottom:2px;">🎯 달성률</div>
                        <div style="font-size:1.5rem; font-weight:700; color:#{'22c55e' if rate_h>=100 else 'f59e0b' if rate_h>=50 else 'e94560'}; line-height:1.1;">{rate_h}%</div>
                        <div style="font-size:0.65rem; color:#94a3b8;">목표 대비</div>
                    </div>
                    <div style="flex:1; background:#1e293b; border-radius:8px; padding:10px 14px;">
                        <div style="font-size:0.7rem; color:#94a3b8; margin-bottom:2px;">🐉 토큰</div>
                        <div style="font-size:1.5rem; font-weight:700; color:#a78bfa; line-height:1.1;">{token_info_h['monthly_remaining']}회</div>
                        <div style="font-size:0.65rem; color:#94a3b8;">남은 횟수</div>
                    </div>
                </div>
                <div style="background:#334155; border-radius:4px; height:6px; margin:0 8px 8px 16px;">
                    <div style="background:{'#22c55e' if rate_h>=100 else '#f59e0b' if rate_h>=50 else '#e94560'}; width:{rate_h}%; height:6px; border-radius:4px;"></div>
                </div>
                """, unsafe_allow_html=True)
            except:
                pass

            # ② 위젯 공간 (중간)
            st.markdown("""
            <div style="
                border: 2px dashed #334155;
                border-radius: 10px;
                padding: 28px 16px;
                text-align: center;
                color: #475569;
                font-size: 0.82rem;
                margin-bottom: 10px;
            ">📈 향후 통계 위젯이 추가될 공간입니다</div>
            """, unsafe_allow_html=True)

            # ③ 모니터링 버튼 (하단)
            st.markdown('<div style="font-size:0.82rem; font-weight:600; color:#94a3b8; margin-bottom:4px;">🐉 모니터링</div>', unsafe_allow_html=True)
            if st.button("🐉 드래곤아이즈 자동 추천 리스트 생성", use_container_width=True, type="primary", key="home_dragon_btn"):
                st.session_state.current_page = "home"
                st.session_state.active_tab = 3
                st.rerun()
            qa1, qa2, qa3 = st.columns(3)
            with qa1:
                if st.button("📝 텍스트 분석", use_container_width=True, key="home_text_btn"):
                    st.session_state.current_page = "home"; st.rerun()
            with qa2:
                if st.button("🎬 유튜브 분석", use_container_width=True, key="home_yt_btn"):
                    st.session_state.current_page = "home"; st.rerun()
            with qa3:
                if st.button("📁 보고서 목록", use_container_width=True, key="home_rep_btn"):
                    st.session_state.current_page = "home"; st.rerun()

    # ══════════════════════════════
    # 홈 대시보드
    # ══════════════════════════════
    elif page == "home":

        lang = st.session_state.get("lang", "ko")
        chat_info = can_use_chat(user["id"])

        with st.container(border=True):
            chat_header1, chat_header2, chat_header3, chat_header4 = st.columns([2,1,1,1])
            with chat_header1:
                st.markdown("### 🐲 드래곤파더")
            with chat_header2:
                st.metric("오늘", f"{chat_info.get('today_used',0)}/{CHAT_DAILY_LIMIT}턴")
            with chat_header3:
                st.metric("이번주", f"{chat_info.get('week_used',0)}/{CHAT_WEEKLY_LIMIT}턴")
            with chat_header4:
                st.metric("이번달", f"{chat_info.get('monthly_used',0)}/{chat_info.get('monthly_limit', CHAT_MONTHLY_LIMIT)}턴")

            if st.session_state.chat_history:
                chat_box = st.container(height=250)
                with chat_box:
                    for msg in st.session_state.chat_history[-10:]:
                        if msg["role"] == "user":
                            with st.chat_message("user"):
                                st.write(msg["content"])
                        else:
                            with st.chat_message("assistant", avatar="🐲"):
                                st.write(msg["content"])
            else:
                st.caption("💡 예: '이 댓글이 그루밍 패턴인지 분석해줘' / '보고서 작성 주의사항은?' / 'Roblox 위험 패턴은?'")

            if not chat_info["ok"]:
                reason = chat_info.get("reason")
                if reason == "weekend":
                    st.warning("😊 오늘은 주말입니다. AI 채팅은 평일(월~금)에만 사용 가능합니다.")
                elif reason == "daily":
                    st.warning(f"📌 오늘 한도({CHAT_DAILY_LIMIT}턴) 도달. 내일 다시 사용 가능합니다.")
                elif reason == "weekly":
                    st.warning(f"📌 이번 주 한도({CHAT_WEEKLY_LIMIT}턴) 도달. 다음 주 월요일에 재시작됩니다.")
                elif reason == "monthly":
                    st.warning("📌 이번 달 한도 도달. 관리자에게 추가 토큰을 요청하세요.")

            ic1, ic2 = st.columns([6, 1])
            with ic1:
                user_input = st.chat_input(
                    "드래곤파더에게 질문하세요... (최대 300자)" if chat_info["ok"] else "사용 불가 상태입니다",
                    max_chars=300,
                    disabled=not chat_info["ok"],
                    key="main_chat_input"
                )
            with ic2:
                if st.button("🗑️", help="대화 초기화", key="clear_chat_top"):
                    st.session_state.chat_history = []; st.rerun()

            if user_input and chat_info["ok"]:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                with st.spinner("🐲 드래곤파더가 답변 중..."):
                    try:
                        api_history = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.chat_history[:-1]
                        ]
                        response = chat_with_ai(api_history, user_input, lang)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        supabase.table("chat_logs").insert({
                            "user_id": user["id"],
                            "message": user_input,
                            "response": response,
                            "tokens_used": 1
                        }).execute()
                        use_chat_token(user["id"])
                        st.rerun()
                    except Exception as e:
                        st.session_state.chat_history.pop()
                        st.error(f"오류: {str(e)}")

        st.divider()

        active_tab_idx = st.session_state.get("active_tab", 0)

        tab_defs = [
            ("text",    t("tab_text")),
            ("youtube", t("tab_youtube")),
            ("keyword", t("tab_keyword")),
            ("dragon",  t("tab_dragon")),
            ("naver",   "🟢 네이버 탐색"),
            ("history", t("tab_history")),
            ("reports", t("tab_reports")),
            ("stats",   t("tab_stats")),
            ("notice",  "📢 공지사항"),
            ("chat",    "🐲 드래곤파더"),
        ]
        if is_admin or is_lead or is_super:
            tab_defs.append(("org", "🏢 조직관리"))
        if is_admin or is_super:
            tab_defs.append(("admin", t("tab_admin")))

        if active_tab_idx == 99:
            admin_keys = [i for i, d in enumerate(tab_defs) if d[0] == "admin"]
            if admin_keys:
                admin_item = tab_defs.pop(admin_keys[0])
                tab_defs.insert(0, admin_item)
            st.session_state.active_tab = 0

        if active_tab_idx == 98:
            notice_keys = [i for i, d in enumerate(tab_defs) if d[0] == "notice"]
            if notice_keys:
                notice_item = tab_defs.pop(notice_keys[0])
                tab_defs.insert(0, notice_item)
            st.session_state.active_tab = 0

        if active_tab_idx == 3:
            dragon_item = tab_defs.pop(3)
            tab_defs.insert(0, dragon_item)
            st.session_state.active_tab = 0

        tab_keys   = [d[0] for d in tab_defs]
        tab_labels = [d[1] for d in tab_defs]

        tabs = st.tabs(tab_labels)
        tab_map = {key: tabs[i] for i, key in enumerate(tab_keys)}

        tab1      = tab_map["text"]
        tab2      = tab_map["youtube"]
        tab3      = tab_map["keyword"]
        tab4      = tab_map["dragon"]
        tab_naver = tab_map["naver"]
        tab5      = tab_map["history"]
        tab6      = tab_map["reports"]
        tab7      = tab_map["stats"]
        tab_chat   = tab_map["chat"]
        tab_notice = tab_map.get("notice")
        tab_org    = tab_map.get("org")
        tab8       = tab_map.get("admin")

        # ── 텍스트 분석 ──
        with tab1:
            st.subheader(t("text_title"))
            st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)
            content = st.text_area(t("text_input"), height=150)
            if st.button(t("analyze_start"), key="text_go"):
                if content:
                    with st.spinner(t("analyzing")):
                        msg = client.messages.create(
                            model="claude-sonnet-4-20250514", max_tokens=1024,
                            messages=[{"role":"user","content":f"""아동 안전 모니터링 전문가로서 아래 콘텐츠를 분석해주세요.
콘텐츠: {content}
형식:
심각도: 1~5 (1=안전, 5=매우위험)
분류: (스팸/부적절/성인/그루밍/안전 중 하나)
이유: (간단한 설명)
조치: (권고 조치)"""}])
                    rt = msg.content[0].text
                    sev = extract_severity(rt); cat = extract_category(rt)
                    st.subheader(f"{sev_icon(sev)} {t('result_title')}")
                    st.write(rt)
                    if st.button(t("to_report"), key="text_report"):
                        open_report_form(content, rt, sev, cat, "기타", from_tab=0); st.rerun()
                else:
                    st.warning(t("enter_text"))

        # ── 유튜브 분석 ──
        with tab2:
            st.subheader(t("yt_title"))
            st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)
            url = st.text_input(t("yt_url"))
            if st.button(t("analyze_start"), key="yt_go"):
                if url:
                    try:
                        with st.spinner(t("yt_collecting")):
                            vid = url.split("v=")[-1].split("&")[0]
                            vr = youtube.videos().list(part="snippet", id=vid).execute()
                            sn = vr["items"][0]["snippet"]
                            title = sn["title"]; desc = sn.get("description","")[:500]; tags = sn.get("tags",[])
                            comments = []
                            try:
                                cr = youtube.commentThreads().list(part="snippet",videoId=vid,maxResults=50,order="relevance").execute()
                                for item in cr.get("items",[]):
                                    comments.append(item["snippet"]["topLevelComment"]["snippet"]["textDisplay"])
                            except Exception:
                                comments = ["댓글 수집 불가"]
                            st.success(f"영상 제목: {title}")
                            st.markdown(f"▶️ [유튜브에서 보기]({url})")
                        with st.spinner(t("yt_analyzing")):
                            at = f"제목: {title}\n설명: {desc}\n태그: {', '.join(tags[:10])}\n댓글:\n{chr(10).join(comments[:20])}"
                            msg = client.messages.create(
                                model="claude-sonnet-4-20250514", max_tokens=2048,
                                messages=[{"role":"user","content":f"""아동 안전 모니터링 전문가로서 분석해주세요.
{at}
형식:
[영상 전체 분석]
심각도: 1~5
분류: (안전/스팸/부적절/성인/그루밍)
이유: (설명)
조치: (권고 조치)
[위험 댓글 목록]
위험 댓글 최대 5개. 없으면 "위험 댓글 없음"
"""}])
                        rt = msg.content[0].text
                        sev = extract_severity(rt); cat = extract_category(rt)
                        st.subheader(f"{sev_icon(sev)} {t('result_title')}")
                        st.write(rt)
                        if st.button(t("to_report"), key="yt_report"):
                            open_report_form(url, rt, sev, cat, "YouTube", from_tab=1); st.rerun()
                    except Exception as e:
                        st.error(t("error", str(e)))
                else:
                    st.warning(t("enter_url"))

        # ── 키워드 탐색 ──
        with tab3:
            st.subheader(t("kw_title"))
            keyword = st.text_input(t("kw_input"))
            max_r = st.slider(t("kw_count"), 5, 20, 10)
            if st.button(t("kw_start")):
                if keyword:
                    try:
                        analyzed_urls = get_analyzed_urls()
                        with st.spinner(f"'{keyword}' 검색 중..."):
                            sr = youtube.search().list(part="snippet",q=keyword,type="video",maxResults=max_r,relevanceLanguage="ko").execute()
                            videos = []; skipped = 0
                            for item in sr.get("items",[]):
                                v = item["id"]["videoId"]
                                u = f"https://www.youtube.com/watch?v={v}"
                                if u in analyzed_urls:
                                    skipped += 1; continue
                                videos.append({"id":v,"title":item["snippet"]["title"],
                                    "description":item["snippet"].get("description","")[:200],
                                    "channel":item["snippet"]["channelTitle"],"url":u})
                        if skipped > 0:
                            st.caption(f"⏭️ 이미 분석한 영상 {skipped}개 제외됨")
                        if not videos:
                            st.warning("새로운 영상이 없습니다."); st.stop()
                        st.info(f"새 영상 {len(videos)}개 분석 시작...")
                        results = []; prog = st.progress(0)
                        for i, video in enumerate(videos):
                            with st.spinner(f"({i+1}/{len(videos)}) {video['title'][:30]}..."):
                                msg = client.messages.create(
                                    model="claude-sonnet-4-20250514", max_tokens=512,
                                    messages=[{"role":"user","content":f"""아동 안전 모니터링 전문가로서 분석해주세요.
제목: {video['title']}
설명: {video['description']}
채널: {video['channel']}
형식:
심각도: (1~5)
분류: (안전/스팸/부적절/성인/그루밍)
이유: (한 줄)"""}])
                                rt = msg.content[0].text
                                sev = extract_severity(rt); cat = extract_category(rt)
                                results.append({**video,"analysis":rt,"severity":sev,"category":cat,"search_type":"keyword"})
                                mark_url_analyzed(video["url"], video["title"], "keyword", user["id"])
                            prog.progress((i+1)/len(videos))
                        st.session_state.search_results = results
                        st.success(f"완료! {len(results)}개 분석됨")
                    except Exception as e:
                        st.error(f"오류: {str(e)}")
                else:
                    st.warning(t("enter_keyword"))

            if st.session_state.search_results:
                st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)
                results_to_show = list(st.session_state.search_results)
                sc1, sc2 = st.columns([3, 1])
                with sc1:
                    st.subheader(f"탐색 결과 ({len(results_to_show)}개)")
                with sc2:
                    sort_key = st.selectbox(t("sort"), [t("sort_sev_high"), t("sort_sev_low"), t("sort_newest")], key="sort_search")
                if sort_key == t("sort_sev_high"):
                    results_to_show.sort(key=lambda x: x["severity"], reverse=True)
                elif sort_key == t("sort_sev_low"):
                    results_to_show.sort(key=lambda x: x["severity"])
                for r in results_to_show:
                    icon = sev_icon(r["severity"])
                    with st.expander(f"{icon} {r['title']} — {r['channel']}"):
                        ca, cb = st.columns([4,1])
                        with ca:
                            st.write(r["analysis"])
                        with cb:
                            st.markdown(f"**[▶️ 유튜브 열기]({r['url']})**")
                            if st.button("📋 보고서 작성", key=f"sr_{r['id']}"):
                                open_report_form(r["url"],r["analysis"],r["severity"],r["category"],"YouTube",from_tab=2); st.rerun()
                if st.button(t("kw_clear")):
                    st.session_state.search_results = []; st.rerun()

        # ── 드래곤아이즈 추천 ──
        with tab4:
            st.subheader(t("dragon_title"))
            st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)
            st.caption("AI가 플랫폼별 위험 키워드를 자동 생성하고 유튜브를 탐색합니다. 이미 분석한 영상은 자동 제외됩니다.")

            token_info = can_use_dragon(user["id"])
            col_t1, col_t2, col_t3 = st.columns(3)
            col_t1.metric(t("dragon_used"), f"{token_info['used']}/{token_info['monthly_limit']}회")
            col_t2.metric(t("dragon_today"), f"{token_info['today_used']}/{token_info['daily_limit']}회")
            col_t3.metric(t("dragon_remain"), f"{token_info['monthly_remaining']}회")

            if not token_info["ok"]:
                if token_info["monthly_remaining"] <= 0:
                    st.warning("이번달 추천 한도에 도달했습니다. 관리자에게 추가 토큰을 요청하세요.")
                else:
                    st.warning(f"오늘 추천 한도({DAILY_DRAGON_LIMIT}회)에 도달했습니다. 내일 다시 사용 가능합니다.")

            btn1, btn2, btn3, btn4 = st.columns(4)
            with btn1:
                run_general = st.button(t("dragon_general"), use_container_width=True, disabled=not token_info["ok"])
            with btn2:
                run_roblox = st.button(t("dragon_roblox"), use_container_width=True, disabled=not token_info["ok"])
            with btn3:
                run_minecraft = st.button(t("dragon_minecraft"), use_container_width=True, disabled=not token_info["ok"])
            with btn4:
                run_gambling = st.button("🎰 도박 추천", use_container_width=True, disabled=not token_info["ok"])

            selected_platform = None
            selected_label = ""
            selected_type = ""
            if run_general:
                selected_platform = "general"; selected_label = "🐉 일반"; selected_type = "dragon_general"
            elif run_roblox:
                selected_platform = "roblox"; selected_label = "🎮 Roblox"; selected_type = "dragon_roblox"
            elif run_minecraft:
                selected_platform = "minecraft"; selected_label = "⛏️ Minecraft"; selected_type = "dragon_minecraft"
            elif run_gambling:
                selected_platform = "gambling"; selected_label = "🎰 도박"; selected_type = "dragon_gambling"

            if selected_platform and token_info["ok"]:
                try:
                    with st.spinner(f"{selected_label} 위험 키워드 생성 중..."):
                        keywords = generate_recommend_keywords(selected_platform)
                    if keywords:
                        st.success(f"키워드 {len(keywords)}개 생성됨!")
                        st.write("🔑 " + " | ".join(keywords))
                    else:
                        st.error("키워드 생성 실패."); st.stop()

                    all_results = []; prog = st.progress(0)
                    analyzed_urls = get_analyzed_urls()
                    for i, kw in enumerate(keywords):
                        with st.spinner(f"'{kw}' 탐색 중... ({i+1}/{len(keywords)})"):
                            try:
                                results = search_and_analyze(kw, max_results=3, analyzed_urls=analyzed_urls,
                                                             search_type=selected_type, assigned_to=user["id"])
                                all_results.extend(results)
                                for r in results:
                                    analyzed_urls.add(r["url"])
                            except Exception:
                                pass
                        prog.progress((i+1)/len(keywords))

                    all_results.sort(key=lambda x: x["severity"], reverse=True)
                    risky = [r for r in all_results if r["severity"] >= 2]
                    existing = list(st.session_state.recommend_results)
                    merged = all_results + [r for r in existing if r["url"] not in {x["url"] for x in all_results}]
                    st.session_state.recommend_results = merged
                    use_dragon_token(user["id"])
                    st.success(f"완료! {selected_label} — {len(all_results)}개 중 주의 필요 {len(risky)}개 발견")
                except Exception as e:
                    st.error(f"오류: {str(e)}")

            if st.session_state.recommend_results:
                st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)
                results = list(st.session_state.recommend_results)
                rc1, rc2 = st.columns([3,1])
                with rc1:
                    st.subheader(f"추천 결과 ({len(results)}개)")
                with rc2:
                    sort_rec = st.selectbox(t("sort"), [t("sort_sev_high"),t("sort_sev_low"),t("sort_newest")], key="sort_rec")

                if sort_rec == t("sort_sev_high"):
                    results.sort(key=lambda x: x["severity"], reverse=True)
                elif sort_rec == t("sort_sev_low"):
                    results.sort(key=lambda x: x["severity"])

                risky = [r for r in results if r["severity"] >= 2]
                safe  = [r for r in results if r["severity"] < 2]

                if risky:
                    st.subheader(f"🚨 주의 필요 ({len(risky)}개)")
                    for r in risky:
                        icon = sev_icon(r["severity"])
                        with st.expander(f"{icon} [{search_type_label(r.get('search_type',''))}] {r['title']} — {r['channel']}"):
                            ca, cb = st.columns([4,1])
                            with ca:
                                st.write(r["analysis"])
                            with cb:
                                st.markdown(f"**[▶️ 유튜브 열기]({r['url']})**")
                                if st.button("📋 보고서 작성", key=f"rec_{r['id']}"):
                                    open_report_form(r["url"],r["analysis"],r["severity"],r["category"],"YouTube",from_tab=3); st.rerun()
                with st.expander(f"✅ 안전 판정 ({len(safe)}개)"):
                    for r in safe:
                        st.caption(f"✅ [{r.get('keyword','')}] {r['title']}")
                if st.button(t("dragon_clear")):
                    st.session_state.recommend_results = []; st.rerun()

        # ── 탐색 히스토리 ──
        with tab5:
            st.subheader(t("history_title"))
            st.caption(t("history_caption"))
            st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)

            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                ftype = st.selectbox(t("filter_type"), ["전체","🐉 일반추천","🎮 Roblox추천","⛏️ Minecraft추천","🔍 키워드탐색"])
            with fc2:
                freported = st.selectbox(t("filter_reported"), ["전체",t("reported"),t("not_reported")])
            with fc3:
                fdate = st.date_input(t("after_date"), value=None, key="hist_date")

            if is_admin:
                hist = supabase.table("analyzed_urls").select("*").order("analyzed_at", desc=True).limit(1000).execute()
            else:
                hist = supabase.table("analyzed_urls").select("*").eq("assigned_to", user["id"]).order("analyzed_at", desc=True).limit(1000).execute()

            data = hist.data if hist.data else []

            type_map = {"🐉 일반추천":"dragon_general","🎮 Roblox추천":"dragon_roblox",
                        "⛏️ Minecraft추천":"dragon_minecraft","🔍 키워드탐색":"keyword"}
            if ftype != "전체":
                data = [d for d in data if d.get("search_type") == type_map.get(ftype)]
            if freported == t("reported"):
                data = [d for d in data if d.get("reported")]
            elif freported == t("not_reported"):
                data = [d for d in data if not d.get("reported")]
            if fdate:
                data = [d for d in data if str(d.get("analyzed_at",""))[:10] >= str(fdate)]

            st.caption(f"총 {len(data)}건")

            all_users_res = supabase.table("users").select("id,name").execute()
            user_map = {u["id"]: u["name"] for u in (all_users_res.data or [])}

            for d in data:
                stype = search_type_label(d.get("search_type",""))
                reported_badge = "✅ 보고서 작성" if d.get("reported") else "⏳ 미작성"
                assigned_name = user_map.get(d.get("assigned_to",""), t("unassigned"))
                analyzed_date = str(d.get("analyzed_at",""))[:16]

                ca, cb = st.columns([5,1])
                with ca:
                    st.markdown(f"**{d.get('title','(제목없음)')}**")
                    st.caption(f"{stype} | {analyzed_date} | 담당: {assigned_name} | {reported_badge}")
                with cb:
                    if "youtube.com" in d.get("url",""):
                        st.markdown(f"[▶️ 열기]({d['url']})")
                    if not d.get("reported"):
                        if st.button(t("write_btn"), key=f"hist_{d['id']}"):
                            open_report_form(d["url"], "", 1, "안전", "YouTube", from_tab=4); st.rerun()
                st.divider()

        # ── 보고서 목록 ──
        with tab6:
            st.subheader(t("report_list"))
            st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)

            all_reps_data = supabase.table("reports").select("*").order("created_at", desc=True).execute()
            all_users_r = supabase.table("users").select("id,name").execute()
            umap_r = {u["id"]: u["name"] for u in (all_users_r.data or [])}

            if all_reps_data.data:
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    fsev = st.selectbox(t("filter_sev"), ["전체","1","2","3","4","5"])
                with fc2:
                    fcat = st.selectbox(t("filter_cat"), ["전체","안전","스팸","부적절","성인","그루밍","미분류"])
                with fc3:
                    fwriter = st.selectbox(t("filter_writer"), ["전체"] + list(set(umap_r.values())))

                filtered = all_reps_data.data
                if fsev != "전체":
                    filtered = [r for r in filtered if r.get("severity") == int(fsev)]
                if fcat != "전체":
                    filtered = [r for r in filtered if r.get("category") == fcat]
                if fwriter != "전체":
                    writer_id = next((uid for uid, name in umap_r.items() if name == fwriter), None)
                    if writer_id:
                        filtered = [r for r in filtered if r.get("user_id") == writer_id]

                sort_rep = st.selectbox(t("sort"), [t("sort_sev_high"),t("sort_sev_low"),t("sort_newest"),t("sort_oldest")], key="sort_rep")
                if sort_rep == t("sort_sev_high"):
                    filtered.sort(key=lambda x: x.get("severity", 0), reverse=True)
                elif sort_rep == t("sort_sev_low"):
                    filtered.sort(key=lambda x: x.get("severity", 0))
                elif sort_rep == t("sort_newest"):
                    filtered.sort(key=lambda x: str(x.get("created_at","")), reverse=True)
                elif sort_rep == t("sort_oldest"):
                    filtered.sort(key=lambda x: str(x.get("created_at","")))

                st.caption(f"총 {len(filtered)}건")

                if is_admin and filtered:
                    with st.expander("📧 선택 보고서 일괄 이메일 발송"):
                        recipients = supabase.table("email_recipients").select("*").eq("active", True).execute()
                        if recipients.data:
                            rec_names = [f"{r['name']} ({r['type']}) — {r['email']}" for r in recipients.data]
                            selected_recs = st.multiselect("수신자 선택", rec_names)
                            bulk_subject = st.text_input("제목", value=f"[DragonEyes] Monitoring Report — {len(filtered)} cases")
                            bulk_memo = st.text_area("추가 메모 (선택)", height=60)
                            if st.button("📧 선택된 수신자에게 일괄 발송 (UI 미리보기)", type="primary"):
                                st.success(f"✅ {len(selected_recs)}명에게 {len(filtered)}건 발송 예정")
                                with st.expander("📄 발송 미리보기 (병기 형식)"):
                                    st.markdown(f"**Subject / 제목:** {bulk_subject}")
                                    st.markdown(f"**To / 수신자:** {', '.join(selected_recs)}")
                                    st.markdown(f"**Total / 총:** {len(filtered)}건")
                                    if bulk_memo:
                                        st.markdown(f"**Memo / 메모:** {bulk_memo}")
                                    st.divider()
                                    for idx, rep in enumerate(filtered[:3]):
                                        sv = rep.get('severity', 0)
                                        has_en = bool(rep.get("result_en"))
                                        ec1, ec2 = st.columns(2)
                                        with ec1:
                                            st.markdown(f"**{idx+1}. {sev_icon(sv)} {rep.get('category','-')}** | {rep.get('platform','-')} | {str(rep.get('created_at',''))[:10]}")
                                            st.caption(str(rep.get("result",""))[:150] + "...")
                                        with ec2:
                                            if has_en:
                                                st.markdown(f"**🇺🇸 English**")
                                                st.caption(str(rep.get("result_en",""))[:150] + "...")
                                            else:
                                                st.caption("⬜ No English translation")
                                    if len(filtered) > 3:
                                        st.caption(f"... and {len(filtered)-3} more reports")
                        else:
                            st.info("등록된 수신자가 없습니다. 관리자 탭에서 수신자를 추가하세요.")

                for r in filtered:
                    sev = r.get("severity",0); icon = sev_icon(sev)
                    created = str(r.get("created_at",""))[:16]
                    preview = str(r.get("content",""))[:50]
                    writer = umap_r.get(r.get("user_id",""), "알 수 없음")
                    can_edit_r = is_admin or r.get("user_id") == user["id"]
                    en_badge = " ✅🌐EN" if r.get("result_en") else " ⬜번역없음"

                    ca, cb, cc, cd = st.columns([5, 1, 1, 1])
                    with ca:
                        st.markdown(f"{icon} **{r.get('category','-')}** | {r.get('platform','-')} | {created} | 👤 {writer} |{en_badge}")
                        st.caption(preview+"...")
                    with cb:
                        if st.button(t("detail"), key=f"det_{r['id']}"):
                            st.session_state.selected_report = r
                            go_to("report_detail", from_tab=5); st.rerun()
                    with cc:
                        if is_admin:
                            if st.button("📧 발송", key=f"email_{r['id']}"):
                                st.session_state[f"show_email_{r['id']}"] = True
                    with cd:
                        if can_edit_r:
                            if st.button("🗑️ 삭제", key=f"del_{r['id']}"):
                                if delete_report(r["id"]): st.rerun()

                    if is_admin and st.session_state.get(f"show_email_{r['id']}", False):
                        with st.container(border=True):
                            st.caption("📧 이메일 발송")
                            recipients = supabase.table("email_recipients").select("*").eq("active", True).execute()
                            if recipients.data:
                                rec_options = {f"{rc['name']} ({rc['type']}) — {rc['email']}": rc for rc in recipients.data}
                                selected_rec = st.selectbox("수신자", list(rec_options.keys()), key=f"rec_sel_{r['id']}")
                                email_subject = st.text_input("제목",
                                    value=f"[DragonEyes] Monitoring Report — {r.get('category','')} {sev_icon(sev)}",
                                    key=f"subj_{r['id']}")
                                email_memo = st.text_area("추가 메모", height=60, key=f"memo_{r['id']}")

                                with st.expander("📄 발송 내용 미리보기 (병기)"):
                                    pc1, pc2 = st.columns(2)
                                    with pc1:
                                        orig_flag2 = "🇰🇷" if st.session_state.get("lang","ko") == "ko" else "🇯🇵"
                                        st.markdown(f"**{orig_flag2} 원문**")
                                        st.caption(str(r.get("result",""))[:300] + "...")
                                    with pc2:
                                        if r.get("result_en"):
                                            st.markdown("**🇺🇸 English**")
                                            st.caption(str(r.get("result_en",""))[:300] + "...")
                                        else:
                                            st.warning("⬜ 영어 번역 없음 — 상세보기에서 먼저 번역해주세요.")

                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    if st.button("📧 발송 (미리보기)", key=f"send_{r['id']}", type="primary"):
                                        rc = rec_options[selected_rec]
                                        supabase.table("email_logs").insert({
                                            "report_id": r["id"],
                                            "recipient_id": rc["id"],
                                            "sent_by": user["id"],
                                            "subject": email_subject,
                                            "status": "pending"
                                        }).execute()
                                        st.success(f"✅ {rc['name']} ({rc['email']})에게 발송 예정으로 저장됨")
                                        st.session_state[f"show_email_{r['id']}"] = False
                                        st.rerun()
                                with ec2:
                                    if st.button("취소", key=f"cancel_email_{r['id']}"):
                                        st.session_state[f"show_email_{r['id']}"] = False; st.rerun()
                            else:
                                st.warning("등록된 수신자가 없습니다.")
                                if st.button("닫기", key=f"close_email_{r['id']}"):
                                    st.session_state[f"show_email_{r['id']}"] = False; st.rerun()
                    st.divider()
            else:
                st.info(t("no_reports"))

        # ── 내 성과 ──
        with tab7:
            st.subheader(f"📈 {user['name']}님의 성과 현황")
            st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)
            all_my = supabase.table("reports").select("*").eq("user_id", user["id"]).execute()
            if all_my.data:
                df = pd.DataFrame(all_my.data)
                df["created_at"] = pd.to_datetime(df["created_at"])
                df["month"] = df["created_at"].dt.strftime("%Y-%m")
                this_month = date.today().strftime("%Y-%m")
                c1,c2,c3,c4 = st.columns(4)
                month_cnt = len(df[df["month"]==this_month])
                total_cnt = len(df)
                target = user.get("monthly_target",10)
                rate = min(int(month_cnt/target*100),100)
                c1.metric("이번달", f"{month_cnt}건", f"목표 {target}건")
                c2.metric("달성률", f"{rate}%")
                c3.metric("누적 총계", f"{total_cnt}건")
                c4.metric("이번달 목표", f"{target}건")
                st.progress(rate/100)
                if rate >= 100: st.success("🎉 이번달 목표 달성!")
                elif rate >= 70: st.info("💪 잘 하고 있어요!")
                else: st.warning("📌 꾸준히 해봐요!")
                monthly = df.groupby("month").size().reset_index(name="건수")
                st.bar_chart(monthly.set_index("month"))
                cmts = supabase.table("comments").select("*").eq("user_id", user["id"]).order("created_at", desc=True).limit(3).execute()
                if cmts.data:
                    st.subheader("💬 관리자 코멘트")
                    for c in cmts.data:
                        st.info(f"📝 {c['content']}\n\n_{str(c['created_at'])[:10]}_")
            else:
                st.info("아직 보고서가 없습니다!")

        # ── 네이버 탐색 ──
        with tab_naver:
            st.subheader("🟢 네이버 카페·블로그·뉴스 탐색")
            st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)
            if not NAVER_CLIENT_ID:
                st.error("네이버 API 키가 설정되지 않았습니다. .env 파일에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 추가하세요.")
            else:
                n1, n2 = st.columns([3,1])
                with n1:
                    naver_query = st.text_input("🔍 검색어 입력", placeholder="예: 미성년자 채팅 만남, 어린이 온라인 위험")
                with n2:
                    naver_type = st.selectbox("검색 대상", ["카페", "블로그", "뉴스", "전체"])

                naver_cols = st.columns(3)
                with naver_cols[0]:
                    auto_keywords = st.button("🐉 위험 키워드 자동 생성", use_container_width=True)
                with naver_cols[1]:
                    do_search = st.button("🔍 검색 시작", use_container_width=True, type="primary")
                with naver_cols[2]:
                    display_count = st.slider("결과 수", 5, 20, 10)

                if auto_keywords:
                    import random
                    pool = [
                        "미성년자 채팅 만남", "초등학생 온라인 만남", "청소년 개인방송",
                        "어린이 랜덤채팅", "중학생 SNS 만남", "10대 화상채팅",
                        "청소년 섹스토션 피해", "어린이 딥페이크 피해", "청소년 사진 협박",
                        "미성년자 그루밍", "초등학생 유해 콘텐츠", "청소년 사이버성폭력",
                        "청소년 불법도박 사이트", "초등학생 온라인도박", "미성년자 스포츠토토",
                        "청소년 파워볼 사이트", "중학생 도박 빠짐", "10대 온라인카지노",
                        "청소년 달팽이게임", "사다리게임 미성년자", "소셜그래프 청소년",
                        "학생 대리베팅 모집", "미성년자 총판 모집", "학생 도박빚 협박",
                    ]
                    picked = random.choice(pool)
                    st.session_state["naver_auto_kw"] = picked
                    st.info(f"🔑 자동 생성 키워드: **{picked}**  ← 위 검색어 입력창에 복사해서 사용하세요.")

                def naver_search(query, search_type, display=10):
                    headers = {
                        "X-Naver-Client-Id": NAVER_CLIENT_ID,
                        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
                    }
                    endpoints = {
                        "카페":  "cafearticle",
                        "블로그": "blog",
                        "뉴스":  "news",
                    }
                    results = []
                    types = list(endpoints.keys()) if search_type == "전체" else [search_type]
                    for t_type in types:
                        ep = endpoints[t_type]
                        url = f"https://openapi.naver.com/v1/search/{ep}.json"
                        params = {"query": query, "display": display, "sort": "date"}
                        resp = requests.get(url, headers=headers, params=params, timeout=10)
                        if resp.status_code == 200:
                            items = resp.json().get("items", [])
                            for item in items:
                                item["_type"] = t_type
                                results.append(item)
                        else:
                            st.warning(f"{t_type} 검색 오류: {resp.status_code}")
                    return results

                def clean_html(text):
                    import re
                    return re.sub(r'<[^>]+>', '', text)

                if do_search and naver_query:
                    with st.spinner(f"네이버 {naver_type} 검색 중..."):
                        items = naver_search(naver_query, naver_type, display_count)

                    if not items:
                        st.warning("검색 결과가 없습니다.")
                    else:
                        st.success(f"총 {len(items)}개 결과 발견")
                        with st.spinner("🐲 드래곤파더가 위험도 분석 중..."):
                            analyzed = []
                            for item in items:
                                title = clean_html(item.get("title",""))
                                desc  = clean_html(item.get("description",""))
                                link  = item.get("link","") or item.get("url","")
                                src_type = item.get("_type","")
                                pub_date = item.get("pubDate","") or item.get("postdate","")

                                try:
                                    msg = client.messages.create(
                                        model="claude-sonnet-4-20250514", max_tokens=200,
                                        messages=[{"role":"user","content":f"""아동 온라인 안전 모니터링 전문가로서 다음 게시물이 아동에게 위험한지 분석하세요.

제목: {title}
내용 요약: {desc}
출처: 네이버 {src_type}

위험도 판단 기준:
- 미성년자 대상 만남·채팅·유인
- 그루밍, 섹스토션, 사진/영상 협박
- 아동 대상 유해 콘텐츠 유포

반드시 아래 형식으로만 답변:
심각도: (1~5)
분류: (안전/스팸/부적절/그루밍/섹스토션/폭력유도)
이유: (한 줄)"""}]
                                    )
                                    resp_text = msg.content[0].text
                                    sev = 1
                                    for line in resp_text.splitlines():
                                        if "심각도:" in line:
                                            import re
                                            m = re.search(r'\d', line)
                                            if m: sev = int(m.group())
                                    cat = "안전"
                                    for c in ["섹스토션","폭력유도","그루밍","성인","부적절","스팸"]:
                                        if c in resp_text: cat = c; break
                                    reason = ""
                                    for line in resp_text.splitlines():
                                        if "이유:" in line:
                                            reason = line.replace("이유:","").strip()
                                except Exception:
                                    sev, cat, reason = 1, "안전", "분석 실패"

                                analyzed.append({
                                    "title": title, "desc": desc, "link": link,
                                    "type": src_type, "pubDate": pub_date,
                                    "severity": sev, "category": cat, "reason": reason
                                })

                        analyzed.sort(key=lambda x: x["severity"], reverse=True)
                        risky = [a for a in analyzed if a["severity"] >= 3]
                        safe  = [a for a in analyzed if a["severity"] < 3]

                        sev_icon_map = {1:"✅",2:"🟡",3:"🟠",4:"🔴",5:"🚨"}

                        if risky:
                            st.markdown(f"### 🚨 주의 필요 ({len(risky)}개)")
                            for a in risky:
                                with st.expander(f"{sev_icon_map.get(a['severity'],'⚪')} [{a['type']}] {a['title'][:60]}"):
                                    st.markdown(f"**심각도:** {a['severity']} | **분류:** {a['category']}")
                                    st.markdown(f"**이유:** {a['reason']}")
                                    st.markdown(f"**내용:** {a['desc'][:200]}")
                                    st.markdown(f"**날짜:** {a['pubDate']}")
                                    st.markdown(f"[🔗 원문 보기]({a['link']})")
                        else:
                            st.success("🟢 주의 필요한 게시물이 없습니다.")

                        if safe:
                            with st.expander(f"✅ 안전 판정 ({len(safe)}개)"):
                                for a in safe:
                                    st.caption(f"{sev_icon_map.get(a['severity'],'⚪')} [{a['type']}] {a['title'][:60]} — {a['reason']}")
                elif do_search and not naver_query:
                    st.warning("검색어를 입력하세요.")

        # ── 대화형 AI 채팅 ──
        with tab_chat:
            st.subheader("🐲 드래곤파더")
            st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)
            lang = st.session_state.get("lang", "ko")

            chat_info = can_use_chat(user["id"])
            ci1, ci2, ci3, ci4 = st.columns(4)
            if chat_info.get("ok"):
                ci1.metric("📅 오늘 사용", f"{chat_info['today_used']}/{CHAT_DAILY_LIMIT}턴")
                ci2.metric("📆 이번주", f"{chat_info['week_used']}/{CHAT_WEEKLY_LIMIT}턴")
                ci3.metric("🗓️ 이번달", f"{chat_info['monthly_used']}/{chat_info['monthly_limit']}턴")
                ci4.metric("✅ 오늘 남은 턴", f"{chat_info['today_remaining']}턴")
            else:
                ci1.metric("📅 오늘 사용", f"{chat_info.get('today_used',0)}/{CHAT_DAILY_LIMIT}턴")
                ci2.metric("📆 이번주", f"{chat_info.get('week_used',0)}/{CHAT_WEEKLY_LIMIT}턴")
                ci3.metric("🗓️ 이번달", f"{chat_info.get('monthly_used',0)}/{chat_info.get('monthly_limit', CHAT_MONTHLY_LIMIT)}턴")
                ci4.metric("✅ 오늘 남은 턴", "0턴")

            if not chat_info["ok"]:
                reason = chat_info.get("reason")
                if reason == "weekend":
                    st.warning("😊 오늘은 주말입니다. AI 채팅은 평일(월~금)에만 사용 가능합니다.")
                elif reason == "daily":
                    st.warning(f"📌 오늘 한도({CHAT_DAILY_LIMIT}턴)에 도달했습니다. 내일 다시 사용 가능합니다.")
                elif reason == "weekly":
                    st.warning(f"📌 이번 주 한도({CHAT_WEEKLY_LIMIT}턴)에 도달했습니다. 다음 주 월요일에 재시작됩니다.")
                elif reason == "monthly":
                    st.warning(f"📌 이번 달 한도에 도달했습니다. 관리자에게 추가 토큰을 요청하세요.")
            else:
                st.caption("아동 안전 모니터링 관련 질문을 해보세요. 질문은 300자 이내로 입력해주세요.")

            st.divider()

            chat_container = st.container()
            with chat_container:
                if not st.session_state.chat_history:
                    st.info("💡 예시 질문: '이 댓글이 그루밍 패턴인지 분석해줘' / '보고서 작성할 때 주의사항은?' / 'Roblox에서 흔한 위험 패턴은?'")
                for msg in st.session_state.chat_history:
                    if msg["role"] == "user":
                        with st.chat_message("user"):
                            st.write(msg["content"])
                    else:
                        with st.chat_message("assistant", avatar="🐲"):
                            st.write(msg["content"])

            if chat_info["ok"]:
                user_input = st.chat_input("드래곤파더에게 질문하세요... (최대 300자)", max_chars=300)
                if user_input:
                    st.session_state.chat_history.append({"role": "user", "content": user_input})
                    with st.spinner("🐲 드래곤파더가 답변 중..."):
                        try:
                            api_history = [
                                {"role": m["role"], "content": m["content"]}
                                for m in st.session_state.chat_history[:-1]
                            ]
                            response = chat_with_ai(api_history, user_input, lang)
                            st.session_state.chat_history.append({"role": "assistant", "content": response})
                            supabase.table("chat_logs").insert({
                                "user_id": user["id"],
                                "message": user_input,
                                "response": response,
                                "tokens_used": 1
                            }).execute()
                            use_chat_token(user["id"])
                            st.rerun()
                        except Exception as e:
                            st.session_state.chat_history.pop()
                            st.error(f"오류: {str(e)}")
            else:
                st.chat_input("사용 불가 상태입니다", disabled=True)

            if st.session_state.chat_history:
                if st.button("🗑️ 대화 초기화", key="clear_chat"):
                    st.session_state.chat_history = []
                    st.rerun()

        # ── 공지사항 탭 ──
        if tab_notice:
            with tab_notice:
                st.subheader("📢 공지사항")
                st.markdown(GUIDELINE_BADGE_FULL, unsafe_allow_html=True)

                if is_high:
                    with st.expander("➕ 새 공지 / 업무지시 작성", expanded=False):
                        ann_type = st.selectbox("유형", ["notice","work_order","urgent"],
                            format_func=lambda x:{"notice":"🔵 공지사항","work_order":"🟠 업무지시","urgent":"🚨 긴급공지"}[x],
                            key="ann_type_sel")
                        ann_title = st.text_input("제목", key="ann_title_inp")
                        ann_content = st.text_area("내용", height=150, key="ann_content_inp")

                        all_teams_ann = get_all_teams()
                        all_users_ann = get_all_users()
                        target_type = st.selectbox("수신 대상", ["all","team","user"],
                            format_func=lambda x:{"all":"📢 전체","team":"👥 특정 팀","user":"👤 특정 사용자"}[x],
                            key="ann_target_type")
                        target_id = None
                        if target_type == "team" and all_teams_ann:
                            sel_team = st.selectbox("팀 선택", all_teams_ann, format_func=lambda x: x["name"], key="ann_target_team")
                            target_id = sel_team["id"] if sel_team else None
                        elif target_type == "user" and all_users_ann:
                            sel_user = st.selectbox("사용자 선택", all_users_ann, format_func=lambda x: f'{x["name"]} ({x.get("email","")})', key="ann_target_user")
                            target_id = sel_user["id"] if sel_user else None

                        if st.button("📤 발송", type="primary", key="ann_send_btn"):
                            if ann_title and ann_content:
                                try:
                                    supabase.table("announcements").insert({
                                        "type": ann_type,
                                        "title": ann_title,
                                        "content": ann_content,
                                        "sender_id": user["id"],
                                        "target_type": target_type,
                                        "target_id": str(target_id) if target_id else None,
                                    }).execute()
                                    st.success("✅ 공지가 발송됐습니다!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"오류: {str(e)}")
                            else:
                                st.warning("제목과 내용을 입력해주세요.")

                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    filter_type = st.selectbox("유형 필터", ["전체","notice","work_order","urgent"],
                        format_func=lambda x:{"전체":"전체","notice":"🔵 공지사항","work_order":"🟠 업무지시","urgent":"🚨 긴급공지"}.get(x,x),
                        key="ann_filter_type")
                with fc2:
                    filter_period = st.selectbox("기간", ["전체","이번달","이번주"], key="ann_filter_period")
                with fc3:
                    filter_search = st.text_input("검색", placeholder="제목 검색...", key="ann_filter_search")

                try:
                    ann_query = supabase.table("announcements").select("*").eq("is_deleted", False).order("created_at", desc=True).limit(100)
                    if filter_type != "전체":
                        ann_query = ann_query.eq("type", filter_type)
                    announcements_list = ann_query.execute().data or []
                except:
                    announcements_list = []

                if filter_period == "이번주":
                    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
                    announcements_list = [a for a in announcements_list if str(a.get("created_at",""))[:10] >= week_start]
                elif filter_period == "이번달":
                    this_month = date.today().strftime("%Y-%m")
                    announcements_list = [a for a in announcements_list if str(a.get("created_at",""))[:7] == this_month]

                if filter_search:
                    announcements_list = [a for a in announcements_list if filter_search.lower() in a.get("title","").lower() or filter_search.lower() in a.get("content","").lower()]

                try:
                    my_reads = [r["announcement_id"] for r in (supabase.table("announcement_reads").select("announcement_id").eq("user_id", user["id"]).execute().data or [])]
                except:
                    my_reads = []

                all_users_map2 = {u["id"]: u["name"] for u in get_all_users()}

                type_icon = {"notice":"🔵","work_order":"🟠","urgent":"🚨"}
                type_label_map = {"notice":"공지사항","work_order":"업무지시","urgent":"긴급공지"}
                target_label_map = {"all":"전체","team":"특정팀","user":"특정사용자"}

                if not announcements_list:
                    st.info("공지사항이 없습니다.")
                else:
                    st.caption(f"총 {len(announcements_list)}건")
                    for ann in announcements_list:
                        is_read = ann["id"] in my_reads
                        icon = type_icon.get(ann["type"],"📢")
                        read_badge = "✅" if is_read else "🔴 미확인"
                        sender_name = all_users_map2.get(ann.get("sender_id",""), "알 수 없음")
                        ann_date = str(ann.get("created_at",""))[:10]
                        target_str = target_label_map.get(ann.get("target_type","all"), "전체")

                        with st.expander(f"{icon} **{ann['title']}**  |  {ann_date}  |  {read_badge}"):
                            st.markdown(f"**유형:** {type_label_map.get(ann['type'],'공지')} | **발송:** {sender_name} | **수신:** {target_str}")
                            st.divider()
                            st.markdown(ann["content"])

                            if not is_read:
                                if st.button("✅ 확인했습니다", key=f"read_ann_{ann['id']}"):
                                    mark_announcement_read(ann["id"], user["id"])
                                    st.rerun()

                            if is_high:
                                try:
                                    read_count = supabase.table("announcement_reads").select("id", count="exact").eq("announcement_id", ann["id"]).execute()
                                    total_users = len(get_all_users())
                                    rc = read_count.count or 0
                                    st.caption(f"👁️ 읽음: {rc}명 / {total_users}명")
                                except:
                                    pass

                                if st.button("🗑️ 삭제", key=f"del_ann_{ann['id']}"):
                                    supabase.table("announcements").update({"is_deleted": True}).eq("id", ann["id"]).execute()
                                    st.rerun()

        # ── 조직관리 탭 ──
        if tab_org and (is_admin or is_lead):
            with tab_org:
                st.subheader("🏢 조직관리")

                # ★ 수정: role_label() 함수 사용
                st.info(f"현재 권한: **{role_label(user_role)}**")

                org_tab1, org_tab2, org_tab3 = st.tabs(["👥 팀 관리", "🏖️ 휴가/병가 관리", "📋 업무지시"])

                with org_tab1:
                    all_teams_org = get_all_teams()
                    all_users_org = get_all_users()
                    umap_org = {u["id"]: u["name"] for u in all_users_org}

                    if is_high:
                        with st.expander("➕ 새 팀 생성", expanded=False):
                            new_team_name = st.text_input("팀 이름", key="new_team_name")
                            new_team_desc = st.text_input("설명 (선택)", key="new_team_desc")
                            leader_candidates = [u for u in all_users_org if u.get("role_v2") in ("team_leader","user","director","group_leader","superadmin")]
                            sel_leader = st.selectbox("팀장 지정", [None]+leader_candidates,
                                format_func=lambda x: "지정 안함" if x is None else x["name"],
                                key="new_team_leader")
                            if st.button("✅ 팀 생성", key="create_team_btn"):
                                if new_team_name:
                                    supabase.table("teams").insert({
                                        "name": new_team_name,
                                        "description": new_team_desc,
                                        "leader_id": sel_leader["id"] if sel_leader else None
                                    }).execute()
                                    st.success(f"✅ {new_team_name} 팀이 생성됐습니다!")
                                    st.rerun()
                                else:
                                    st.warning("팀 이름을 입력해주세요.")

                    if not all_teams_org:
                        st.info("생성된 팀이 없습니다.")
                    else:
                        for team in all_teams_org:
                            members = get_team_members(team["id"])
                            leader_name = umap_org.get(team.get("leader_id",""), "미지정")
                            with st.expander(f"🏢 **{team['name']}**  |  팀장: {leader_name}  |  팀원: {len(members)}명"):
                                if team.get("description"):
                                    st.caption(team["description"])

                                if members:
                                    for m in members:
                                        mc1, mc2, mc3 = st.columns([4,2,2])
                                        with mc1:
                                            # ★ 수정: role_icon() 함수 사용
                                            rb = role_icon(m.get("role_v2","user"))
                                            st.write(f"{rb} {m['name']} ({m.get('email','')})")
                                        with mc2:
                                            if is_high:
                                                _all_roles = ["user","team_leader","group_leader","director","group_leader_2","director_2","group_leader_3","director_3","group_leader_4","director_4","superadmin"]
                                                new_role = st.selectbox("역할",
                                                    _all_roles,
                                                    index=_all_roles.index(m.get("role_v2","user")) if m.get("role_v2","user") in _all_roles else 0,
                                                    key=f"role_sel_{m['id']}",
                                                    format_func=lambda x: role_label(x),
                                                    label_visibility="collapsed")
                                        with mc3:
                                            if is_high:
                                                if st.button("저장", key=f"save_role_{m['id']}"):
                                                    supabase.table("users").update({"role_v2": new_role}).eq("id", m["id"]).execute()
                                                    st.success(f"✅ {m['name']} 역할 변경됨"); st.rerun()
                                else:
                                    st.caption("팀원 없음")

                                if is_high:
                                    st.divider()
                                    unassigned_users = [u for u in all_users_org if not u.get("team_id")]
                                    if unassigned_users:
                                        add_member = st.selectbox("팀원 추가",
                                            [None]+unassigned_users,
                                            format_func=lambda x: "선택..." if x is None else f'{x["name"]} ({x.get("email","")})',
                                            key=f"add_member_{team['id']}")
                                        if st.button("➕ 추가", key=f"add_btn_{team['id']}"):
                                            if add_member:
                                                supabase.table("users").update({"team_id": team["id"]}).eq("id", add_member["id"]).execute()
                                                st.success(f"✅ {add_member['name']}님이 {team['name']}에 추가됐습니다!"); st.rerun()

                with org_tab2:
                    leave_type_map = {"annual":"🏖️ 연차","half":"🌤️ 반차","sick":"🤒 병가","other":"📝 기타"}
                    status_map = {"pending":"⏳ 대기","approved":"✅ 승인","rejected":"❌ 반려"}

                    st.subheader("📝 휴가/병가 신청")
                    with st.container(border=True):
                        lc1, lc2, lc3 = st.columns(3)
                        with lc1:
                            leave_type = st.selectbox("유형",
                                ["annual","half","sick","other"],
                                format_func=lambda x: leave_type_map[x],
                                key="leave_type_sel")
                        with lc2:
                            leave_start = st.date_input("시작일", key="leave_start")
                        with lc3:
                            leave_end = st.date_input("종료일", key="leave_end")
                        leave_reason = st.text_input("사유 (선택)", key="leave_reason")
                        if st.button("📤 신청", type="primary", key="leave_submit"):
                            if leave_start <= leave_end:
                                supabase.table("leave_requests").insert({
                                    "user_id": user["id"],
                                    "type": leave_type,
                                    "start_date": leave_start.isoformat(),
                                    "end_date": leave_end.isoformat(),
                                    "reason": leave_reason,
                                    "status": "pending"
                                }).execute()
                                st.success("✅ 신청이 접수됐습니다!")
                                st.rerun()
                            else:
                                st.warning("종료일이 시작일보다 빠릅니다.")

                    st.subheader("📋 내 신청 현황")
                    my_leaves = supabase.table("leave_requests").select("*").eq("user_id", user["id"]).order("created_at", desc=True).limit(20).execute().data or []
                    if not my_leaves:
                        st.info("신청 내역이 없습니다.")
                    else:
                        for lv in my_leaves:
                            lv_icon = leave_type_map.get(lv["type"],"📝")
                            st.markdown(f"{lv_icon} **{lv['start_date']} ~ {lv['end_date']}**  {status_map.get(lv['status'],'?')}  |  {lv.get('reason','')}")

                    if is_lead:
                        st.divider()
                        st.subheader("✅ 승인 대기 목록")
                        try:
                            if is_high:
                                pending_leaves = supabase.table("leave_requests").select("*").eq("status","pending").order("created_at", desc=True).execute().data or []
                            else:
                                my_team_id = user.get("team_id")
                                if my_team_id:
                                    team_user_ids = [u["id"] for u in get_team_members(my_team_id)]
                                    pending_leaves = supabase.table("leave_requests").select("*").in_("user_id", team_user_ids).eq("status","pending").order("created_at", desc=True).execute().data or [] if team_user_ids else []
                                else:
                                    pending_leaves = []
                        except:
                            pending_leaves = []

                        umap3 = {u["id"]: u["name"] for u in get_all_users()}
                        if not pending_leaves:
                            st.info("대기 중인 신청이 없습니다.")
                        else:
                            for lv in pending_leaves:
                                req_name = umap3.get(lv.get("user_id",""), "알 수 없음")
                                lv_icon = leave_type_map.get(lv["type"],"📝")
                                with st.container(border=True):
                                    pa1, pa2, pa3 = st.columns([5,1,1])
                                    with pa1:
                                        req_email = {u["id"]: u.get("email","") for u in get_all_users()}.get(lv.get("user_id",""),"")
                                        st.markdown(f"**{req_name}** `{req_email}` | {lv_icon} {lv['start_date']} ~ {lv['end_date']}")
                                        if lv.get("reason"):
                                            st.caption(f"사유: {lv['reason']}")
                                    with pa2:
                                        if st.button("✅ 승인", key=f"approve_leave_{lv['id']}"):
                                            supabase.table("leave_requests").update({
                                                "status": "approved",
                                                "approved_by": user["id"],
                                                "approved_at": datetime.now().isoformat()
                                            }).eq("id", lv["id"]).execute()
                                            st.success("승인됨"); st.rerun()
                                    with pa3:
                                        if st.button("❌ 반려", key=f"reject_leave_{lv['id']}"):
                                            supabase.table("leave_requests").update({
                                                "status": "rejected",
                                                "approved_by": user["id"],
                                                "approved_at": datetime.now().isoformat()
                                            }).eq("id", lv["id"]).execute()
                                            st.warning("반려됨"); st.rerun()

                with org_tab3:
                    if is_lead:
                        st.subheader("📤 업무지시 발송")
                        with st.container(border=True):
                            wo_title = st.text_input("제목", key="wo_title_inp")
                            wo_content = st.text_area("내용", height=120, key="wo_content_inp")
                            wc1, wc2 = st.columns(2)
                            with wc1:
                                wo_priority = st.selectbox("우선순위",
                                    ["high","normal","low"],
                                    format_func=lambda x:{"high":"🔴 높음","normal":"🟡 보통","low":"🟢 낮음"}[x],
                                    key="wo_priority_sel")
                            with wc2:
                                wo_target_type = st.selectbox("수신 대상",
                                    ["all","team","user"],
                                    format_func=lambda x:{"all":"📢 전체","team":"👥 팀","user":"👤 개인"}[x],
                                    key="wo_target_type")

                            wo_target_id = None
                            all_teams_wo = get_all_teams()
                            all_users_wo = get_all_users()
                            if wo_target_type == "team" and all_teams_wo:
                                sel_wo_team = st.selectbox("팀 선택", all_teams_wo, format_func=lambda x:x["name"], key="wo_team_sel")
                                wo_target_id = sel_wo_team["id"] if sel_wo_team else None
                            elif wo_target_type == "user" and all_users_wo:
                                sel_wo_user = st.selectbox("사용자 선택", all_users_wo, format_func=lambda x: f'{x["name"]} ({x.get("email","")})', key="wo_user_sel")
                                wo_target_id = sel_wo_user["id"] if sel_wo_user else None

                            if st.button("📤 업무지시 발송", type="primary", key="wo_send_btn"):
                                if wo_title and wo_content:
                                    supabase.table("work_orders").insert({
                                        "title": wo_title,
                                        "content": wo_content,
                                        "from_user_id": user["id"],
                                        "target_type": wo_target_type,
                                        "target_id": str(wo_target_id) if wo_target_id else None,
                                        "priority": wo_priority,
                                        "status": "sent"
                                    }).execute()
                                    st.success("✅ 업무지시가 발송됐습니다!")
                                    st.rerun()
                                else:
                                    st.warning("제목과 내용을 입력해주세요.")

                    st.subheader("📥 수신 업무지시")
                    try:
                        all_wo = supabase.table("work_orders").select("*").order("created_at", desc=True).limit(50).execute().data or []
                        my_wo = []
                        for wo in all_wo:
                            if wo.get("target_type") == "all":
                                my_wo.append(wo)
                            elif wo.get("target_type") == "team" and wo.get("target_id") == str(user.get("team_id","")):
                                my_wo.append(wo)
                            elif wo.get("target_type") == "user" and wo.get("target_id") == str(user["id"]):
                                my_wo.append(wo)
                    except:
                        my_wo = []

                    priority_icon = {"high":"🔴","normal":"🟡","low":"🟢"}
                    umap4 = {u["id"]: u["name"] for u in get_all_users()}

                    if not my_wo:
                        st.info("수신된 업무지시가 없습니다.")
                    else:
                        for wo in my_wo:
                            p_icon = priority_icon.get(wo.get("priority","normal"),"🟡")
                            sender = umap4.get(wo.get("from_user_id",""), "알 수 없음")
                            wo_date = str(wo.get("created_at",""))[:10]
                            with st.expander(f"{p_icon} **{wo['title']}**  |  {sender}  |  {wo_date}"):
                                st.markdown(wo["content"])
                                woc1, woc2 = st.columns(2)
                                with woc1:
                                    status_label = {"sent":"📨 수신","read":"👁️ 확인","done":"✅ 완료"}.get(wo.get("status","sent"),"?")
                                    st.caption(f"상태: {status_label}")
                                with woc2:
                                    if wo.get("status") != "done":
                                        if st.button("✅ 완료 처리", key=f"wo_done_{wo['id']}"):
                                            supabase.table("work_orders").update({"status":"done"}).eq("id", wo["id"]).execute()
                                            st.rerun()

        # ── 관리자 탭 ──
        if (is_admin or is_super) and tab8:
            with tab8:
                st.subheader(t("admin_title"))
                admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5, admin_tab6 = st.tabs([
                    t("admin_team"), t("admin_assign"), t("admin_token"), t("admin_email"), t("admin_log"), "💬 채팅 토큰"
                ])

                # 팀 현황
                with admin_tab1:
                    all_users_data = supabase.table("users").select("*").execute()
                    all_reps = supabase.table("reports").select("*").execute()
                    if all_users_data.data and all_reps.data:
                        df_r = pd.DataFrame(all_reps.data)
                        df_r["created_at"] = pd.to_datetime(df_r["created_at"])
                        this_month = date.today().strftime("%Y-%m")
                        df_r["month"] = df_r["created_at"].dt.strftime("%Y-%m")
                        summary = []
                        for u in all_users_data.data:
                            ur = df_r[df_r["user_id"]==u["id"]]
                            mr = ur[ur["month"]==this_month]
                            tgt = u.get("monthly_target",10)
                            rt = min(int(len(mr)/tgt*100),100) if tgt>0 else 0
                            ti = get_token_info(u["id"])
                            # ★ 수정: role_label() 함수 사용
                            _role_label_str = role_label(u.get("role_v2","user"))
                            summary.append({
                                "역할": _role_label_str,
                                "이름": u["name"] + "  (" + u.get("email","") + ")",
                                "이번달": len(mr),
                                "목표": tgt,
                                "달성률": f"{rt}%",
                                "누적": len(ur),
                                "드래곤토큰": f"{ti['used_count']}/{MONTHLY_DRAGON_LIMIT+ti.get('extra_tokens',0)}회"
                            })
                        st.dataframe(pd.DataFrame(summary), use_container_width=True)

                    st.subheader("💬 팀원에게 코멘트")
                    all_users_data2 = supabase.table("users").select("*").execute()
                    tu_name = st.selectbox(t("select_member"), [u["name"] + " (" + u.get("email","") + ")" for u in all_users_data2.data])
                    cmt_text = st.text_area(t("comment_content"))
                    if st.button(t("send_comment")):
                        if cmt_text:
                            tu = next(u for u in all_users_data2.data if u["name"]==tu_name)
                            supabase.table("comments").insert({"user_id":tu["id"],"admin_id":user["id"],"content":cmt_text}).execute()
                            st.success(f"✅ {tu_name}님께 전송됐습니다!")
                        else:
                            st.warning("코멘트 내용을 입력해주세요.")

                # 목록 배정
                with admin_tab2:
                    st.subheader("🎯 미배정 / 재배정 목록 관리")
                    all_users_data3 = supabase.table("users").select("*").execute()
                    umap = {u["id"]: u["name"] for u in (all_users_data3.data or [])}

                    unassigned = supabase.table("analyzed_urls").select("*").is_("assigned_to", "null").order("analyzed_at", desc=True).limit(100).execute()
                    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                    overdue = supabase.table("analyzed_urls").select("*").eq("reported", False).lt("analyzed_at", week_ago).order("analyzed_at", desc=True).limit(100).execute()

                    user_list = all_users_data3.data or []
                    user_options = {f"{u['name']} ({u.get('email','')})": u["id"] for u in user_list}

                    st.markdown(f"**미배정 목록 ({len(unassigned.data)}건)**")
                    for d in (unassigned.data or []):
                        with st.container(border=True):
                            col_a, col_b = st.columns([4, 2])
                            with col_a:
                                st.caption(f"{search_type_label(d.get('search_type',''))} | {str(d.get('analyzed_at',''))[:10]}")
                                st.write(d.get('title','')[:60])
                            with col_b:
                                sel_key = f"sel_assign_{d['id']}"
                                btn_key = f"assign_{d['id']}"
                                sel = st.selectbox(
                                    "담당자 선택",
                                    options=list(user_options.keys()),
                                    key=sel_key,
                                    label_visibility="collapsed"
                                )
                                if st.button("✅ 배정", key=btn_key, use_container_width=True):
                                    uid = user_options.get(sel)
                                    if uid:
                                        supabase.table("analyzed_urls").update({
                                            "assigned_to": uid,
                                            "assigned_at": datetime.now().isoformat()
                                        }).eq("id", d["id"]).execute()
                                        st.success(f"✅ 배정됨!"); st.rerun()
                                    else:
                                        st.warning("담당자를 선택해주세요.")

                    st.divider()
                    st.markdown(f"**⚠️ 1주일 경과 미작성 목록 ({len(overdue.data)}건)**")
                    for d in (overdue.data or []):
                        with st.container(border=True):
                            col_a, col_b = st.columns([4, 2])
                            with col_a:
                                current_assignee = umap.get(d.get("assigned_to",""), t("unassigned"))
                                st.caption(f"{search_type_label(d.get('search_type',''))} | 담당: {current_assignee} | {str(d.get('analyzed_at',''))[:10]}")
                                st.write(d.get('title','')[:60])
                            with col_b:
                                sel_key2 = f"sel_reassign_{d['id']}"
                                btn_key2 = f"reassign_{d['id']}"
                                sel2 = st.selectbox(
                                    "담당자 선택",
                                    options=list(user_options.keys()),
                                    key=sel_key2,
                                    label_visibility="collapsed"
                                )
                                if st.button("🔄 재배정", key=btn_key2, use_container_width=True):
                                    uid2 = user_options.get(sel2)
                                    if uid2:
                                        supabase.table("analyzed_urls").update({
                                            "assigned_to": uid2,
                                            "assigned_at": datetime.now().isoformat()
                                        }).eq("id", d["id"]).execute()
                                        st.success(f"✅ 재배정됨!"); st.rerun()
                                    else:
                                        st.warning("담당자를 선택해주세요.")

                # 토큰 관리
                with admin_tab3:
                    st.subheader("🪙 드래곤 추천 토큰 관리")
                    st.caption(f"기본 월 {MONTHLY_DRAGON_LIMIT}회 제공. 추가 토큰을 배정할 수 있습니다.")
                    all_users_data4 = supabase.table("users").select("*").execute()
                    for u in (all_users_data4.data or []):
                        ti = get_token_info(u["id"])
                        total = MONTHLY_DRAGON_LIMIT + ti.get("extra_tokens",0)
                        tc1, tc2, tc3 = st.columns([3,1,1])
                        with tc1:
                            st.write(f"**{u['name']}** `{u.get('email','')}` — 이번달 {ti['used_count']}/{total}회 사용")
                        with tc2:
                            extra = st.number_input("추가", min_value=0, max_value=50, value=0, key=f"tok_{u['id']}", label_visibility="collapsed")
                        with tc3:
                            if st.button("배정", key=f"tok_btn_{u['id']}"):
                                if extra > 0:
                                    add_extra_tokens(u["id"], extra)
                                    st.success(f"{u['name']}님께 {extra}회 추가됨"); st.rerun()
                        st.divider()

                # 수신자 관리
                with admin_tab4:
                    st.subheader("📧 이메일 수신자 관리")
                    st.caption("보고서를 발송할 기관, 의뢰인, 변호사를 등록합니다.")

                    with st.container(border=True):
                        st.markdown("**새 수신자 등록**")
                        nc1, nc2 = st.columns(2)
                        with nc1:
                            new_name = st.text_input("이름 / 기관명", key="new_rec_name")
                            new_email = st.text_input("이메일", key="new_rec_email")
                        with nc2:
                            new_type = st.selectbox("유형", ["agency","client","lawyer"],
                                format_func=lambda x:{"agency":"🏢 기관","client":"👤 의뢰인","lawyer":"⚖️ 변호사"}[x],
                                key="new_rec_type")
                            new_memo = st.text_input("메모 (선택)", key="new_rec_memo")
                        if st.button("➕ 수신자 등록", type="primary"):
                            if new_name and new_email:
                                try:
                                    supabase.table("email_recipients").insert({
                                        "name": new_name,
                                        "email": new_email,
                                        "type": new_type,
                                        "memo": new_memo
                                    }).execute()
                                    st.success(f"✅ {new_name} 등록됨!"); st.rerun()
                                except Exception as e:
                                    st.error(f"오류: {str(e)}")
                            else:
                                st.warning("이름과 이메일을 입력해주세요.")

                    st.subheader("등록된 수신자 목록")
                    recs = supabase.table("email_recipients").select("*").order("created_at", desc=False).execute()
                    type_label_rec = {"agency":"🏢 기관","client":"👤 의뢰인","lawyer":"⚖️ 변호사"}
                    for rc in (recs.data or []):
                        rc1, rc2, rc3 = st.columns([5, 1, 1])
                        with rc1:
                            status = "✅ 활성" if rc.get("active") else "❌ 비활성"
                            st.markdown(f"**{rc['name']}** {type_label_rec.get(rc.get('type',''),'')} | {rc['email']} | {status}")
                            if rc.get("memo"):
                                st.caption(rc["memo"])
                        with rc2:
                            new_active = not rc.get("active", True)
                            btn_label = "❌ 비활성화" if rc.get("active") else "✅ 활성화"
                            if st.button(btn_label, key=f"toggle_{rc['id']}"):
                                supabase.table("email_recipients").update({"active": new_active}).eq("id", rc["id"]).execute()
                                st.rerun()
                        with rc3:
                            if st.button("🗑️ 삭제", key=f"del_rec_{rc['id']}"):
                                supabase.table("email_recipients").delete().eq("id", rc["id"]).execute()
                                st.rerun()
                        st.divider()

                # 발송 이력
                with admin_tab5:
                    st.subheader("📨 이메일 발송 이력")
                    logs = supabase.table("email_logs").select("*").order("sent_at", desc=True).limit(200).execute()
                    all_users_log = supabase.table("users").select("id,name").execute()
                    umap_log = {u["id"]: u["name"] for u in (all_users_log.data or [])}
                    recs_log = supabase.table("email_recipients").select("id,name,email,type").execute()
                    rmap_log = {r["id"]: r for r in (recs_log.data or [])}
                    all_reps_log = supabase.table("reports").select("id,category,severity,platform").execute()
                    repmap_log = {r["id"]: r for r in (all_reps_log.data or [])}

                    if logs.data:
                        st.caption(f"총 {len(logs.data)}건")
                        for lg in logs.data:
                            rec = rmap_log.get(lg.get("recipient_id",""), {})
                            rep = repmap_log.get(lg.get("report_id",""), {})
                            sender = umap_log.get(lg.get("sent_by",""), "알 수 없음")
                            sent_at = str(lg.get("sent_at",""))[:16]
                            status_icon = "✅" if lg.get("status") == "sent" else "⏳"
                            type_label2 = {"agency":"🏢","client":"👤","lawyer":"⚖️"}
                            lc1, lc2 = st.columns([5,1])
                            with lc1:
                                st.markdown(f"{status_icon} **{rec.get('name','?')}** {type_label2.get(rec.get('type',''),'')} `{rec.get('email','')}` | {sent_at} | 발송자: {sender}")
                                st.caption(f"제목: {lg.get('subject','')} | 보고서: {sev_icon(rep.get('severity',0))} {rep.get('category','-')} {rep.get('platform','-')}")
                            with lc2:
                                st.caption(lg.get("status",""))
                            st.divider()
                    else:
                        st.info("발송 이력이 없습니다.")

                # 채팅 토큰 관리
                with admin_tab6:
                    st.subheader("💬 채팅 토큰 관리")
                    st.caption(f"기본 월 {CHAT_MONTHLY_LIMIT}턴 / 하루 {CHAT_DAILY_LIMIT}턴 / 주 {CHAT_WEEKLY_LIMIT}턴 제공 (평일만)")
                    all_users_ct = supabase.table("users").select("*").execute()
                    for u in (all_users_ct.data or []):
                        ct = get_chat_token_info(u["id"])
                        total = CHAT_MONTHLY_LIMIT + ct.get("extra_tokens", 0)
                        today_used = get_chat_today_count(u["id"])
                        week_used = get_chat_week_count(u["id"])
                        cc1, cc2, cc3 = st.columns([4, 1, 1])
                        with cc1:
                            st.write(f"**{u['name']}** `{u.get('email','')}` — 이번달 {ct['used_count']}/{total}턴 | 오늘 {today_used}/{CHAT_DAILY_LIMIT}턴 | 이번주 {week_used}/{CHAT_WEEKLY_LIMIT}턴")
                        with cc2:
                            extra = st.number_input("추가", min_value=0, max_value=500, value=0, key=f"chat_tok_{u['id']}", label_visibility="collapsed")
                        with cc3:
                            if st.button("배정", key=f"chat_tok_btn_{u['id']}"):
                                if extra > 0:
                                    add_chat_extra_tokens(u["id"], extra)
                                    st.success(f"{u['name']}님께 {extra}턴 추가됨"); st.rerun()
                        st.divider()

                    st.subheader("📋 최근 채팅 로그")
                    chat_logs = supabase.table("chat_logs").select("*").order("created_at", desc=True).limit(50).execute()
                    all_users_cl = supabase.table("users").select("id,name").execute()
                    umap_cl = {u["id"]: u["name"] for u in (all_users_cl.data or [])}
                    if chat_logs.data:
                        for lg in chat_logs.data:
                            uname = umap_cl.get(lg.get("user_id",""), "?")
                            created = str(lg.get("created_at",""))[:16]
                            with st.expander(f"👤 {uname} | {created} | Q: {str(lg.get('message',''))[:40]}..."):
                                lc1, lc2 = st.columns(2)
                                with lc1:
                                    st.markdown("**질문**")
                                    st.write(lg.get("message",""))
                                with lc2:
                                    st.markdown("**답변**")
                                    st.write(lg.get("response",""))
                    else:
                        st.info("채팅 로그가 없습니다.")