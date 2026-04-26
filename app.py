import streamlit as st
import anthropic
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from supabase import create_client
from datetime import date, datetime, timedelta
import pandas as pd
import requests
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
# v2026.03.15 — 보고서↔탐색URL 양방향 연결, YouTube 메타데이터 30일 보관 정책, 모바일 PWA 최적화
# v2026.04.19 — 보안 패치: URL 토큰 노출 방지, 세션 복원 시 토큰 즉시 삭제
# v2026.04.21 — 한국어 번역 62개 추가
# v2026.04.24 — 로그인 페이지 배너 이미지 추가
# v2026.04.26 — Resend 발신자 도메인 변경 (dragoneyes@dragoneyes.co.kr), 이메일 발송 에러 로깅 추가
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

# PWA 메타태그 (숨김 처리)
st.markdown("""
<style>
head { display: none !important; }
</style>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="DragonEyes">
<meta name="theme-color" content="#0f3460">
""", unsafe_allow_html=True)

# ── 모바일 반응형 CSS ──
st.markdown("""
<style>
/* ════════════════════════════════
   모바일 최적화 CSS (Android PWA)
   ════════════════════════════════ */

/* 모바일 기본 (768px 이하) */
@media (max-width: 768px) {

    /* 전체 여백 축소 */
    .block-container {
        padding: 0.3rem 0.4rem !important;
        max-width: 100% !important;
    }

    /* 컬럼 세로 배치 */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* 버튼 터치 친화적 */
    button {
        min-height: 2.8rem !important;
        font-size: 0.95rem !important;
    }
    button[kind="primary"] {
        min-height: 3rem !important;
        font-size: 1rem !important;
    }

    /* 입력창 */
    input, textarea, select {
        font-size: 1rem !important;
        min-height: 2.5rem !important;
    }

    /* 탭 스크롤 가능하게 */
    [data-testid="stTabs"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }
    button[data-baseweb="tab"] {
        font-size: 0.68rem !important;
        padding: 0.25rem 0.4rem !important;
        white-space: nowrap !important;
        min-width: fit-content !important;
    }

    /* 배너 모바일 축소 */
    div[style*="grid-template-columns: 1fr 1fr"] {
        grid-template-columns: 1fr !important;
    }

    /* 헤더 버튼 작게 */
    [data-testid="stHorizontalBlock"] button {
        padding: 0.2rem 0.3rem !important;
        font-size: 0.75rem !important;
        min-height: 2.2rem !important;
    }

    /* 메트릭 카드 */
    [data-testid="metric-container"] {
        padding: 0.2rem !important;
    }
    [data-testid="metric-container"] label {
        font-size: 0.65rem !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
    }

    /* 사이드바 숨김 */
    [data-testid="stSidebar"] { display: none !important; }

    /* 헤더 폰트 */
    h1 { font-size: 1.2rem !important; }
    h2 { font-size: 1rem !important; }
    h3 { font-size: 0.9rem !important; }

    /* 테이블 가로 스크롤 */
    [data-testid="stDataFrame"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }

    /* expander 터치 */
    [data-testid="stExpander"] summary {
        min-height: 2.5rem !important;
        display: flex !important;
        align-items: center !important;
    }

    /* 채팅 입력창 */
    [data-testid="stChatInput"] textarea {
        font-size: 1rem !important;
    }

    /* 드래곤파더 채팅 높이 */
    div[style*="height: 340px"] { height: 220px !important; }
    div[style*="height: 320px"] { height: 200px !important; }
    div[style*="height: 250px"] { height: 180px !important; }

    /* 컨테이너 높이 모바일 조정 */
    div[style*="height: 420px"] { height: auto !important; max-height: 300px !important; overflow-y: auto !important; }
    div[style*="height: 360px"] { height: auto !important; max-height: 280px !important; overflow-y: auto !important; }
    div[style*="height: 290px"] { height: auto !important; max-height: 250px !important; overflow-y: auto !important; }

    /* 이미지/비디오 */
    img, video, iframe { max-width: 100% !important; }

    /* 로그인 화면 */
    [data-testid="stForm"] {
        padding: 1rem !important;
    }

    /* 통계 카드 모바일 */
    div[style*="display:flex;gap:6px"] {
        flex-wrap: wrap !important;
        gap: 4px !important;
    }
    div[style*="display:flex;gap:12px"] {
        flex-wrap: wrap !important;
        gap: 6px !important;
    }

    /* 알림 메시지 */
    [data-testid="stAlert"] {
        font-size: 0.85rem !important;
        padding: 0.5rem !important;
    }
}

/* 태블릿 (768px ~ 1024px) */
@media (min-width: 769px) and (max-width: 1024px) {
    .block-container { padding: 0.8rem !important; }
    button[data-baseweb="tab"] {
        font-size: 0.78rem !important;
        padding: 0.35rem 0.4rem !important;
    }
    [data-testid="column"] {
        min-width: 45% !important;
    }
}

/* ── 공통 PC/모바일 스타일 ── */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 0.4rem !important;
}
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlock"] > div:first-child {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
h1 { font-size: 1.5rem !important; margin: 0 !important; }
h2 { font-size: 1.1rem !important; margin: 0 !important; }
h3 { font-size: 0.95rem !important; margin: 0 !important; }
hr { margin: 0.25rem 0 !important; }
[data-testid="metric-container"] { padding: 0.15rem 0.25rem !important; }
[data-testid="metric-container"] label { font-size: 0.72rem !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 0.68rem !important; }
[data-testid="stHeading"] { margin: 0.1rem 0 !important; }
[data-testid="stVerticalBlock"] > div { gap: 0.25rem !important; }
[data-testid="stHorizontalBlock"] { gap: 0.4rem !important; align-items: center !important; }
[data-testid="stProgressBar"] { margin: 0.15rem 0 !important; }
button[kind="secondary"] { padding: 0.25rem 0.4rem !important; font-size: 0.82rem !important; }
p { margin-bottom: 0.2rem !important; }

/* PWA 스타일 — 상태바 영역 대응 */
@media (display-mode: standalone) {
    .block-container {
        padding-top: env(safe-area-inset-top, 1rem) !important;
        padding-bottom: env(safe-area-inset-bottom, 0.4rem) !important;
    }
}
</style>
""", unsafe_allow_html=True)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
TERMS_VERSION = "v1.0"
TERMS_CONTENT = {
    "title": "DragonEyes 최종사용자 이용약관 동의서",
    "version": "v1.0",
    "date": "2026년 4월 18일",
    "sections": [
        {
            "num": "1",
            "title": "시스템 소개",
            "items": [
                "(1) 본 시스템은 '드래곤아이즈' 입니다. AI Agent가 온라인 유해컨텐츠를 자동으로 추적·모니터링하여 유해컨텐츠로 의심되는 콘텐츠를 추천리스트 형태로 각 사용자에게 중복 없이 제공합니다.",
                "(2) 관리자는 사용자의 업무 목표(모니터링 건수)를 설정하고 업무 달성도를 모니터링하며, 필요한 지시를 할 수 있습니다.",
                "(3) 라이선스 신청 업체의 동의가 있을 경우 위탁관리 업체도 사용자를 관리할 수 있게 지원합니다.",
                "(4) 드래곤아이즈의 자동추적 기능은 외부의 업무 요청을 수용할 수 있으며, 상황에 따라 자동 검색과 보고서 작성 업무 범위가 변경될 수 있습니다.",
            ]
        },
        {
            "num": "2",
            "title": "시스템 사용조건",
            "items": [
                "(1) 시스템 사용자 라이선스는 1인 1 라이선스를 배정하는 것을 원칙으로 합니다.",
                "(2) 모든 사용자는 '등록사용자'로 인식됩니다. 타인의 라이선스를 공유하는 것을 금합니다. 다만 시스템관리자의 허락이 있는 경우는 예외를 적용할 수 있습니다.",
                "(3) 사용자 라이선스는 연간 구독을 기본으로 한 사용자 계약입니다. 단기 사용계약은 별도의 협의를 거쳐 계약할 수 있습니다.",
                "(4) 드래곤아이즈 시스템을 사용하기 위해 제공되는 사용자 정보는 라이선스 마케팅 목적으로 사용될 수 있습니다.",
                "(5) 드래곤아이즈 모니터링 결과 작성된 보고서는 공공의 이익을 위해 통계 자료로 사용될 수 있습니다.",
                "(6) 드래곤아이즈 모니터링 결과 작성된 보고서에 대한 권리는 드래곤아이즈 시스템 관리자에게 귀속됩니다. 이에 동의하지 않는 사용자는 시스템을 사용할 수 없습니다.",
            ]
        },
    ]
}

DAILY_DRAGON_LIMIT = 9999  # 테스트 중 제한 해제
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
    # 위탁/업체 관리자
    "agency_admin":   "🤝 위탁관리자",
    "tenant_admin":   "🏢 업체관리자",
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
    "agency_admin":   "🤝",
    "tenant_admin":   "🏢",
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
        "dragon_monthly_limit":"월간 한도 도달. 관리자에게 토큰 요청하세요.",
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
        "email_preview":"📄 발송 미리보기","email_no_rec":"등록된 수신자가 없습니다.",
        "email_single":"📧 발송","email_sent_ok":"✅ {}에게 발송 예정으로 저장됨",
        "new_recipient":"**새 수신자 등록**","rec_name":"이름 / 기관명","rec_email":"이메일","rec_type":"유형",
        "rec_memo":"메모 (선택)","rec_add":"➕ 수신자 등록","rec_added":"✅ {} 등록됨!",
        "rec_list":"등록된 수신자 목록","rec_active":"✅ 활성","rec_inactive":"❌ 비활성",
        "deactivate":"❌ 비활성화","activate":"✅ 활성화",
        "today":"오늘",
        "this_week":"이번주",
        "this_month_label":"이번달",
        "turn":"턴",
        "chat_input_ph":"드래곤파더에게 질문하세요... (최대 300자)",
        "chat_disabled":"사용 불가 상태입니다",
        "chat_limit_daily":"오늘 한도({}턴) 도달",
        "chat_limit_weekly":"이번 주 한도({}턴) 도달",
        "chat_limit_monthly":"월간 한도 도달. 관리자에게 토큰 요청하세요.",
        "yt_watch":"▶️ 유튜브에서 보기",
        "yt_open_link":"▶️ 열기",
        "video_title":"영상 제목: {}",
        "search_result_cnt":"탐색 결과 ({}개)",
        "recommend_result_cnt":"추천 결과 ({}개)",
        "safe_count":"✅ 안전 판정 ({}개)",
        "skipped_cnt":"⏭️ 이미 분석한 영상 {}개 제외됨",
        "new_video_cnt":"새 영상 {}개 분석 시작...",
        "analyze_done":"완료! {}개 분석됨",
        "kw_gen_done":"키워드 {}개 생성됨!",
        "kw_gen_fail":"키워드 생성에 실패했습니다.",
        "dragon_monthly_warn":"월간 한도 도달. 관리자에게 토큰 요청하세요.",
        "dragon_daily_warn":"오늘 추천 한도({}회)에 도달했습니다. 내일 다시 사용 가능합니다.",
        "total_count":"총 {}건",
        "naver_found_msg":"총 {}개 결과 발견",
        "naver_searching_msg":"네이버 {} 검색 중...",
        "naver_pub_date":"게시일: {}",
        "write_report_safe":"안전",
        "ann_read_btn":"✅ 확인했습니다",
        "role_current":"현재 권한: **{}**",
        "team_created":"✅ {} 팀이 생성됐습니다!",
        "role_changed":"✅ {} 역할 변경됨",
        "member_added":"✅ {}님이 {}에 추가됐습니다!",
        "save_btn":"저장",
        "add_btn":"➕ 추가",
        "leave_start":"시작일",
        "leave_end":"종료일",
        "leave_reason_label":"사유: {}",
        "leave_approve":"✅ 승인",
        "leave_reject":"❌ 반려",
        "leave_approved":"승인됨",
        "leave_rejected":"반려됨",
        "work_order_title":"제목",
        "work_order_content":"내용",
        "cancel_btn":"취소",
        "close_btn":"닫기",
        "email_subject_label":"제목",
        "email_memo_label":"추가 메모 (선택)",
        "email_memo_label2":"추가 메모",
        "profile_contact_label":"수신: {}",
        "delete_error_msg":"삭제 오류: {}",
        "save_error_msg":"저장 오류: {}",
        "send_error_msg":"전송 오류: {}",
        "change_error_msg":"변경 오류: {}",
        "staff_error_msg":"직원 정보 불러오기 오류: {}",
        "error_msg":"오류: {}",
        "team_fail_msg":"팀 현황 불러오기 실패: {}",
        "write_report_help":"보고서 작성",
        "unassigned_label":"미배정",
        "naver_safe_cnt":"✅ 안전 판정 ({}개)",
        "dragon_fs_btn":"🐲 큰 화면에서 드래곤파더와 대화하기",
        "home_text_btn":"📝 텍스트 분석","home_yt_btn":"🎬 유튜브 분석","home_rep_btn":"📁 보고서 목록",
        "widget_placeholder":"📈 향후 통계 위젯이 추가될 공간입니다",
        "chat_caption":"아동 안전 모니터링 관련 질문을 해보세요. 질문은 300자 이내로 입력해주세요.",
        "chat_example":"💡 예: '이 댓글이 그루밍 패턴인지 분석해줘' / '보고서 작성 주의사항은?' / 'Roblox 위험 패턴은?'",
        "chat_example_short":"💡 예: '보고서 작성할 때 주의사항은?'",
        "col_name":"이름","col_month":"이번달","col_goal":"목표","col_rate":"달성률","col_total":"누적",
        "monthly_this":"이번달","write_report_btn":"📋 보고서 작성",
        "dragon_monitoring":"🐉 드래곤파더",
        "monthly_limit_warn":"📌 월간 한도 도달. 관리자에게 토큰 요청하세요.",
        "unit_items":"건",
        "banner_line1":"이 곳은 온라인 유해 컨텐츠를 모니터링하는 Claude 기반의 AI Agent 드래곤파더와 함께 작업하는 곳입니다.","banner_line2":"어린이 아동학대, 그루밍, 성폭력, 도박 등과 관련한 다양한 불법 컨텐츠를 감시합니다.","badge_intl":"국제기관 가이드라인 준수","badge_ncmec":"NCMEC 가이드라인 준수","badge_iwf":"IWF 글로벌 기준","home_footer":"이곳은 최승현님이 만드는 AI Agent 드래곤파더 월드입니다.","ann_unread":"미확인",
        "hdr_work":"💼 일하기","hdr_home":"🏠 홈","hdr_write":"📋 작성","hdr_notice":"📢 공지","hdr_admin":"👑 관리자","hdr_profile":"👤 사용자",
        "save_error":"저장 오류: {}","delete_error":"삭제 오류: {}","error":"오류: {}","no_url":"URL을 입력해주세요.",
        # 공지 팝업
        "ann_confirm":"✅ 확인 (다시 안 보기)","ann_later":"나중에 다시 알림","ann_date":"발송일:",
        # 일하기 페이지
        "work_title":"💼 일하기 — {}님","work_team_status":"📊 팀별 업무 현황",
        "work_pending":"⚠️ 내 담당 대기 목록","work_no_pending":"✅ 대기 중인 항목이 없습니다!",
        "work_no_team":"배정된 팀이 없습니다.","work_no_members":"팀원이 없습니다.",
        "work_no_assigned":"배정된 팀이 없습니다.","work_no_teams":"생성된 팀이 없습니다.",
        "work_team_fail":"팀 현황 불러오기 실패: {}","work_no_member":"팀원 없음",
        "work_preview":"미리보기","work_write":"보고서 작성",
        "work_prev_btn":"◀ 이전","work_next_btn":"다음 ▶",
        "work_goto":"🚀 바로가기","work_dragon_btn":"🐉 드래곤아이즈 자동 추천 리스트 생성",
        "work_total":"총 {}건 | {}/{}p",
        # 팝업
        "popup_close":"✖ 닫기","popup_write":"📋 보고서 작성",
        # 사용자 정보
        "profile_title":"👤 내 프로필","profile_my_info":"📋 내 정보",
        "profile_name":"이름","profile_email":"이메일","profile_team":"소속팀",
        "profile_role":"권한","profile_phone":"📞 연락처","profile_birth":"🎂 생년월일",
        "profile_addr":"🏠 주소","profile_addr_ph":"서울시 ...","profile_emergency":"🆘 비상연락처",
        "profile_emergency_ph":"관계 / 010-0000-0000","profile_save":"💾 저장",
        "profile_saved":"✅ 정보가 저장되었습니다!","profile_save_fail":"저장 오류: {}",
        "profile_pw":"🔐 비밀번호 변경","profile_pw_new":"새 비밀번호",
        "profile_pw_confirm":"비밀번호 확인","profile_pw_change":"🔐 비밀번호 변경",
        "profile_pw_empty":"새 비밀번호를 입력해주세요.","profile_pw_mismatch":"비밀번호가 일치하지 않습니다.",
        "profile_pw_short":"비밀번호는 6자 이상이어야 합니다.","profile_pw_ok":"✅ 비밀번호가 변경되었습니다!",
        "profile_pw_fail":"변경 오류: {}","profile_contact":"📬 본사에 문의",
        "profile_contact_to":"수신:","profile_subject":"제목","profile_subject_ph":"문의 제목을 입력해주세요",
        "profile_body":"내용","profile_body_ph":"문의 내용을 입력해주세요",
        "profile_send":"📨 본사로 전송","profile_sent":"✅ 본사에 메시지를 전송했습니다!",
        "profile_send_fail":"전송 오류: {}","profile_subject_empty":"제목을 입력해주세요.",
        "profile_body_empty":"내용을 입력해주세요.",
        "profile_staff":"📊 전체 직원 정보 관리 (디렉터 이상)",
        "profile_staff_csv":"📥 직원 정보 CSV 다운로드",
        "profile_staff_fail":"직원 정보 불러오기 오류: {}",
        # 채널 모니터링
        "ch_monitor_title":"📡 위험 채널 모니터링",
        "ch_monitor_caption":"심각도 3+ 영상이 포함된 채널이 자동으로 등록됩니다.",
        "ch_no_channels":"등록된 모니터링 채널이 없습니다. 자동 검색을 실행하면 위험 채널이 자동 등록됩니다.",
        "ch_total":"총 {}개 채널 모니터링 중","ch_stat_channels":"모니터링 채널 수",
        "ch_stat_avg":"평균 위험도","ch_stat_total":"총 위험 감지 건수",
        "ch_view":"▶️ 채널 보기","ch_scan":"🔍 지금 스캔","ch_scan_ing":"스캔 중...",
        "ch_scan_done":"{}개 영상 스캔 완료 — 위험 {}개","ch_no_new":"새 영상 없음",
        "ch_delete":"🗑️ 삭제","ch_scan_all":"🐉 모니터링 채널 전체 스캔",
        "ch_scan_all_done":"✅ 전체 스캔 완료 — 위험 콘텐츠 {}개 발견",
        # 네이버
        "naver_title":"🟢 네이버 카페·블로그·뉴스 검색",
        "naver_query":"🔍 검색어 입력","naver_query_ph":"예: 미성년자 채팅 만남, 아동 온라인 위험",
        "naver_type":"검색 대상","naver_auto_kw":"🐉 위험 키워드 자동 생성",
        "naver_search":"🔍 검색 시작","naver_result_count":"결과 개수",
        "naver_auto_kw_msg":"🔑 자동 생성 키워드: **{}**",
        "naver_searching":"네이버 {} 검색 중...","naver_analyzing":"🐲 드래곤파더가 위험도 분석 중...",
        "naver_no_result":"검색 결과가 없습니다.","naver_found":"총 {}개 결과 발견",
        "naver_risky":"### 🚨 주의 필요 ({}개)","naver_safe_all":"🟢 주의 필요한 게시물이 없습니다.",
        "naver_safe_list":"✅ 안전 판정 ({}개)","naver_enter_query":"검색어를 입력해주세요.",
        "naver_original":"🔗 원문 보기","naver_write_report":"📋 보고서 작성",
        "naver_cafe":"카페","naver_blog":"블로그","naver_news":"뉴스","naver_all":"전체",
        # 드래곤파더 채팅
        "chat_clear":"대화 초기화","chat_daily_limit":"오늘 한도({}턴) 도달",
        "chat_weekly_limit":"이번 주 한도({}턴) 도달",
        "chat_monthly_limit":"월간 한도 도달. 관리자에게 토큰 요청하세요.",
        "chat_fullscreen":"드래곤파더와 전체화면 대화",
        # 보고서 제출
        "report_submitted":"✅ 보고서가 제출되었습니다!",
        # 홈
        "home_back":"◀ 홈으로",
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
        "today":"Today",
        "this_week":"This Week",
        "this_month_label":"This Month",
        "turn":"turns",
        "chat_input_ph":"Ask DragonFather... (max 300 chars)",
        "chat_disabled":"Currently unavailable",
        "chat_limit_daily":"Daily limit ({} turns) reached",
        "chat_limit_weekly":"Weekly limit ({} turns) reached",
        "chat_limit_monthly":"Monthly limit reached. Ask admin for more tokens.",
        "yt_watch":"▶️ Watch on YouTube",
        "yt_open_link":"▶️ Open",
        "video_title":"Video title: {}",
        "search_result_cnt":"Search Results ({})",
        "recommend_result_cnt":"Recommended Results ({})",
        "safe_count":"✅ Safe ({})",
        "skipped_cnt":"⏭️ {} already-analyzed videos excluded",
        "new_video_cnt":"Analyzing {} new videos...",
        "analyze_done":"Done! {} analyzed",
        "kw_gen_done":"{} keywords generated!",
        "kw_gen_fail":"Keyword generation failed.",
        "dragon_monthly_warn":"Monthly limit reached. Ask admin for more tokens.",
        "dragon_daily_warn":"Daily limit ({} times) reached. Try again tomorrow.",
        "total_count":"Total: {}",
        "naver_found_msg":"Found {} results",
        "naver_searching_msg":"Searching Naver {}...",
        "naver_pub_date":"Published: {}",
        "write_report_safe":"Safe",
        "ann_read_btn":"✅ Confirmed",
        "role_current":"Current role: **{}**",
        "team_created":"✅ Team {} created!",
        "role_changed":"✅ {} role changed",
        "member_added":"✅ {} added to {}!",
        "save_btn":"Save",
        "add_btn":"➕ Add",
        "leave_start":"Start Date",
        "leave_end":"End Date",
        "leave_reason_label":"Reason: {}",
        "leave_approve":"✅ Approve",
        "leave_reject":"❌ Reject",
        "leave_approved":"Approved",
        "leave_rejected":"Rejected",
        "work_order_title":"Title",
        "work_order_content":"Content",
        "cancel_btn":"Cancel",
        "close_btn":"Close",
        "email_subject_label":"Subject",
        "email_memo_label":"Additional Memo (optional)",
        "email_memo_label2":"Additional Memo",
        "profile_contact_label":"To: {}",
        "delete_error_msg":"Delete error: {}",
        "save_error_msg":"Save error: {}",
        "send_error_msg":"Send error: {}",
        "change_error_msg":"Change error: {}",
        "staff_error_msg":"Staff load error: {}",
        "error_msg":"Error: {}",
        "team_fail_msg":"Failed to load team: {}",
        "write_report_help":"Write Report",
        "unassigned_label":"Unassigned",
        "naver_safe_cnt":"✅ Safe ({})",
        "dragon_fs_btn":"🐲 Chat with DragonFather in Fullscreen",
        "home_text_btn":"📝 Text Analysis","home_yt_btn":"🎬 YouTube Analysis","home_rep_btn":"📁 Reports",
        "widget_placeholder":"📈 Statistics widget will be added here",
        "chat_example":"💡 e.g. 'Analyze this comment for grooming patterns' / 'Report writing tips?' / 'Roblox risk patterns?'",
        "chat_example_short":"💡 e.g. 'What to check when writing a report?'",
        "col_name":"Name","col_month":"This Month","col_goal":"Goal","col_rate":"Rate","col_total":"Total",
        "monthly_this":"This Month","write_report_btn":"📋 Write Report",
        "dragon_monitoring":"🐉 DragonFather",
        "monthly_limit_warn":"📌 Monthly limit reached. Ask admin for more tokens.",
        "unit_items":"",
        "banner_line1":"This is a place to work with Claude-based AI Agent DragonFather to monitor harmful online content.","banner_line2":"We monitor illegal content related to child abuse, grooming, sexual violence, and gambling.","badge_intl":"International Guidelines Compliant","badge_ncmec":"NCMEC Guidelines","badge_iwf":"IWF Global Standards","home_footer":"This is the AI Agent DragonFather World created by SeungHyun Choi.","ann_unread":"Unread",
        "hdr_work":"💼 Work","hdr_home":"🏠 Home","hdr_write":"📋 Write","hdr_notice":"📢 Notice","hdr_admin":"👑 Admin","hdr_profile":"👤 Profile",
        "save_error":"Save error: {}","delete_error":"Delete error: {}","error":"Error: {}","no_url":"Please enter a URL.",
        # announcement popup
# 2nd pass
        "logout_help":"Logout","translate_ok":"✅ Translation complete!",
        "unassigned_team":"Unassigned","no_new_video":"No new videos found.",
        "monthly_limit_short":"Monthly limit reached.",
        "filter_all":"All",
        "history_types":["All","🐉 General","🎮 Roblox","⛏️ Minecraft","🔍 Keyword"],
        "report_cats":["All","Safe","Spam","Inappropriate","Adult","Grooming","Unclassified"],
        "no_reports_yet":"No reports yet!",
        "naver_api_error":"Naver API key is not set.",
        "chat_caption":"Ask questions about child safety monitoring. Max 300 characters.",
        "ann_new":"➕ New Notice / Work Order","ann_type":"Type","ann_title_label":"Title",
        "ann_content_label":"Content","ann_target":"Recipients","ann_team_sel":"Select Team",
        "ann_user_sel":"Select User","ann_sent":"✅ Notice sent!",
        "ann_title_empty":"Please enter a title and content.",
        "ann_filter_type":"Type Filter","ann_filter_period":"Period","ann_filter_search":"Search",
        "ann_filter_period_opts":["All","This Month","This Week"],"ann_search_ph":"Search title...",
        "ann_none":"No announcements.",
        "org_new_team":"➕ Create New Team","org_team_name":"Team Name","org_team_desc":"Description (optional)",
        "org_leader":"Assign Leader","org_create_team":"✅ Create Team","org_team_name_empty":"Please enter a team name.",
        "org_add_member":"Add Member",
        "leave_type":"Type","leave_reason":"Reason (optional)",
        "leave_submitted":"✅ Request submitted!","leave_date_error":"End date is before start date.",
        "leave_none":"No requests.","leave_pending":"✅ Pending Approvals",
        "leave_pending_none":"No pending requests.",
        "profile_subject_body_empty":"Please enter both subject and message.",
        "no_english":"⬜ No English translation — please translate in detail view first.",
        "no_recipients":"No recipients registered.",
        "ann_confirm":"✅ Confirm (Don't show again)","ann_later":"Remind me later","ann_date":"Sent:",
        # work page
        "work_title":"💼 Work — {}","work_team_status":"📊 Team Work Status",
        "work_pending":"⚠️ My Assigned Pending List","work_no_pending":"✅ No pending items!",
        "work_no_team":"Not assigned to a team.","work_no_members":"No team members.",
        "work_no_assigned":"No team assigned.","work_no_teams":"No teams created.",
        "work_team_fail":"Failed to load team status: {}","work_no_member":"No members",
        "work_preview":"Preview","work_write":"Write Report",
        "work_prev_btn":"◀ Prev","work_next_btn":"Next ▶",
        "work_goto":"🚀 Quick Access","work_dragon_btn":"🐉 Generate DragonEyes Auto List",
        "work_total":"Total {} | {}/{}p",
        # popup
        "popup_close":"✖ Close","popup_write":"📋 Write Report",
        # user profile
        "profile_title":"👤 My Profile","profile_my_info":"📋 My Information",
        "profile_name":"Name","profile_email":"Email","profile_team":"Team",
        "profile_role":"Role","profile_phone":"📞 Phone","profile_birth":"🎂 Birthday",
        "profile_addr":"🏠 Address","profile_addr_ph":"Enter address...","profile_emergency":"🆘 Emergency Contact",
        "profile_emergency_ph":"Relation / Phone number","profile_save":"💾 Save",
        "profile_saved":"✅ Information saved!","profile_save_fail":"Save error: {}",
        "profile_pw":"🔐 Change Password","profile_pw_new":"New Password",
        "profile_pw_confirm":"Confirm Password","profile_pw_change":"🔐 Change Password",
        "profile_pw_empty":"Please enter a new password.","profile_pw_mismatch":"Passwords do not match.",
        "profile_pw_short":"Password must be at least 6 characters.","profile_pw_ok":"✅ Password changed!",
        "profile_pw_fail":"Change error: {}","profile_contact":"📬 Contact HQ",
        "profile_contact_to":"To:","profile_subject":"Subject","profile_subject_ph":"Enter subject",
        "profile_body":"Message","profile_body_ph":"Enter your message",
        "profile_send":"📨 Send to HQ","profile_sent":"✅ Message sent to HQ!",
        "profile_send_fail":"Send error: {}","profile_subject_empty":"Please enter a subject.",
        "profile_body_empty":"Please enter a message.",
        "profile_staff":"📊 Staff Directory (Director+)",
        "profile_staff_csv":"📥 Download Staff CSV",
        "profile_staff_fail":"Error loading staff: {}",
        # channel monitoring
        "ch_monitor_title":"📡 Risk Channel Monitoring",
        "ch_monitor_caption":"Channels with severity 3+ videos are automatically registered.",
        "ch_no_channels":"No monitored channels yet. Run auto-search to register risk channels.",
        "ch_total":"Monitoring {} channels","ch_stat_channels":"Monitored Channels",
        "ch_stat_avg":"Avg Risk Level","ch_stat_total":"Total Risk Detections",
        "ch_view":"▶️ View Channel","ch_scan":"🔍 Scan Now","ch_scan_ing":"Scanning...",
        "ch_scan_done":"{} videos scanned — {} at risk","ch_no_new":"No new videos",
        "ch_delete":"🗑️ Remove","ch_scan_all":"🐉 Scan All Monitored Channels",
        "ch_scan_all_done":"✅ Full scan complete — {} risk items found",
        # naver
        "naver_title":"🟢 Naver Café·Blog·News Search",
        "naver_query":"🔍 Enter search term","naver_query_ph":"e.g. minor chat meeting, child online danger",
        "naver_type":"Search Target","naver_auto_kw":"🐉 Auto-generate Risk Keywords",
        "naver_search":"🔍 Start Search","naver_result_count":"Result count",
        "naver_auto_kw_msg":"🔑 Auto keyword: **{}**",
        "naver_searching":"Searching Naver {}...","naver_analyzing":"🐲 DragonFather analyzing risk...",
        "naver_no_result":"No results found.","naver_found":"Found {} results",
        "naver_risky":"### 🚨 Needs Attention ({})","naver_safe_all":"🟢 No concerning posts found.",
        "naver_safe_list":"✅ Safe ({})","naver_enter_query":"Please enter a search term.",
        "naver_original":"🔗 View Original","naver_write_report":"📋 Write Report",
        "naver_cafe":"Café","naver_blog":"Blog","naver_news":"News","naver_all":"All",
        # dragon chat
        "chat_clear":"Clear Chat","chat_daily_limit":"Daily limit ({} turns) reached",
        "chat_weekly_limit":"Weekly limit ({} turns) reached",
        "chat_monthly_limit":"Monthly limit reached. Ask admin for more tokens.",
        "chat_fullscreen":"Chat with DragonFather in fullscreen",
        # report
        "report_submitted":"✅ Report submitted!",
        # home
        "home_back":"◀ Home",
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
        "today":"本日",
        "this_week":"今週",
        "this_month_label":"今月",
        "turn":"ターン",
        "chat_input_ph":"ドラゴンファーザーに質問... (最大300文字)",
        "chat_disabled":"現在使用できません",
        "chat_limit_daily":"本日の上限（{}ターン）に達しました",
        "chat_limit_weekly":"今週の上限（{}ターン）に達しました",
        "chat_limit_monthly":"今月の上限に達しました。管理者に追加を申請してください。",
        "yt_watch":"▶️ YouTubeで見る",
        "yt_open_link":"▶️ 開く",
        "video_title":"動画タイトル: {}",
        "search_result_cnt":"検索結果（{}件）",
        "recommend_result_cnt":"推薦結果（{}件）",
        "safe_count":"✅ 安全判定（{}件）",
        "skipped_cnt":"⏭️ 分析済み{}件を除外",
        "new_video_cnt":"新規{}件の分析開始...",
        "analyze_done":"完了！{}件分析済み",
        "kw_gen_done":"{}個のキーワードを生成しました！",
        "kw_gen_fail":"キーワード生成に失敗しました。",
        "dragon_monthly_warn":"今月の上限に達しました。管理者に追加を申請してください。",
        "dragon_daily_warn":"本日の推薦上限（{}回）に達しました。明日また使用できます。",
        "total_count":"合計: {}件",
        "naver_found_msg":"{}件の結果が見つかりました",
        "naver_searching_msg":"Naver {} 検索中...",
        "naver_pub_date":"投稿日: {}",
        "write_report_safe":"安全",
        "ann_read_btn":"✅ 確認しました",
        "role_current":"現在の権限: **{}**",
        "team_created":"✅ {}チームが作成されました！",
        "role_changed":"✅ {}の役割が変更されました",
        "member_added":"✅ {}さんが{}に追加されました！",
        "save_btn":"保存",
        "add_btn":"➕ 追加",
        "leave_start":"開始日",
        "leave_end":"終了日",
        "leave_reason_label":"理由: {}",
        "leave_approve":"✅ 承認",
        "leave_reject":"❌ 却下",
        "leave_approved":"承認されました",
        "leave_rejected":"却下されました",
        "work_order_title":"タイトル",
        "work_order_content":"内容",
        "cancel_btn":"キャンセル",
        "close_btn":"閉じる",
        "email_subject_label":"件名",
        "email_memo_label":"追加メモ（任意）",
        "email_memo_label2":"追加メモ",
        "profile_contact_label":"宛先: {}",
        "delete_error_msg":"削除エラー: {}",
        "save_error_msg":"保存エラー: {}",
        "send_error_msg":"送信エラー: {}",
        "change_error_msg":"変更エラー: {}",
        "staff_error_msg":"スタッフ情報読み込みエラー: {}",
        "error_msg":"エラー: {}",
        "team_fail_msg":"チーム読み込み失敗: {}",
        "write_report_help":"レポート作成",
        "unassigned_label":"未割り当て",
        "naver_safe_cnt":"✅ 安全判定（{}件）",
        "dragon_fs_btn":"🐲 フルスクリーンでドラゴンファーザーと会話",
        "home_text_btn":"📝 テキスト分析","home_yt_btn":"🎬 YouTube分析","home_rep_btn":"📁 レポート一覧",
        "widget_placeholder":"📈 今後、統計ウィジェットが追加される予定です",
        "chat_example":"💡 例: 'このコメントはグルーミングパターン？' / 'レポート作成の注意点は？' / 'Robloxのリスクパターンは？'",
        "chat_example_short":"💡 例: 'レポート作成時の注意点は？'",
        "col_name":"名前","col_month":"今月","col_goal":"目標","col_rate":"達成率","col_total":"累計",
        "monthly_this":"今月","write_report_btn":"📋 レポート作成",
        "dragon_monitoring":"🐉 ドラゴンファーザー",
        "monthly_limit_warn":"📌 今月の上限に達しました。管理者に追加を申請してください。",
        "unit_items":"件",
        "banner_line1":"ここはClaude基盤のAI Agent ドラゴンファーザーと共にオンライン有害コンテンツをモニタリングする場所です。","banner_line2":"子どもへの性的虐待、グルーミング、性暴力、ギャンブル等の違法コンテンツを監視します。","badge_intl":"国際機関ガイドライン準拠","badge_ncmec":"NCMECガイドライン","badge_iwf":"IWFグローバル基準","home_footer":"ここはChoi SeungHyunが作るAI Agent ドラゴンファーザーワールドです。","ann_unread":"未確認",
        "hdr_work":"💼 作業","hdr_home":"🏠 ホーム","hdr_write":"📋 作成","hdr_notice":"📢 公知","hdr_admin":"👑 管理者","hdr_profile":"👤 ユーザー",
        "save_error":"保存エラー: {}","delete_error":"削除エラー: {}","error":"エラー: {}","no_url":"URLを入力してください。",
        # 公知ポップアップ
# 2次翻訳
        "logout_help":"ログアウト","translate_ok":"✅ 翻訳完了！",
        "unassigned_team":"未割り当て","no_new_video":"新しい動画がありません。",
        "monthly_limit_short":"今月の上限に達しました。",
        "filter_all":"すべて",
        "history_types":["すべて","🐉 一般","🎮 Roblox","⛏️ Minecraft","🔍 キーワード"],
        "report_cats":["すべて","安全","スパム","不適切","成人向け","グルーミング","未分類"],
        "no_reports_yet":"まだレポートがありません！",
        "naver_api_error":"Naver APIキーが設定されていません。",
        "chat_caption":"子どもの安全モニタリングに関する質問をどうぞ。300文字以内で入力してください。",
        "ann_new":"➕ 新規公知 / 業務指示作成","ann_type":"種別","ann_title_label":"タイトル",
        "ann_content_label":"内容","ann_target":"受信対象","ann_team_sel":"チーム選択",
        "ann_user_sel":"ユーザー選択","ann_sent":"✅ 公知が送信されました！",
        "ann_title_empty":"タイトルと内容を入力してください。",
        "ann_filter_type":"種別フィルター","ann_filter_period":"期間","ann_filter_search":"検索",
        "ann_filter_period_opts":["すべて","今月","今週"],"ann_search_ph":"タイトル検索...",
        "ann_none":"公知事項がありません。",
        "org_new_team":"➕ 新規チーム作成","org_team_name":"チーム名","org_team_desc":"説明（任意）",
        "org_leader":"リーダー指定","org_create_team":"✅ チーム作成","org_team_name_empty":"チーム名を入力してください。",
        "org_add_member":"メンバー追加",
        "leave_type":"種別","leave_reason":"理由（任意）",
        "leave_submitted":"✅ 申請が受け付けられました！","leave_date_error":"終了日が開始日より前です。",
        "leave_none":"申請履歴がありません。","leave_pending":"✅ 承認待ちリスト",
        "leave_pending_none":"待機中の申請がありません。",
        "profile_subject_body_empty":"件名と内容を両方入力してください。",
        "no_english":"⬜ 英語翻訳なし — 詳細画面で先に翻訳してください。",
        "no_recipients":"受信者が登録されていません。",
        "ann_confirm":"✅ 確認（次回から表示しない）","ann_later":"後で確認","ann_date":"送信日:",
        # 作業ページ
        "work_title":"💼 作業 — {}さん","work_team_status":"📊 チーム別業務状況",
        "work_pending":"⚠️ 担当未作成リスト","work_no_pending":"✅ 未作成リストはありません！",
        "work_no_team":"チームに割り当てられていません。","work_no_members":"チームメンバーがいません。",
        "work_no_assigned":"チームが割り当てられていません。","work_no_teams":"チームが作成されていません。",
        "work_team_fail":"チーム状況の読み込み失敗: {}","work_no_member":"メンバーなし",
        "work_preview":"プレビュー","work_write":"レポート作成",
        "work_prev_btn":"◀ 前へ","work_next_btn":"次へ ▶",
        "work_goto":"🚀 クイックアクセス","work_dragon_btn":"🐉 ドラゴンアイズ自動リスト生成",
        "work_total":"合計 {}件 | {}/{}p",
        # ポップアップ
        "popup_close":"✖ 閉じる","popup_write":"📋 レポート作成",
        # ユーザー情報
        "profile_title":"👤 ユーザー情報","profile_my_info":"📋 マイ情報",
        "profile_name":"名前","profile_email":"メールアドレス","profile_team":"所属チーム",
        "profile_role":"役割","profile_phone":"📞 電話番号","profile_birth":"🎂 生年月日",
        "profile_addr":"🏠 住所","profile_addr_ph":"住所を入力...","profile_emergency":"🆘 緊急連絡先",
        "profile_emergency_ph":"関係 / 電話番号","profile_save":"💾 保存",
        "profile_saved":"✅ 情報が保存されました！","profile_save_fail":"保存エラー: {}",
        "profile_pw":"🔐 パスワード変更","profile_pw_new":"新しいパスワード",
        "profile_pw_confirm":"パスワード確認","profile_pw_change":"🔐 パスワードを変更",
        "profile_pw_empty":"新しいパスワードを入力してください。","profile_pw_mismatch":"パスワードが一致しません。",
        "profile_pw_short":"パスワードは6文字以上必要です。","profile_pw_ok":"✅ パスワードが変更されました！",
        "profile_pw_fail":"変更エラー: {}","profile_contact":"📬 本社に連絡",
        "profile_contact_to":"宛先:","profile_subject":"件名","profile_subject_ph":"件名を入力してください",
        "profile_body":"内容","profile_body_ph":"内容を入力してください",
        "profile_send":"📨 本社へ送信","profile_sent":"✅ 本社にメッセージが送信されました！",
        "profile_send_fail":"送信エラー: {}","profile_subject_empty":"件名を入力してください。",
        "profile_body_empty":"内容を入力してください。",
        "profile_staff":"📊 全スタッフ情報管理（ディレクター以上）",
        "profile_staff_csv":"📥 全スタッフCSVダウンロード",
        "profile_staff_fail":"スタッフ情報読み込みエラー: {}",
        # チャンネルモニタリング
        "ch_monitor_title":"📡 危険チャンネルモニタリング",
        "ch_monitor_caption":"深刻度3以上の危険動画が発見されたチャンネルが自動登録されます。",
        "ch_no_channels":"モニタリングチャンネルがまだありません。自動検索を実行すると危険チャンネルが自動登録されます。",
        "ch_total":"{}チャンネルをモニタリング中","ch_stat_channels":"モニタリングチャンネル",
        "ch_stat_avg":"平均リスクレベル","ch_stat_total":"総リスク検出数",
        "ch_view":"▶️ チャンネルを見る","ch_scan":"🔍 今すぐスキャン","ch_scan_ing":"スキャン中...",
        "ch_scan_done":"{}件の動画スキャン完了 — 危険{}件","ch_no_new":"新しい動画なし",
        "ch_delete":"🗑️ 削除","ch_scan_all":"🐉 全モニタリングチャンネル一括スキャン",
        "ch_scan_all_done":"✅ 全スキャン完了 — 危険コンテンツ{}件発見",
        # ネイバー
        "naver_title":"🟢 Naver カフェ·ブログ·ニュース検索",
        "naver_query":"🔍 検索ワード入力","naver_query_ph":"例: 未成年者チャット, 子どもオンライン危険",
        "naver_type":"検索対象","naver_auto_kw":"🐉 危険キーワード自動生成",
        "naver_search":"🔍 検索開始","naver_result_count":"結果数",
        "naver_auto_kw_msg":"🔑 自動生成キーワード: **{}**",
        "naver_searching":"Naver {} 検索中...","naver_analyzing":"🐲 ドラゴンファーザーがリスク分析中...",
        "naver_no_result":"検索結果がありません。","naver_found":"{}件の結果が見つかりました",
        "naver_risky":"### 🚨 要注意（{}件）","naver_safe_all":"🟢 問題のある投稿はありません。",
        "naver_safe_list":"✅ 安全判定（{}件）","naver_enter_query":"検索ワードを入力してください。",
        "naver_original":"🔗 元記事を見る","naver_write_report":"📋 レポート作成",
        "naver_cafe":"カフェ","naver_blog":"ブログ","naver_news":"ニュース","naver_all":"すべて",
        # ドラゴンチャット
        "chat_clear":"会話をクリア","chat_daily_limit":"本日の上限（{}ターン）に達しました",
        "chat_weekly_limit":"今週の上限（{}ターン）に達しました",
        "chat_monthly_limit":"今月の上限に達しました。管理者に追加を申請してください。",
        "chat_fullscreen":"フルスクリーンでドラゴンファーザーと会話",
        # レポート
        "report_submitted":"✅ レポートが提出されました！",
        # ホーム
        "home_back":"◀ ホームへ",
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

# 동의 페이지 직접 접근 처리 (로그인 없이 접근 가능)
if "req_id" in params and st.session_state.get("current_page") != "consent_page":
    st.session_state.current_page = "consent_page"

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
    """역할 반환: superadmin > agency_admin > tenant_admin > group_leader > director > team_leader > user"""
    return user.get("role_v2") or ("admin" if user.get("role") == "admin" else "user")

def is_superadmin(user):
    return get_user_role(user) == "superadmin"

def is_agency_admin(user):
    """위탁관리자 여부"""
    return get_user_role(user) == "agency_admin"

def is_tenant_admin(user):
    """업체관리자 여부"""
    return get_user_role(user) in ("tenant_admin", "agency_admin", "superadmin")

def is_director(user):
    return get_user_role(user) in (
        "superadmin", "agency_admin",
        "group_leader", "group_leader_2", "group_leader_3", "group_leader_4",
        "director", "director_2", "director_3", "director_4",
    )

def is_team_leader(user):
    return get_user_role(user) in (
        "superadmin", "agency_admin", "tenant_admin",
        "group_leader", "group_leader_2", "group_leader_3", "group_leader_4",
        "director", "director_2", "director_3", "director_4",
        "team_leader",
    )

# ── 위탁관리자 헬퍼 함수 ──
@st.cache_data(ttl=60, show_spinner=False)
def get_agency_tenants(agency_user_id):
    """위탁관리자가 담당하는 업체 목록"""
    try:
        agency = supabase.table("agencies").select("id").eq("user_id", agency_user_id).execute()
        if not agency.data:
            return []
        agency_id = agency.data[0]["id"]
        at = supabase.table("agency_tenants").select("tenant_id").eq("agency_id", agency_id).execute()
        if not at.data:
            return []
        tenant_ids = [x["tenant_id"] for x in at.data]
        tenants = supabase.table("tenants").select("*").in_("id", tenant_ids).execute()
        return tenants.data or []
    except:
        return []

@st.cache_data(ttl=60, show_spinner=False)
def get_tenant_users(tenant_id):
    """특정 업체의 사용자 목록"""
    try:
        return supabase.table("users").select("*").eq("tenant_id", tenant_id).execute().data or []
    except:
        return []

@st.cache_data(ttl=60, show_spinner=False)
def get_all_tenants():
    """전체 업체 목록"""
    try:
        return supabase.table("tenants").select("*").order("name").execute().data or []
    except:
        return []

@st.cache_data(ttl=60, show_spinner=False)
def _pay_label(pt):
    """납입 종류 한글 라벨"""
    return {"monthly":"월납", "annual":"연납", "lump_sum":"일시납"}.get(pt or "", "-")

def get_all_agencies():
    """전체 위탁관리자 목록"""
    try:
        return supabase.table("agencies").select("*").execute().data or []
    except:
        return []

def send_notification(sent_by_id, target_type, target_id, channel, subject, body):
    """알림 발송 + 실제 이메일 발송 (Resend)"""
    email_sent = False
    recipient_email = None

    try:
        # 수신자 이메일 조회
        if target_id and target_type == "individual":
            user_res = supabase.table("users").select("email,name").eq("id", str(target_id)).execute()
            if user_res.data:
                recipient_email = user_res.data[0].get("email", "")

        # Resend로 실제 이메일 발송
        if recipient_email and RESEND_API_KEY and channel in ("email", "both"):
            try:
                resend.api_key = RESEND_API_KEY
                resend.Emails.send({
                    "from": "AI agent_dragoneyes <dragoneyes@dragoneyes.co.kr>",
                    "to": [recipient_email],
                    "subject": subject,
                    "html": f"""
                    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
                        <div style="background:linear-gradient(135deg,#0f3460,#16213e);padding:20px;border-radius:8px;margin-bottom:20px;">
                            <h2 style="color:white;margin:0;">🐉 DragonEyes 모니터링</h2>
                        </div>
                        <div style="background:#f8fafc;padding:20px;border-radius:8px;border:1px solid #e2e8f0;">
                            <h3 style="color:#1e293b;">{subject}</h3>
                            <div style="color:#475569;line-height:1.8;white-space:pre-wrap;">{body}</div>
                        </div>
                        <p style="color:#94a3b8;font-size:0.8rem;margin-top:16px;text-align:center;">
                            본 메일은 DragonEyes 모니터링 시스템에서 자동 발송되었습니다.
                        </p>
                    </div>
                    """,
                })
                email_sent = True
            except Exception as e:
                email_sent = False
                # v2026.04.26 — 이메일 발송 에러 로깅
                try:
                    st.warning(f"⚠️ 이메일 발송 실패: {str(e)[:200]}")
                except:
                    pass

        # DB에 발송 기록 저장
        supabase.table("notifications").insert({
            "sent_by": sent_by_id,
            "target_type": target_type,
            "target_id": str(target_id) if target_id else "all",
            "channel": channel,
            "subject": subject,
            "body": body,
            "status": "sent" if email_sent else "pending",
        }).execute()
        return True
    except:
        return False

def can_approve(user, target_user=None):
    role = get_user_role(user)
    if role in ("superadmin", "group_leader", "director"):
        return True
    if role == "team_leader":
        if target_user is None:
            return True
        return target_user.get("team_id") == user.get("team_id")
    return False

@st.cache_data(ttl=30, show_spinner=False)
def get_all_users():
    try:
        return supabase.table("users").select("*").execute().data or []
    except:
        return []

def check_user_terms(user):
    """사용자 동의 여부 확인"""
    return user.get("terms_agreed", False) and user.get("terms_version") == TERMS_VERSION

def save_user_consent(user_id, name, email):
    """사용자 동의 저장"""
    try:
        supabase.table("user_consents").insert({
            "user_id": user_id,
            "consent_version": TERMS_VERSION,
            "name": name,
            "email": email,
        }).execute()
        supabase.table("users").update({
            "terms_agreed": True,
            "terms_agreed_at": datetime.now().isoformat(),
            "terms_version": TERMS_VERSION,
        }).eq("id", user_id).execute()
        return True
    except Exception as e:
        return False

@st.cache_data(ttl=60, show_spinner=False)
def get_all_teams():
    try:
        return supabase.table("teams").select("*").execute().data or []
    except:
        return []

@st.cache_data(ttl=60, show_spinner=False)
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
                # 🔒 보안: URL에 토큰을 심지 않습니다 (4/19 패치 + 4/26 재적용)
                # 토큰은 st.session_state.access_token 에만 보관
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
        "ko": """당신은 Dragon J Holdings의 드래곤파더입니다. DragonEyes 팀의 아동 온라인 안전 전문 AI 동반자입니다.

【전문 역할】
당신은 다음 분야의 전문가입니다:
- 온라인 그루밍 패턴 식별 및 분석
- 아동 성착취 콘텐츠(CSAM) 탐지 방법론
- 섹스토션·딥페이크 피해 대응
- 유튜브·로블록스·마인크래프트·틱톡 등 플랫폼별 위험 패턴
- NCMEC·WeProtect·IWF 국제 가이드라인
- 한국 아동청소년 보호 관련 법령 (청소년성보호법, 아동복지법 등)
- 보고서 작성 방법 및 증거 보존

【업무 지원】
- 댓글/제목/설명에서 위험 신호 분석 요청시 9가지 체크리스트로 상세 분석
  ① 그루밍 ② 연락처 유도 ③ 성적 접근 ④ 개인정보 요구
  ⑤ 아이템 미끼 ⑥ 협박/섹스토션 ⑦ 도박 유도 ⑧ 가출/납치 ⑨ 자해/폭력
- 보고서 작성 도움: 심각도·분류·위험신호·이유 형식으로 구체적 안내
- 법적 신고 절차 안내 (경찰청 사이버범죄신고시스템, 방심위 등)

【대화 방식】
- 업무 질문은 전문적이고 구체적으로 답변
- 일상 대화, 고민 상담, 잡담, 유머도 자유롭게
- 최신 정보 필요시 웹 검색 적극 활용
- 팀원들이 즐겁고 편안하게 일할 수 있도록 친근하고 따뜻하게
- 답변은 간결하되 핵심을 빠짐없이""",

        "en": """You are DragonFather, the expert AI companion of Dragon J Holdings DragonEyes team.

【Expert Role】
You are an expert in:
- Online grooming pattern identification and analysis
- CSAM detection methodologies
- Sextortion and deepfake victim support
- Platform-specific risks: YouTube, Roblox, Minecraft, TikTok
- NCMEC, WeProtect, IWF international guidelines
- Korean child protection laws

【Work Support】
- Analyze comments/titles/descriptions using 9-point checklist:
  ① Grooming ② Contact solicitation ③ Sexual approach ④ Personal info requests
  ⑤ Item baiting ⑥ Sextortion/threats ⑦ Gambling ⑧ Runaway/abduction ⑨ Self-harm
- Help with report writing: severity, category, risk signals, summary
- Guide on legal reporting procedures

【Communication】
- Professional and specific for work questions
- Warm and casual for daily conversation
- Use web search for latest information
- Be concise but thorough""",

        "ja": """あなたはDragon J Holdings DragonEyesチームの専門AIコンパニオン、ドラゴンファーザーです。

【専門分野】
- オンライングルーミングパターンの識別・分析
- CSAM検出方法論
- セクストーション・ディープフェイク被害対応
- YouTube・ロブロックス・マインクラフト等のプラットフォーム別リスク
- NCMEC・WeProtect・IWF国際ガイドライン

【業務サポート】
- コメント・タイトル・説明文の9項目チェックリスト分析
- レポート作成支援
- 最新情報はウェブ検索を活用

【対話スタイル】
- 業務質問は専門的に、日常会話は温かく親しみやすく"""
    }

    tools = [{"type": "web_search_20250305", "name": "web_search"}]
    recent = messages_history[-8:] if len(messages_history) > 8 else messages_history
    recent.append({"role": "user", "content": user_message[:500]})

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
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

def learn_keywords_from_report(content, result, severity, category):
    """보고서에서 위험 키워드를 자동 추출해서 학습"""
    if severity < 3:
        return  # 심각도 3 미만은 학습 안함
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=200,
            messages=[{"role": "user", "content": f"""아래 아동 안전 보고서에서 YouTube/네이버 검색에 사용할 수 있는 위험 키워드 3~5개를 추출하세요.
검색 키워드로 쓸 수 있는 2~5단어 조합으로 추출하세요.

분류: {category}
심각도: {severity}
내용/URL: {str(content)[:200]}
분석결과: {str(result)[:300]}

반드시 아래 형식으로만 (한 줄에 하나씩):
키워드1
키워드2
키워드3"""}]
        )
        keywords = [k.strip() for k in msg.content[0].text.strip().splitlines() if k.strip() and len(k.strip()) > 2]
        for kw in keywords[:5]:
            try:
                existing = supabase.table("learned_keywords").select("id,use_count").eq("keyword", kw).execute()
                if existing.data:
                    supabase.table("learned_keywords").update({
                        "use_count": existing.data[0]["use_count"] + 1,
                        "last_used_at": datetime.now().isoformat(),
                        "category": category,
                        "severity": severity,
                    }).eq("keyword", kw).execute()
                else:
                    supabase.table("learned_keywords").insert({
                        "keyword": kw,
                        "source_url": str(content)[:200],
                        "category": category,
                        "severity": severity,
                        "use_count": 1,
                    }).execute()
            except:
                pass
    except:
        pass

@st.cache_data(ttl=120, show_spinner=False)
def get_learned_keywords(limit=20):
    """학습된 키워드 중 자주 사용된 것 반환"""
    try:
        res = supabase.table("learned_keywords").select("keyword,use_count,category").order("use_count", desc=True).limit(limit).execute()
        return [r["keyword"] for r in (res.data or [])]
    except:
        return []

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

        # analyzed_urls에서 해당 URL의 id 조회 (양방향 연결용)
        analyzed_url_id = None
        if content and ("youtube.com" in content or "youtu.be" in content):
            try:
                au = supabase.table("analyzed_urls").select("id").eq("url", content).execute()
                if au.data:
                    analyzed_url_id = au.data[0]["id"]
            except Exception:
                pass

        # 보고서 저장
        res = supabase.table("reports").insert({
            "user_id": st.session_state.user["id"],
            "content": content,
            "result": result,
            "severity": severity,
            "category": category,
            "platform": platform,
            "result_en": result_en,
            "content_en": content_en,
            "analyzed_url_id": analyzed_url_id,  # analyzed_urls 연결
        }).execute()

        # 보고서 ID 가져와서 analyzed_urls에 역방향 연결
        if res.data and analyzed_url_id:
            report_id = res.data[0]["id"]
            supabase.table("analyzed_urls").update({
                "reported": True,
                "report_id": report_id,  # reports 역방향 연결
            }).eq("url", content).execute()
        elif "youtube.com" in content or "youtu.be" in content:
            supabase.table("analyzed_urls").update({"reported": True}).eq("url", content).execute()

        # 키워드 자동 학습 (심각도 3 이상)
        if severity >= 3:
            learn_keywords_from_report(content, result, severity, category)

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
        st.error(t("delete_error_msg").format(str(e)))
        return False

@st.cache_data(ttl=30, show_spinner=False)
def get_analyzed_urls():
    try:
        res = supabase.table("analyzed_urls").select("url").execute()
        return set(r["url"] for r in res.data)
    except Exception:
        return set()

def mark_url_analyzed(url, title="", search_type="keyword", assigned_to=None):
    """URL 분석 기록 저장 — YouTube API 이용약관 준수:
    - 영상 제목(title)은 탐색 히스토리 UI 표시 목적으로만 보관
    - analyzed_at 기준 30일 경과 데이터는 자동 삭제 (메타데이터 보관 기간 정책)
    - URL은 중복 분석 방지를 위해 1000건 한도로 보관
    """
    try:
        data = {
            "url": url,
            "title": title,
            "search_type": search_type,
            "assigned_to": assigned_to,
            "assigned_at": datetime.now().isoformat() if assigned_to else None,
        }
        supabase.table("analyzed_urls").upsert(data).execute()

        # 30일 경과 데이터 자동 삭제 (YouTube API 메타데이터 보관 기간 정책)
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        try:
            supabase.table("analyzed_urls").delete().lt("analyzed_at", cutoff).execute()
        except Exception:
            pass

        # 1000건 초과 시 오래된 것부터 삭제
        all_urls = supabase.table("analyzed_urls").select("id").order("analyzed_at", desc=False).execute()
        if all_urls.data and len(all_urls.data) > 1000:
            old_ids = [r["id"] for r in all_urls.data[:len(all_urls.data)-1000]]
            for oid in old_ids:
                supabase.table("analyzed_urls").delete().eq("id", oid).execute()
    except Exception:
        pass

def register_watched_channel(channel_id, channel_name, severity, added_by=None):
    """위험 채널 자동 등록 / 기존 채널이면 위험도 업데이트"""
    try:
        existing = supabase.table("watched_channels").select("*").eq("channel_id", channel_id).execute()
        if existing.data:
            ch = existing.data[0]
            new_count = ch["risk_count"] + 1
            new_avg = ((ch["avg_severity"] * ch["risk_count"]) + severity) / new_count
            supabase.table("watched_channels").update({
                "risk_count": new_count,
                "avg_severity": round(new_avg, 2),
                "last_detected_at": datetime.now().isoformat(),
                "channel_name": channel_name,
            }).eq("channel_id", channel_id).execute()
        else:
            supabase.table("watched_channels").insert({
                "channel_id": channel_id,
                "channel_name": channel_name,
                "risk_count": 1,
                "avg_severity": float(severity),
                "first_detected_at": datetime.now().isoformat(),
                "last_detected_at": datetime.now().isoformat(),
                "status": "monitoring",
                "added_by": added_by,
            }).execute()
    except Exception:
        pass

@st.cache_data(ttl=60, show_spinner=False)
def get_watched_channels():
    """모니터링 중인 채널 목록"""
    try:
        return supabase.table("watched_channels").select("*").order("risk_count", desc=True).execute().data or []
    except:
        return []

def scan_watched_channel(channel_id, channel_name, max_results=5, assigned_to=None):
    """모니터링 채널의 최신 영상을 자동 스캔"""
    try:
        sr = youtube.search().list(
            part="snippet", channelId=channel_id, type="video",
            maxResults=max_results, order="date", safeSearch="none"
        ).execute()
        results = []
        for item in sr.get("items", []):
            vid = item["id"]["videoId"]
            url = f"https://www.youtube.com/watch?v={vid}"
            title = item["snippet"]["title"]
            desc = item["snippet"].get("description","")[:300]
            published = item["snippet"].get("publishedAt","")[:10]
            comments = get_video_comments(vid, max_comments=20)
            comment_text = "\n".join([f"- {c}" for c in comments[:10]]) if comments else "없음"
            msg = client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=300,
                messages=[{"role":"user","content":f"""아동 안전 전문 분석가로서 위험 채널의 최신 영상을 분석하세요.

채널: {channel_name}
제목: {title}
설명: {desc}
댓글: {comment_text}

반드시 아래 형식으로만:
심각도: (1~5)
분류: (안전/부적절/그루밍/섹스토션/도박/폭력유도)
위험신호: (구체적 패턴)
이유: (한 줄)"""}]
            )
            rt = msg.content[0].text
            sev = extract_severity(rt)
            cat = extract_category(rt)
            mark_url_analyzed(url, title, "channel_monitor", assigned_to)
            results.append({
                "id": vid, "title": title, "channel": channel_name,
                "url": url, "analysis": rt, "severity": sev,
                "category": cat, "search_type": "channel_monitor",
                "published": published
            })
        return results
    except Exception as e:
        return []

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
        st.session_state.prev_tab = from_tab  # 돌아올 탭도 from_tab으로 고정
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
            # 접근 시도 패턴 — 실제 그루밍에서 쓰이는 표현
            "초등학생 친구 구함", "중학생 친구 만들기", "여중생 친구해요",
            "10대 여자친구 구함", "청소년 여친 사귀기", "어린 친구 채팅",
            # 플랫폼 유도 패턴
            "카카오톡 알려줘 나이", "디스코드 여자 초등", "틱톡 여중생 팔로우",
            # 성적 접근 패턴 (간접적)
            "어린 여자아이 예쁜", "초등학생 몸매", "중학생 교복 영상",
            # 협박/섹스토션 패턴
            "사진 보내줘 조건", "영상통화 어린이", "나체 사진 아이",
            # 실종/납치 관련
            "미성년자 가출 쉼터", "청소년 가출 도와줘", "10대 가출 채팅",
        ],
        "gambling": [
            # 불법 도박 사이트 직접 홍보
            "토토사이트 추천 안전", "먹튀없는 카지노 사이트", "합법 배팅 사이트 순위",
            "바카라 필승법 공유", "스포츠토토 당첨 비법", "파워볼 패턴 분석",
            # 청소년 타깃 위장
            "용돈 버는 앱 추천 학생", "게임으로 돈버는 방법 10대", "소액투자 수익 인증",
            "하루 10만원 버는법 알바", "재택알바 나이무관 일당지급", "카카오페이 용돈",
            # 도박 광고 위장 콘텐츠
            "무료 머니 지급 이벤트", "첫충 보너스 카지노", "가입즉시 포인트 지급",
            "토큰게임 수익인증", "코인게임 환전가능", "크래쉬게임 전략",
            # 대리베팅/총판 모집
            "대리베팅 알바 모집", "토토 총판 수익 공유", "배팅 대행 알바",
            "스포츠 분석가 모집 재택", "승부예측 알바 고수익", "베팅방 운영 수익",
            # SNS 도박 유도
            "오픈채팅 배팅방 초대", "텔레그램 토토방 무료입장", "카톡 도박방 링크",
        ],
        "roblox": [
            # 실제 로블록스 내 위험 표현
            "로블록스 여자친구 사귀기", "roblox 여친 구함", "로블록스 커플 게임",
            # 연락처 교환 유도
            "로블록스 카톡 친추", "roblox 디코 서버 초대", "로블록스 인스타 맞팔",
            # 성인 접근 패턴
            "로블록스 성인 전용 게임", "roblox 19금 서버", "로블록스 야한 게임",
            # 개인정보 요구
            "로블록스 실제 나이 몇살", "roblox 학교 어디 다녀", "로블록스 집 주소",
            # 아이템/로벅스 미끼
            "로벅스 무료 지급 이벤트", "로블록스 아이템 공짜", "roblox 해킹 툴 무료",
        ],
        "minecraft": [
            # 마인크래프트 내 위험 표현
            "마인크래프트 여친 서버", "마크 커플 서버 모집", "마인크래프트 여자 친구",
            # 연락처 교환 유도
            "마인크래프트 카톡 서버", "마크 디스코드 초대 여자", "마인크래프트 인스타 팔로우",
            # 성인 접근 패턴
            "마인크래프트 야한 스킨", "마크 성인 서버", "마인크래프트 19금 모드",
            # 개인정보 요구
            "마인크래프트 실제 나이", "마크 학교 어디", "마인크래프트 실제 만남",
            # 아이템 미끼
            "마인크래프트 무료 렐름", "마크 계정 공유 공짜", "마인크래프트 해킹 무적",
        ],
    }
    pool = keyword_pools.get(platform, keyword_pools["general"])
    # 학습된 키워드 추가 (최대 5개)
    learned = get_learned_keywords(limit=10)
    if learned:
        pool = pool + learned
    return random.sample(pool, min(10, len(pool)))

def get_video_comments(video_id, max_comments=30):
    """유튜브 영상 댓글 수집 — 위험 패턴 탐지용"""
    try:
        res = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_comments,
            order="relevance",
            textFormat="plainText"
        ).execute()
        comments = []
        for item in res.get("items", []):
            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            if len(text.strip()) > 2:
                comments.append(text.strip()[:200])
        return comments
    except:
        return []  # 댓글 비활성화 or API 오류시 빈 리스트

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

        # 댓글 수집
        comments = get_video_comments(vid, max_comments=30)
        comment_text = ""
        if comments:
            # 위험 키워드 포함 댓글 우선 필터링
            danger_keywords = ["카카오", "카톡", "디스코드", "인스타", "텔레그램",
                              "나이", "학교", "만나", "사진", "영상", "선물",
                              "친구해", "여친", "남친", "좋아해", "사랑해"]
            flagged = [c for c in comments if any(k in c for k in danger_keywords)]
            normal = [c for c in comments if c not in flagged]
            selected = (flagged + normal)[:15]
            comment_text = "\n".join([f"- {c}" for c in selected])

        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=500,
            messages=[{"role": "user", "content": f"""당신은 아동 온라인 안전 전문 분석가입니다. 아래 유튜브 영상이 아동·청소년에게 위험한지 매우 엄격하게 분석하세요.

제목: {title}
채널: {channel}
업로드일: {published}
설명: {desc}
{"댓글 샘플:" + chr(10) + comment_text if comment_text else "댓글: 없음 또는 비활성화"}

【위험 신호 체크리스트 — 하나라도 해당하면 심각도 3 이상】
① 그루밍: 성인이 어린이/청소년에게 친구/연인 관계 유도, 나이 묻기, 학교 묻기
② 연락처 유도: 카카오톡·디스코드·인스타·텔레그램 등 외부 플랫폼으로 이동 유도
③ 성적 접근: 교복·신체·나이 관련 성적 암시, 야한 스킨/모드/서버
④ 개인정보: 주소·학교·전화번호 요구
⑤ 미끼: 무료 아이템·로벅스·게임 코인으로 미성년자 유인
⑥ 협박/섹스토션: 사진·영상 요구 후 유포 협박
⑦ 도박/사행성: 불법 배팅·토토·카지노 사이트 홍보, 첫충/보너스/무료머니 광고, 대리베팅·총판 모집, 파워볼·코인게임 수익인증, "용돈 버는 법" 위장 도박 유도
⑧ 가출/납치: 가출 조장, 만남 장소 공유
⑨ 자해/폭력: 자해 방법, 폭력 챌린지 유도

【댓글 분석 주의사항】
- 댓글에서 연락처 요청, 만남 유도, 나이/학교 묻기 패턴이 있으면 심각도 +1
- 댓글이 없어도 제목/설명만으로 위험 판단 가능

【중요】
- 제목/설명이 애매하거나 의심스러우면 심각도를 높게 잡으세요
- 안전으로 분류하려면 명백히 교육적이거나 공식 채널이어야 함

반드시 아래 형식으로만 답변하세요:
심각도: (1~5)
분류: (안전/스팸/부적절/성인/그루밍/섹스토션/도박/폭력유도/개인정보침해)
위험신호: (발견된 위험 패턴 구체적으로, 없으면 "없음")
이유: (한 줄 요약)"""}]
        )
        rt = msg.content[0].text
        sev = extract_severity(rt)
        cat = extract_category(rt)

        if search_type in ["dragon_general", "dragon_roblox", "dragon_minecraft"]:
            if sev < 2 or cat in ["안전"]:  # 기준 완화: 스팸도 포함
                analyzed_urls.add(url)
                mark_url_analyzed(url, title, search_type, assigned_to)
                continue

        mark_url_analyzed(url, title, search_type, assigned_to)
        # 심각도 3 이상이면 채널 자동 모니터링 등록
        if sev >= 3:
            register_watched_channel(
                channel_id=item["snippet"]["channelId"],
                channel_name=channel,
                severity=sev,
                added_by=assigned_to
            )
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
    /* 로그인 페이지 국기 버튼 크기 키우기 (v2026.04.26) */
    [data-testid="stHorizontalBlock"] button p {
        font-size: 2.5rem !important;
        line-height: 1.2 !important;
        margin: 0 !important;
    }
    [data-testid="stHorizontalBlock"] button {
        padding: 8px !important;
        height: auto !important;
        min-height: 60px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    with lc2:
        if st.button("🇰🇷", help="한국어", key="login_flag_ko"): st.session_state.lang = "ko"; st.rerun()
    with lc3:
        if st.button("🇺🇸", help="English", key="login_flag_en"): st.session_state.lang = "en"; st.rerun()
    with lc4:
        if st.button("🇯🇵", help="日本語", key="login_flag_ja"): st.session_state.lang = "ja"; st.rerun()

    # ── 로그인 배너 (v2026.04.26 base64 임베딩) ──
    _banner_b64 = "iVBORw0KGgoAAAANSUhEUgAABkAAAADICAIAAAA/Xbp/AACLIElEQVR4nO3ddXxTVxsH8BPXNqm7QhV3d9+wOWPuytjGXN+5O1M2xjbGYGNDhgx3aIu0tNDSlrqmmqRJ48n7R0qaJjfJrQCV3/fDH8m55557bu5Nmjyc8xxGZMI9pIsxaJZ1qkHnbe04REd7Q71fl54bo7MNejxCp5tnuHzSwUN0qEMud+q6YzM60mD7jtnpthl0mrial6MT26irdq/L0e4Pu3Yfomv65GpzB1/NrmjDQ9P0Wu3U3d8VJ9/JurTev+07yuV5g7hotSvvzqtxObr8ywrlX/Qu1eaW6fK7p9Pt0t7T3W3VNV25HF/YHNti0G/N5XudQfmsXR/j7fobS33Bab7D3X7xatcHkdMfdLcnQet1ZtCu6er+c1dA74p4+p7i+e3m4Z1B44pQvaY032q0v2Z5ep1b72Pal87hwJ7vSE+3fcd/q1AcxLEmi8Oh2uL2cng8LkUter8Jab7baH/sduyDyH21Tv1tdOw4za/ZtI7JYDK78BtnSz267+CO/D1qxz4ub3CadyXN0+jy7zm0MK/KUQEAAAAAAAAArjAGE2GQngpXDgAAAAAAAMCd1uFX0JMhetWjsa92BwAAAAAAAAC6L0SvegGErnoBXEIAAAAAAAAA6LUQveodcBUBAAAAAAAAqGH4VU+H6FWvgSmEAAAAAAAAABQQverRmAhd9S64nAAAAAAAAADQqyB61fvgigIAAAAAAAA4wvCrngvRq14JFxUAAAAAAAAAeglEr3orXFcAAAAAAACANjD8qodC9KoXQxJ3AAAAAAAAAOjZmEzW1e4CXF6ITQIAAAAAAAC0YnG4V7sL0D6IXvUFCGABAAAAAAAAtED0qsdB9KqPQAALAAAAAAAAAHokRK/6DgSwAAAAAAAAAAghhI3hVz0Kold9CgJYAAAAAAAAANDDIHrV1yCABQAAAAAAAIDhVz0Jold9EAJYAAAAAAAAANBjIHrVNyGABQAAAAAAAH0dhl/1FIhe9VkIYAEAAAAAAAAAQLeGABYAAAAAAAD0aRh+1VNg+FVfhgAWAAAAAAAAAHR3iF71cQhgAQAAAAAAQN+F4Vc9AqJXgAAWAAAAAAAAAHRfiF4BQQALAAAAAAAA+iwMv+r+EL0CKwSwAAAAAAAAAACgW0MACwAAAAAAAPoiDL/q/jD8CmwQwAIAAAAAAACAbgfRK7CHABYAAAAAAAAAdC+IXoEDBLAAAAAAAACgz8H8QYCeBQEsAAAAAAAAAOhGMPwKnCGABQAAAAAAAH0Lhl91Z0wWoldAAQEsAAAAAAAAAOgWEL0CVxDAAgAAAAAAAACAbg0BLAAAAAAAAOhDMH+w28LwK3ADASwAAAAAAAAAuMoQvQL3EMACAAAAAACAvgLDrwB6KASwAAAAAAAAAOBqwvAr8AgBLAAAAAAAAAAA6NYQwAIAAAAAAIA+AfMHuycMvwI6EMACAAAAAAAAAIBuDQEsAAAAAAAAALg6MPwKaEIACwAAAAAAAHo/zB/shhC9AvoQwAIAAAAAAAAAgG4NASwAAAAAAAAAuNIw/AraBQEsAAAAAAAA6OUwfxCgp0MACwAAAAAAAACuKAy/gvZCAAsAAAAAAAAAALo19tXuQE/CFbEixoiEgRxCiLxYV5aiuto9AgAAAAAAAA8wf7C7wfAr6AAEsOgSBbJnvRPuFcSzlciy1Affq9KrzVexVwAAAAAAAAAAvR6mENI18r5Aa/SqSaZrkukIIUGDRAkLpFe5WwAAAAAAAAA9B4ZfQccggEVX5DgvQsjJH2s2P1i8+cFiWZaaEJK0wOdq9wsAAAAAAAAAoJfr01MIgwYJY6d5RYz14olbAsA6lUmW1VyeqipLVevVJuddCvcrrQ9KU9VBg0S2HXu6pITwHRtfodxkMpsVCrVc0dwoV53PKTudUXjyzMWq6sYr3ENwIyk+7N8Nz3dgx2qZfOK817q8PwAAAAAA3QcSYAH0Dn03gDXy/oCkhb4OhTwxK3KcV+Q4L53KlLO1MfdfuS2MlbGujjCI7ak4sK+8dCwm09fHy9fHi5CgEUP73XnrVELIkeM5q37Zc+R4ztXuHQAAAAAAAPQYmD8IHdZXojAOxj0R1H+m1Pq4oVBTmqKWF+sIIdJoXr8ZXl5BPJ6YNXSpf9JCn8z19Re2NhJCstbXE0bL7kEDhbHTJYQQnYpilJbViwvThkTUEkJ+O5a8PSPGVn7t0KLHZp0ND1T8cSTpva2jL9MJXm6TxidNGp90Kr1g+XM/YTQWAAAAAAAAAFxWfTGAFTFWbI1e6VSmE19Wl6WobJvKUlRZ6+uDBgmHLPG1zhAcdX/g4CV+sqzmhiKdNYAVOVbkGyOw1s/5lzp2s+PZzclh9dbHydF1tgDWiwvTHpqeZX380PSs384OryjpwZdg5LB+2ze+/PQLPx88ev5q9wUAAAAAAMAR5g92Kxh+BZ3Rg6MnHTZ4ScvMwUPvVcqymp0ryLKad2c1Bw0SJs6XRo7zss0rdKhWmtKUtb6e2MZlXfLiwjRb9IoQ4s0x2spt0SurO4aceb+kpw7CspJKRN998fCSez7NyCy62n0BAAAAAAAAgN6pLwawfGMFhJDSE02U0SsbWVazLKtZFMiOGOsVOUYkjeFbU7Y3yXSNRfryVFXBpYTu9sb2r3KIUqXkBxNCrh1a5FBOCDnO5ikXlRJCSDOPI+Py8iRMXTdaFzJhxON6vVHA50q8hdFRgSOH9btuwdjY6CCHalwu+7vPH1q05D1ZjeKq9BMo3XrfF3qD0X0dg9HlHFgAAAAAAACA7qPPBbCCBgmtD8pTVW6qsXhqjlc9IcQiUJSc5Bcf55nNXKNBZFY5jsNy8OScM/ZPc9SCB8qDvW/LeG/oWYeaSgP7cCDXaNEQQixMrS6RoYvSSreFtPeMLjeNVq/R6qtr5Ckn875e9d/CeaPefnWpWMy3rxMYIHnuyetWvLSmXS37SEUP3DVr0oTkmKgghUK992Dm+59u0mj19nW8vQTjRidMGJs4MDnS388rwM9bbzA2NKiyckoPHzu/decpvd5DjMbG38/r+gVjxo6KT4wL85GKNFp9ZXXjzt1n1m44rGzStKvnQgF32uSBM6cOTk4MD/SXcLnsmhpFcWnN/sPndu8/K6vteCCPz+PMmzVs/pzh0ZGBIcHSpiZtaXndnoOZ6/46qlJr29XU2XMlLS+O4xjBq8BLzJ81dfCc6YP7xwYHBUp0OkNtnTI7r2LXvrMHj2bTvIgcDuvGhWMnjk0ckBAmlYpYLGZNraKyWn4sNXfvoXMXC6sv91kAAAAAAHQ3NydlToooSq2MWHtuOGWFL2dvTq2M/P089VZKNyWenRRemFYVufb8CFd1xoaWTIooCBSqqlTee0viM2tCnet8MfNv22OzhbHi0E3OdT6b+meDVvRO6jVmC2Ogf8V9A499fmZGidLPvs5dA44PCSi3L9lXmrS9cDDN0/l0ygZCiIUQlZ5/rj5s88VhBrPjTMZPp6w/WR3zR+4YN+3c0P/0hND8kzLqanclHR3iX9amk2XJ24uHOFT7ZNI6+6fPHr3VbHH8wcZkWGZFnhseUCzi6Eqb/LYUjqhp9nY+4seXmmo28PLlQf8UjFIbeBTVJq7TGLlvpN5gsjAJIdf3SxsXkv9X/tg0WT83J9s99bkAlo2qlvo3M4un5gUXcvhNrUX2jwkx6LwsOr5J52U0iBz2HRPdODau9Vd0jlpwc1oCIWRDcrZtIqHN+7VxjUYGsXvjGAPdxdS6A4vFsmXHyXM5ZX+vfVbiLbTftPDaUV9+t72ktNZhl+8+f3j29NY37WvvrF+74RAhZM7MYR+/dadI1BIIEwq4dyyZ8u/OU6fSC6wlwUHSB+6edeuNE/k8jn2DPB7HSyyIigyYP2fEk4/Mf+Wd9QePnHPfbS6X/cyyhXcumcLltt7wPB5HKhElJ4SvWLaQci+TyRw/YplDIYvJvPn68csfvibAv80nSGSEf2SE/+QJyS+tuP6XPw5+8+MuN0Gx7z57YNa01k/btz/+5+ffDxBC5s8Z8frzN/r6iFs76cfx9/MaPiTm7lunPLLix7PnStyfaWeMGBq7YfWT9iXKJs2YmS8bDC5HaT3x0LwnHpprX/LSW+v/3HzCvoTJZCy5fvzTj14jlbS+X/g8jsRb2D82eOHcEcWlta+//9fx1Dw3fWMwGNfOGfbMY/PDQtusHBoZ7h8Z7j92ZP8Vj1176HjOF9/tzMouc9UIAAAAAEDvM8BfVqnyTvavYRBi6ao2/aorVd5JfjJXbc6MylsYdy6/MWBXUWJ/ad2wwArKABYhpFDuf6Iimrjtmy9fPTyw9JQsylWFYxX9s+vD+klrRgcX7S1JrtV4Vakl7TqjfHnQicrYOJ+acSEFGiNnW6FjXImOJN/KKrU0ybeK8mU5Vhmf3RDWT1IzOqhwb9mAWo1XlVpK2U6RMiC1uiV4ZHGKXhFCFsWenhial14bJWuWTAjJWz501/unFjTp+c41L8qDjlfFh4kbZkScN1qYf+SOpzyigK2P96nKaQhjEMtA/x78i6nvBrAoMb2aRMHZDGabX+zKCIE6kKeVcphGc/AZBYenJkTNJvVMLpMQQtgMM4tBCLGwGE9OKbDtZY1eyU3sL4cUJYkcYxmbav2+q/FxePn553xJT1BQVL3i5V9+/OoR+0IWk/nA3bNeeXOdq72srAGIm6+f8O5rtzGZbd6rZrMl+0IZISQyIuDhe2ffsHAMh+Ph/gwN8V315cPPvvLr5u1prupIvIVrVz0xIDHCfVN0CIW8Lz+4Z9qkgW7qcLnsB+6aOWf60PuWfVtYLKPTbFy/YB6X8+Gbt82f4/L/N4ICpatXPrr4tg/LKupd1emk0xmFRSU1MVGBthJvL8H40QmHjmW72mXKhCT7pyaTec/BTPsSPo/z5fv3TJ88wM1xoyMDfl75yItv/PHPNuqLyGQyPnnrjvlzPfyX0ZTxSZPGJv742/5Pv9lhMpndVwYAAACAvqDXZ3APFjX5Cpp/OjvqviEnI7zlpUpp59sMEjX5CppXZ465d3BqhHdjqdLHoYKQY5gbe6FA7r/yzESLhbGXxLMYLr9+1zaL0qpaIlNMFz/vSpR+M6NyTrsOYF2UBxLCYDLMo4OLchpCihT+7T0puVaYURuZURsZ6dXQT+I46oKOIKHSl69ekz3h7uRj4V4NZU2OP94vKgKJgjAZ5tFBhTkNIUXKAFdN1Wm8TspiXW314mrHhVw8Vx++9sIEQshFedDjQ/ZMCcvZVjTMuXKjTpRZF5FZF5HkWxkupl5ijhBSrxUP8S/NaQiLkdSyGGaNsae+L7pRxqUrjCtyPHcmRytuG72qSxRfuC6kdLJ/faKXOphvZjM5epfvzMG+3mP8W4dQWcdefTmk6LoAx4jDS5VJ91Uk2Jcw1GzxIX9xqh/pIfYdzDx55qJD4fTJ7iI7VmEhvoMGRL39yq0O0StCyMXCqmaNnhDyydt3LrlhgsfolRWLyXz39duiIwNdbf1p5aNdEr3i8zh//LjcffTKJjLCf+OvK/rHBtOpPGxQzK/fPeYmemUllQifW76IToMdtnFLikPJ3Jku/2vCRyoalBxpX3LiVH6jXG17yuGwfv76EffRKysmk/He67dOGJNAufWBO2d4jF7Z2kmMCzObu+p/ngAAAAAAurXkAJlSxz8rC1UZuAMCaP33uUcD/KuVOv7ZmlC1gZvsT9FmmFjOZRnTKiNto4esc9Mo+QvVI4NLRwaXhnq7nG90ri5Uymse6F9xubOfMAjx5mqMrnvrRpJvpVIvyKqLUBt4Sb5VXd43m1BRI4thzqpr+Q1bpAxo0vPDxQ2u6jMZlv5SWZBQUalyDDXalDT5D/ArYzPNg/1KLzSG8liGru/3FdFXAlhGqVE1TqUaptaaWi6VNNpxdijPv8wWvdL5cC5eE1g9wscobAmj+F1o8ilUV4yQFk/2y7smKPvGsPyFIfkLQ+rjxEyT5fqYxp8ntpk59efo3D9H5zpEr5QG9nXZST9US61PTRaW4ESg15ZY319jBZku77buac3vBxxKgoN8IsM9xMLj+4d+9t49bDbF4qmZl+bHffbNNsp9LRbqwASfx3n+qcWUm269aeLwITEOhZu2pS1/fvVzr/22/7CHuYf23n5lycC28Rr3JN7Cbz55QCikmITsIL5/yMhhtKYfz50xNMCPYvJzV9m0Lc1kbhOinTV1MItF/SkxeXySQxRy5550+6fPLVs4iuq8qmRyudJx/QQmk/HmSzfxuByHcrGI/9j9sx0Km5t1x9PyduzJyMous78rGhpVL7yxztV9AgAAAADQywz0l+U3+lsIudjgP4Aq2NQBAy61md/oP8CfIs+sD19DCFHq+YSQJ0ce+nLmP1/O/MdfoHauSQjpJ627Y+DJOwaeHODnMujDZFhSq2JmReUYzJcrQCHhaQb6V9yamOrF1V5o6Eji6WTfyovyQAshBYrAZN/KznRmVFDhJ5PWfTJp3dyoTOet3lwNIURtbP0hqTbwvbjUCWpGBRV+OPGPhwftk+uE+8pcDh2oUPmyGOZ+kupkv/KL8mAmo6f+YuoTUwgb58pV41vCvY2kUVrFmBwS6xvTJrLAYJq43i0jCeUxwurRfsa2r019IkX6dj6T3V/C/nxWkf3YKyvKaYOvF0dXEY4t7xWvRGiNW5n5ZqO/Vh+mMQbqmSyD2cTlloiEWZcxVNF5J9JynQtHj4wrLa9zs1d8/zZTo9NO56dnFvN5nH4xQccvNXg8NTflZN7YUfGEEJPJvO2/Uzv3pGdkFdfVK4ODfMaMjHvl2Rt9pG0SkM2cMjjA37u2znFdyIfvmeVQ8urb63//64j18cYtKSseX/DYA22yOK3dcNiaSN4+DjJjyqDrFjgm6pMr1B9/9e/REzlanWHIwKgnH52fFB9mX6FfTNDTj81/+6O/CW2Hj+fsO5TVqFDH9wu5e+lUsajNPGcmkzFj6qD1fx+j32C71NQpDx3LmT6p9YNPKhGOGx1/9MQF58qTx7edP2g27z7Q+vk7cmjs3UunOOyyadvJj776t6ZOSQiJiQp4++Vbxozob9saGe5/3fxR6/85br/L1EnJAkGbAa5Z2WX3L/+hobHlHRcW4vP0o9cunDeCEPLSWxtq69tkrAMAAAAA6K34bGOsTwOLYR4RXE4IsRAi5upUes//g+6hTWm9+zYbtQJCiISnIYTsKExK9pNNj8p31WBqZdS67JGEECaL5Wp8FY9tOFCWMCFsR5hY3pnOuxHvUx3nU63UCfaXJR4oS2zv7nyWIUZSx2KYhweWEOvLwtGpqDKm02HLgVWpphjFotAJCSFiTusSXmKupoqqJiEkXx58ShazJOFEdn1YdbObvGCW7IbwcSH5IrauQBHUsW53B70/gCWfqrRFr6yOygrzlDW3JY+yL+RIW6JXVSOklLEqSoO5GhLJepKMvLGp+QH+GedM7Vabav1+rQ08rvC2MBn2g95MkU2ND1ywMBkWJsPMtibSImYGw8IyNCc3c2oFnGrHASndR6NcXVJaGxXZZmZvWCjdWZByhfrpl9YcPHKOcpjox19t/XPNiu27T3+2cltxaY2tvLKqYdO/qZnnSv775xX7kUEsFnPi2KRN21LtGxmYFBEa0mZm8rmcMlv0yuqr73cunj86zK7ahbyKPzYeJaRNvxyCXIQQZZPmzodXns9pSYC392DWyTMFa394Ijkx3L7arTdO/G717joaURW5Qv3US78ePt6ScGo7If/tzdj6x/MOo5ySE8Ko9qaQnfqpm6219cpxs15xLt+4OcU+gEUImTdjqHMAi8lkOASwUk62mT/46H2zGYw2Pf/8250rf9xle1pUUnv3Y9/+8vUjo+1iWNcvGO0QwEro75gMcuWPu2zRK0JIRVXjilfX/rPt5LDB0fvaM6QOAAAAAHq3Xp8AK8GvlsUwrz47qtnA8eLp7hp0Otm/Jq2yU+lTEnxrWAzzz1mj1QauN1d758BTSX6yk1VtZqJUqiQGM2tMaGlKZXReQyCPZXITwLJisiim4NgwCJHrhKdlkQ5LDXahk9Uxf+SO7vDu8T4yFsP8S86EZgPXm6u9LfFEom/VKVl0x1pznwOrUi01WZhDA0qtdfpJZGKOzjnllpVcJzxdEzM0oGRsSMG+soFuYmoZtVF3JR1Or402mHpwFKj3TyFUjW35reub2zTw9zLvkmZCSI1G9W3JEW1Sa1CTydQTQirG+tCPXpktjBQN94yKk6blPGeWhGhn5agFqXVi67/PCkI+Kwi54ey4sP0jH8uOTalvbdZ1hrs2LOzuPjG1stoxS5zDwChXTCbzYytWuVk98ExG4bRrX1v+3Gr76JVNQVH1jj1nHAqd5/clJYQ7lPy3N92hxGAw7tl/1r5k0bWjHOqMHNZvyEDHhIIvv7nOFr2yUiib7338G6OxzQoAfB7ntpsmOZ+Cg7r6plvu/dwWvbLKyas4luo4zC026vLGy/cfOW8fHiKEzJ4+mMV0/KAYlBzpcK137s2wPY7rF+wQ3srJq/j25z0OjRgMpu/X7LMvGTY42s9XbF/i7SVw2Mu5M4SQY6m5K1ftci4HAAAAAOitBvjLmvS8dFlobkPA6apwjZFDmbKqXZL9q5v0vHRZWF5DwOnqCI2R4zwzUW3g7i2Oj5HULxtxZFZ07vRId9Eraw6sEUElI4JKuCyX65sTQvaVJkW4TkN+BfgJVCMCS0YElgwNKHXYlORbqTLwz9ZG5MuDztREaY2cpM7NInRDZeAfq4xP9Km8I/HorMhzdyYd0xo5hyuS3OxyqCKJwzRODqOYN2NzoTFMa+ScrXOZKb9H6OUBLG2MziJsCReJZTpGISdyU0vyHa3ZWLeo3ihtGTPFFClKpvg19hNTN0RIoECcKA2aGBSbKG2JIDAZFibDYptpqDUbJ+UOvfVo/yUn4m5Jjf+sIPSzgtC02jZBKMal9NJMT3mmmTomu45imcxuRdnkmMnIR0IrgPX9z7spZyDac7/cXtZ5x88U++XzrAL8HedglpZRTG8sKWuzCIXDmDJCyOQJyQ4lDY0q++lyNrV1yr0Hszzu7uzXDYcuFlJMLz+Z7pgp38spoNO1jEbTlh2n7Et8pKIxI/s7VHNcf7Dt/MHpTqnuV67aRbky4JETF+zHbRFCktuGHR2iaYSQ+++c5jCzEgAAAACgD0r2l5UoWmaWWQgpVUiT/Go6md7IsU2lT6KvzLnN/wqT/sodKmDr58TkCjiGjblD6rVCygatObBuT069PTlVwNa7OXRNs1dmHd3pJpdDrKT2tqQTtyWduCn+lMOmJN+qEmXLZCMLIaVNvok+1Zcvk9TWwmG7SgaHixunhF2oUPl8njHX/XTFi/KgCpXv+NA8N6+w0cx8NeXm8/WOgzx6lh48eIwObZTO9lgeJZQQJaPJKKzRNgfyCSEWobnq6SpuIZ8QQqTeet/WcF6iNGh6cD8vHsXv5DKV/IK8NQgtqNOFZCgYJouFxTCxWudMWUso+mShXlqBYbZYLk0W48i4kr0hTG13Dy9ac0XZo5OzXKcz/Lx2fwcOFxggGTIwKjY6KDoqcPgQxyGXzkN1nBlNFCF/g6FNYYCfN5PJsF/JbvzoeIddtu445TDSyubvrSlzZw61Lxk0INLbS6Bsos6618LFR19jo2MqRBGNV7iT/tqScs9tU+1L5s4cejwtz75kStuoXOqpi/aRpnGj4uy3ms2WlFOOkTgri8VSUdVgP5grMT7siN2MxdMZRQ67DB8c889vT3/x3c6dezOw4CAAAAAA9FmvHJpj/3Tl6fGU1Z7YvZj+4n6vHp5nX/nrMxMoq1kIOVIWe6TM5Tw4q+V7byD28wepuvHUwZttj9ecpz4Fq9Sq2NQqD0ek9PShW2jUWeJm6/9S2iwH/13WNFc1U6v7WfNbubLiyFKPnbEQxu7SgbtLW4cFUF7AZ+ya+ix9rquqzxxdal/cZOA/e/Q2j33onnp5AMueMkpIiJIQwta0GQmij7VOJGwTvVoUNSD35x0F2+UWL/bQx8aEjWwdaJenbDNgx8hj6rzYfHkXTPdjKVjsKhH/gje3nDp63d14OQ2EUTitLudsy/a0+ga6mbZZTOb4sQkL5o4cMyo+Isxdgi0vsWMAq7LKcQBqRBjFIolREW2GXCmbNA5hkYQ4x/8HuJBf4aobF/IcN7GYzP6xIWfOFrraxQ3n19MhJdblkHexKvN86eABrVMy50wf/L/3/7K9LFKJaFDbCZv28wcJIYMHtBmYWlpe5+cj9vOhHt6obtbZP/WRtLn5T5zMu5BXkdg2O35MZMDn79753BML/tqS+sffx+obXK7ICwAAAAAAAL1DLw9gGUI6ElcaIA0q3JdVsF1OCGE0Gcu2n7MFsPRG47n6Nst/Grw4FWN8xZWawOyOLH/GKfIiTXxuDY/ZyGfL2YRBXERXuyOJt2OgTS6nXjzVnvu5gTYcDvu2myc9ct8c55mAlJwjOzl5jikAx49JWPXLXofCcW0HWFVUNdg/5fM4QoFj9seaOoWrbtTUKS0Wi0P+cl8XsRuPKKfd0XTrfV/oDdSrChBCjEZ3LW/ckmIfwPLz9Ro1vF/qpVFUk8cn2r/aDvMH2WyWw2i46MiA3f+8RLPbDnMkTSbz06/8tmntCh7XcUGD0GCf5Q/NffiemX9vTf1m9R5ZjcuLAgAAAAAAAD1dLw9gOdAOsXD0ZmWUh/FNPBZb6yLGcrKuXGumCAqoQgV8uUEk0zlvck94tGWqoJlv1oc368M0xkCDNlxv9jYSQgQsJuO4j/SQtL3NXhnRTmmnGhWeA1h0xEYHrfrqEee0Vu2Sm1+Zm1+ZENe6jN2UCcljRsalnmrNMnjt7OEO2d8PHT1v/9SHKvZUW6t0dVCj0dTQqPLzbbMUgENi8ivj7LkSvd5ISEciov/+d+alFdfxea0xoznTh9gCWJPGtUmAlXb6ov2QOpp50FzhsB0XKMkvqH765d8+fOM2yumTPC576Y0T5s8Z/tp7f23f7ZikHwAAAAD6pl6/BCFAH9Tdsyx1EqeqzaiN3AWh527wnLRModOx7CarRVzbMvW0TCU/KqOeCBYoECsiPORgYlDl61HckdfwUG79I3kN911UXFfRPK5B219lEbUOHGue1E3HlUSE+fv7OY6NKiiiyETeXglxof/8/pyr6FVDo+p4aq7HHPBW367e7VDy08pHb7l+fIC/d1iI7wN3zfz0vbvttxqNpn+2ptqXUAZ/LJZennqpSaXZta/N4oxTJ7YmvRo9os2k7p17Muyf8viOQ6XaRaXWOhfu3p+5+PaPM7MdM/fbeHsJPn/3zkfundmZQwMAAAAAQNdqTYAF0Gm9fAQWW9cmQkdzmYBMeeXSGcN4Eu/mQmXgxHBJqA8h5KKibntptnPlQIH4ttjhAg5XEaM9mLldpXe3sEIHMCnWzWs3/wDjhInK5mbWnl2SLmiOEELItMkDnAvTTrlbQpUODof9xQf3OmdkLy2vW//3sb0HzlpX65s/d8S40QkeW9u64+S8WcPmTB9iKxEKuO+97jJl3U+/7issbrNMrPMqeISQwEBJjlOuKys2m+U8YbAnJmnauCV10TUjbU8jw/1jogKLSmrCQnzDQnxt5WazxWFBRjrTSN0oLace/VhcWnvjXZ9NmzTg0XtnDRlIvfjr8ofnpZ4qOJPpmPcdAAAAAAAAerpeHsDi5/DJvHbvVaZq3FJyfvyAqLCRUXqj8aKiLq2urEzlmBHcamZovIDDJYRIuHyJv0hV2cUBLOnBTk2jI4SERxmee7FcJDITQnIuCMtLOzVAxorBYNy11HHlhfyCKspwT7vMnDoovn+ofYnFYvn8m+3f/rTL1cJ/7i1/fvU3nzwwffJAjzU3bUv7+KutDoVanaFZo3dIgxXo7zIOGODv7ZAAi7iIgnVzKafyyysbwkNbY1VTJiQVldQ4DL9KO32xrr7JfqCaSq01Gk1su5mAGo1++LQXHVZ7tGrX7EaLxbL/8Pn9h88PHRR1161Trpk51CHxGYvJfO+1JXNufK89rQIAAAAAAEAP0MunELLlbOGZjmTkuSCXrc5L++Ds/s/OH/67ONNV9IoQEu3l62pTJzGVbMEfIfwLHmYm2guPMj6+XDZ8ROsQGKHQZIteEUJEQpdZvdvlrqVTY6ODHAp3tV2KrmPmzhzmUPLTr/u++n5Hx6JXhBAuhx0Y4GHcmaxW8fzra595+Rcz1TTPvIuVDiVx/UJcNRXf33GT2WzpkpmVV5jFYvnn3zazKadOSCaEjB7e375wJ9VFLy5ts1KnQMAdMaQj6926kpFV8tRLv85f8qHzpMLY6MC42OAuPBYAAAAAAAB0B718BBYhxOc/iVFq0sdSJNbpvEBBFyfnZik43Do+u4bDK5Vwqts3VCo8ymiNVcUnac6cbgnbPb5cZotedZUJYxJfWnG9Q6FGq1/z+/7ONx4e5udQsnXnqQ63xudxflr5yMCkCOvTg0fPH025MGp4/5AgKSFErmjOza84efriwaPn3az3dyw1d+igaPuShfNGfvD5Zspdblg41qEkK7tUoWzu8ClcRX9vTVv24FzbgLLRI/oLBNzRI1oDWGazZdf+s847HkvL7d82ijR90oCUTk8vdZBfWH37Q1///ctTDhGrmOjA/MKeFzEEAAAAAOhlkAALulbvD2AxtcygNf6qYWrF1CazT9eMP7LhsdrEmKThIdLwEEJIRnYe09COsBHnooR/UcSuEjJ1zI4sGkcIIWTx4nprrEokMickaXJzBAlJmoRkjX2dspJOLcbB5bLvWjr9+ScXs1iOY/fWbzzaJRPlBHzHHpaVU6QB83JKkkXp7tumjbIbMfTSm+uqZfLVv7UG2ui81oePZT92/xz7kgB/7xlTBu12it34+ohnTR3svDudrnZDFVUNx9PyJoxpyTXG5bIXXzMqKsLfVuHkmYK6+ibnHY+eyL1ryRT7kttvnrhpx8mcXOrEYe75+ohNJrOiiSIIqNHot/135qlHr7EvFIv4HTgKAAAAAPQaWIIQoFfq/QEsK3G6SJwuMgQbdCF6o8R0/30j/ESteaDH+iVaH4woN518aVm5wPTjCK/jCe1+cYZOaEkWrvbiFBzNorkXu1rAz/EiHHPzkEZjoN4oNRqC9IQQhprjfcxHmOW40h8lodA8bKRj8uxFi+X2T0tLuM3NLPrxMR6Xw2Aw+DyOVCLqFxM8ZmTc4vljKKfjFRbLPvv6X7rtulVSWpsYH2ZfMmhA1NETOfYlY0bGvfS04xAwSouuGWV7rFJrq2XyDnTpVHpBVnbpoORI+8L3Xl9aUlabm986u1As4v/41SNcbpvbRqcz/P7XkQ4ctPMGJkXo9UZCPETpyirq3QwQ27gl1RbAIoQ8t3yB/dYde9Mp9zp0PLuopMZ+HUkul/35u3fe/uDXtfVK5/ocDmv08P7HUqlXlnz/9Vvj+4U89cqv6ZnFzlslEqFDSUMDRUwNAAAAAAAAerS+EsCy4lRzONUcQhizb5g9e0SbXEuGqsqGP/+s3PxPcJMmmJCRpfUPX+fXgRiWVZJfUAGhG8AyBmuaFpRbmMTCZFhYxMxgWEMOZm+jckIjzQDWsJGOMQjn4VfHj9BqyibzxGd0qjU36x5e/p1K1TWTNB0WASSEvPXyksef+fH8hTJCiI9UfO8d0x++d7bzEDBKEXYTEsUi/pQJyYc6NB5q5Q//ff/5g/YlUolo7Q9PvP/Z5qMpF3Q6w+ABkU8/vsAhyEUI2fDP8do6ipDNFfDnmqfoVFv+wprtu8+42rp7f6aySWNbFNJL3DrwzWy27N6XSbmX2Wz5dvWeD99os9pjv+igPZte+vKH/zZvP2UdrMdgMEICJdMnD3zonpnBgZJFt33sPETr5sVjp00aQAjZ8NPyTdtP/vjrAfvpgcMHx9x6/XiHQ2dml9E5cQAAAAAAAOhB+lAAaxCriRBSauIrCHf3/ozZM4YRQpTppzWHjzQcOWguLnGof//ppuMJPu7bDHKRA6u0uNzVLgwLocgT3mn+fm1WPxw1Wj16nOOEvvQzIqHQ9PiTsoQkzddfBJ053QUJvGpqFY8+/cPFrks5lHne8UJERQb8++eLdfVKnc4YHCxlMdux8oBcoRYKebanP618NPV0/oW8CqWy2Wgyk0uDkzRafXOzrqyiPv9iVU2dwrmdvQczN28/ufjaUfaFvj7iD9+83c3RC4tlH6/smoFpV4tOb/h35+nbbp7ovOlUegHlcCqrTdtPzp0xxGHxR7GI/9JTi196arFcoZbVKiNCfe2vzrPLFtz7+Hf29cNCfV9acZ31MYPBuH7+6Ovnjy4srikolul0hsgI/8FOEcMjKRd64pqPAAAAAAAA4F7vD2DNZdcuZNdEMduMDyrZeU5713hOSGjl00+ZmqgnHO2J8pzEis+kyLMu1zZnZOd1yfqO3sc8RNBsEhJ19k+nzXSMLJSWcJvVjGdfqoyM0hNCxk9QdT6AlXoqf/lzP9XUUkR8Omz3/rNnzxUPGRjtUO7v5zh8zGAwcjgebuAjJy7cYjdCh8lkjBsVP25UvJtdcnIr1m44tHFLitHUZt3DV976I75fSHJiuMdTsFI2aR5d8aNafVlWD7iSNm5NpQxg7diT4WYvi8Wy4tW1G9c81S/GcbVKQohUIpJKHJcHnTQucdyouBMnW3O9v7ziOpFdhMsqNjowNjqQUNHrjR98vtVNrwAAAAAAAKCH6pIwS/f1ILdsGbfUIXpFCIliaguWLrkwbbIteiVdsDBi1Y+JBw7H/7udGR312mzJHxMcl8Nz5jwCS2PQZ2w5zNJ1auE/hpElOisO+DXS/fxBodD8+HLZhMm0xptknBZdf1OjNXpFCBF2bmnCE2l5dzz45ZJ7Pu3a6BUhxGKxvPXBRovF3TA1k8n81od/fffzbo+tffb1tuLSmnZ1ICkh7J3Xlv76/TL76XKEEI1Wv+S+z2lmZC8rr7vxzo/zC6radejuKSu7NPdipUOh2WxxzmHvoEmlufnez4+l5tE8kNFocli78PV3/zpw5Dz93Z986VesPwgAAAAA0B1gCULocr15BNaD3LJFbM/BC2Z0VMy7H/DjEwghB2oz/q1J/X6pUWumtZBZsLBNgKmhoj7z6MlymZwwaWdKtwvUMJoJu8JffNaLU00xsMvZhElNw0aq45M0xw57Hks1Y45CZBe0qqxox8IcTSpNo1ytUKhzL1amnsxPOZlXXllPf/f2OnO28M6Hvvro7TuDA6WUW994/6+s7JIZUwZ5bKqmTrH0/i/2bHpV1M6V6caMjHv9hZufeeUX+0K1Wnv/su9uvXHisofm+ft5Ue6o1xvX/nl45Q//ucmM3uNs3Jz68jPX2ZecziisoZHbS6FsvnfZd7dcN+6x+2YHBVKk/7fS64279p/96oddRSVt3rC19coHn1w1aVziA3fNGDcqzs2BsrLLXn57Q05eR1Y5BAAAAAAAgO6PEZlwT5e3SbOsUw06b2tbS0IM64SOGaarAwTlAtOYRl7096v0alXZA/f733FX0PInD9RmfFbw2/bylrEeZguDyfCcqCpQIL4/Yaz1scagP7t7d3GO0sRiWFgMC5NhYRLrA/OlBy1p2pnWCsTMbFPNwiTMJrbgrA+rgU8IYRg5HsNYz71YZU3T/vXnQTNnKx1StqdrGCFcZjDLRLlvJ3JgMVw+8VBKq0EbqUT0yH1zpk4aEBbiSwipqGpIP1u0defJ49a16lweos0Gfz+vj966c8qEZFuJyWQmhNDJAW82W8bPfqm2jmKGqVDAnTF18Mwpg5ITwwP8vTkcdm2dsri05sCR8//tzZDVyN02zKB82DEMOk10+nLcccuk15+/0b7kjQ82/rbBbnVFT+9RHpczZULSlAlJQwZG+ft5Sb2FKrW2rr7pXE7ZyTMFuw9kyRWOa2g6iIkOnDohecLYhMhw/0B/bzabpVQ2V1Q1nsks2nMg61RGIf0zdO4ejbPwuDO9Vtp9iK7pk6vNHbwBu6IND03Ta7VTd39XnHwn69J6/7bvKF17OS416KLVrrw7r8bl6PIvK057X4bL0ZV/QFy00fF2ae/p7rbqmq50ybcTD0dg0G/N5XudQfmsXR/j9L4ju2mZZuc8fPFq1wcRw7Ga25Og9TozaNd0df+5K6B3RZxOy9MRnMo8vDNoXBGq15TmW81T91sr07xBaf6Jo7jtPd+Rnm5763Y2h+u6clf8YfN023f8E5ZB2lwVun1ws53ux27HPojcVGOyWJ3/20j33diRz/gu+8bZUo/uO/jy9dVdVer+0bx5KbZ0+fccWnptAGsuu3YZt9S+5FQk996lPoSQKczQ/devJoRo83L58QlPn/3+i/xNNINW9m6IHpwgbcnFk7/37OmM84SQjgWwCCFmNsO2CqG1hKHm+G0OdRPG+um3lh/t6adE8Uka2wCrzQrmTw2cZpNJyGKtijQ6x7Cqa9gvPxPVrpO1Q+O2bd/l7tDNQeP7gbeX4M81T8f3D7U+ra1TLr7tw6rqRvvaTAbDS8yPCPe/9caJt97omOnpoSe/33uQ7mqStHXl748rE8D65dtHJ4xJsD3V642TrvlffUOT2506vY266mX4QUj1sP0702ul3Yfomj652tzBV/My/umi+bWJfi36vwRoas9unr9WdsWrd3m/Sbj7ytuVd+fVuBxd/mWF/g/+jh+gK/+AuGij4+3S3pPuL6lOnGJXfDvxcAQEsOw3tOuDyOkPutuToP2bGwEs6teU5luN9tcsBLCoK9OMAdD/fuP0xvLcBzfb6X7sduyDyE01BLBctHH5+uquau8IYPXyHFj2bEnZD5iqDtRmEEL48QnvXVj/Rf4mQkh7o1eJ0iBb9IoQkp17scs6eonZ29g4WU6n5rCRamv0SmVhv1xh/qqW2WwyEUKaTaYqPUWuqx1bfLu0p93UM8sW2qJXhJAX/ve7Q/SKEGKxWJRNmvM5Za+89ceJtFyHrRJv4WXvZbcXGx04fnSbtPdbdp5qE70CAAAAAAAAuMx6bQDrhFFaYpfHaosx8O+QMOtjJsPyeuYvhJD3Lqx/5dya9rbszeFfGz7g+ujWBEylJ4u0qvYsNuc2Q3mHqSzsh6pEKZo2ya1CuI6XODdHcOwIdf6m3oTDYd+0eJztqdFoco5POSircEzsVS2Td3nHehY2m/Xea7c6/D/zmt8PXa3+AAAAAAC41zL8CgB6nV6bxF1BOC9q48ex5YSQE0apgnAIqbNtPdJwYfaxJ/ZVUa+PxmeyA4SOIZ4ggVjCFkR5SR0StxNC0tPOdGXX7XhntiNN1XuV+uo2WbCIlMsLZrVJLaRWM1evCvT3N/oFGHJz2qyy18tEhPnxeK2zL9lsllQiqnadnYrFYk4Ym2hfotcbz18ou3w97LZ8pKJGuZrBYCTGh7727A0jhsbabz2Wmuu8KCEAAAAAAADAZdVrA1iEEAXh/GcMsD3lVrP1l36JMxmWPZX5lEsF8pnspf2HO0epXCk9WaRXaAiLwTBZLE6TfDtDujOAf4FujOnHemaKxvFqzhNpHEo2rPOfMEm58LpGQsj6tf57drtcGK6n0+oMDiUvPLX4mVd/MxopstpzOOwvP7zXmi3eZseeM3KF+mpN7r1aGAzGfxtf5HDYHDZLIHD8zyuT2fzRl/9elY4BAAAAAABAX9abA1gOOLI22dApk161N3rVUFF//NAJFu0+mHhMVSDPPs7FMLV0g2U0mxkMpsUSrDGE6y1BeaLTWR66oVYzramv0jWMPxopZoOOELY5x+oa9rBh6mEjPSz31jtUyxpr65QB/q2v4cJrRsX3D924NeVEWm5NrVLZpPHzFYeF+E4en3TLDRMC/dvE8uobmj74bPOV7nQ3kBgX6ufrcobpd6v3nMvpi6PSAAAAAACAPiaL/q9kALr6UABLnC5STG0y+xhdVehA9GrP2v9YOjNh01vU4VI6db3A5cKCEr1pQaWWEKIPUHlssLyEl5CsIYRsbDAR4vgBIWSxhgnanGxwoDE4sKVErWYeO9qO+Yk9jtlsWfXL3pdWXG9fmBgf9sozN3jcVy5XP/Tk9zV1isvWu+5rwtgEV5u27Trz+bc7r2RnAAAAAAAAAKz6UACLEOK32af2nlrKTYEC8W2xwwUcrsVsbqxqrM8pd9OOobQss0HJlxuYTinSCSHhQdJJ4dXRAf7Wp01a3S8XTLVaFiGEpTN7V2gtTK1BwDLxmEYu08xl2sezFNyWOBSXQ7F6oIPcC7yEZM1mBcXkQULIYK7GTZL+r78Mbm6+vEFxidSLEGI0mtSq5pjYiGHDkwkhZ06fLy5y99p2oXUbj42ZMCopIZzNIoHedGcCpp8tevrlNaVldV7eovmLphPCaKiX79p55LJ2tfuYOIYigGUwmL5dvfurH3ZZLs/6AwAAAAAAAADu9a0AFr+I57PJRz5HYRG2CQ+NDIiYFBhjjV5d3J/Fzr1ge13OVmmZOsdYkpnH5BMKAgHvrklkeAyDkBBCyKXf+py4aPZHB5ouKlqzL7H1ZqbRwtaYLUzCZxm0Uo4tjCXnMqV6MyHEL0BVX+tukNTpM94Lr5efVBkJoVhoY5SYTQh1FGz1qsArkMH96x/e5HA42efy33j1i35xUbfctoAQIpcrbQEsBoMxbPgAmq1lZeYZDI5prdzj83neAaEVDWaGxRjozXNf2WKxnEov+GXdwZ170q0lQpFg0XWzCCGFBaV9J4D16TfbCYORFB8q8RYqlM2l5fXHUnM3/HO8qs8vyAgAAAAAAABXUd8KYBFCxOkifhFfMbVJG6Mz+xhG8w0zgiPCREJCZMRAErTZM8YQMkZqv0uF0pyZ1XwqhVuvrnPRaovHZ/HiQlqHU9nG/IgZxodG8p7d1+xqR57SaAtgqTkMqZ7WuZSXsKtrWJTDrwghUVzqwTKrVwUeO+KY5OjX9Z/y+R5CPFYvP/dxfl6x9XFkVGhAgK9znXNZuXq952ATg8F4/pWH6RyUEPLI/a821MsdCgUC3tI7Fo0cPcjLS1RVWbtr5+G9u48771teWf/iMz8umDeyf0xwgL93gL+3j1Ss1xvrm0xNBp6ZwTHoDefP5f30w8b6ukaPPbnvwZtnzZlAs9sXcgr/98oXNCt3B5nnS+9+9Jur3QsAAAAAAACANvpcAIsQwpaz/Tb7EEJuv7t+xqwmQios2grierW5MG9m2ATxvAnkTJF3SRY5kEOdnWpQgsg+emWPQUiYN8VsPobZYmEyCCFmelm0nH1yLJgMklFuCuEyCWmz4p5azfz6i+Bc2isbejRn3uRZcyc6lz/+4Gu1tQ1ddRQri9lxNJmPj/cLrzwSHRNufRoZFfrAw0uiosN+/vFvs1PlgiLZ599sty+Zv3D67XctYrAYTEJ4fN7wkYNiYiM/eOf7KzbDEQAAAAAAoGe5fkbcnAkxWw5c3HGksJNNMRhkQD+/fuFSXwnfaDTXK7SZ+XXlsiY6+y6cErtwauzWg4VbD3nuxrN3jfCT8D/65XS9Qkun8Wkjw6+ZGL3/ZPnOY8UeKz94/cDwIPGPm7NLq2n1vF1evHdEbJjk7R9Plla5a/yp24cmxfh+tjY9p8jDgIw3HxkT4CN47dvU2kZNl/b0CumLASybtWv8igp59z9URzN6NDxGPDyGXLdQnF9lIIRcLNQRQoJCiRefRwgJDhYQ4jJDvHsGYQfTUeWbXOZ6D2a1iV6VlnC//iKkrpbtMlBHiMFg/On7De6PKKv2MAyNPrPZfMt1j7uOHBJCyKcrXwkLC7L2zWHTo8vusEavmprUFWXVcQnRLBZr9txJpSVVe3YddX/oAQPj7rh7MSHEYrHk5xX7+kn9/X18fCXPvPjA8kfeNJlMbvY9sC8l+3y+fcmEiSNGjh5ECCksKPt3yz77TU3KPrHmIwAAAAAA9DIxYZLrZsSHBoiy8uv+2JmjN5gIIb4SQf8IqU/bDC2/vnNNWCB19psjZyre+iHVuTwi2OuNh8eFBznudSpb9vaqtGZty4SeOxckS8U8hwrHz1Z5i7kRwV7e4ja5dAJ8BPMmRIcFimsaNQdOlhWWt6zKlRzrFxog4nIpfnTHhHnPHBMZ7CesrFPvOlZSXqMihAT4CgbH++cUtY7JuG/RAD7Pcff03NrjZ6uSY32TYnw37Mp32Mrnsu5ekET1kjAIIfVyzcZ9BdbnYwcFhwWKUrJkFTWOv+6DfIQRQWIuh0UIuWV2XLC/0H5rXol857ES64lHBIl5l07wfw+NGTMwyL5m6jnZG9+nEUJCA0ShASI2y2Wy7G6uTwewCCHHDos1zYx7H6wXiTwnTbexjrRyGm/lLnpVoTTrvNjW8VZGAZNptJjZDCOXaWExLAKOnkURxNE0U2S2cmAJdDnbUGVhixlGQohazdy3S7JlE8VcPwcmk2n/XoopeG21dnXVd+t//G697ekzLz44asxgj0dpF8GliY0GY5uXNzomfPDQREJIaUnlay99qtHoEhJjX31jGYfDXrBo+r49x50HYdlbfMMsQojFYvnikzUpx9MZDMYzL9w/YtQgf3+fiZNHHDqQ5mbfwoLSwoJS+5JJk0dZH3h5iU4cS2//WQIAAAAAAHQj/SOknzwzXSzkEEKGJQYNSQh85pMDZrO7NZ12HS/WaFt+tTGYLT8bC8qo13Z/85FxYYHiLQcLthwsrGloZjEZkSFe9y4aMDI56LFbBn/0y2lrtWmjwkMD2gS5VBrD8bNVzg0O6u//9uPj+ZeCODfM6P/pb2f2ppY617SZMTpixZ3DWZe6et20fm+vSkvJqnauOWd8lETs+PNcbzBT9sSKy2FdN62fq60F5QpbAGvG6PBJw0Jl9c3OASx7YwcFJ8b42JcIeGxrAMvBqWxZnbxlgFWgj2DUgCDnOj1UXw9gEULOnBIRQpY9Rb06YVdJs7Aboz0HpOw1qz3U53DMPpJmFaGet5ivNYU0sdKOeu/ZJbncCw52CR9fyeAhiYQQmazuQnYBIYTBYIi9RIQQrVan07YJ1c2a0zJ1ccO6bRqNjhCSe6Ew9UTGxMkjg4L9Bw9JyEjPcXWgwCA/64Hyc4tTjqcTQiwWy29rNo8YNYgQMmP2BPcBLAc8HjcuIdr6OCDQNzgkoLrq8t5LAAAAAAAAl9WdCweKhZyfNmXuOlb82sPjh8QHTBgaduSMu3Qrqzdl2eImTBabuJ5r4y3ihgWKjSbzd39lmi4FxXKLG3/bnjMsMXBAPz9bzXte233pIeO66f0evsnlgImn7xjO57K+3nB2T0rpkHj/Vx8c8/gtQ05kVqk11NmZ+VzWsluHmM2Wz9amn8qumTA05PFbBj99x7Bbnv/PufLNz+8ghAzs7/fJU5NqGjR3vLrLzetgr06uue2V3favQ3iQ14+vTqe5u7MnPz6SW+xhnuC2I8W2xyOSAhHA6m3OnBL9+L3l/occJ8cVF3M0zaykZFoTZd1osrB/U/AI0dGpHKY2EULUnqJXhBBvabObnr2x3dtvi5/7CXrdSmRU6KNP3E4IOXLopDWA5esr4XI5hGreYmhYECHEZDKdzWgNVJ0+mTVx8kjrVjcBrJCQwJb6p8/ZCquraisrZKFhQdaW6bv1tvleXiLb04cfu/WNV7+yWNz91wQAAAAAAEC3JRZyxg8JrVdo/tiZY7GQX/89/+FTU2aPj3YfwLpjfnJz6wislklqVbWqbYeLHGoq1XpZQ3OQr/ChGwdvOVhQ09DMYjEjg71uvzaJEJJXIm9vh/0k/NAAUVl1kzUlVkpW9cnzsnGDQ/pHSM/mUQ8viA2XCHjsE5lVe1JKCSHbDhdNHxU+oJ9fxKVZjWMHh/j7CHYcKz53sd5aEhchJYQE+Aj8JPx6hXbzp/MFvO4YUXn5vpETh4Ze7V5cFt3x5b58tDE6lobJqW6JDRmlRtVQNb+Ezy/iUc4lXP+7X242f9Zc5aLr5c5zDHOy+Ss/D7z3wboRI10uL2iVZg7Sm2iljpLoW7IvKRR8z5Wl2hrXWzXRtOJlnREeERwU5G97KpU6Lm5ICPGWeI2fOLxf/6gOtB8S2hJpch7TFBDoSwiRy5vsc2PVXVpD0LrVRiQSTJ85jhCiVKpOpWXZtjbUye2r1dfLQ8OCxGKhQMjXuIsNtho7fuicayZbW66R1fePi0pM6nfbnYvW/bbV/RxGAAAAAACA7inYT8RgMC4UNVj/Xz6nsI4QEuJPneXKZv4UihlzZ/NqnQNYhJA3v0955YExi6f1W9x2nt25i3Ur12fYnt48O95X0vLTuF+E1NWhmUwGIcR+FIF1tiOT6XI8h3W2o8QuwZb1sS39VlSIV1SIV3purTWAxeWwFk2NJYQwGOTO+Umf/Z6+J6WUw2GNHxwsaZul67JaNDWmQdESnNqbWrZoagwhJDKY4pf4vrSy8pqWjMyVtb0kNXNfCWCZ+ebKJ6tNAgshhF/E89vsw5azqx+WmQQWBWniVrODfg48c0pUWsJbcnuDUGgmhOzd5ZWbzSeE7PnPO/20cMntDfaBKrWauXqVf3Mzc+XnQcNHqm9cWh8SSJH520JILj+ZsMIG+uWn1Xhe3s7b0BL1aKzx8OlACOFw3GXdMkqNqqEqcQbFrdxVZsyecO2Cae7rhEcEL19xb8faLyoqf/fNbwICfetqHQdJ+vpKCSFqVZv3YVNTy1NfP6l9uVTq/dCjtxJCCgtKT6VlSX28reXq5jYrL6iaWq6vj4+3xwAWl8u54+7rZs2ZYH26etVfRYXlH376PI/Hnb9wWkJizNdfrsVcQgAAAAAA6HH8fYSEEKWqJYtLs9ZoNJkDfFoziN+7eNC9iwet3pz1+/YcQsidL++wlvt48zd+srC2UbP0xZ3E7Wyg/FL5va/vHpIQMCQ+4Na5Capmw89bz+cWN+aVtPnpN2NMZHSot6tG7pifdMf8pDVbs//4L1dW3xwZ4jV/cszelNLB8QFjBgbr9Kb8Upez7cpqVPImXXKs74LJMQdOli+YEhMeJK6qVdfJW34JbtiVt3pLtvUceBzWy/ePCvEXbT5YMLCf39zxUWqN4cdN53UGU3TI5CsZwJo2Mtz2+HxB/dzxLkeKHDpTmZlfx+OwhAJ2qL9o/qTo7UcpEmb1LH0lgKUPMVijV4QQbYyu+mFZ6OchthJ9sFF2T03Qz4F1teyVnwU6724t9w80TpjUFBFpkDey/tshqattefVq2YH/1fQbF6kghDQ35oRwmWImgxBSIYivYIVZ6/CZ1JmqHCQoWmJS1ZUu36X2wpqNZSKXLcunKNsVwGIxmcNHDnRfp6Soor5eTr9N6gOxWNZl+wghto+16NiWt2JAgO+YcUNtlZuUah6Pay25kF2gUDQRQpRKlY+Pt0AosG9WeOmpUuFukVF5o9KhvpXYq+UTufFSBWdsNmvAwLiRowePGjNIKm25Rv9s3JVyPIMQ8umHPz317L18Pi8uPvqTL166kFNw+tS5U6lZNTX1bvoDAAAAAADQfSjVOkKIgN/yg5fDZrJZTKW6dTxHQZm8qEJRXKGcPT76+XtGO+we4CPY89319iUPvLm3pNLxR5bJbDmTU1MhU906N0Gp1v17qNBVf+5+bVdVLcW0p6IKRWGFsrhSSQj5bO2ZNx8dt2zJ0GVLhhJCLBbLyg1nVc3UCbAIIUaj+cs/Ml66b9TjS4Y8vmQIIURnMH2+LsO5Zlyk9H8PjfWX8itr1as3Zwf7C798buoNM/rHRUqf/fyoq/at/KWCXSsXua/TLg45sOY9vpUQ8u6yccMSAhxqvvnwGIeS1HOyLuzJVdFXAljsxjZZzE0CS+2SenG6SDWsZcyOPtioHNskPShx00hdLXvLP61p/7kiVvgY0eAlvuIADiGkgogJIWuVNVEin0lB0Qwm02I3iaxE7SHRGiGEa7LENukJIWo112MGd0JIczNX7PL9SIh1ENZYpTiFViyMEMLhcl545RH3db7+8rdD+x2XQX33ja/P2uecsou0Z5/Lf+PVL2bOmfjAw0tshTwe9+nn7nd1iMTkfonJ1Os1vPX6SkVmLiGkRlbn4+MtlXoxmUzbZD1fv5bLJ6tuEzCqqJA9vewd29Pampb1UP3aDtSyPlWpmt0MvwoNC3rx1daXSKfTr/1ly55dLR9bZzMu/O+VLx9ffkd4RDCLxRwwMG7AwDiD3mirAAAAAAAA0M1V16kJIXGRUuvT/hE+hJCq2tY18g6dLrOOvUqK8du8/6JzC4y2c/ea1K1Lcl07KWb50mEO9UMDxLu/bRPzuvd/e8pl7sYlEEKOpleu3X6BEEIYJD239uF39s+fHBMeKK5p0OxNLc0panC/+7GMqsffOzhnfFSwv7CyRr39aDHlOoDlMhWDQY5lVH79Z6bOYCqpanrgrX2P3jR4x1GKqZE2eoNp+9Fi62MBjzV9VESz1njgVMusrLpGdzN+xAJOWKC4tNrD6buSkVtnjdyZzBaDwazSGOrkmnqFzv4q9FC9M4Bl5ptrlzRoY3SEEH4RT5TLF6YL/TZL6xfLbXW0Mbqg9V6axGbbOCzVWJX7AJYNV8RKWCBNuMaH7+U4KHJWaNy6i2dG+Yfz7V7bzAZZSZOceDK8QcszWQghFcVSOt1oVnOjmw2ECNzUaZwsF2aImNoesAphu1RV1iQkxnI4nIGD4zMzLlgLh49oGT5WVeUmOVjr1uEjB2z5Z4/1cVCwvzV9e2WFu7B0aUll+pnsYcOTdTr98aNn/ly/o7GhzbqwxUXlzz71/uSpo+deMzk6JqypSX3ogGO8DwAAAAAAoNtqUGgzLtQMTQxcNC3u0KnSuxcNJITsSy11rplTVJ9T1DJ6ICHaNyZMIvXiGYxmhdqQlV9X16hx3qWkSrnlYIHHPqg1rdEWFpMp4LP5XLafhB8WJFa5CMRU16n/O1ZiMpnLqeJQlKrq1Bv35mt1JpWLxQoJIRqd8bH3DzYqW0NONQ3N//s+xX3LWr3py/VnrY/9pfzpoyLkTbqv1p91NbFyyZz4RVNjxQKOjzdP6sUjhDz7+THnaiwmg8dl8TgsiRcv0EdQWt1U6/Qi2wJnfC5reFJgoK8g0Ecg4HE4bOZHv5wxmS22xSJ7nN4ZwGoe1myNXhFCtDE6bYxOPkUZtCbAIYalTtCIMkTKcS03t0lg0cbo+EUe5q+qxqrufnSoc+jKKogvjvb2O1lXPikomhCiNRmP1BTRyX7FNVkGN7S8D8tKfN1XtlLKhVK9WaI3Kbgu41MmgUUxReGzy0ODdy55ms4RCSFdsqxhc7Pmluse70yDe3cfmzp9LCFkydL5uTmFOp0+tl/EhEkjCCH1dY0ZZ1wuQUgIqZHVZ2ZcGDw0MT4hZvTYIWkpZxkMxm13tgzs3LuL4mPC3rrftu7+7+i5zDyDgfozzmKxHDqQeuhAqlTq7esn1evdDpMDAAAAAADoZn7alPnR01OfWDr8iaXDCSG5xQ37Ul1mUAoP8nrr8YkOqcQtFnL4dPlHv5zWG9pkiz53sf7cxfpFU/uJBJxNBy5qtO4yO7d05n+z7J8eS68srFA4V/Px5v/w6gxZffOdr+6yL69paCaEmEwUK8XPHhf12C2Dtx4s/PrPTLuuE5PZYrarbo1e/fPxtXwe+/oV27T61jOyBr/MnV6GPjLYS2cw6vQmWUPzmQu1lbVqyjDTJ09PtH/61frMHZfCVQ5mj4189KZBvLaxAo3O+Pm6sxfLKF69HqF3BrCMPMcF4EwCS82t9WGfBeui9KphLbNnNYnN/hv8bQEsQogx2EBcB7DCpghG3Rb0ReVRHU/HJy5XCZwe3G91XlqkWHqmvqJYWd9sokju7mxMbcvwq8pKbzrzBwkhBgNTIecPbtAfCXY3CEsxtkmQK+QXe17WsMNGjh7UPy7aWyL29hZ7S8QisfCFFR/Q2TEyKpTBYBJCSoor2nXE/Lzic1l5AwfF9+sf9cU3r1eUVcUnxnK5HELI1s37TJ5e803/7Bk8NJHBYCxfcU9+bpGPryQo2J8QUlfXeOzIKff7lpVWlZVW0emkXK6Uy12m0wIAAAAAAOiesgvrn/xw//Uz40P8Recu1q3dnm00uVxm/Zm7RkYGe/25K3fLgYt1Cg2LyYgK9XnsliFTRobnlcr/2p3nvMuNM+OC/IS7T5S4D2CdOi8rqlAYTWa9waw3mBsUGlmDpqRSOXFYKP1zef6L9mV0+XNP/p978p3LmUwGy2lZwxe+sg6AYNgPzBjYz2/mmAjbUwGXRQiRevGeXDrUft/fd+bVNmre+cnDL1CrlKzq4iqlyWQxmswGo7lRqauTa3NLqFMVWY+l0Rnf/vFkZn59s9YgFnKHJwQ8edvQZ+8cdup8jUbnOW7YDfXOABa/hKcgjvNFjVKTfKrS5z+JJlFjnTZoEliaxrStpnUxrmqQcOR9/j7RPEJIsiZwf3XBdZEDXB29RKXgsthrL6bT73CE2jC0oWXIWHGeP/0dy4t9owOrj7idRUgIaZjTEPp9O97h7TV73mSHEof86K689f4KPp9nMpmX3ri8vQf95svfXnjlkcioUB8fb59LCwvu3X2cTsKp7HP5v63ZfPtdi1gspi3fVmOD4uP3fjC5/lwGAAAAAADoI/JLGz9YTSsdSrCfiBCy81hRdb2aEGIk5GKZPCWzamB/v2A/oae93Vn1T9alh21+qrcrgHXlhQeK5zmtDyjksx0WDdx6qMh5AqArG3ZTxNRc8ZPwGQwiq28+kVVtNlsIIUqV/mhG1V0LE4N8hT7ePE0tAljdBr+IF7TGv2mMqjmpTWo0xbQm0QUBp5prujTB0KGC8/xBUSB7xH0BkWPEtpLpwf1W5pyYHtxPwm0zpklrMuYp6o/ICuR6Xbt6K9Gb5pW3DAqrrxXV14rd17dXXek9QF85sFF3zsfdzEd9sIEymzuPxx07YXi7emt14XyBTFZnfWyxWIxGk8lkMugNjQ2KhgZFfX0j0yky3eXq6+WvvfzZ0tsXjho9WOwlklXX7tp5ZPd/dIPr27bur66uve6G2ZFRoTqt/lxW7tpfttTXucu1z+Nxx9otj0hfTk5BjQwLEQIAAAAAQC/03/HiO+Ynf/bstJTMygaFlsVkRIRIxgwK1htMB06Wudlx3XvznAvP5tU++9mRDncmyE+465vrnMt/257TkvHdycKpsQunxjqXz3t8i/PcwC2fLXCuuXHvxVWbz9ue/nei5L8TrTMu2/42vuy/lAkhhRXK/FJ5XKT0u5emZRc2aLRGoYA9qL9fkK8w62J9Za36CvThcuidASxCCL+Ixy/iGaXG2lvr9cGtwUXZ3bW2rO3Ou7DlbV6QxIU+A2/yc0h3JeHyk33aDMLSmown68pP1ZbSnC1oj2uyLCxVWycP6g3MjJPh7dq9Wc0tK/YZxlW4D2ARF9ncRWLhY0/c0d4+E0K++uwXmazul5/+/vWnvyk2X4m3JCGEaJq1P/3w508//NmxY59KyzqdluW53iUikeCRZbfRr2+z8ovfEMACAAAAAIBeac2Wc6VVytnjokckBUm9+QaDSa7S7Ukp+fdgYX6pnHKXg6fLvUXUmXM8Lj7oilZv3Hms2NXWi1Q9KalS7jzmMreXQ/BqT0oph0OdftrVVL5O0hlMGp3RbG53gi2LxfL8l8cXTomZMCRk7KBgkYCtajbI6pt3Hi3Zerj4MvT0Cum1ASwrtpwd9HNA1SM1RmlLaMlV9IoQIjnUOkCJK2JNfSkkcAD1PLjhfmFrL6ZPD+7HY7E7HLoihHBNlluKmqT6ljlrZ9MiaGa/speXHTQjutHjICyTwNI4R+63xa8D/QQAAAAAAAD4aVPW6s1ZFqdxSfvTSventS5TyGSxidvBBT9tOteZbqzbmbthV56pbWRH1Wz4/Pd2ZPIhhJzNqzubV+euht05tEn07lzvMgzjeP7L4069oPDyyhQGgzhcFI3OuGF3vm3i4WXp3xXXywNYhBCmlum32Ud2t9ub8tKILetjQ7Bh8VvR4gCOq8pRImmUl3RtwRm9ydix0BUhRKI3LSxV26JXGWnh1RXeHbiprIOwxrPked5cPcvd/k1DVd6p3hxZ63k11MtvXvxYOw/Y9fc9i8XcsOkr93U2/7Pnj9+2dvmh26WhQbHkhnbn6gIAAAAAAOgdLBbn4BUFs8nEZFEPVuoSZrOlA+OSeiuaF6UXYF7tDlwJ3CqXoSgb3/+k1gcRY8Wyu2tOGIvdVM5T1il0Grle1+HoVYTacEuRyhq90huYJ49FlRX7dKwpQkhedhDPZJlfrvJYs352Q4eP0l65F4ou5BSUllResSMCAAAAAAAAQK/U+0dgmflm2T217utIDnhxqjmEkNjp3uOfCBqq91mdlxbvHRAlkjrUlGlVeyrzS5rknenSwEbdtKqWtQYUcv7ZtAiFnO9+F/ea1dy884HxA2oi1IYykbtonTZGq43W8os7dTia3nrtS9tjeaPyQk4BIUQubzOf+fuvf2cyaQXmy8uq29sBo9F0IaeQEFJX15GwncFgLCwoJYRUlMs6sDsAAAAAAAAAdBVGZMI9Xd4mzbJONei8jaqWNXpln8TdGbeaHfJtMLkUvbIWptWWH5MVPpI0ns9qifFpTcYjNUVpNeXt7HzbY5ks88tVYeqWcVu55wPzzge1qcFwcSaecDjm6ddmW/iWNf293U8kFF4QBP4Z2IFDXMJw+cRDKa0GO71T1x2b0ZEG23fMTrdNaybz1bwcndhGXbV7XY52f9i1+xBd0ydXmzv4anZFGx6aptdqp+7+rjj5TtbtmkwEl/FyXGrQRatdeXdejcvR5V9WnPa+DJejK/+AuGij4+3S3tPdbdU1XemSbycejsCg35rL9zr1olTt+hhv199Y6gtO8x3u9otXuz6InP6guz0JWq8zg3ZNV/efuwJ6V8TT9xTPbzcP7wwaV4TqNaX5VqP9NcvT69x6H9O+dA4H9nxHerrtrdvZHK7ryl3xh83Tbd/xT1gGaXNV6PbBzXa6H7sd+yByU43Jcvpd2qlvD137NZv2PnRbdnfbU3/gt0f7fzc5F9O8K2meRpd/z6Gll08hVExVuo9esTQM/01+pG30ihAyOiA82ttvY0nLEnUlavlPeWmdjF4NbNTdfVFpjV7V1YgO7Y7LdYhedYLBwCzO8+eZLJNlWvc1mxM1Rom71wQAAAAAAAAAoFvpzQEso9SoHKd2X0e6S8qp5oRNEdhHr6zmhSXUNjcdkRWn1ZavvZgu1+s63JMIteH6kqZpVRqeyaJWc9OORR0/GNvJaYPOCvMDCSFJch3X5CGBm2qo52xZAAAAAAAAAADdRG/OgWX08ZBhXZjDF6eLDMGGcff3d97KZ7FnhCb8W5bdmT4MbNQNq9dZk7Wr1dy884F0krULRXqBUG99XF8rpnksg4FZXyv2C1DFK/XnfHhuaqqGqKWHpDSbBQAAAAAAAAC4unpzAMsj6UEJIWTxC/34XtQTOAtUdR1rWaI3JSn0cQqDNXSlkPML8/zdhK6EIn1wqNInSCWR6EQivXMFtZqrbebW1wgVcqFSwW9Wc53rcDhmL2kzIcRjAMsoNRolRraiT199AAAAAAAAAOgp+nQIo/IR2UxLvE80daxnU+n57Maa9rYZoTYkKIxJ8pb5hhWVXsW5/m5GUUVEN0ZEN/oFepjqKBLpRSK9X0DL1D+9gdkkF1rjWQYDkxDC4ZjjB1RzOWZCiC1JvBvGEAMCWAAAAAAAAHA5mE0mFovWivMANPXmEIY2ykPWKimXNySeOo16ZoOsXdErrskSr9TbZgvqDcyyIp+ifH/KoVJWwWHKAUOrKMdbeT4cx+wXoLLFszpAG6TjXxB0eHcAAAAAAAAAgCumVwWwtElabZCeEGIINhh9jO7XHySETArqx2dRvAIyrYp+6iuuyTK8QTu4Qc8zWcilRFfVFRLrwChKHI558JjSsNAmmodoLzm3N+fmBwAAAAAAAIC+pvcEsORTlYpp7QsJHZEV8NmseG9/h/Jt9KJXlKErjznahSL9qAklEqnWeZOOxajjM5UctorTWsgxkQCdkRDirzXzPC0vaJUv4XiuRAghZNsrcpo1r7AF7/he7S4AAAAAAAAAXE3PPjDjkx/3WyytoQAfiXBoUtiBlHxCSHiwtLxaftU6d8X1ngCWamz75tONDgwnhPxVlBXlJV0QniTh8q3lR2TF1c0eMlIRQiLUhqlVGtuEwbxzQYX5joEwZxyOedzUIodpgzoWo9CLe9Kfq+B6niEcoTZI9Gax0RzabBQZLNYO2MuR8lICMDcQAAAAAAAAgDz34Cy9wWQhRN2s23fsQlF5/ZU8emiQ5IY5Q1f+eshW8uwDM77/45hSpSWESL0FDy2Z8MEPe13t7i3mO5SIBNz42KADKfl8HmfpopFf/3pYrelIYqKeqPcEsNprtF+EhMsf7BOypzJ/dV7ayIDISUHRWpPxVG2px30nVWuGNrQk2FLI+RlpEQq5411Fafy0AofoVYWItS1crGdRL4PorEzEKRO1KZHoTd4Gs0RvJoSUidh0omCEELa87156AAAAAADoxYwGPZvjMhkx9EGr/zquVGnDg32WLhr1+5a0il4xakmrM3z4vcvIV6/Ue6IY0l0S+RyFSUAxyY4tZ4nShaqxKtvWYKHIOuQqiC++PXZYZoNsX2VuZkNlqEjSbHK3hB/XZJlfrrIt81dW7HMuPdRNuit7A4ZWOswcPBAiOOdDvQYifQouS8FlOUS1POLJOntcAAAAAAAAAFfMJhOzOy1EWF7deCg1b/LouD+2niSEPH3f9ENpF2eMT/htU9qghND+UQFeYt7ZnIr/DmUTQkYPiRozNEYs4rFZzPLqxp83psRE+F0zZQCPx6mSKbbuy7SOe1px/4zDaRfHD4/lsFnrt5/uzIS+mHC/eVOS+Tx2ZY3i333nHMZV9Yv0v2baAEJIda3SVvjmU9f+7/MdZovl6fumHzl5ceywGA6b9eeOM9ZujBocNWZIlEjIY7OYFdXytZtPzp2SHBooYbOZOw5ml1Q0dLirV0vvCWCJ00XidJEh2KAL0RslrUEovozLz+ETQrxTxPWLG5uTtISQQdJQ+30H+wbFS/x2VuR6XHnQIXqVnhZGCK3BUxKptl98m5GKXRK96hi2nM2p5hBC5r8tbf/eDJdPPJTSahAAAAAAAADgciivko8ZGmN9LPEWBPiKP16112y2CPmcPUcvCPicZXdOOXOuTKc3zhif8NGqvYSQJ+6aum7rKbGIt3TBqB//PCara5oxPmHxrCG/bz1JCPHxFlosli9/OTR9fPzEEf3Wbz9NpxsP3TrBbLYQQpjMlp/DYhHv1gUjfvrzhKy+afq4+EWzBq3b2tqUUMC9Yd7Q3zalVdUohw2IGC11HMAi9RaYzZaVvx6eNi5uwojYDdvPSLwE08fGf7J6H7GQx++csn7bmahwv+AA71UbjosEXKPJMRlRj9B7AlhWnGqONTTjjKllBqz30yZp6xY1BAnFDlv5LHY/sb/7ANbYWo1T9IquAUMr7Z+eDOBdregVIUR8tp3jtQAAAAAAAAB6OrvhEywmc9+xXGsgqaSiITkuODxYajJbfKXCSpnCbLFYN7FYTA6bFRvhX12nlNU1EULSMktW3DeDxWSazGZCyJlzZRYLKSip7RfpOS+2lUMOLEJIbLifrE4pq28ihJzMKn363mksJsNkbplDFh3uW14lr6pREkJq66kXr0s/X26xWApL66zdsFgsLadgISwmg8NmVdUouBzWghkDT6QX1zW0L4d4N9HbAlge8XP4wVVBUWukzpsKVHVudpToTaNqW/JeqdXcc+kh9A8qkWr9A1sTw1eIWFcxzzpLw/BO9bpaRwcAAAAAAAC4KiJCfKxBKCuTyUwIEQq4ty8edeRkwf7jef4+YgaDoVRpSyoa7r1pPJPFOHzyoqpZxyDEcimc1LImYNupREaTmXJuEYvJtO3oDoPYal1qn0FISxGHzeJyaUVvjCaztWdKlba0suGeG8YymYyjpwpUzTpCyHfrjiX2C7rl2mFpZ0tOZnpO/93d9LkAFiEkWkJdXqx0txjBqLrWCajnM0Jo5r2yio1vExo76U8r4/tl4pXmzdR2o3nIAAAAAAAA0Ct1qzRY4SE+U0bH/bY5zaE8NFBiMJhyLlaLhDxfqYgQwuGwgvy9v/j5gC1KVVhWP3/6ID8fUX2jesTAyIsltSa3s/D6RfqLhbzM3Mr+UQG1NIY7FZXVz5820E8qqperRwyIsLVvtlhYLGZZlXzhzEFSb4FcqYkK86Vzshw2K8jP68tLqx8yCMNPKtIbjDkXq7lsVkK/QASwegaDt7dzoUyrcpO+nWuyJMlbh19VV7RvBFNQmML2uELEKhNRT3K8ArjVHOkh6dU6OgAAAAAAwBVgNOjZXCxECC3uvWk8IUTVrNuw/XSlTO6wtbCsbuyw6MfvnCKra6prVBFCDAaTwWB65oGZGp1Bpzemny87fa50/bZTt1wzgs1m1jWoNu0+6/6IVTXKG+YOnTc5Wd6k+WvnGY89bFLr1m8/c/M1w9hsVl2javOeTGt5zsXqiSNjD6bkbz9w/p4bx2p1huyL1XRO2WA0GYymFfdN12gNOr0xI7u8rlG9YNxADpvFYJCt+87RaaS7YUQm3NPlbdIs61SDzttoHyJ2umT8E0EOhXnKur+KslztEqE2LC5pmQNYkOd3PsN+/qCHAweHKUdPKLE93RwluloBLJaGEfJDKFvRyahl90ji7nKnrjs2oyMNtu+YnW6bQaeJq3k5OrGNumr3uhzt/rBr9yG6pk+uNnfw1eyKNjw0Ta/VTt39XXHynaxL6/3bvqNcnjeIi1a78u68Gpejy7+sOO19GS5HV/4BcdFGx9ulvae726prutIl3048HIFBvzWX73UG5bN2fYy3628s9QWn+Q53+8WrXR9ETn/Q3Z4ErdeZQbumq/vPXQG9K+Lpe4rnt5uHdwaNK0L1mtJ8q9H+muXpdW69j2lfOocDe74jPd329ttdBLC64g+bp9u+45+wDOJ8IjT64GY73Y/djn0Qua9mrdo6AqtT3x669mu2h32CA7wnj+7/5/YzhEHCg6X33zLhjS93tMzsc9Ua3XdwV/fVRdUgf+/Jo/r9tTOdEBIeLL33pnFvr9zleAo0b16KLV3+PYeWdsyD6zVEgRTxI5nG3aC+sGaj7bFS3r4JgCFhrYtc6liMqxi9Cv41hC3vi2PuAAAAAAAAAGgKDZKYbRmvCKltULmNXnVHbU7BQup64Ck4QziDFo7d5MJmdftGotrPHyz0ujqjWNlydtCGQFfrMwIAAAAAAABcDt0qDRZN5/OqosP87r5xLINB9AbTH1tPXu0etVt2flV0qM9d148hhBgMpvXbPE9j7P4QwKIlQGf0XImKRKrlclpTu+VKrsILzi/iB/7pj8TtAAAAAAAAAB7p9MZ/dmUQcrWmynUBnd646VIiLdJVySuutj4awDoiK7Y9rtOp1Ua9QqdxU79SyA5Tt4zCkki19bUimgcKj26wPb7y8wdZGobPbl9xhvhKHhQAAAAAAAAAoGv1xQDWiZISjtLAY3EIIVEiH3+eKEwgqWAr5PoaOrv7BKlIvh/NYwWHNdkeX+H5g9KD3t6p3hh4BQAAAAAAfZDRoGdzsBBht9ATZxFCN9QXA1iDBaHj45xXIeRnN7oMYFUI2aOIzvo4LLQpR6SnkwkrIrpRJNLbnp70b9+nJ0vD8Er1EuWKrLmrjFKjUWrURmn1QQZ9iMEo9TCr0TvVm6nti0n6AQAAAAAAAKCX6YsBLHUtReiHx3L3Uig5bSJBQ0dVHD8Y4/FA8QNaI2JyLlPBbUfImaVhBP8abJ92nS1ns+VsfnHrGohmvlkfrG+Y06gPNji3ULewXpgn4BcLsPIgAAAAAAAAAPRoCG20COK7SxSl4LLkXKZU35KO3T9QPWx0RXpamJtdEgbI7Idfpfvx2tUfn8NSj4sGMrVMbjWXqWERQhHAak7SNCdpCCH8Ir7fbl8sQQgAAAAAAABXhdlkYrIxixA6pS9OMZNlNTsX8llsKdddjMkhAhUR3ThsdIWryhHRjQlth1+d82lHAIulYQgzPOSJN0qNjXMaK56o0MZo3dfUxmgrHqrUJrrLUg8AAAAAANDLGA16z5UAoIfohSOwDMEG5ViVUWoihLDlLJ6MI0wXOmSDUtUaxAGOI5JCRRI3edzzvLnja7Q8k8VWEhHd6BugLsrzq68VK+QtM/uCw5SxcXX+gWr7fQ+GCNp1Crxivpv0VUapUTFF0TRU7aoCpdqFtWHFYcjpDgAAAAAAAAA9Tm8LYBmlxspH2gShVITIpyjFKWLpQW9bYUOhzjmA1U/s7yaPu57FOB7In1bVZhyTSKQfOKzKfZdypLwyUfum7wlL+a42yafIm8Y0mQQWVxVcMQks+mADvxgBLAAAAAAAALjSsBYhdFJvm0KoGkoxPdAksCimNcnurrOt3FdznmLaXbzEz33j53x4OdL2pbKSc5mHg1xGo1zhFVPsYuabq++skU9VdiB61YLf7h1nzp44a+4kV1vDI4Kvv2kOg8Hw2A6DweByO5uEK7ZfxMLFM2hWHj9h+Ogxg+1LOBy2UChw9Y/OWXTGjFnjJk8dRbPytBljZ8waf1n7Y2/K1NGTp9DqW0JizK23zaff8uQpIydPGWlfwmQy2V039T0gwHf2nAlMpofPMYnEKzY2ghAilXrdcdcivsDzu3jQoPiBg+JodmPM2MH0K/v4eIeEBBBCAgJ977hzAc1XY/KUkZMmj6B5iI6ZNn30xEnDaVa+5ppJc+dOpFNz6tSRNJtNSIi+Zckcmh0AAAAAAIC+preNwHJDG6OrfrjGf4svP0dQltI08l5/hwp8FjvZJ9DNICxCyN5QgY5Jhjbo6BxRzmVuiPHSs9odGXFOuG7mm6vvklGuNuiKV4bIb4ufaqi6cXaDSWBhaRjs9udxHzAonsVi7vnvCOXW0WOH3HLbghPH0qsqqV+0yOiwOfMmDx2W7OPrzWKxNBqtrLruxNEzu3Ye1mg8pO7y8ZUo5E1ms9lWEts/cuF1M7du3udQUygUEEKam9sMjhs/cbhWq0tLzbSVXDN/6tI7Fro63DPL3ysvazOYLnlA3JTpYxISYry8RHwBr6lJ3VCvyMy4sOu/I40NCveddzZ0+ACtVnf44Ek6lQcNjmcxWfv2HG/vUdxISIy96ZZ5MTFhWq3u/PmL63/f1nDpLIaNSDaZzIcPee5beETwtBlj/vh9m62Ew2Hz+DzS9h7XNGtNJhMhZMjQJELI4UOnbJvmXTt55qxxTz3xHv2ei0QCBpPpcAiL2aJWa8Ijgu6+97oD+1Pt7xPrLmw2W6FounSCSdddP3P54++KxaJ510zaunm/VqOzr2w0GnW6Nm+u6TPHmE3mc1n5Dp1hMBgSiZdC0WSxtIaDp88YK6uuc65Maeascf37R7737iofH++58yb9uWGX0WiybkpIiL7xpjnRMaFarT77fMH69TsbG5QtpzAs0WQyHzl82r6ppOTYKVNGxsVHeXmJ+HxuU1NzY6MyMzN3z+4TjY1KOp2xN3RoglarP3rkjPVpZFTIu+8td6jz7dcbjh1LJ4T0j4s0mcy214TNZhkMFKu7EkIGD0kw6A22Znk8Lofj+HdHrdZYLJaw8KCpU0duWL+rvT0HAAAAAIC+oLcFsLxTWhcTVI1VOQxWMgkssiX13ifE5oPeNec1gQMcU1MNkAa5D2ARQo4EC4q92KPqtGFqk5tqOVLe4SB+B6JX/CKK4VfKMcoORK8IIeIMMa+a1zi50TvNmy2nuNyTpoxa9tTdDoVffLL62JHTzpXtiUSCKdPGmkymaxZM/en7P50rxCfGvvL646dPZX312ZqK8mqNRust8UpK7n/jLfNGjxvy+kufGwzUZxQXH718xT0Bgb7NzZr1a7ft2nnYZR/EwieeumvI0CSLxXI2I+erz35Rq93FxSoqZE8ve8e+xNXlmTRl1AOPLNn89+5tW/bX1Tbq9QahiB8ZGTrv2invffTMc09/qLwUHLF57c1lyQP6Ozf1xadrThxLdygMCvb/4utXHArXrP7nvx3UJ/v+x89GR7tc9fKTD346dfKcq62EkLj46Ff/99iO7Qd/XbNJIODdcNPc199c9vwzH2m1FKHYn9a8IxQ5vjVqaxueePRt58qTp466/8GbHArfe+eHzLMX3PSnXd798OmAAF/n/ix//F3K+jfcNPu662cyGIz9+1J+WvW3m5ZHjR609LZrg4L9LRbLxfzSNT9vKipyuTKDt7f49jsWjBk7mMNh6/WG48cy1v2+Ta2iGPJpM3LUwH79Izb8sdNNHZu4uKiXX314544jv/26lS/g3XDDrNdef+TF5z/Taqkzj06cOOy+B27YsvnAtm2H6+vker1BKORHRAbPnTfx7XeeePGFz5VKlcMur7zyUFJyrHNTK79al3Ii06Gwolz22COtV9zLW/T+B09VUoWqhwxNeOaZu+6842WHMCKlJUvmzpo9zqHwyeUf1NXJPe4LAAAA0AFGg57N4V7tXkALzCKEzuhtASymlik96G2UGlVDm11NtVOOUzUnabMquDMGxNiXK/Ta83IZnaOUiThlIo5Eb0pS6EObjSKDRao3E0IqRCwlh10tYJaJ2ApuB9+W/BKKj9emMY7hEle8MkSisyK+3SRETjUn8M9AV/VTjqdnnMm2PeXyuN+sequuttH9USIiQx5/8i6lsumrz9a8/vZywmD88etWhzFQs+dOKigo+eKTn20lDfXyY0dO5V4oWPn9m0kD+mdm5Di37OMrefWNZXt2H936z94Bg+Ief/LOxkZFWspZym488/wDbDbrqcffIoQ8/uRdK55/4M3XvnLfc5pGjx1yPivvn427bDGuJqX6/Ln8woKy1b+9n5gU69ylzz5ezWGzCSFjJwy79bYFyx9901quoopx1NY0PHTfq/bxs48+fV4hd3mV33njGyaLYqIcm8X++vvXPZ7OoutmnDqZte63f61PP/nwpy+/fnX8xOH7955wrvzMUx9YJ1Tefd/1HDZ71fd/EkJcxSb27Tmxb88J24kIhfyf1lDHlTps+WPvEEIIgzy14m4en/f+Oz+4qTxgYP/F18344L0f1SrNy689lJdb7DBqyWbgwLjlT93xx+87Dh06yedxb7hp9kuvPPT8s580UA2vYzKZTz9zF5fLeeuNb8vKqqOiQu+7//onlt/+/rur7IdiOYiM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"
    st.markdown(
        f'<div style="text-align:center;margin:0 auto 20px auto;max-width:1100px;">'
        f'<img src="data:image/png;base64,{_banner_b64}" style="width:100%;height:auto;border-radius:12px;" />'
        f'</div>',
        unsafe_allow_html=True
    )
    st.write("")
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

    # ── 최종사용자 동의 체크 (미동의 시 강제 표시) ──
    if not check_user_terms(user) and st.session_state.get("current_page") not in ("terms_agree",):
        st.session_state.current_page = "terms_agree"

    if st.session_state.get("current_page") == "terms_agree":
        st.markdown('<div style="font-size:1.4rem;font-weight:700;padding:8px 0;">🐉 드래곤아이즈 모니터링</div>', unsafe_allow_html=True)
        st.divider()
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0f3460,#16213e);border-radius:12px;padding:20px 24px;margin-bottom:16px;">
            <h2 style="color:white;margin:0 0 8px 0;">📋 최종사용자 이용약관 동의</h2>
            <p style="color:#94a3b8;margin:0;">DragonEyes 시스템을 사용하기 위해 아래 이용약관에 동의하셔야 합니다.</p>
            <p style="color:#f59e0b;margin:4px 0 0 0;font-size:0.85rem;">⚠️ 모든 필수 항목에 동의하지 않으면 시스템을 사용할 수 없습니다.</p>
        </div>
        """, unsafe_allow_html=True)
        for section in TERMS_CONTENT["sections"]:
            st.markdown(f"### {section['num']}. {section['title']}")
            with st.container(border=True):
                for item in section["items"]:
                    st.markdown(f"<p style='margin:6px 0;font-size:0.92rem;'>{item}</p>", unsafe_allow_html=True)
        st.divider()
        st.markdown("### ✍️ 동의 확인")
        a1 = st.checkbox("**[필수]** 시스템 소개 및 운영 방침을 확인하였으며 이에 동의합니다.", key="ta1")
        a2 = st.checkbox("**[필수]** 시스템 사용조건(라이선스, 데이터 권리 등) 모든 항목에 동의합니다.", key="ta2")
        a3 = st.checkbox("**[필수]** 모니터링 결과 보고서에 대한 권리가 드래곤아이즈 시스템 관리자에게 귀속됨에 동의합니다.", key="ta3")
        a4 = st.checkbox("**[필수]** 사용자 정보가 라이선스 마케팅 목적으로 활용될 수 있음에 동의합니다.", key="ta4")
        all_agreed = a1 and a2 and a3 and a4
        st.markdown(f"<p style='color:#64748b;font-size:0.8rem;'>동의자: {user.get('name','')} ({user.get('email','')}) | 버전: {TERMS_VERSION} | 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)
        tc1, tc2 = st.columns(2)
        with tc1:
            if st.button("✅ 모든 항목 동의 후 시작", type="primary", use_container_width=True, disabled=not all_agreed, key="terms_submit"):
                if save_user_consent(user["id"], user.get("name",""), user.get("email","")):
                    st.session_state.user["terms_agreed"] = True
                    st.session_state.user["terms_version"] = TERMS_VERSION
                    st.session_state.current_page = "home_landing"
                    st.success("✅ 동의 완료! 시스템을 시작합니다.")
                    st.rerun()
                else:
                    st.error("동의 처리 중 오류가 발생했습니다.")
        with tc2:
            if st.button("🚪 동의 거부 후 로그아웃", use_container_width=True, key="terms_logout"):
                st.query_params.clear()
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
        st.stop()

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

    # ── 미확인 공지 팝업 (로그인 후 한 번만) ──
    unread_ann = get_unread_announcements(user["id"])
    if unread_ann and not st.session_state.get("ann_popup_dismissed"):
        ann_id = unread_ann[0]["id"]
        latest = supabase.table("announcements").select("*").eq("id", ann_id).execute().data
        if latest:
            ann = latest[0]
            type_color = {"notice": "🔵", "work_order": "🟠", "urgent": "🚨"}.get(ann["type"], "📢")
            type_label = {"notice": "공지사항", "work_order": "업무지시", "urgent": "긴급공지"}.get(ann["type"], "공지")
            with st.container(border=True):
                st.markdown(f"### {type_color} {type_label}")
                st.markdown(f"**{ann['title']}**")
                st.markdown(f'<div style="color:#1e293b;">{ann["content"]}</div>', unsafe_allow_html=True)
                st.caption(f"{t('ann_date')} {str(ann.get('created_at',''))[:10]}")
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button(t("ann_confirm"), key="ann_popup_confirm", use_container_width=True, type="primary"):
                        mark_announcement_read(ann["id"], user["id"])
                        st.session_state.ann_popup_dismissed = True
                        st.rerun()
                with bc2:
                    if st.button(t("ann_later"), key="ann_popup_later", use_container_width=True):
                        st.session_state.ann_popup_dismissed = True
                        st.rerun()

    # ── 상단 헤더 ──
    _show_admin_btn = is_admin or is_super
    try:
        _unread_cnt = len(get_unread_announcements(user["id"]))
    except:
        _unread_cnt = 0
    _notice_label = f"{t('hdr_notice')} 🔴{_unread_cnt}" if _unread_cnt > 0 else t("hdr_notice")

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
        h1, h_right = st.columns([3, 7])
    else:
        h1, h_right = st.columns([3, 7])

    with h1:
        title_text = t("app_title").replace("🐉 ", "").replace("🐉 ", "")
        st.markdown(f'<div style="font-size:1.6rem; font-weight:700; display:flex; align-items:center; gap:6px; margin:0; padding:4px 0">🐉 {title_text}</div>', unsafe_allow_html=True)

    with h_right:
        _show_agency_btn = is_agency_admin(user) or is_superadmin(user)
        if _show_admin_btn and _show_agency_btn:
            spacer, bc_ko, bc_en, bc_jp, bc_agency, bc_work, bc_home, bc_write, bc_notice, bc_admin, bc_profile, bc_logout = st.columns([0.5, 0.28, 0.28, 0.28, 0.65, 0.5, 0.42, 0.42, 0.52, 0.52, 0.5, 0.25])
        elif _show_admin_btn:
            spacer, bc_ko, bc_en, bc_jp, bc_work, bc_home, bc_write, bc_notice, bc_admin, bc_profile, bc_logout = st.columns([1.2, 0.28, 0.28, 0.28, 0.5, 0.42, 0.42, 0.52, 0.52, 0.5, 0.25])
            bc_agency = None
        else:
            spacer, bc_ko, bc_en, bc_jp, bc_work, bc_home, bc_write, bc_notice, bc_profile, bc_logout = st.columns([1.5, 0.28, 0.28, 0.28, 0.5, 0.42, 0.42, 0.52, 0.5, 0.25])
            bc_agency = None

        with bc_ko:
            if st.button("🇰🇷", use_container_width=True, key="flag_ko", help="한국어"):
                st.session_state.lang = "ko"; st.rerun()
        with bc_en:
            if st.button("🇺🇸", use_container_width=True, key="flag_en", help="English"):
                st.session_state.lang = "en"; st.rerun()
        with bc_jp:
            if st.button("🇯🇵", use_container_width=True, key="flag_ja", help="日本語"):
                st.session_state.lang = "ja"; st.rerun()
        if bc_agency:
            with bc_agency:
                if st.button("🤝 위탁대시보드", use_container_width=True, key="hdr_agency_btn"):
                    go_to("agency_dashboard"); st.rerun()
        with bc_work:
            if st.button(t("hdr_work"), use_container_width=True, key="hdr_work_btn"):
                go_to("work_page"); st.rerun()
        with bc_home:
            if st.button("🏠 홈", use_container_width=True):
                go_home(); st.rerun()
        with bc_write:
            if st.button(t("hdr_write"), use_container_width=True):
                open_report_form(from_tab=st.session_state.active_tab); st.rerun()
        with bc_notice:
            if st.button(_notice_label, use_container_width=True, key="hdr_notice_btn"):
                st.session_state.current_page = "home"
                st.session_state.active_tab = 98
                st.rerun()
        if _show_admin_btn:
            with bc_admin:
                if st.button(t("hdr_admin"), use_container_width=True, key="hdr_admin_btn"):
                    st.session_state.current_page = "home"
                    st.session_state.active_tab = 99
                    st.rerun()
        with bc_profile:
            if st.button(t("hdr_profile"), use_container_width=True, key="hdr_profile_btn"):
                go_to("user_profile"); st.rerun()
        with bc_logout:
            if st.button("🚪", use_container_width=True, help=t("logout_help")):
                st.query_params.clear()
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()

    st.markdown(f"""
    <div style="
        display: grid;
        grid-template-columns: 1fr 1fr;
        align-items: center;
        gap: 16px;
        background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
        border-left: 5px solid #e94560;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        margin-bottom: -0.5rem;
    ">
        <div style="color:white; font-size:0.88rem; line-height:1.6;">
            🛡️ <strong>{t("banner_line1")}</strong><br>
            {t("banner_line2")}
        </div>
        <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center; justify-content:flex-end;">
            <span style="color:#94a3b8; font-size:0.68rem; font-weight:600; letter-spacing:0.05em; white-space:nowrap; margin-right:2px;">🛡️ {t("badge_intl")}</span>
            <span style="background:linear-gradient(135deg,#1a3a5c,#0e2a4a);border:1px solid #2563eb55;color:#60a5fa;font-size:0.68rem;font-weight:700;padding:4px 10px;border-radius:20px;white-space:nowrap;">🇺🇸 {t("badge_ncmec")}</span>
            <span style="background:linear-gradient(135deg,#1a3a5c,#0e2a4a);border:1px solid #7c3aed55;color:#a78bfa;font-size:0.68rem;font-weight:700;padding:4px 10px;border-radius:20px;white-space:nowrap;">🌍 WeProtect Global Alliance</span>
            <span style="background:linear-gradient(135deg,#1a3a5c,#0e2a4a);border:1px solid #059669aa;color:#34d399;font-size:0.68rem;font-weight:700;padding:4px 10px;border-radius:20px;white-space:nowrap;">🇬🇧 {t("badge_iwf")}</span>
            <span style="background:linear-gradient(135deg,#1a3a5c,#0e2a4a);border:1px solid #d9770655;color:#fb923c;font-size:0.68rem;font-weight:700;padding:4px 10px;border-radius:20px;white-space:nowrap;">⚙️ Tech Coalition</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════
    # ══════════════════════════════
    if page == "report_form":
        col_back, col_title = st.columns([1,5])
        with col_back:
            if st.button(t("prev")):
                go_back(); st.rerun()
        with col_title:
            st.subheader(t("report_title"))
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
                            prev_tab = st.session_state.get("prev_tab", 0)
                            st.session_state.prefill_content = ""
                            st.session_state.prefill_result = ""
                            st.session_state.current_page = prev
                            st.session_state.active_tab = prev_tab  # 탭 복원
                            st.success(t("report_submitted"))
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

            # 보고서 고유번호 + 탐색 URL 연결 표시
            report_uid = r.get("id","")
            analyzed_url_id = r.get("analyzed_url_id")
            rc_id1, rc_id2 = st.columns(2)
            with rc_id1:
                st.markdown(f"<span style='font-size:0.78rem;color:#64748b;'>🔖 보고서 번호: <code style='background:#f1f5f9;padding:2px 6px;border-radius:4px;color:#1d4ed8;font-weight:700;'>#{report_uid[:8].upper() if report_uid else 'N/A'}</code></span>", unsafe_allow_html=True)
            with rc_id2:
                if analyzed_url_id:
                    st.markdown(f"<span style='font-size:0.78rem;color:#64748b;'>🔗 탐색 기록 연결: <code style='background:#f0fdf4;padding:2px 6px;border-radius:4px;color:#16a34a;font-weight:700;'>#{analyzed_url_id[:8].upper()}</code></span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='font-size:0.78rem;color:#94a3b8;'>🔗 탐색 기록 연결: 없음</span>", unsafe_allow_html=True)
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
                            st.success(t("translate_ok"))
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
            if st.button(t("home_back")):
                go_home(); st.rerun()
        with col_title:
            st.subheader("🐲 드래곤파더 — 전체화면 대화")

        chat_info = can_use_chat(user["id"])
        ci1, ci2, ci3 = st.columns(3)
        ci1.metric("오늘", f"{chat_info.get('today_used',0)}/{CHAT_DAILY_LIMIT}턴")
        ci2.metric("이번주", f"{chat_info.get('week_used',0)}/{CHAT_WEEKLY_LIMIT}턴")
        ci3.metric("이번달", f"{chat_info.get('monthly_used',0)}/{chat_info.get('monthly_limit', CHAT_MONTHLY_LIMIT)}턴")

        chat_box = st.container(height=550)
        with chat_box:
            if not st.session_state.chat_history:
                st.caption("💡 예: '이 댓글이 그루밍 패턴인지 분석해줘'")
                st.caption(t("chat_example_short"))
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
            if reason == "daily": st.warning(t("chat_limit_daily").format(CHAT_DAILY_LIMIT))
            elif reason == "weekly": st.warning(t("chat_limit_weekly").format(CHAT_WEEKLY_LIMIT))
            elif reason == "monthly": st.warning(t("chat_limit_monthly"))

        ic1, ic2 = st.columns([6, 1])
        with ic1:
            fs_input = st.chat_input(
                t("chat_input_ph") if chat_info["ok"] else t("chat_disabled"),
                max_chars=300, disabled=not chat_info["ok"], key="dragon_fs_input"
            )
        with ic2:
            if st.button("🗑️", help=t("chat_clear"), key="clear_fs"):
                st.session_state.chat_history = []; st.rerun()

        if fs_input and chat_info["ok"]:
            st.session_state.chat_history.append({"role": "user", "content": fs_input})
            with st.spinner("🐲 " + t("dragon_caption")[:10] + "..."):
                try:
                    api_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history[:-1]]
                    response = chat_with_ai(api_history, fs_input, lang)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    supabase.table("chat_logs").insert({"user_id": user["id"], "message": fs_input, "response": response, "tokens_used": 1}).execute()
                    use_chat_token(user["id"])
                    st.rerun()
                except Exception as e:
                    st.session_state.chat_history.pop()
                    st.error(t("error_msg").format(str(e)))

    # ══════════════════════════════
    # 💼 일하기 페이지
    # ══════════════════════════════
    elif page == "license_request":
        # ══════════════════════════════
        # 📋 신규 라이선스 신청 페이지 (위탁관리자용)
        # ══════════════════════════════
        col_back, col_title = st.columns([1, 5])
        with col_back:
            if st.button("◀ 돌아가기"):
                go_to("agency_dashboard"); st.rerun()
        with col_title:
            st.subheader("📋 신규 사용자 라이선스 신청")

        st.info("💡 신청 후 시스템관리자 검토 → 업체 관리자 이메일 동의 → 라이선스 활성화 순으로 진행됩니다.")

        # 위탁관리자 agency_id 조회
        my_agency = None
        try:
            ag_res = supabase.table("agencies").select("*").eq("user_id", user["id"]).execute()
            if ag_res.data:
                my_agency = ag_res.data[0]
        except:
            pass

        # 관할 장애인고용공단 지역지사 옵션
        DISABILITY_OFFICES = [
            "선택안함",
            "서울지역본부", "서울남부지사", "서울동부지사", "서울북부지사",
            "부산지역본부", "대구지역본부", "인천지역본부", "광주지역본부",
            "대전지역본부", "울산지사", "세종지사",
            "경기지역본부", "경기북부지사", "경기서부지사",
            "강원지사", "충북지사", "충남지사", "전북지사", "전남지사",
            "경북지사", "경남지사", "제주지사", "기타"
        ]

        with st.form("license_request_form"):
            st.markdown("### 🏢 업체 정보")
            fc1, fc2 = st.columns(2)
            with fc1:
                req_company = st.text_input("업체명 *", placeholder="예: (주)포유솔루션")
                req_biz_num = st.text_input("사업자등록번호", placeholder="000-00-00000")
                req_company_type = st.text_input("업종", placeholder="예: 아동교육, 복지기관")
                req_address = st.text_input("업체 주소")
            with fc2:
                req_company_phone = st.text_input("업체 대표전화", placeholder="02-0000-0000")
                req_company_email = st.text_input("업체 대표이메일", placeholder="info@company.com")
                req_plan = st.selectbox("라이선스 플랜",
                    ["basic", "standard", "premium"],
                    format_func=lambda x: {"basic":"🥉 Basic (3명/월)", "standard":"🥈 Standard (5명/월)", "premium":"🥇 Premium (무제한/월)"}[x])
                req_users = st.number_input("요청 사용자 수", min_value=1, max_value=50, value=5)

            st.divider()
            st.markdown("### ♿ 장애인 고용 정보 (선택)")
            dc1, dc2 = st.columns(2)
            with dc1:
                req_disability_office = st.selectbox("관할 장애인고용공단 지사", DISABILITY_OFFICES)
            with dc2:
                req_disability_org = st.text_input("소속 장애인 단체", placeholder="예: 한국장애인고용협회")

            st.divider()
            st.markdown("### 👤 업체 관리자 정보 (필수 — 이메일 동의 진행)")
            ac1, ac2 = st.columns(2)
            with ac1:
                req_admin_name = st.text_input("관리자 이름 *", placeholder="홍길동")
                req_admin_email = st.text_input("관리자 이메일 * (동의 이메일 수신)", placeholder="admin@company.com")
            with ac2:
                req_admin_phone = st.text_input("관리자 연락처 *", placeholder="010-0000-0000")
                req_admin_title = st.text_input("직함", placeholder="예: 대표이사, 팀장")

            st.divider()
            st.markdown("### 📝 사용 목적")
            req_purpose = st.text_area("사용 목적 및 특이사항", height=80,
                placeholder="예: 아동 온라인 안전 모니터링 업무, 담당 기관명 등")

            st.divider()
            st.markdown("### 📎 첨부 파일")
            st.caption("⚠️ 사업자등록증은 필수입니다. JPG, PNG, PDF 형식 (최대 10MB)")
            req_business_cert = st.file_uploader(
                "📄 사업자등록증 * (필수)",
                type=["jpg", "jpeg", "png", "pdf"],
                key="biz_cert_upload"
            )
            req_additional_files = st.file_uploader(
                "📂 추가 첨부파일 (선택, 여러 개 가능)",
                type=["jpg", "jpeg", "png", "pdf"],
                accept_multiple_files=True,
                key="additional_files_upload",
                help="명함, 재직증명서, 계약서 등"
            )

            submitted = st.form_submit_button("📤 라이선스 신청 제출", type="primary", use_container_width=True)

            if submitted:
                # ─── 필수 검증 ───
                if not req_company or not req_admin_name or not req_admin_email or not req_admin_phone:
                    st.error("업체명, 관리자 이름, 관리자 이메일, 관리자 연락처는 필수 입력 항목입니다.")
                elif not req_business_cert:
                    st.error("📎 사업자등록증 첨부는 필수입니다.")
                else:
                    try:
                        import time as _time
                        # ─── 1단계: 사업자등록증 업로드 ───
                        biz_cert_path = None
                        ts = int(_time.time())
                        cert_ext = req_business_cert.name.split(".")[-1].lower()
                        biz_cert_path = f"license-requests/{user['id']}/{ts}_biz_cert.{cert_ext}"

                        try:
                            supabase.storage.from_("license-documents").upload(
                                biz_cert_path,
                                req_business_cert.getvalue(),
                                file_options={"content-type": req_business_cert.type or "application/octet-stream"}
                            )
                        except Exception as up_err:
                            st.error(f"📎 사업자등록증 업로드 실패: {str(up_err)}")
                            st.stop()

                        # ─── 2단계: 추가 파일 업로드 ───
                        additional_files_list = []
                        if req_additional_files:
                            for idx, af in enumerate(req_additional_files):
                                try:
                                    af_ext = af.name.split(".")[-1].lower()
                                    af_path = f"license-requests/{user['id']}/{ts}_extra_{idx}_{af.name}"
                                    supabase.storage.from_("license-documents").upload(
                                        af_path,
                                        af.getvalue(),
                                        file_options={"content-type": af.type or "application/octet-stream"}
                                    )
                                    additional_files_list.append({
                                        "path": af_path,
                                        "name": af.name,
                                        "size": af.size,
                                    })
                                except Exception as up_err:
                                    st.warning(f"⚠️ 추가 파일 '{af.name}' 업로드 실패: {str(up_err)}")

                        # ─── 3단계: DB INSERT ───
                        supabase.table("license_requests").insert({
                            "agency_id": my_agency["id"] if my_agency else None,
                            "requested_by": user["id"],
                            "request_type": "new_tenant",
                            "company_name": req_company,
                            "company_address": req_address,
                            "company_phone": req_company_phone,
                            "company_email": req_company_email,
                            "business_number": req_biz_num,
                            "company_type": req_company_type,
                            "admin_name": req_admin_name,
                            "admin_email": req_admin_email,
                            "admin_phone": req_admin_phone,
                            "admin_title": req_admin_title,
                            "requested_users": req_users,
                            "license_plan": req_plan,
                            "purpose": req_purpose,
                            "status": "pending",
                            "disability_office": req_disability_office if req_disability_office != "선택안함" else None,
                            "disability_org": req_disability_org or None,
                            "business_cert_path": biz_cert_path,
                            "additional_files": additional_files_list,
                        }).execute()
                        st.success("✅ 라이선스 신청이 완료됐습니다! 시스템관리자 검토 후 연락드리겠습니다.")

                        # ─── 4단계: 시스템관리자 알림 ───
                        attach_info = f"\n📎 사업자등록증: 첨부됨"
                        if additional_files_list:
                            attach_info += f"\n📂 추가 첨부: {len(additional_files_list)}건"
                        supabase.table("hq_messages").insert({
                            "from_user_id": user["id"],
                            "from_name": user["name"],
                            "from_email": user.get("email",""),
                            "subject": f"[DragonEyes] 신규 라이선스 신청 — {req_company}",
                            "body": f"업체명: {req_company}\n관리자: {req_admin_name} ({req_admin_email})\n플랜: {req_plan}\n사용자수: {req_users}명\n목적: {req_purpose}{attach_info}",
                            "recipient": "kingcas7@gmail.com",
                        }).execute()
                    except Exception as e:
                        st.error(f"신청 오류: {str(e)}")

        # 내 신청 이력
        st.divider()
        st.markdown("### 📜 신청 이력")
        try:
            my_requests = supabase.table("license_requests").select("*").eq("requested_by", user["id"]).order("created_at", desc=True).execute().data or []
            status_map = {
                "pending": "⏳ 검토중",
                "approved": "✅ 승인됨",
                "consent_sent": "📧 동의메일 발송",
                "consented": "✍️ 동의완료",
                "active": "🟢 활성화",
                "rejected": "❌ 반려"
            }
            if my_requests:
                for req in my_requests:
                    st.markdown(f"**{req['company_name']}** | {status_map.get(req['status'],'?')} | {str(req.get('created_at',''))[:10]} | 관리자: {req.get('admin_name','')} ({req.get('admin_email','')})")
            else:
                st.info("신청 이력이 없습니다.")
        except Exception as e:
            st.error(f"이력 조회 오류: {str(e)}")

    elif page == "consent_page":
        # ══════════════════════════════
        # ✍️ 최종사용자 동의 페이지
        # ══════════════════════════════
        st.subheader("✍️ DragonEyes 서비스 이용 동의")

        # URL 파라미터에서 request_id 가져오기
        params = st.query_params
        req_id = params.get("req_id", "")

        if not req_id:
            st.error("잘못된 접근입니다. 이메일의 링크를 통해 접속해주세요.")
        else:
            try:
                req_data = supabase.table("license_requests").select("*").eq("id", req_id).execute().data
                if not req_data:
                    st.error("신청 정보를 찾을 수 없습니다.")
                else:
                    req = req_data[0]
                    if req["status"] == "active":
                        st.success("✅ 이미 동의가 완료되어 라이선스가 활성화되어 있습니다.")
                    elif req["status"] not in ["approved", "consent_sent", "consented"]:
                        st.warning("아직 관리자 승인이 완료되지 않았습니다.")
                    else:
                        st.markdown(f"""
                        <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:16px;margin-bottom:16px;">
                            <h4 style="margin:0 0 8px 0;">🏢 {req['company_name']} 귀중</h4>
                            <p style="margin:0;color:#475569;">안녕하세요, <strong>{req['admin_name']}</strong>님.<br>
                            DragonEyes 모니터링 시스템 사용 신청에 감사드립니다.<br>
                            아래 이용 조건을 확인하시고 모든 항목에 동의하시면 라이선스가 즉시 활성화됩니다.</p>
                        </div>
                        """, unsafe_allow_html=True)

                        # 동의 항목 표시
                        consent_items = supabase.table("consent_items").select("*").eq("is_active", True).order("order_num").execute().data or []
                        all_agreed = True
                        agreed_items = {}

                        for item in consent_items:
                            with st.container(border=True):
                                ci1, ci2 = st.columns([1, 10])
                                with ci2:
                                    st.markdown(f"**{'[필수] ' if item['is_required'] else '[선택] '}{item['title']}**")
                                    st.caption(item['content'])
                                agreed = st.checkbox(
                                    f"위 내용에 동의합니다{'(필수)' if item['is_required'] else '(선택)'}",
                                    key=f"consent_{item['id']}"
                                )
                                agreed_items[item['id']] = agreed
                                if item['is_required'] and not agreed:
                                    all_agreed = False

                        st.divider()
                        # 서명 정보
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            consent_name = st.text_input("성명 *", value=req.get('admin_name',''), placeholder="동의자 성명")
                        with sc2:
                            consent_email = st.text_input("이메일 *", value=req.get('admin_email',''), placeholder="동의자 이메일")

                        if not all_agreed:
                            st.warning("⚠️ 필수 동의 항목을 모두 체크해주세요.")

                        if st.button("✅ 모든 항목 동의 및 라이선스 활성화", type="primary",
                            use_container_width=True, disabled=not all_agreed):
                            try:
                                # 동의 기록 저장
                                for item_id, agreed in agreed_items.items():
                                    supabase.table("consent_records").insert({
                                        "request_id": req_id,
                                        "consent_item_id": item_id,
                                        "consented": agreed,
                                        "consented_by_name": consent_name,
                                        "consented_by_email": consent_email,
                                    }).execute()

                                # 신청 상태 → consented
                                supabase.table("license_requests").update({
                                    "status": "consented",
                                    "consented_at": datetime.now().isoformat(),
                                }).eq("id", req_id).execute()

                                # 시스템관리자에게 동의 완료 알림
                                supabase.table("hq_messages").insert({
                                    "from_user_id": None,
                                    "from_name": consent_name,
                                    "from_email": consent_email,
                                    "subject": f"[DragonEyes] 동의 완료 — {req['company_name']}",
                                    "body": f"{req['company_name']} {consent_name}님이 모든 항목에 동의하였습니다.\n라이선스 활성화를 진행해 주세요.",
                                    "recipient": "kingcas7@gmail.com",
                                }).execute()

                                st.success("✅ 동의가 완료됐습니다! 시스템관리자가 라이선스를 최종 활성화 후 안내드리겠습니다.")
                                st.balloons()
                            except Exception as e:
                                st.error(f"동의 처리 오류: {str(e)}")
            except Exception as e:
                st.error(f"오류: {str(e)}")

    elif page == "agency_dashboard":
        # ══════════════════════════════
        # 🤝 위탁관리자 전용 모니터링 대시보드
        # ══════════════════════════════
        col_back, col_title = st.columns([1, 5])
        with col_back:
            if st.button("🏠 홈"):
                go_home(); st.rerun()
        with col_title:
            st.subheader("🤝 위탁관리자 모니터링 대시보드")

        # 신규 라이선스 신청 버튼
        ab1, ab2, ab3 = st.columns([2, 2, 6])
        with ab1:
            if st.button("➕ 신규 라이선스 신청", type="primary", use_container_width=True, key="new_license_btn"):
                go_to("license_request"); st.rerun()
        with ab2:
            if st.button("📋 신청 이력 보기", use_container_width=True, key="license_history_btn"):
                go_to("license_request"); st.rerun()
        st.divider()

        today = date.today()
        this_month = today.strftime("%Y-%m")
        this_week_start = today - timedelta(days=today.weekday())  # 월요일
        today_str = today.isoformat()
        week_str = this_week_start.isoformat()

        # 담당 업체 목록
        if is_superadmin(user):
            my_tenants = get_all_tenants()
        else:
            my_tenants = get_agency_tenants(user["id"])

        if not my_tenants:
            st.info("담당 업체가 없습니다. 관리자에게 업체 배정을 요청해주세요.")
        else:
            # 전체 보고서 데이터 한 번만 로드
            # 보고서 데이터 캐싱 (1분)
            _cache_key = "all_reps_ag_cache"
            _cache_time = "all_reps_ag_time"
            import time
            if _cache_key not in st.session_state or (time.time() - st.session_state.get(_cache_time, 0)) > 60:
                st.session_state[_cache_key] = supabase.table("reports").select("user_id,created_at,severity").execute().data or []
                st.session_state[_cache_time] = time.time()
            all_reps_ag = st.session_state[_cache_key]

            # 전체 사용자 목록
            all_tenant_users = []
            for tn in my_tenants:
                all_tenant_users.extend(get_tenant_users(tn["id"]))
            all_uid_set = {u["id"] for u in all_tenant_users}

            # ── 전체 요약 카드 ──
            total_today = len([r for r in all_reps_ag if r["user_id"] in all_uid_set and str(r.get("created_at",""))[:10] == today_str])
            total_week  = len([r for r in all_reps_ag if r["user_id"] in all_uid_set and str(r.get("created_at",""))[:10] >= week_str])
            total_month = len([r for r in all_reps_ag if r["user_id"] in all_uid_set and str(r.get("created_at",""))[:7] == this_month])
            risky_cnt   = len([r for r in all_reps_ag if r["user_id"] in all_uid_set and r.get("severity",0) >= 4])

            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            sc1.metric("담당 업체", f"{len(my_tenants)}개")
            sc2.metric("총 사용자", f"{len(all_tenant_users)}명")
            sc3.metric("📅 오늘 보고서", f"{total_today}건")
            sc4.metric("📆 이번주 보고서", f"{total_week}건")
            sc5.metric("🗓️ 이번달 보고서", f"{total_month}건")
            st.divider()

            # ── 현황 필터 탭 ──
            filter_tab1, filter_tab2, filter_tab3, filter_tab4, filter_tab5 = st.tabs([
                "📋 전체 현황", "⚠️ 일일 50% 미만", "✅ 일일 50% 이상", "📊 달성률별 그룹", "📅 캘린더 현황"
            ])

            def calc_user_stats(u, all_reps):
                """사용자 일일/주간/월별 통계 계산"""
                ur_all  = [r for r in all_reps if r["user_id"] == u["id"]]
                ur_today = [r for r in ur_all if str(r.get("created_at",""))[:10] == today_str]
                ur_week  = [r for r in ur_all if str(r.get("created_at",""))[:10] >= week_str]
                ur_month = [r for r in ur_all if str(r.get("created_at",""))[:7] == this_month]
                tgt = u.get("monthly_target", 10)
                monthly_rate = min(int(len(ur_month)/tgt*100), 100) if tgt > 0 else 0
                # 일일 목표 = 월목표 / 22영업일 (근사)
                daily_tgt = max(1, round(tgt / 22))
                daily_rate = min(int(len(ur_today)/daily_tgt*100), 100) if daily_tgt > 0 else 0
                return {
                    "today": len(ur_today), "week": len(ur_week), "month": len(ur_month),
                    "total": len(ur_all), "tgt": tgt, "daily_tgt": daily_tgt,
                    "monthly_rate": monthly_rate, "daily_rate": daily_rate,
                }

            PAGE_SIZE_AGENCY = 50  # 페이지당 사용자 수

            def render_user_table(users_list, tab_key, show_bulk=True):
                """사용자 현황 테이블 렌더링 — 페이지네이션 + 정렬 + 선택 발송"""
                if not users_list:
                    st.info("해당하는 사용자가 없습니다.")
                    return

                total_cnt = len(users_list)

                # ── 정렬 + 검색 컨트롤 ──
                ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2, 2, 2, 2])
                with ctrl1:
                    sort_key = st.selectbox("정렬 기준",
                        ["월달성률 낮은순", "월달성률 높은순", "일일달성률 낮은순", "이번달 많은순", "이름순"],
                        key=f"sort_{tab_key}")
                with ctrl2:
                    search_name = st.text_input("이름 검색", key=f"search_{tab_key}", placeholder="이름 입력...")
                with ctrl3:
                    page_key = f"page_{tab_key}"
                    if page_key not in st.session_state:
                        st.session_state[page_key] = 0
                    total_pages = max(1, (total_cnt + PAGE_SIZE_AGENCY - 1) // PAGE_SIZE_AGENCY)
                    st.markdown(f"<div style='padding-top:28px;color:#64748b;font-size:0.85rem;'>총 {total_cnt}명 | {st.session_state[page_key]+1}/{total_pages}p</div>", unsafe_allow_html=True)
                with ctrl4:
                    # 전체 선택 버튼 (체크박스 대신 버튼으로 처리)
                    sel_state_key = f"sel_state_{tab_key}"
                    if sel_state_key not in st.session_state:
                        st.session_state[sel_state_key] = False
                    btn_label = "☑️ 전체 해제" if st.session_state[sel_state_key] else "☐ 전체 선택"
                    if st.button(btn_label, key=f"sel_all_btn_{tab_key}", use_container_width=True):
                        new_state = not st.session_state[sel_state_key]
                        st.session_state[sel_state_key] = new_state
                        # 각 행 체크박스 session_state도 함께 초기화
                        for u in users_list:
                            k = f"sel_{tab_key}_{u['id']}"
                            st.session_state[k] = new_state
                        st.rerun()
                    sel_all = st.session_state[sel_state_key]

                # 검색 필터
                if search_name:
                    users_list = [u for u in users_list if search_name in u.get("name","")]

                # 통계 계산 후 정렬
                users_with_stats = []
                for u in users_list:
                    stats = calc_user_stats(u, all_reps_ag)
                    users_with_stats.append((u, stats))

                sort_map = {
                    "월달성률 낮은순": lambda x: x[1]["monthly_rate"],
                    "월달성률 높은순": lambda x: -x[1]["monthly_rate"],
                    "일일달성률 낮은순": lambda x: x[1]["daily_rate"],
                    "이번달 많은순": lambda x: -x[1]["month"],
                    "이름순": lambda x: x[0].get("name",""),
                }
                users_with_stats.sort(key=sort_map.get(sort_key, sort_map["월달성률 낮은순"]))

                # 페이지네이션
                page_num = st.session_state[page_key]
                paged = users_with_stats[page_num*PAGE_SIZE_AGENCY:(page_num+1)*PAGE_SIZE_AGENCY]

                # 헤더
                st.markdown("""<div style="display:grid;grid-template-columns:0.3fr 1.8fr 0.7fr 0.7fr 0.7fr 0.7fr 0.8fr 0.8fr 0.5fr;
                    gap:4px;background:#1e3a5f;color:white;padding:6px 8px;border-radius:6px;
                    font-size:0.75rem;font-weight:700;margin-bottom:4px;">
                    <div>선택</div><div>이름</div><div>오늘</div><div>이번주</div><div>이번달</div>
                    <div>목표</div><div>일일달성률</div><div>월달성률</div><div>알림</div>
                </div>""", unsafe_allow_html=True)

                selected_users = []
                for u, stats in paged:
                    d_color = "#22c55e" if stats["daily_rate"] >= 50 else "#ef4444"
                    m_color = "#22c55e" if stats["monthly_rate"] >= 100 else "#f59e0b" if stats["monthly_rate"] >= 50 else "#ef4444"
                    d_icon = "✅" if stats["daily_rate"] >= 50 else "⚠️"
                    rc = st.columns([0.3, 1.8, 0.7, 0.7, 0.7, 0.7, 0.8, 0.8, 0.5])
                    ind_key = f"sel_{tab_key}_{u['id']}"
                    sel = rc[0].checkbox("", key=ind_key, label_visibility="collapsed")
                    if sel:
                        selected_users.append(u)
                    rc[1].write(f"👤 **{u['name']}**")
                    rc[2].write(f"{stats['today']}건")
                    rc[3].write(f"{stats['week']}건")
                    rc[4].write(f"{stats['month']}건")
                    rc[5].write(f"{stats['tgt']}건")
                    rc[6].markdown(f"<span style='color:{d_color};font-weight:700'>{d_icon} {stats['daily_rate']}%</span>", unsafe_allow_html=True)
                    rc[7].markdown(f"<span style='color:{m_color};font-weight:700'>{stats['monthly_rate']}%</span>", unsafe_allow_html=True)
                    with rc[8]:
                        if st.button("📧", key=f"notif_{tab_key}_{u['id']}", help="개인 이메일"):
                            st.session_state["quick_notif_user"] = u
                            st.session_state["quick_notif_show"] = True
                            st.rerun()

                # 페이지 이동 버튼
                pp1, pp2, pp3, pp4 = st.columns([1, 1, 4, 2])
                with pp1:
                    if st.button("◀ 이전", key=f"prev_{tab_key}", disabled=page_num==0):
                        st.session_state[page_key] -= 1; st.rerun()
                with pp2:
                    if st.button("다음 ▶", key=f"next_{tab_key}", disabled=page_num>=total_pages-1):
                        st.session_state[page_key] += 1; st.rerun()
                with pp4:
                    st.markdown(f"<div style='text-align:right;color:#94a3b8;font-size:0.8rem;padding-top:8px;'>{page_num+1} / {total_pages} 페이지</div>", unsafe_allow_html=True)

                # ── 선택된 사용자에게 일괄 이메일 ──
                if show_bulk and (selected_users or sel_all):
                    target_users = [u for u, _ in users_with_stats] if sel_all else selected_users
                    with st.container(border=True):
                        st.markdown(f"**📧 선택된 {len(target_users)}명에게 일괄 이메일 발송**")
                        bc1, bc2 = st.columns([3, 1])
                        with bc1:
                            bulk_s = st.text_input("제목", key=f"bulk_s_{tab_key}",
                                value="[DragonEyes] 업무 현황 안내")
                            bulk_b = st.text_area("내용", key=f"bulk_b_{tab_key}", height=80,
                                value="안녕하세요.\n\n업무 목표 달성을 위해 꾸준한 모니터링 활동 부탁드립니다.\n\n감사합니다.\n[DragonEyes 관리팀]")
                        with bc2:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button(f"📧 {len(target_users)}명 발송",
                                key=f"bulk_send_{tab_key}", type="primary", use_container_width=True):
                                subj = st.session_state.get(f"bulk_s_{tab_key}", "")
                                body = st.session_state.get(f"bulk_b_{tab_key}", "")
                                if subj and body:
                                    for tu in target_users:
                                        send_notification(user["id"], "individual", tu["id"], "email", subj, body)
                                    st.success(f"✅ {len(target_users)}명에게 발송 완료!")
                                else:
                                    st.warning("제목과 내용을 입력해주세요.")

                return [u for u, _ in users_with_stats]  # 정렬된 전체 목록 반환

            # ── 탭1: 전체 현황 ──
            with filter_tab1:
                # 보기 모드 선택
                view_mode = st.radio("보기 모드",
                    ["🏢 업체별 보기", "👥 전체 통합 보기", "📊 업체 요약 비교"],
                    horizontal=True, key="tab1_view_mode")
                st.divider()

                if view_mode == "🏢 업체별 보기":
                    # 업체 필터
                    tenant_names = ["전체 업체"] + [tn["name"] for tn in my_tenants]
                    sel_tenant_filter = st.selectbox("업체 선택", tenant_names, key="tenant_filter_sel")

                    show_tenants = my_tenants if sel_tenant_filter == "전체 업체" else [tn for tn in my_tenants if tn["name"] == sel_tenant_filter]

                    for tn in show_tenants:
                        t_users = get_tenant_users(tn["id"])
                        if not t_users:
                            st.info(f"🏢 **{tn['name']}** — 소속 사용자 없음")
                            continue
                        tn_today = len([r for r in all_reps_ag if r["user_id"] in {u["id"] for u in t_users} and str(r.get("created_at",""))[:10] == today_str])
                        tn_month = len([r for r in all_reps_ag if r["user_id"] in {u["id"] for u in t_users} and str(r.get("created_at",""))[:7] == this_month])
                        tn_avg = int(sum(calc_user_stats(u, all_reps_ag)["monthly_rate"] for u in t_users) / len(t_users)) if t_users else 0
                        avg_color = "#22c55e" if tn_avg >= 100 else "#f59e0b" if tn_avg >= 50 else "#ef4444"
                        below_50_cnt = sum(1 for u in t_users if calc_user_stats(u, all_reps_ag)["monthly_rate"] < 50)

                        with st.expander(
                            f"🏢 **{tn['name']}** | 👥 {len(t_users)}명 | 📅 오늘 {tn_today}건 | 🗓️ 이번달 {tn_month}건 | 📊 평균달성률 {tn_avg}% | ⚠️ 50%미만 {below_50_cnt}명",
                            expanded=(sel_tenant_filter != "전체 업체")
                        ):
                            # 업체 요약 카드
                            tc1, tc2, tc3, tc4 = st.columns(4)
                            tc1.metric("총 사용자", f"{len(t_users)}명")
                            tc2.metric("오늘 보고서", f"{tn_today}건")
                            tc3.metric("이번달 보고서", f"{tn_month}건")
                            tc4.metric("평균 달성률", f"{tn_avg}%")
                            render_user_table(t_users, f"all_{tn['id'][:8]}")

                elif view_mode == "👥 전체 통합 보기":
                    # 모든 업체 사용자 합쳐서 표시
                    all_users_flat = []
                    for tn in my_tenants:
                        for u in get_tenant_users(tn["id"]):
                            u["_tenant_name"] = tn["name"]
                            all_users_flat.append(u)
                    st.caption(f"담당 전체 사용자 {len(all_users_flat)}명")
                    render_user_table(all_users_flat, "all_flat")

                elif view_mode == "📊 업체 요약 비교":
                    # 업체별 요약 테이블
                    st.markdown("### 📊 업체별 성과 비교")
                    st.markdown("""<div style="display:grid;grid-template-columns:2fr 0.8fr 0.8fr 0.8fr 0.8fr 0.8fr 1fr;
                        gap:4px;background:#1e3a5f;color:white;padding:6px 8px;border-radius:6px;
                        font-size:0.75rem;font-weight:700;margin-bottom:4px;">
                        <div>업체명</div><div>사용자</div><div>오늘</div><div>이번달</div>
                        <div>평균달성률</div><div>50%미만</div><div>상태</div>
                    </div>""", unsafe_allow_html=True)

                    tenant_summary = []
                    for tn in my_tenants:
                        t_users = get_tenant_users(tn["id"])
                        if not t_users:
                            continue
                        tn_today = len([r for r in all_reps_ag if r["user_id"] in {u["id"] for u in t_users} and str(r.get("created_at",""))[:10] == today_str])
                        tn_month = len([r for r in all_reps_ag if r["user_id"] in {u["id"] for u in t_users} and str(r.get("created_at",""))[:7] == this_month])
                        rates = [calc_user_stats(u, all_reps_ag)["monthly_rate"] for u in t_users]
                        tn_avg = int(sum(rates)/len(rates)) if rates else 0
                        below50 = sum(1 for r in rates if r < 50)
                        tenant_summary.append((tn, t_users, tn_today, tn_month, tn_avg, below50))

                    # 평균달성률 낮은 순 정렬
                    tenant_summary.sort(key=lambda x: x[4])

                    for tn, t_users, tn_today, tn_month, tn_avg, below50 in tenant_summary:
                        avg_color = "#22c55e" if tn_avg >= 100 else "#f59e0b" if tn_avg >= 50 else "#ef4444"
                        status = "🟢 양호" if tn_avg >= 80 else "🟡 주의" if tn_avg >= 50 else "🔴 위험"
                        rc = st.columns([2, 0.8, 0.8, 0.8, 0.8, 0.8, 1])
                        rc[0].write(f"🏢 **{tn['name']}**")
                        rc[1].write(f"{len(t_users)}명")
                        rc[2].write(f"{tn_today}건")
                        rc[3].write(f"{tn_month}건")
                        rc[4].markdown(f"<span style='color:{avg_color};font-weight:700'>{tn_avg}%</span>", unsafe_allow_html=True)
                        rc[5].write(f"⚠️ {below50}명" if below50 > 0 else "✅ 0명")
                        rc[6].write(status)

                    # 전체 합계
                    st.divider()
                    all_flat2 = []
                    for tn in my_tenants:
                        all_flat2.extend(get_tenant_users(tn["id"]))
                    if all_flat2:
                        total_rates = [calc_user_stats(u, all_reps_ag)["monthly_rate"] for u in all_flat2]
                        total_avg = int(sum(total_rates)/len(total_rates)) if total_rates else 0
                        total_today2 = len([r for r in all_reps_ag if r["user_id"] in {u["id"] for u in all_flat2} and str(r.get("created_at",""))[:10] == today_str])
                        total_month2 = len([r for r in all_reps_ag if r["user_id"] in {u["id"] for u in all_flat2} and str(r.get("created_at",""))[:7] == this_month])
                        total_below = sum(1 for r in total_rates if r < 50)
                        rc = st.columns([2, 0.8, 0.8, 0.8, 0.8, 0.8, 1])
                        rc[0].markdown("**📊 전체 합계**")
                        rc[1].markdown(f"**{len(all_flat2)}명**")
                        rc[2].markdown(f"**{total_today2}건**")
                        rc[3].markdown(f"**{total_month2}건**")
                        rc[4].markdown(f"**{total_avg}%**")
                        rc[5].markdown(f"**{total_below}명**")
                        rc[6].markdown("**—**")

                    # 업체별 일괄 이메일 발송
                    st.divider()
                    with st.container(border=True):
                        st.markdown("**📧 성과 미달 업체 일괄 이메일 발송**")
                        danger_tenants = [(tn, t_users) for tn, t_users, _, _, tn_avg, _ in tenant_summary if tn_avg < 50]
                        if danger_tenants:
                            st.warning(f"⚠️ 달성률 50% 미만 업체: {len(danger_tenants)}개")
                            ds1 = st.text_input("제목", key="danger_subj", value="[DragonEyes] 업무 목표 달성 독려")
                            ds2 = st.text_area("내용", key="danger_body", height=80,
                                value="안녕하세요.\n\n이번달 업무 목표 달성률이 저조합니다.\n배정된 콘텐츠 확인 및 보고서 작성을 부탁드립니다.\n\n감사합니다.\n[DragonEyes 관리팀]")
                            if st.button("📧 50% 미만 업체 전원 발송", type="primary", key="send_danger"):
                                cnt = 0
                                for _, t_users in danger_tenants:
                                    for u in t_users:
                                        send_notification(user["id"], "individual", u["id"], "email",
                                            st.session_state.get("danger_subj",""),
                                            st.session_state.get("danger_body",""))
                                        cnt += 1
                                st.success(f"✅ {cnt}명에게 발송 완료!")
                        else:
                            st.success("🎉 모든 업체가 50% 이상 달성 중입니다!")

            # ── 탭2: 일일 50% 미만 ──
            with filter_tab2:
                st.caption(f"📅 오늘({today_str}) 일일 목표 대비 달성률 50% 미만 사용자")
                below50_users = []
                for tn in my_tenants:
                    for u in get_tenant_users(tn["id"]):
                        stats = calc_user_stats(u, all_reps_ag)
                        if stats["daily_rate"] < 50:
                            u["_tenant_name"] = tn["name"]
                            below50_users.append(u)

                if below50_users:
                    st.warning(f"⚠️ 총 {len(below50_users)}명이 오늘 일일 목표 50% 미만입니다.")
                    render_user_table(below50_users, "below50")

                    # 그룹 이메일 발송
                    st.divider()
                    with st.container(border=True):
                        st.markdown("**📧 이 그룹에 일괄 이메일 발송**")
                        b50_subj = st.text_input("제목", key="b50_subj", value=f"[DragonEyes] {today_str} 업무 독려 안내")
                        b50_body = st.text_area("내용", key="b50_body", height=100,
                            value=f"안녕하세요.\n\n오늘({today_str}) 업무 달성률이 목표의 50%에 미달하고 있습니다.\n배정된 콘텐츠를 확인하고 보고서를 작성해 주시기 바랍니다.\n\n감사합니다.\n[DragonEyes 관리팀]")
                        if st.button("📧 50% 미만 그룹 일괄 발송", type="primary", key="send_b50"):
                            for bu in below50_users:
                                send_notification(user["id"], "individual", bu["id"], "email", b50_subj, b50_body)
                            st.success(f"✅ {len(below50_users)}명에게 이메일 발송 저장 완료!")
                else:
                    st.success("🎉 오늘 모든 사용자가 일일 목표 50% 이상 달성 중입니다!")

            # ── 탭3: 일일 50% 이상 ──
            with filter_tab3:
                st.caption(f"📅 오늘({today_str}) 일일 목표 대비 달성률 50% 이상 사용자")
                above50_users = []
                for tn in my_tenants:
                    for u in get_tenant_users(tn["id"]):
                        stats = calc_user_stats(u, all_reps_ag)
                        if stats["daily_rate"] >= 50:
                            u["_tenant_name"] = tn["name"]
                            above50_users.append(u)

                if above50_users:
                    st.success(f"✅ 총 {len(above50_users)}명이 오늘 일일 목표 50% 이상 달성 중입니다!")
                    render_user_table(above50_users, "above50")

                    # 격려 이메일 발송
                    st.divider()
                    with st.container(border=True):
                        st.markdown("**📧 이 그룹에 격려 이메일 발송**")
                        a50_subj = st.text_input("제목", key="a50_subj", value=f"[DragonEyes] {today_str} 업무 수고 감사 안내")
                        a50_body = st.text_area("내용", key="a50_body", height=100,
                            value=f"안녕하세요.\n\n오늘({today_str}) 업무 목표를 훌륭하게 달성하고 계십니다.\n꾸준한 모니터링 활동에 감사드립니다.\n\n감사합니다.\n[DragonEyes 관리팀]")
                        if st.button("📧 50% 이상 그룹 일괄 발송", type="primary", key="send_a50"):
                            for au in above50_users:
                                send_notification(user["id"], "individual", au["id"], "email", a50_subj, a50_body)
                            st.success(f"✅ {len(above50_users)}명에게 이메일 발송 저장 완료!")
                else:
                    st.info("오늘 아직 50% 이상 달성한 사용자가 없습니다.")

            # ── 탭4: 달성률별 그룹 ──
            with filter_tab4:
                st.caption("월별 목표 달성률 기준으로 그룹을 나눠 일괄 이메일을 발송합니다.")

                # 달성률별 분류
                group_100  = []  # 100% 이상
                group_80   = []  # 80~99%
                group_50   = []  # 50~79%
                group_low  = []  # 50% 미만

                for tn in my_tenants:
                    for u in get_tenant_users(tn["id"]):
                        stats = calc_user_stats(u, all_reps_ag)
                        u["_stats"] = stats
                        u["_tenant_name"] = tn["name"]
                        rt = stats["monthly_rate"]
                        if rt >= 100: group_100.append(u)
                        elif rt >= 80: group_80.append(u)
                        elif rt >= 50: group_50.append(u)
                        else: group_low.append(u)

                # 요약 바 — 클릭 시 해당 그룹으로 스크롤
                if "jump_to_group" not in st.session_state:
                    st.session_state.jump_to_group = None

                g1, g2, g3, g4 = st.columns(4)
                with g1:
                    st.markdown(f"""<div style="background:#f0fdf4;border:2px solid #22c55e;border-radius:10px;
                        padding:12px;text-align:center;cursor:pointer;">
                        <div style="font-size:1.5rem;font-weight:700;color:#16a34a;">{len(group_100)}명</div>
                        <div style="font-size:0.8rem;color:#16a34a;font-weight:600;">🏆 100% 달성</div>
                        <div style="font-size:0.72rem;color:#4ade80;">↑ 목표 완료</div>
                    </div>""", unsafe_allow_html=True)
                    if st.button("🏆 그룹 보기", key="jump_g100", use_container_width=True):
                        st.session_state.jump_to_group = "g100"
                        st.rerun()
                with g2:
                    st.markdown(f"""<div style="background:#eff6ff;border:2px solid #3b82f6;border-radius:10px;
                        padding:12px;text-align:center;cursor:pointer;">
                        <div style="font-size:1.5rem;font-weight:700;color:#2563eb;">{len(group_80)}명</div>
                        <div style="font-size:0.8rem;color:#2563eb;font-weight:600;">📈 80~99%</div>
                        <div style="font-size:0.72rem;color:#60a5fa;">↑ 거의 다됐어요</div>
                    </div>""", unsafe_allow_html=True)
                    if st.button("📈 그룹 보기", key="jump_g80", use_container_width=True):
                        st.session_state.jump_to_group = "g80"
                        st.rerun()
                with g3:
                    st.markdown(f"""<div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:10px;
                        padding:12px;text-align:center;cursor:pointer;">
                        <div style="font-size:1.5rem;font-weight:700;color:#d97706;">{len(group_50)}명</div>
                        <div style="font-size:0.8rem;color:#d97706;font-weight:600;">📊 50~79%</div>
                        <div style="font-size:0.72rem;color:#fbbf24;">↑ 노력 필요</div>
                    </div>""", unsafe_allow_html=True)
                    if st.button("📊 그룹 보기", key="jump_g50", use_container_width=True):
                        st.session_state.jump_to_group = "g50"
                        st.rerun()
                with g4:
                    st.markdown(f"""<div style="background:#fef2f2;border:2px solid #ef4444;border-radius:10px;
                        padding:12px;text-align:center;cursor:pointer;">
                        <div style="font-size:1.5rem;font-weight:700;color:#dc2626;">{len(group_low)}명</div>
                        <div style="font-size:0.8rem;color:#dc2626;font-weight:600;">⚠️ 50% 미만</div>
                        <div style="font-size:0.72rem;color:#f87171;">↑ 즉시 독려 필요</div>
                    </div>""", unsafe_allow_html=True)
                    if st.button("⚠️ 그룹 보기", key="jump_glow", use_container_width=True):
                        st.session_state.jump_to_group = "glow"
                        st.rerun()
                st.divider()

                # 그룹별 표시 + 이메일 발송
                jump = st.session_state.get("jump_to_group")
                for grp_name, grp_users, grp_color, grp_key, default_msg in [
                    ("🏆 100% 달성 그룹", group_100, "#22c55e", "g100",
                     "이번달 목표를 훌륭하게 달성하셨습니다! 수고하셨습니다."),
                    ("📈 80~99% 그룹", group_80, "#3b82f6", "g80",
                     "이번달 목표 달성이 얼마 남지 않았습니다. 조금만 더 힘내주세요!"),
                    ("📊 50~79% 그룹", group_50, "#f59e0b", "g50",
                     "이번달 중간 이상 달성하고 계십니다. 꾸준한 모니터링 활동 부탁드립니다."),
                    ("⚠️ 50% 미만 그룹", group_low, "#ef4444", "glow",
                     "이번달 업무 목표 달성률이 저조합니다. 배정된 콘텐츠를 확인하고 보고서를 작성해 주세요."),
                ]:
                    if not grp_users:
                        continue
                    # 버튼 클릭 시 해당 그룹 자동 펼침
                    is_jumped = (jump == grp_key)
                    if is_jumped:
                        st.session_state.jump_to_group = None  # 한 번만 펼침
                    with st.expander(f"{grp_name} — {len(grp_users)}명",
                        expanded=(grp_key in ["glow","g50"] or is_jumped)):
                        render_user_table(grp_users, grp_key)
                        st.divider()
                        gc1, gc2 = st.columns([3, 1])
                        with gc1:
                            grp_subj = st.text_input("제목", key=f"subj_{grp_key}",
                                value=f"[DragonEyes] 이번달 업무 현황 안내 ({grp_name})")
                            grp_body = st.text_area("내용", key=f"body_{grp_key}", height=80,
                                value=f"안녕하세요.\n\n{default_msg}\n\n감사합니다.\n[DragonEyes 관리팀]")
                        with gc2:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button(f"📧 일괄 발송\n({len(grp_users)}명)", key=f"send_{grp_key}", use_container_width=True, type="primary"):
                                subj_val = st.session_state.get(f"subj_{grp_key}", "")
                                body_val = st.session_state.get(f"body_{grp_key}", "")
                                if subj_val and body_val:
                                    for gu in grp_users:
                                        send_notification(user["id"], "individual", gu["id"], "email", subj_val, body_val)
                                    st.success(f"✅ {len(grp_users)}명에게 발송 완료!")
                                else:
                                    st.warning("제목과 내용을 입력해주세요.")

            # ── 탭5: 캘린더 현황 ──
            with filter_tab5:
                import calendar as cal_mod

                st.markdown("### 📅 업체별 일별 근무자 현황 캘린더")

                # 컨트롤
                cc1, cc2, cc3 = st.columns([2, 2, 4])
                with cc1:
                    # 업체 선택
                    cal_tenant_names = ["전체 업체"] + [tn["name"] for tn in my_tenants]
                    cal_sel_tenant = st.selectbox("업체 선택", cal_tenant_names, key="cal_tenant_sel")
                with cc2:
                    # 연월 선택
                    cal_year = st.selectbox("연도", list(range(2025, 2028)), index=1, key="cal_year")
                    cal_month = st.selectbox("월", list(range(1, 13)), index=today.month-1, key="cal_month")
                with cc3:
                    cal_view = st.radio("보기 방식",
                        ["📅 월간 캘린더", "📊 일별 막대그래프", "📋 일별 상세 테이블"],
                        horizontal=True, key="cal_view_mode")

                # 해당 업체 사용자 목록
                if cal_sel_tenant == "전체 업체":
                    cal_users = []
                    for tn in my_tenants:
                        cal_users.extend(get_tenant_users(tn["id"]))
                else:
                    cal_tenant_obj = next((tn for tn in my_tenants if tn["name"] == cal_sel_tenant), None)
                    cal_users = get_tenant_users(cal_tenant_obj["id"]) if cal_tenant_obj else []

                if not cal_users:
                    st.info("사용자가 없습니다.")
                else:
                    cal_uid_set = {u["id"] for u in cal_users}

                    # 해당 월 보고서 데이터 로드
                    cal_month_str = f"{cal_year}-{str(cal_month).zfill(2)}"
                    cal_reps = [r for r in all_reps_ag
                        if r["user_id"] in cal_uid_set
                        and str(r.get("created_at",""))[:7] == cal_month_str]

                    # 일별 집계
                    days_in_month = cal_mod.monthrange(cal_year, cal_month)[1]
                    daily_counts = {}  # {day: {user_id: count}}
                    for r in cal_reps:
                        day = int(str(r.get("created_at",""))[:10].split("-")[2])
                        uid = r["user_id"]
                        if day not in daily_counts:
                            daily_counts[day] = {}
                        daily_counts[day][uid] = daily_counts[day].get(uid, 0) + 1

                    # ── 보기 방식 1: 월간 캘린더 ──
                    if cal_view == "📅 월간 캘린더":
                        st.markdown(f"#### {cal_year}년 {cal_month}월 — {cal_sel_tenant}")

                        # 요일 헤더
                        week_days = ["월", "화", "수", "목", "금", "토", "일"]
                        cols = st.columns(7)
                        for i, wd in enumerate(week_days):
                            color = "#ef4444" if wd == "일" else "#3b82f6" if wd == "토" else "#1e293b"
                            cols[i].markdown(f"<div style='text-align:center;font-weight:700;color:{color};padding:4px;'>{wd}</div>", unsafe_allow_html=True)

                        # 달력 그리기
                        first_weekday = cal_mod.monthrange(cal_year, cal_month)[0]  # 0=월요일
                        day_num = 1
                        week_cells = []

                        # 첫 주 빈칸
                        for _ in range(first_weekday):
                            week_cells.append(None)

                        for d in range(1, days_in_month + 1):
                            week_cells.append(d)

                        # 7개씩 나눠서 주 단위 출력
                        for week_start in range(0, len(week_cells), 7):
                            week = week_cells[week_start:week_start+7]
                            # 7개 미만이면 None으로 채움
                            while len(week) < 7:
                                week.append(None)

                            cols = st.columns(7)
                            for i, day in enumerate(week):
                                with cols[i]:
                                    if day is None:
                                        st.markdown("<div style='height:70px;'></div>", unsafe_allow_html=True)
                                    else:
                                        day_data = daily_counts.get(day, {})
                                        total_reports = sum(day_data.values())
                                        active_users = len(day_data)
                                        total_users = len(cal_users)

                                        # 오늘 표시
                                        is_today = (day == today.day and cal_month == today.month and cal_year == today.year)
                                        # 주말
                                        is_weekend = (week_start // 7 * 7 + i) % 7 >= 5

                                        # 달성률 색상
                                        if total_reports == 0:
                                            bg = "#f8fafc" if not is_today else "#fef9c3"
                                            text_color = "#94a3b8"
                                        elif active_users >= total_users:
                                            bg = "#dcfce7"
                                            text_color = "#16a34a"
                                        elif active_users >= total_users * 0.5:
                                            bg = "#fef9c3"
                                            text_color = "#d97706"
                                        else:
                                            bg = "#fee2e2"
                                            text_color = "#dc2626"

                                        border = "3px solid #3b82f6" if is_today else "1px solid #e2e8f0"
                                        day_color = "#ef4444" if i == 6 else "#3b82f6" if i == 5 else "#1e293b"

                                        st.markdown(f"""
                                        <div style="background:{bg};border:{border};border-radius:8px;
                                            padding:6px;min-height:70px;cursor:pointer;">
                                            <div style="font-weight:700;color:{day_color};font-size:0.9rem;">{day}</div>
                                            <div style="font-size:0.75rem;color:{text_color};font-weight:600;margin-top:4px;">
                                                {total_reports}건
                                            </div>
                                            <div style="font-size:0.65rem;color:#64748b;">
                                                {active_users}/{total_users}명
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)

                        # 범례
                        st.markdown("""
                        <div style="display:flex;gap:12px;margin-top:8px;font-size:0.78rem;">
                            <span>🟢 전원 활동</span>
                            <span>🟡 50% 이상</span>
                            <span>🔴 50% 미만</span>
                            <span>⬜ 활동 없음</span>
                            <span>🔵 테두리=오늘</span>
                        </div>
                        """, unsafe_allow_html=True)

                        # 날짜 클릭 → 해당 날 상세
                        st.divider()
                        sel_day = st.selectbox("날짜 선택 (상세 보기)",
                            list(range(1, days_in_month+1)),
                            index=min(today.day, days_in_month)-1,
                            format_func=lambda x: f"{cal_year}년 {cal_month}월 {x}일",
                            key="cal_detail_day")

                        sel_day_str = f"{cal_year}-{str(cal_month).zfill(2)}-{str(sel_day).zfill(2)}"
                        st.markdown(f"#### 📋 {cal_year}년 {cal_month}월 {sel_day}일 상세")

                        day_detail = daily_counts.get(sel_day, {})
                        dh1, dh2, dh3 = st.columns(3)
                        dh1.metric("보고서 합계", f"{sum(day_detail.values())}건")
                        dh2.metric("활동 사용자", f"{len(day_detail)}명")
                        dh3.metric("미활동", f"{len(cal_users)-len(day_detail)}명")

                        # 사용자별 상세
                        umap_cal = {u["id"]: u for u in cal_users}
                        for u in cal_users:
                            cnt = day_detail.get(u["id"], 0)
                            icon = "✅" if cnt > 0 else "❌"
                            color = "#22c55e" if cnt > 0 else "#ef4444"
                            dc1, dc2, dc3 = st.columns([3, 1, 1])
                            dc1.write(f"{icon} **{u['name']}**")
                            dc2.markdown(f"<span style='color:{color};font-weight:700'>{cnt}건</span>", unsafe_allow_html=True)
                            with dc3:
                                if cnt == 0:
                                    if st.button("📧", key=f"cal_notif_{u['id']}_{sel_day}", help="업무 독려"):
                                        body = f"안녕하세요 {u.get('name','')}님.\n\n{sel_day_str} 업무 보고서가 아직 없습니다.\n확인 부탁드립니다.\n\n[DragonEyes 관리팀]"
                                        send_notification(user["id"], "individual", u["id"], "email",
                                            f"[DragonEyes] {sel_day_str} 업무 현황 확인 요청", body)
                                        st.success("발송!")

                        # 미활동자 일괄 독려
                        inactive = [u for u in cal_users if u["id"] not in day_detail]
                        if inactive:
                            st.divider()
                            if st.button(f"📧 {sel_day}일 미활동 {len(inactive)}명 일괄 독려", type="primary", key="cal_bulk_inactive"):
                                for u in inactive:
                                    body = f"안녕하세요 {u.get('name','')}님.\n\n{sel_day_str} 업무 보고서가 없습니다.\n확인 부탁드립니다.\n\n[DragonEyes 관리팀]"
                                    send_notification(user["id"], "individual", u["id"], "email",
                                        f"[DragonEyes] {sel_day_str} 업무 현황 확인 요청", body)
                                st.success(f"✅ {len(inactive)}명에게 독려 발송 완료!")

                    # ── 보기 방식 2: 막대그래프 ──
                    elif cal_view == "📊 일별 막대그래프":
                        import pandas as pd
                        st.markdown(f"#### {cal_year}년 {cal_month}월 일별 보고서 현황 — {cal_sel_tenant}")

                        chart_data = []
                        for d in range(1, days_in_month+1):
                            day_data = daily_counts.get(d, {})
                            chart_data.append({
                                "날짜": f"{d}일",
                                "보고서수": sum(day_data.values()),
                                "활동인원": len(day_data),
                            })
                        df_chart = pd.DataFrame(chart_data)
                        st.bar_chart(df_chart.set_index("날짜")["보고서수"])

                        st.divider()
                        # 주간 합계
                        st.markdown("**📊 주간 합계**")
                        for week_num in range(0, days_in_month, 7):
                            week_days_range = list(range(week_num+1, min(week_num+8, days_in_month+1)))
                            week_total = sum(sum(daily_counts.get(d, {}).values()) for d in week_days_range)
                            week_active = sum(len(daily_counts.get(d, {})) for d in week_days_range)
                            st.markdown(f"**{week_days_range[0]}~{week_days_range[-1]}일**: 보고서 {week_total}건 | 활동 연인원 {week_active}명")

                    # ── 보기 방식 3: 일별 상세 테이블 ──
                    elif cal_view == "📋 일별 상세 테이블":
                        import pandas as pd
                        st.markdown(f"#### {cal_year}년 {cal_month}월 일별 사용자 현황 — {cal_sel_tenant}")

                        # 사용자 × 날짜 매트릭스
                        matrix_data = {}
                        for u in cal_users:
                            row = {"이름": u["name"]}
                            monthly_total = 0
                            for d in range(1, days_in_month+1):
                                cnt = daily_counts.get(d, {}).get(u["id"], 0)
                                row[f"{d}일"] = cnt if cnt > 0 else ""
                                monthly_total += cnt
                            row["합계"] = monthly_total
                            row["달성률"] = f"{min(int(monthly_total/u.get('monthly_target',10)*100),100)}%"
                            matrix_data[u["name"]] = row

                        df_matrix = pd.DataFrame(list(matrix_data.values()))

                        # 스타일링
                        st.dataframe(df_matrix.set_index("이름"), use_container_width=True, height=400)

                        # CSV 다운로드
                        csv_cal = df_matrix.to_csv(index=False, encoding="utf-8-sig")
                        st.download_button(
                            f"📥 {cal_year}년 {cal_month}월 현황 CSV 다운로드",
                            data=csv_cal.encode("utf-8-sig"),
                            file_name=f"업무현황_{cal_sel_tenant}_{cal_year}{str(cal_month).zfill(2)}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

            # ── 빠른 개인 알림 팝업 ──
            if st.session_state.get("quick_notif_show") and st.session_state.get("quick_notif_user"):
                qnu = st.session_state.quick_notif_user
                with st.container(border=True):
                    st.markdown(f"**📧 {qnu['name']}님에게 이메일 발송**")
                    qn_subj = st.text_input("제목", key="qn_subj",
                        value=f"[DragonEyes] {qnu['name']}님 업무 현황 안내")
                    qn_body = st.text_area("내용", key="qn_body", height=80,
                        value=f"안녕하세요 {qnu['name']}님.\n\n업무 현황 관련 안내 드립니다.\n\n감사합니다.\n[DragonEyes 관리팀]")
                    qnc1, qnc2 = st.columns(2)
                    with qnc1:
                        if st.button("📧 발송", type="primary", key="qn_send"):
                            send_notification(user["id"], "individual", qnu["id"], "email",
                                st.session_state.get("qn_subj",""), st.session_state.get("qn_body",""))
                            st.success(f"✅ {qnu['name']}님에게 발송 저장됨!")
                            st.session_state.quick_notif_show = False
                            st.rerun()
                    with qnc2:
                        if st.button("✖ 닫기", key="qn_close"):
                            st.session_state.quick_notif_show = False
                            st.rerun()

    elif page == "work_page":
        lang = st.session_state.get("lang", "ko")
        token_info = can_use_dragon(user["id"])
        all_my = supabase.table("reports").select("id,severity,created_at").eq("user_id", user["id"]).execute()
        df_my = pd.DataFrame(all_my.data) if all_my.data else pd.DataFrame()
        this_month = date.today().strftime("%Y-%m")
        month_cnt = len(df_my[df_my["created_at"].str[:7] == this_month]) if not df_my.empty else 0
        target = user.get("monthly_target", 10)
        rate = min(int(month_cnt / target * 100), 100) if target > 0 else 0
        history_cnt = len(st.session_state.search_results) + len(st.session_state.recommend_results)
        _role = get_user_role(user)

        # 달성률 카드
        st.markdown(f"""<div style="display:flex;gap:6px;margin:10px 0 6px 0;">
            <div style="flex:1;background:linear-gradient(135deg,#0ea5e9,#06b6d4);border-radius:8px;padding:5px 8px;text-align:center;"><div style="font-size:0.62rem;color:#e0f7ff;">{t("month_report")}</div><div style="font-size:1rem;font-weight:700;color:#fff;">{month_cnt}{t("unit_reports")}</div><div style="font-size:0.58rem;color:#bae6fd;">{t("goal").format(target)}</div></div>
            <div style="flex:1;background:linear-gradient(135deg,#10b981,#34d399);border-radius:8px;padding:5px 8px;text-align:center;"><div style="font-size:0.62rem;color:#d1fae5;">{t("achievement")}</div><div style="font-size:1rem;font-weight:700;color:#fff;">{rate}%</div><div style="font-size:0.58rem;color:#a7f3d0;">{t("goal").format(target)}</div></div>
            <div style="flex:1;background:linear-gradient(135deg,#f59e0b,#fbbf24);border-radius:8px;padding:5px 8px;text-align:center;"><div style="font-size:0.62rem;color:#fef3c7;">{t("dragon_token")}</div><div style="font-size:1rem;font-weight:700;color:#fff;">{token_info["monthly_remaining"]}{t("unit_times")}</div><div style="font-size:0.58rem;color:#fde68a;">{t("token_remain").format(token_info["monthly_remaining"])[:3]}</div></div>
            <div style="flex:1;background:linear-gradient(135deg,#ec4899,#f472b6);border-radius:8px;padding:5px 8px;text-align:center;"><div style="font-size:0.62rem;color:#fce7f3;">{t("tab_history")}</div><div style="font-size:1rem;font-weight:700;color:#fff;">{history_cnt}{t("unit_reports")}</div><div style="font-size:0.58rem;color:#fbcfe8;">{t("pending_list")}</div></div>
        </div><div style="background:#334155;border-radius:4px;height:4px;margin:0 0 6px 0;"><div style="background:{"#22c55e" if rate>=100 else "#f59e0b" if rate>=50 else "#e94560"};width:{rate}%;height:4px;border-radius:4px;"></div></div>""", unsafe_allow_html=True)

        # 페이지네이션 미리 계산
        PAGE_SIZE = 10
        if "work_page_num" not in st.session_state:
            st.session_state.work_page_num = 0
        assigned_all = supabase.table("analyzed_urls").select("*").eq("assigned_to",user["id"]).eq("reported",False).order("analyzed_at",desc=True).execute()
        assigned_data = assigned_all.data if assigned_all.data else []
        total = len(assigned_data)
        total_pages = max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
        page_num = st.session_state.work_page_num
        paged = assigned_data[page_num*PAGE_SIZE:(page_num+1)*PAGE_SIZE]

        # 타이틀 행 (HTML)
        st.markdown(f"""<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:0 0 6px 0;">
            <div style="font-size:1rem;font-weight:700;color:#1e293b;">📊 팀별 업무 현황</div>
            <div style="font-size:1rem;font-weight:700;color:#1e293b;">⚠️ 내게 배정된 미작성 목록 <span style="font-size:0.72rem;font-weight:400;color:#64748b;">총 {total}건 | {page_num+1}/{total_pages}p</span></div>
        </div>""", unsafe_allow_html=True)

        # ── 팝업 (컬럼 밖 전체 너비) ──
        if st.session_state.get("work_popup_id"):
            popup_d = next((x for x in assigned_data if x["id"] == st.session_state.work_popup_id), None)
            if popup_d:
                with st.container(border=True):
                    pc_title, pc_close = st.columns([8, 1])
                    with pc_title:
                        st.markdown(f"**{popup_d.get('title','')[:100]}**")
                    with pc_close:
                        if st.button(t("popup_close"), key="popup_close_btn", use_container_width=True):
                            st.session_state.work_popup_id = None; st.rerun()
                    url = popup_d.get("url","")
                    pv1, pv2, pv3 = st.columns([1, 3, 1])
                    with pv2:
                        if "youtube.com" in url or "youtu.be" in url:
                            st.video(url)
                        else:
                            st.markdown(f"[🔗 링크 열기]({url})")
                    if st.button(t("popup_write"), type="primary", use_container_width=True, key="popup_write_btn"):
                        st.session_state.work_popup_id = None
                        open_report_form(url,"",1,t("write_report_safe"),"YouTube",from_tab=4)
                        st.session_state.current_page = "report_form"; st.rerun()

        work_left, work_right = st.columns([1, 1])

        # ── 왼쪽 ──
        with work_left:
            with st.container(height=420):
                if _role in ("superadmin","group_leader","group_leader_2","group_leader_3","group_leader_4","director","director_2","director_3","director_4"):
                    try:
                        all_teams_dash = supabase.table("teams").select("*").execute().data or []
                        all_users_dash = supabase.table("users").select("*").execute().data or []
                        all_reports_dash = supabase.table("reports").select("user_id,created_at").execute().data or []
                        umap_dash = {u["id"]: u for u in all_users_dash}
                        if all_teams_dash:
                            for team in all_teams_dash:
                                members = [u for u in all_users_dash if u.get("team_id") == team["id"]]
                                leader = umap_dash.get(team.get("leader_id",""), {})
                                with st.expander(f"🏢 **{team['name']}** | 팀장: {leader.get('name','미지정')} | {len(members)}명", expanded=True):
                                    if members:
                                        ch = st.columns([2.5,1,1,1,1])
                                        ch[0].markdown(t("col_name")); ch[1].markdown(t("col_month")); ch[2].markdown(t("col_goal")); ch[3].markdown(t("col_rate")); ch[4].markdown(t("col_total"))
                                        for m in members:
                                            mr = [r for r in all_reports_dash if r["user_id"]==m["id"]]
                                            mm = len([r for r in mr if r["created_at"][:7]==this_month])
                                            mt = len(mr); mtgt = m.get("monthly_target",10)
                                            mrt = min(int(mm/mtgt*100),100) if mtgt>0 else 0
                                            rc = "#22c55e" if mrt>=100 else ("#f59e0b" if mrt>=50 else "#ef4444")
                                            ri = role_icon(m.get("role_v2","user"))
                                            cv = st.columns([2.5,1,1,1,1])
                                            cv[0].write(f"{ri} {m['name']}"); cv[1].write(f"{mm}건"); cv[2].write(f"{mtgt}건")
                                            cv[3].markdown(f"<span style='color:{rc};font-weight:700'>{mrt}%</span>", unsafe_allow_html=True); cv[4].write(f"{mt}건")
                                    else:
                                        st.caption(t("work_no_member"))
                        else:
                            st.info(t("work_no_teams"))
                        no_team = [u for u in all_users_dash if not u.get("team_id")]
                        if no_team:
                            with st.expander(f"👥 **팀 미배정** | {len(no_team)}명"):
                                for u in no_team:
                                    ur = [r for r in all_reports_dash if r["user_id"]==u["id"]]
                                    um = len([r for r in ur if r["created_at"][:7]==this_month])
                                    st.caption(f"{role_icon(u.get('role_v2','user'))} {u['name']} | {t('monthly_this')} {um}{t('unit_reports')}")
                    except Exception as e:
                        st.warning(t("team_fail_msg").format(str(e)))
                elif _role == "team_leader":
                    try:
                        my_team_id = user.get("team_id")
                        if my_team_id:
                            tm = supabase.table("users").select("*").eq("team_id",my_team_id).execute().data or []
                            ar = supabase.table("reports").select("user_id,created_at").execute().data or []
                            if tm:
                                ch = st.columns([2.5,1,1,1,1])
                                ch[0].markdown(t("col_name")); ch[1].markdown(t("col_month")); ch[2].markdown(t("col_goal")); ch[3].markdown(t("col_rate")); ch[4].markdown(t("col_total"))
                                for m in tm:
                                    mr = [r for r in ar if r["user_id"]==m["id"]]
                                    mm = len([r for r in mr if r["created_at"][:7]==this_month])
                                    mt = len(mr); mtgt = m.get("monthly_target",10)
                                    mrt = min(int(mm/mtgt*100),100) if mtgt>0 else 0
                                    rc = "#22c55e" if mrt>=100 else ("#f59e0b" if mrt>=50 else "#ef4444")
                                    is_me = "⭐ " if m["id"]==user["id"] else ""
                                    cv = st.columns([2.5,1,1,1,1])
                                    cv[0].write(f"{is_me}{m['name']}"); cv[1].write(f"{mm}건"); cv[2].write(f"{mtgt}건")
                                    cv[3].markdown(f"<span style='color:{rc};font-weight:700'>{mrt}%</span>", unsafe_allow_html=True); cv[4].write(f"{mt}건")
                            else:
                                st.info(t("work_no_members"))
                        else:
                            st.info(t("work_no_assigned"))
                    except Exception as e:
                        st.warning(t("team_fail_msg").format(str(e)))
                else:
                    st.info(t("work_no_team"))

        # ── 오른쪽 ──
        with work_right:
            with st.container(height=360):
                if not paged:
                    st.info(t("work_no_pending"))
                for d in paged:
                    dc1, dc2, dc3 = st.columns([5, 1, 1])
                    with dc1:
                        st.markdown(f"<div style='font-size:0.85rem;font-weight:600;color:#0f172a;margin:0;line-height:1.2;'>{d.get('title','(제목없음)')[:60]}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size:0.7rem;color:#475569;margin:0;'>{search_type_label(d.get('search_type',''))} | {str(d.get('analyzed_at',''))[:10]}</div>", unsafe_allow_html=True)
                    with dc2:
                        if st.button("🔍", key=f"work_view_{d['id']}", help=t("work_preview")):
                            st.session_state.work_popup_id = d["id"]; st.rerun()
                    with dc3:
                        if st.button("📋", key=f"work_rep_{d['id']}", help=t("write_report_help")):
                            open_report_form(d["url"],"",1,t("write_report_safe"),"YouTube",from_tab=4)
                            st.session_state.current_page = "report_form"; st.rerun()
                    st.markdown("<hr style='margin:0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

            pn1, pn2, pn3 = st.columns([1,2,1])
            with pn1:
                if st.button(t("work_prev_btn"), disabled=page_num==0, use_container_width=True, key="work_prev"):
                    st.session_state.work_page_num -= 1; st.rerun()
            with pn2:
                st.markdown(f"<div style='text-align:center;padding-top:8px;color:#94a3b8;font-size:0.85rem;'>{page_num+1} / {total_pages}</div>", unsafe_allow_html=True)
            with pn3:
                if st.button(t("work_next_btn"), disabled=page_num>=total_pages-1, use_container_width=True, key="work_next"):
                    st.session_state.work_page_num += 1; st.rerun()
            st.divider()
            st.markdown('<div style="font-size:0.82rem;font-weight:600;color:#94a3b8;margin-bottom:4px;">🚀 바로가기</div>', unsafe_allow_html=True)
            if st.button(t("work_dragon_btn"), use_container_width=True, type="primary", key="work_dragon_btn"):
                st.session_state.current_page = "home"; st.session_state.active_tab = 3; st.rerun()
            wg1, wg2, wg3 = st.columns(3)
            with wg1:
                if st.button(t("tab_text"), use_container_width=True, key="work_text_btn"):
                    st.session_state.current_page = "home"; st.rerun()
            with wg2:
                if st.button(t("tab_youtube"), use_container_width=True, key="work_yt_btn"):
                    st.session_state.current_page = "home"; st.rerun()
            with wg3:
                if st.button(t("tab_reports"), use_container_width=True, key="work_rep_btn"):
                    st.session_state.current_page = "home"; st.rerun()

    # ══════════════════════════════
    # 👤 사용자 정보 페이지
    # ══════════════════════════════
    elif page == "user_profile":
        import io
        col_back, col_title = st.columns([1, 5])
        with col_back:
            if st.button(t("home_back")):
                go_home(); st.rerun()
        with col_title:
            st.subheader(t("profile_title"))

        st.divider()

        # ── 내 정보 조회/수정 ──
        with st.container(border=True):
            st.markdown("### " + t("profile_my_info"))
            pc1, pc2 = st.columns(2)
            with pc1:
                st.text_input(t("profile_name"), value=user.get("name",""), disabled=True)
                st.text_input(t("profile_email"), value=user.get("email",""), disabled=True)
                st.text_input(t("profile_team"), value=user.get("team_id",t("unassigned_label")), disabled=True)
                st.text_input(t("profile_role"), value=role_label(user.get("role_v2","user")), disabled=True)
            with pc2:
                new_phone = st.text_input("📱 연락처 (휴대폰)", value=user.get("phone",""), placeholder="010-0000-0000")
                new_birth = st.text_input("🎂 생년월일", value=user.get("birthdate",""), placeholder="1990-01-01")
                new_addr = st.text_input(t("profile_addr"), value=user.get("address",""), placeholder=t("profile_addr_ph"))
                new_emergency = st.text_input(t("profile_emergency"), value=user.get("emergency_contact",""), placeholder=t("profile_emergency_ph"))

            if st.button(t("profile_save"), type="primary", use_container_width=True):
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
                    st.success(t("profile_saved"))
                    st.rerun()
                except Exception as e:
                    st.error(t("save_error_msg").format(str(e)))

        st.divider()

        # ── 비밀번호 변경 ──
        with st.container(border=True):
            st.markdown("### 🔐 비밀번호 변경")
            pw1 = st.text_input(t("profile_pw_new"), type="password", key="pw_new")
            pw2 = st.text_input(t("profile_pw_confirm"), type="password", key="pw_confirm")
            if st.button(t("profile_pw"), use_container_width=True):
                if not pw1:
                    st.warning(t("profile_pw_empty"))
                elif pw1 != pw2:
                    st.error(t("profile_pw_mismatch"))
                elif len(pw1) < 6:
                    st.warning(t("profile_pw_short"))
                else:
                    try:
                        supabase.auth.update_user({"password": pw1})
                        st.success(t("profile_pw_ok"))
                    except Exception as e:
                        st.error(t("change_error_msg").format(str(e)))

        st.divider()

        # ── 시스템관리자에게 연락하기 ──
        with st.container(border=True):
            st.markdown("### 📩 시스템관리자에게 연락하기")
            st.caption("수신: kingcas7@gmail.com (DragonEyes 시스템 관리자)")
            contact_subject = st.text_input(t("profile_subject"), placeholder=t("profile_subject_ph"))
            contact_body = st.text_area(t("profile_body"), height=120, placeholder=t("profile_body_ph"))
            if st.button("📩 시스템관리자에게 전송", type="primary", use_container_width=True):
                if contact_subject and contact_body:
                    try:
                        # Resend로 실제 이메일 발송
                        if RESEND_API_KEY:
                            try:
                                resend.api_key = RESEND_API_KEY
                                resend.Emails.send({
                                    "from": "AI agent_dragoneyes <dragoneyes@dragoneyes.co.kr>",
                                    "to": ["kingcas7@gmail.com"],
                                    "subject": f"[DragonEyes 문의] {contact_subject}",
                                    "html": f"<p><b>발신:</b> {user.get('name','')} ({user.get('email','')})</p><p><b>내용:</b></p><pre>{contact_body}</pre>",
                                })
                            except Exception as e:
                                # v2026.04.26 — 에러 로깅 추가
                                st.warning(f"⚠️ 이메일 발송 실패: {str(e)[:200]}")
                        supabase.table("hq_messages").insert({
                            "from_user_id": user["id"],
                            "from_name": user["name"],
                            "from_email": user.get("email",""),
                            "subject": contact_subject,
                            "body": contact_body,
                            "recipient": "kingcas7@gmail.com",
                        }).execute()
                        st.success("✅ 시스템관리자에게 전송됐습니다!")
                    except Exception as e:
                        st.error(t("send_error_msg").format(str(e)))
                else:
                    st.warning(t("profile_subject_body_empty"))

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
                            t("profile_name"): u.get("name",""),
                            "이메일": u.get("email",""),
                            t("profile_role"): role_label(u.get("role_v2","user")),
                            "소속팀": team_map.get(u.get("team_id",""), t("unassigned_label")),
                            "연락처": u.get("phone",""),
                            "생년월일": u.get("birthdate",""),
                            "주소": u.get("address",""),
                            "비상연락처": u.get("emergency_contact",""),
                            "정보수정일": str(u.get("profile_updated_at",""))[:10],
                        })
                    df_prof = pd.DataFrame(preview_data)
                    st.dataframe(df_prof, use_container_width=True)

                    # CSV 다운로드 (openpyxl 불필요)
                    csv_data = df_prof.to_csv(index=False, encoding="utf-8-sig")
                    st.download_button(
                        label=t("profile_staff_csv"),
                        data=csv_data.encode("utf-8-sig"),
                        file_name=f"DragonEyes_직원정보_{date.today().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        type="primary",
                    )
                except Exception as e:
                    st.error(t("staff_error_msg").format(str(e)))

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
            da1, da2 = st.columns([4, 2])
            with da1:
                st.markdown(f'''
                <div style="padding:2px 0 0 0; line-height:1.2;">
                    <span style="font-size:1.4rem; font-weight:700; color:#1d4ed8;">🐲 {t("dragon_monitoring")}</span>
                    <span style="font-size:0.95rem; color:#60a5fa; margin-left:8px;">✨ {t("chat_caption")[:20]}...</span>
                </div>
                ''', unsafe_allow_html=True)
            with da2:
                if st.button(t("dragon_fs_btn"), key="dragon_fs_btn", use_container_width=True):
                    go_to("dragon_chat"); st.rerun()

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
                            <span style="background:#e94560; color:white; border-radius:4px; padding:1px 5px; font-size:0.65rem; margin-left:4px;">{t("ann_unread")}</span>
                        </div>
                        """, unsafe_allow_html=True)
            except:
                pass

            chat_box = st.container(height=340)
            with chat_box:
                if not st.session_state.chat_history:
                    st.caption("💡 예: '이 댓글이 그루밍 패턴인지 분석해줘'")
                    st.caption(t("chat_example_short"))
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
                if reason == "daily": st.warning(t("chat_limit_daily").format(CHAT_DAILY_LIMIT))
                elif reason == "weekly": st.warning(t("chat_limit_weekly").format(CHAT_WEEKLY_LIMIT))
                elif reason == "monthly": st.warning(t("monthly_limit_short"))

            ic1, ic2 = st.columns([5, 1])
            with ic1:
                home_input = st.chat_input(
                    t("chat_input_ph") if chat_info["ok"] else t("chat_disabled"),
                    max_chars=300, disabled=not chat_info["ok"], key="home_chat_input"
                )
            with ic2:
                if st.button("🗑️", help=t("chat_clear"), key="clear_chat_home"):
                    st.session_state.chat_history = []; st.rerun()

            if home_input and chat_info["ok"]:
                st.session_state.chat_history.append({"role": "user", "content": home_input})
                with st.spinner("🐲 " + t("dragon_caption")[:10] + "..."):
                    try:
                        api_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history[:-1]]
                        response = chat_with_ai(api_history, home_input, lang)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        supabase.table("chat_logs").insert({"user_id": user["id"], "message": home_input, "response": response, "tokens_used": 1}).execute()
                        use_chat_token(user["id"])
                        st.rerun()
                    except Exception as e:
                        st.session_state.chat_history.pop()
                        st.error(t("error_msg").format(str(e)))

        # ── 오른쪽: 통계 (상단) + 모니터링 버튼 (하단) ──
        with right_col:

            st.markdown(f'<div style="font-size:0.82rem; font-weight:600; color:#94a3b8; margin:0 0 4px 0;">📊 {t("admin_team")[:5]}</div>', unsafe_allow_html=True)

            # ① 통계 카드
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
                    <div style="flex:1; background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:10px 14px;">
                        <div style="font-size:0.7rem; color:#3b82f6; margin-bottom:2px; font-weight:600;">{t("month_report")}</div>
                        <div style="font-size:1.5rem; font-weight:700; color:#1d4ed8; line-height:1.1;">{month_cnt_h}건</div>
                        <div style="font-size:0.65rem; color:#64748b;">↑ {t("goal").format(target_h)}</div>
                    </div>
                    <div style="flex:1; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:10px 14px;">
                        <div style="font-size:0.7rem; color:#16a34a; margin-bottom:2px; font-weight:600;">{t("achievement")}</div>
                        <div style="font-size:1.5rem; font-weight:700; color:{'#16a34a' if rate_h>=100 else '#d97706' if rate_h>=50 else '#dc2626'}; line-height:1.1;">{rate_h}%</div>
                        <div style="font-size:0.65rem; color:#64748b;">{t("goal").format(target_h)[:6]}</div>
                    </div>
                    <div style="flex:1; background:#faf5ff; border:1px solid #e9d5ff; border-radius:8px; padding:10px 14px;">
                        <div style="font-size:0.7rem; color:#7c3aed; margin-bottom:2px; font-weight:600;">{t("dragon_token")}</div>
                        <div style="font-size:1.5rem; font-weight:700; color:#7c3aed; line-height:1.1;">{token_info_h['monthly_remaining']}회</div>
                        <div style="font-size:0.65rem; color:#64748b;">{t("token_remain").format("")}</div>
                    </div>
                </div>
                <div style="background:#e2e8f0; border-radius:4px; height:6px; margin:0 8px 8px 16px;">
                    <div style="background:{'#16a34a' if rate_h>=100 else '#d97706' if rate_h>=50 else '#dc2626'}; width:{rate_h}%; height:6px; border-radius:4px;"></div>
                </div>
                """, unsafe_allow_html=True)
            except:
                pass

            # ② 위젯 공간 (중간)
            st.markdown(f"""
            <div style="
                border: 2px dashed #334155;
                border-radius: 10px;
                padding: 28px 16px;
                text-align: center;
                color: #475569;
                font-size: 0.82rem;
                margin-bottom: 10px;
            ">{t("widget_placeholder")}</div>
            """, unsafe_allow_html=True)

            # ③ 모니터링 버튼 (하단)
            st.markdown('<div style="font-size:0.82rem; font-weight:600; color:#94a3b8; margin-bottom:4px;">🐉 모니터링</div>', unsafe_allow_html=True)
            if st.button(t("work_dragon_btn"), use_container_width=True, type="primary", key="home_dragon_btn"):
                st.session_state.current_page = "home"
                st.session_state.active_tab = 3
                st.rerun()
            qa1, qa2, qa3 = st.columns(3)
            with qa1:
                if st.button(t("home_text_btn"), use_container_width=True, key="home_text_btn"):
                    st.session_state.current_page = "home"; st.rerun()
            with qa2:
                if st.button(t("home_yt_btn"), use_container_width=True, key="home_yt_btn"):
                    st.session_state.current_page = "home"; st.rerun()
            with qa3:
                if st.button(t("home_rep_btn"), use_container_width=True, key="home_rep_btn"):
                    st.session_state.current_page = "home"; st.rerun()

        # ── 하단 중앙 문구 ──
        st.markdown(f"""
        <div style="
            text-align: center;
            padding: 18px 0 6px 0;
            color: #475569;
            font-size: 0.88rem;
            letter-spacing: 0.04em;
        ">
            🐉 {t("home_footer")}
        </div>
        """, unsafe_allow_html=True)

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
                st.metric(t("today"), f"{chat_info.get('today_used',0)}/{CHAT_DAILY_LIMIT}턴")
            with chat_header3:
                st.metric(t("this_week"), f"{chat_info.get('week_used',0)}/{CHAT_WEEKLY_LIMIT}턴")
            with chat_header4:
                st.metric(t("this_month_label"), f"{chat_info.get('monthly_used',0)}/{chat_info.get('monthly_limit', CHAT_MONTHLY_LIMIT)}턴")

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
                st.caption(t("chat_example"))

            if not chat_info["ok"]:
                reason = chat_info.get("reason")
                if reason == "weekend":
                    st.warning("😊 오늘은 주말입니다. AI 채팅은 평일(월~금)에만 사용 가능합니다.")
                elif reason == "daily":
                    st.warning(f"📌 오늘 한도({CHAT_DAILY_LIMIT}턴) 도달. 내일 다시 사용 가능합니다.")
                elif reason == "weekly":
                    st.warning(f"📌 이번 주 한도({CHAT_WEEKLY_LIMIT}턴) 도달. 다음 주 월요일에 재시작됩니다.")
                elif reason == "monthly":
                    st.warning(t("monthly_limit_warn"))

            ic1, ic2 = st.columns([6, 1])
            with ic1:
                user_input = st.chat_input(
                    t("chat_input_ph") if chat_info["ok"] else t("chat_disabled"),
                    max_chars=300,
                    disabled=not chat_info["ok"],
                    key="main_chat_input"
                )
            with ic2:
                if st.button("🗑️", help=t("chat_clear"), key="clear_chat_top"):
                    st.session_state.chat_history = []; st.rerun()

            if user_input and chat_info["ok"]:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                with st.spinner("🐲 " + t("dragon_caption")[:10] + "..."):
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
                        st.error(t("error_msg").format(str(e)))

        st.divider()

        active_tab_idx = st.session_state.get("active_tab", 0)

        tab_defs = [
            ("dragon",  t("tab_dragon")),
            ("youtube", t("tab_youtube")),
            ("keyword", t("tab_keyword")),
            ("naver",   "🟢 네이버 탐색"),
            ("discord", "💬 디스코드 탐색"),
            ("history", t("tab_history")),
            ("reports", t("tab_reports")),
            ("stats",   t("tab_stats")),
            ("notice",  "📢 공지사항"),
            ("chat",    "🐲 드래곤파더"),
            ("text",    t("tab_text")),
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
        tab_discord = tab_map["discord"]
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
                            st.success(t("video_title").format(title))
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
                            st.caption(t("skipped_cnt").format(skipped))
                        if not videos:
                            st.warning(t("no_new_video")); st.stop()
                        st.info(t("new_video_cnt").format(len(videos)))
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
                        st.success(t("analyze_done").format(len(results)))
                    except Exception as e:
                        st.error(t("error_msg").format(str(e)))
                else:
                    st.warning(t("enter_keyword"))

            if st.session_state.search_results:
                results_to_show = list(st.session_state.search_results)
                sc1, sc2 = st.columns([3, 1])
                with sc1:
                    st.subheader(t("search_result_cnt").format(len(results_to_show)))
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
                            if st.button(t("write_report_btn"), key=f"sr_{r['id']}"):
                                open_report_form(r["url"],r["analysis"],r["severity"],r["category"],"YouTube",from_tab=2); st.rerun()
                if st.button(t("kw_clear")):
                    st.session_state.search_results = []; st.rerun()

        # ── 드래곤아이즈 추천 ──
        with tab4:
            st.subheader(t("dragon_title"))
            st.caption("AI가 플랫폼별 위험 키워드를 자동 생성하고 유튜브를 탐색합니다. 이미 분석한 영상은 자동 제외됩니다.")

            token_info = can_use_dragon(user["id"])
            col_t1, col_t2, col_t3 = st.columns(3)
            col_t1.metric(t("dragon_used"), f"{token_info['used']}/{token_info['monthly_limit']}회")
            col_t2.metric(t("dragon_today"), f"{token_info['today_used']}/{token_info['daily_limit']}회")
            col_t3.metric(t("dragon_remain"), f"{token_info['monthly_remaining']}회")

            if not token_info["ok"]:
                if token_info["monthly_remaining"] <= 0:
                    st.warning(t("dragon_monthly_warn"))
                else:
                    st.warning(t("dragon_daily_warn").format(DAILY_DRAGON_LIMIT))

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
                        st.success(t("kw_gen_done").format(len(keywords)))
                        st.write("🔑 " + " | ".join(keywords))
                    else:
                        st.error(t("kw_gen_fail")); st.stop()

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
                    st.error(t("error_msg").format(str(e)))

            if st.session_state.recommend_results:
                results = list(st.session_state.recommend_results)
                rc1, rc2 = st.columns([3,1])
                with rc1:
                    st.subheader(t("recommend_result_cnt").format(len(results)))
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
                                if st.button(t("write_report_btn"), key=f"rec_{r['id']}"):
                                    open_report_form(r["url"],r["analysis"],r["severity"],r["category"],"YouTube",from_tab=3); st.rerun()
                with st.expander(t("safe_count").format(len(safe))):
                    for r in safe:
                        st.caption(f"✅ [{r.get('keyword','')}] {r['title']}")
                if st.button(t("dragon_clear")):
                    st.session_state.recommend_results = []; st.rerun()

        # ── 디스코드 탐색 ──
        with tab_discord:
            st.subheader("💬 디스코드 위험 서버·콘텐츠 탐색")
            st.caption("유튜브/네이버에서 디스코드 유도 콘텐츠를 탐지합니다. 디스코드 초대 링크·서버명·채널 관련 위험 패턴을 분석합니다.")

            dc1, dc2 = st.columns([3, 1])
            with dc1:
                discord_query = st.text_input("🔍 검색어", placeholder="예: 디스코드 서버 초대 10대, 디코 여자친구 구함")
            with dc2:
                discord_platform = st.selectbox("플랫폼", ["유튜브", "네이버 카페", "네이버 블로그"])

            # 자동 키워드 생성
            discord_kw_pool = [
                # 미성년자 타깃 디스코드 서버
                "디스코드 서버 초대 중학생", "디코 여자친구 구함 10대",
                "디스코드 한국 10대 서버", "디코 초등학생 채팅방",
                "디스코드 여중생 서버 초대", "디코 나이 상관없는 서버",
                # 그루밍 유도
                "디스코드 친구 구함 여자", "디코 카톡 교환 10대",
                "디스코드 롤플레이 성인", "디코 비밀 채널 초대",
                # 도박/사기
                "디스코드 무료 나이트로 사기", "디코 게임 아이템 사기",
                "디스코드 도박방 초대", "디코 불법 배팅방",
                # 협박/섹스토션
                "디스코드 사진 요구 협박", "디코 영상통화 협박",
            ]

            dkw1, dkw2, dkw3 = st.columns(3)
            with dkw1:
                if st.button("🐉 위험 키워드 자동 생성", key="discord_auto_kw", use_container_width=True):
                    import random
                    st.session_state.discord_kw = random.choice(discord_kw_pool)
                    st.info(f"🔑 키워드: **{st.session_state.discord_kw}**")
            with dkw2:
                do_discord_search = st.button("🔍 탐색 시작", key="discord_search_btn", use_container_width=True, type="primary")
            with dkw3:
                discord_count = st.slider("결과 수", 5, 20, 10, key="discord_count")

            # 검색 실행
            if do_discord_search and discord_query:
                if discord_platform == "유튜브":
                    with st.spinner(f"유튜브에서 '{discord_query}' 탐색 중..."):
                        try:
                            sr = youtube.search().list(
                                part="snippet", q=discord_query + " 디스코드",
                                type="video", maxResults=discord_count + 5,
                                relevanceLanguage="ko", order="date",
                                regionCode="KR", safeSearch="none"
                            ).execute()

                            results = []
                            for item in sr.get("items", []):
                                vid = item["id"]["videoId"]
                                title = item["snippet"]["title"]
                                desc = item["snippet"].get("description","")[:300]
                                channel = item["snippet"]["channelTitle"]
                                published = item["snippet"].get("publishedAt","")[:10]
                                url = f"https://www.youtube.com/watch?v={vid}"

                                # 댓글에서 디스코드 링크 패턴 탐지
                                comments = get_video_comments(vid, max_comments=30)
                                discord_comments = [c for c in comments if
                                    any(kw in c.lower() for kw in ["discord.gg", "discord.com/invite", "디스코드", "디코", ".gg/"])]

                                msg = client.messages.create(
                                    model="claude-sonnet-4-20250514", max_tokens=300,
                                    messages=[{"role":"user","content":f"""아동 안전 전문가로서 이 영상이 아동·청소년을 디스코드로 유인하는 위험 콘텐츠인지 분석하세요.

제목: {title}
채널: {channel}
설명: {desc}
디스코드 관련 댓글 수: {len(discord_comments)}개
디스코드 댓글 샘플: {chr(10).join(discord_comments[:5]) if discord_comments else "없음"}

위험 패턴:
① 미성년자 디스코드 서버 초대/홍보
② 개인정보(나이/학교/연락처) 요구
③ 성적 접근 또는 그루밍 시도
④ 도박/사기 서버 유도
⑤ 협박/섹스토션

반드시 아래 형식으로만:
심각도: (1~5)
분류: (안전/그루밍/섹스토션/도박/사기/개인정보)
위험신호: (구체적 패턴)
이유: (한 줄)"""}]
                                )
                                rt = msg.content[0].text
                                sev = extract_severity(rt)
                                cat = extract_category(rt)

                                results.append({
                                    "title": title, "channel": channel, "url": url,
                                    "published": published, "severity": sev,
                                    "category": cat, "analysis": rt,
                                    "discord_comments": len(discord_comments)
                                })

                            results.sort(key=lambda x: x["severity"], reverse=True)
                            risky = [r for r in results if r["severity"] >= 2]
                            safe = [r for r in results if r["severity"] < 2]

                            sev_icon = {1:"✅",2:"🟡",3:"🟠",4:"🔴",5:"🚨"}

                            if risky:
                                st.markdown(f"### 🚨 위험 감지 ({len(risky)}개)")
                                for r in risky:
                                    with st.expander(f"{sev_icon.get(r['severity'],'⚪')} {r['title'][:60]}"):
                                        rc1, rc2 = st.columns(2)
                                        rc1.markdown(f"**심각도:** {r['severity']} | **분류:** {r['category']}")
                                        rc2.markdown(f"**💬 디스코드 댓글:** {r['discord_comments']}개")
                                        for line in r['analysis'].splitlines():
                                            if "위험신호:" in line or "이유:" in line:
                                                st.markdown(f"**{line}**")
                                        bc1, bc2 = st.columns(2)
                                        with bc1:
                                            st.markdown(f"[▶️ 영상 보기]({r['url']})")
                                        with bc2:
                                            if st.button("📋 보고서 작성", key=f"dc_rep_{r['url'][-10:]}"):
                                                open_report_form(r['url'], r['analysis'], r['severity'], r['category'], "discord", from_tab=4)
                                                st.rerun()
                            else:
                                st.success("🟢 위험한 콘텐츠가 발견되지 않았습니다.")

                            if safe:
                                with st.expander(f"✅ 안전 ({len(safe)}개)"):
                                    for r in safe:
                                        st.caption(f"✅ {r['title'][:60]}")
                        except Exception as e:
                            st.error(f"탐색 오류: {str(e)}")

                else:  # 네이버
                    search_type = "cafearticle" if "카페" in discord_platform else "blog"
                    with st.spinner(f"네이버에서 '{discord_query}' 탐색 중..."):
                        try:
                            headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
                            resp = requests.get(
                                f"https://openapi.naver.com/v1/search/{search_type}.json",
                                headers=headers,
                                params={"query": discord_query + " 디스코드", "display": discord_count, "sort": "date"},
                                timeout=10
                            )
                            items = resp.json().get("items", []) if resp.status_code == 200 else []

                            analyzed = []
                            for item in items:
                                import re as _re
                                title = _re.sub(r'<[^>]+>', '', item.get("title",""))
                                desc = _re.sub(r'<[^>]+>', '', item.get("description",""))
                                link = item.get("link","")

                                msg = client.messages.create(
                                    model="claude-sonnet-4-20250514", max_tokens=200,
                                    messages=[{"role":"user","content":f"""제목: {title}
내용: {desc}

이 게시물이 아동·청소년을 디스코드로 유인하는 위험 게시물인지 분석하세요.
심각도: (1~5)
분류: (안전/그루밍/도박/사기/개인정보)
이유: (한 줄)"""}]
                                )
                                rt = msg.content[0].text
                                sev = extract_severity(rt)
                                analyzed.append({"title":title,"desc":desc,"link":link,"severity":sev,"analysis":rt})

                            analyzed.sort(key=lambda x: x["severity"], reverse=True)
                            risky = [a for a in analyzed if a["severity"] >= 2]

                            if risky:
                                st.markdown(f"### 🚨 위험 게시물 ({len(risky)}개)")
                                for a in risky:
                                    with st.expander(f"🔴 {a['title'][:60]}"):
                                        st.markdown(a["analysis"])
                                        st.markdown(f"[🔗 원문 보기]({a['link']})")
                            else:
                                st.success("🟢 위험한 게시물이 없습니다.")
                        except Exception as e:
                            st.error(f"탐색 오류: {str(e)}")

            elif do_discord_search and not discord_query:
                st.warning("검색어를 입력하세요.")

        # ── 탐색 히스토리 ──
        with tab5:
            st.subheader(t("history_title"))
            st.caption(t("history_caption"))

            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                ftype = st.selectbox(t("filter_type"), LANG.get(st.session_state.get("lang","ko"),LANG["ko"]).get("history_types",["전체","🐉 일반추천","🎮 Roblox추천","⛏️ Minecraft추천","🔍 키워드탐색"]))
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

            st.caption(t("total_count").format(len(data)))

            all_users_res = supabase.table("users").select("id,name").execute()
            user_map = {u["id"]: u["name"] for u in (all_users_res.data or [])}

            # 히스토리 팝업
            if st.session_state.get("hist_popup_id"):
                hist_popup_d = next((x for x in data if x["id"] == st.session_state.hist_popup_id), None)
                if hist_popup_d:
                    with st.container(border=True):
                        hp1, hp2 = st.columns([8, 1])
                        with hp1:
                            st.markdown(f"**{hist_popup_d.get('title','')[:100]}**")
                        with hp2:
                            if st.button(t("popup_close"), key="hist_popup_close", use_container_width=True):
                                st.session_state.hist_popup_id = None; st.rerun()
                        hurl = hist_popup_d.get("url","")
                        pv1, pv2, pv3 = st.columns([1, 3, 1])
                        with pv2:
                            if "youtube.com" in hurl or "youtu.be" in hurl:
                                st.video(hurl)
                            else:
                                st.markdown(f"[🔗 링크 열기]({hurl})")
                        if not hist_popup_d.get("reported"):
                            if st.button(t("popup_write"), type="primary", use_container_width=True, key="hist_popup_write"):
                                st.session_state.hist_popup_id = None
                                open_report_form(hurl,"",1,t("write_report_safe"),"YouTube",from_tab=4); st.rerun()

            for d in data:
                stype = search_type_label(d.get("search_type",""))
                reported_badge = "✅ 보고서 작성" if d.get("reported") else "⏳ 미작성"
                assigned_name = user_map.get(d.get("assigned_to",""), t("unassigned"))
                analyzed_date = str(d.get("analyzed_at",""))[:16]
                report_id = d.get("report_id")
                # 보고서 고유번호 앞 8자리 표시
                report_no = f"📋 #{report_id[:8].upper()}" if report_id else ""

                ca, cb = st.columns([5,1])
                with ca:
                    st.markdown(f"**{d.get('title','(제목없음)')}**")
                    st.caption(f"{stype} | {analyzed_date} | 담당: {assigned_name} | {reported_badge} {report_no}")
                with cb:
                    if "youtube.com" in d.get("url","") or "youtu.be" in d.get("url",""):
                        if st.button(t("yt_open_link"), key=f"hist_open_{d['id']}"):
                            st.session_state.hist_popup_id = d["id"]; st.rerun()
                    if d.get("reported") and report_id:
                        # 보고서 바로 보기 버튼
                        if st.button("📄 보고서", key=f"hist_rep_view_{d['id']}"):
                            try:
                                rep = supabase.table("reports").select("*").eq("id", report_id).execute()
                                if rep.data:
                                    st.session_state.selected_report = rep.data[0]
                                    go_to("report_detail", from_tab=4)
                                    st.rerun()
                            except Exception:
                                pass
                    elif not d.get("reported"):
                        if st.button(t("write_btn"), key=f"hist_{d['id']}"):
                            open_report_form(d["url"], "", 1, "안전", "YouTube", from_tab=4); st.rerun()
                st.divider()

        # ── 보고서 목록 ──
        with tab6:
            st.subheader(t("report_list"))

            all_reps_data = supabase.table("reports").select("*").order("created_at", desc=True).execute()
            all_users_r = supabase.table("users").select("id,name").execute()
            umap_r = {u["id"]: u["name"] for u in (all_users_r.data or [])}

            if all_reps_data.data:
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    fsev = st.selectbox(t("filter_sev"), ["전체","1","2","3","4","5"])
                with fc2:
                    fcat = st.selectbox(t("filter_cat"), LANG.get(st.session_state.get("lang","ko"),LANG["ko"]).get("report_cats",["전체","안전","스팸","부적절","성인","그루밍","미분류"]))
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
                            bulk_subject = st.text_input(t("email_subject_label"), value=f"[DragonEyes] Monitoring Report — {len(filtered)} cases")
                            bulk_memo = st.text_area(t("email_memo_label"), height=60)
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
                            st.info(t("no_recipients"))

                for r in filtered:
                    sev = r.get("severity",0); icon = sev_icon(sev)
                    created = str(r.get("created_at",""))[:16]
                    preview = str(r.get("content",""))[:50]
                    writer = umap_r.get(r.get("user_id",""), "알 수 없음")
                    can_edit_r = is_admin or r.get("user_id") == user["id"]
                    en_badge = " ✅🌐EN" if r.get("result_en") else " ⬜번역없음"
                    report_no = f"#{r['id'][:8].upper()}"
                    link_badge = f" 🔗" if r.get("analyzed_url_id") else ""

                    ca, cb, cc, cd = st.columns([5, 1, 1, 1])
                    with ca:
                        st.markdown(f"{icon} **{r.get('category','-')}** | {r.get('platform','-')} | {created} | 👤 {writer} |{en_badge}")
                        st.caption(f"🔖 {report_no}{link_badge}  |  {preview}...")
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
                                email_memo = st.text_area(t("email_memo_label2"), height=60, key=f"memo_{r['id']}")

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
                                            st.warning(t("no_english"))

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
                                    if st.button(t("cancel_btn"), key=f"cancel_email_{r['id']}"):
                                        st.session_state[f"show_email_{r['id']}"] = False; st.rerun()
                            else:
                                st.warning(t("no_recipients"))
                                if st.button(t("close_btn"), key=f"close_email_{r['id']}"):
                                    st.session_state[f"show_email_{r['id']}"] = False; st.rerun()
                    st.divider()
            else:
                st.info(t("no_reports"))

        # ── 내 성과 ──
        with tab7:
            st.subheader(f"📈 {user['name']}님의 성과 현황")
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
                st.info(t("no_reports_yet"))

        # ── 네이버 탐색 ──
        with tab_naver:
            st.subheader(t("naver_title"))
            if not NAVER_CLIENT_ID:
                st.error(t("naver_api_error"))
            else:
                n1, n2 = st.columns([3,1])
                with n1:
                    naver_query = st.text_input(t("naver_query"), placeholder=t("naver_query_ph"))
                with n2:
                    naver_type = st.selectbox(t("naver_type"), [t("naver_cafe"), t("naver_blog"), t("naver_news"), t("naver_all")])

                naver_cols = st.columns(3)
                with naver_cols[0]:
                    auto_keywords = st.button(t("naver_auto_kw"), use_container_width=True)
                with naver_cols[1]:
                    do_search = st.button(t("naver_search"), use_container_width=True, type="primary")
                with naver_cols[2]:
                    display_count = st.slider(t("naver_result_count"), 5, 20, 10)

                if auto_keywords:
                    import random
                    # 네이버 카페 특화 — 실제 위험 게시물에서 쓰이는 표현
                    pool = {
                        "카페": [
                            # 그루밍/만남 유도
                            "초등학생 친구 구함 카페", "여중생 친구해요", "10대 여자친구 구함",
                            "청소년 남친 여친 구함", "어린 친구 사귀기", "중학생 만남 카페",
                            # 연락처 교환
                            "카카오톡 친추 10대", "디스코드 청소년 서버", "틱톡 팔로우 여중",
                            # 성적 접근
                            "교복 사진 공유 카페", "중학생 몸매 인증", "여고생 사진 모음",
                            # 도박 유도
                            "토토사이트 추천 카페", "먹튀없는 사이트 공유", "배팅방 초대 카페",
                            "파워볼 당첨 비법 카페", "불법도박 총판 모집", "대리베팅 알바 카페",
                            "용돈 버는 법 학생 카페", "소액투자 수익인증 카페", "코인게임 환전",
                            # 가출/납치
                            "가출 청소년 도와줌", "10대 쉼터 카페", "가출 친구 구함",
                        ],
                        "블로그": [
                            "미성년자 조건만남 후기", "청소년 그루밍 방법",
                            "토토사이트 추천 후기 블로그", "카지노 필승법 공유",
                            "파워볼 패턴 분석 블로그", "먹튀검증 사이트 추천",
                            "10대 섹스토션 피해 경험", "어린이 온라인 협박",
                        ],
                        "뉴스": [
                            "청소년 온라인 그루밍 검거", "미성년자 성착취 카페 적발",
                            "아동 섹스토션 피의자", "불법도박사이트 광고 적발",
                            "청소년 도박 중독 실태", "미성년자 도박 알바 검거",
                        ],
                    }
                    sel_type = naver_type if naver_type != "전체" else "카페"
                    kw_pool = pool.get(sel_type, pool["카페"])
                    picked = random.choice(kw_pool)
                    st.session_state["naver_auto_kw"] = picked
                    st.info(f"🔑 자동 생성 키워드: **{picked}**")
                    # 자동으로 검색어 입력란에 반영
                    naver_query = picked

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
                    with st.spinner(t("naver_searching_msg").format(naver_type)):
                        items = naver_search(naver_query, naver_type, display_count)

                    if not items:
                        st.warning(t("naver_no_result"))
                    else:
                        st.success(t("naver_found_msg").format(len(items)))
                        with st.spinner("🐲 드래곤파더가 위험도 분석 중..."):
                            analyzed = []
                            for item in items:
                                title = clean_html(item.get("title",""))
                                desc  = clean_html(item.get("description",""))
                                link  = item.get("link","") or item.get("url","")
                                src_type = item.get("_type","")
                                pub_date = item.get("pubDate","") or item.get("postdate","")
                                cafe_name = clean_html(item.get("cafename",""))

                                try:
                                    msg = client.messages.create(
                                        model="claude-sonnet-4-20250514", max_tokens=300,
                                        messages=[{"role":"user","content":f"""당신은 아동 온라인 안전 전문 분석가입니다. 아래 네이버 {src_type} 게시물이 아동·청소년에게 위험한지 엄격하게 분석하세요.

제목: {title}
내용 요약: {desc}
카페명: {cafe_name if cafe_name else "알 수 없음"}
게시일: {pub_date}

【위험 신호 체크리스트】
① 그루밍: 성인→미성년자 친구/연인 유도, 나이/학교 묻기
② 연락처 유도: 카카오톡·디스코드·인스타 등 유도
③ 성적 접근: 교복·신체·사진 요구, 성적 암시
④ 만남 유도: 실제 만남 장소·시간 제안
⑤ 도박/사행성: 불법 배팅·토토·카지노 사이트 홍보, 첫충/보너스 광고, 대리베팅·총판 모집, "용돈 버는 법" 위장 도박 유도
⑥ 가출 조장: 가출 도움·쉼터 제공 위장
⑦ 협박/섹스토션: 사진·영상 요구 후 협박
⑧ 미끼: 게임 아이템·용돈·알바비 미끼, 무료 머니·포인트 지급 광고

【중요】
- 제목/내용이 애매해도 위험 가능성 있으면 심각도 높게
- 카페명에 "성인" "은밀" "비공개" 포함시 심각도 +1
- 안전 판정은 명백히 교육·뉴스·공식 기관 게시물만

반드시 아래 형식으로만 답변:
심각도: (1~5)
분류: (안전/스팸/부적절/그루밍/섹스토션/도박/가출조장/만남유도/개인정보)
위험신호: (구체적 패턴, 없으면 "없음")
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
                                    for c in ["섹스토션","만남유도","그루밍","도박","가출조장","개인정보","성인","부적절","스팸"]:
                                        if c in resp_text: cat = c; break
                                    reason = ""
                                    danger_signal = ""
                                    for line in resp_text.splitlines():
                                        if "이유:" in line:
                                            reason = line.replace("이유:","").strip()
                                        if "위험신호:" in line:
                                            danger_signal = line.replace("위험신호:","").strip()
                                except Exception:
                                    sev, cat, reason, danger_signal = 1, "안전", "분석 실패", ""

                                analyzed.append({
                                    "title": title, "desc": desc, "link": link,
                                    "type": src_type, "pubDate": pub_date,
                                    "cafename": cafe_name,
                                    "severity": sev, "category": cat,
                                    "reason": reason, "danger_signal": danger_signal
                                })

                        analyzed.sort(key=lambda x: x["severity"], reverse=True)
                        risky = [a for a in analyzed if a["severity"] >= 2]
                        safe  = [a for a in analyzed if a["severity"] < 2]

                        sev_icon_map = {1:"✅",2:"🟡",3:"🟠",4:"🔴",5:"🚨"}

                        if risky:
                            st.markdown(f"### 🚨 주의 필요 ({len(risky)}개)")
                            for a in risky:
                                with st.expander(f"{sev_icon_map.get(a['severity'],'⚪')} [{a['type']}] {a['title'][:60]}"):
                                    sc1, sc2 = st.columns(2)
                                    sc1.markdown(f"**심각도:** {a['severity']} | **분류:** {a['category']}")
                                    if a.get("cafename"):
                                        sc2.markdown(f"**카페:** {a['cafename']}")
                                    if a.get("danger_signal") and a["danger_signal"] != "없음":
                                        st.markdown(f"**⚠️ 위험신호:** {a['danger_signal']}")
                                    st.markdown(f"**이유:** {a['reason']}")
                                    st.markdown(f"**내용:** {a['desc'][:300]}")
                                    st.caption(t("naver_pub_date").format(a['pubDate']))
                                    bc1, bc2 = st.columns(2)
                                    with bc1:
                                        st.markdown(f"[🔗 원문 보기]({a['link']})")
                                    with bc2:
                                        if st.button("📋 보고서 작성", key=f"naver_rep_{a['link'][-20:]}"):
                                            open_report_form(a["link"], f"심각도:{a['severity']}\n분류:{a['category']}\n위험신호:{a.get('danger_signal','')}\n이유:{a['reason']}", a["severity"], a["category"], "naver")
                                            st.rerun()
                        else:
                            st.success("🟢 주의 필요한 게시물이 없습니다.")

                        if safe:
                            with st.expander(t("safe_count").format(len(safe))):
                                for a in safe:
                                    st.caption(f"{sev_icon_map.get(a['severity'],'⚪')} [{a['type']}] {a['title'][:60]} — {a['reason']}")
                elif do_search and not naver_query:
                    st.warning(t("naver_enter_query"))

        # ── 대화형 AI 채팅 ──
        with tab_chat:
            st.subheader("🐲 드래곤파더")
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
                st.caption(t("chat_caption"))

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
                user_input = st.chat_input(t("chat_input_ph"), max_chars=300)
                if user_input:
                    st.session_state.chat_history.append({"role": "user", "content": user_input})
                    with st.spinner("🐲 " + t("dragon_caption")[:10] + "..."):
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
                            st.error(t("error_msg").format(str(e)))
            else:
                st.chat_input(t("chat_disabled"), disabled=True)

            if st.session_state.chat_history:
                if st.button("🗑️ 대화 초기화", key="clear_chat"):
                    st.session_state.chat_history = []
                    st.rerun()

        # ── 공지사항 탭 ──
        if tab_notice:
            with tab_notice:
                st.subheader("📢 공지사항")

                if is_high:
                    with st.expander(t("ann_new"), expanded=False):
                        ann_type = st.selectbox(t("ann_type"), ["notice","work_order","urgent"],
                            format_func=lambda x:{"notice":"🔵 공지사항","work_order":"🟠 업무지시","urgent":"🚨 긴급공지"}[x],
                            key="ann_type_sel")
                        ann_title = st.text_input(t("ann_title_label"), key="ann_title_inp")
                        ann_content = st.text_area(t("ann_content_label"), height=150, key="ann_content_inp")

                        all_teams_ann = get_all_teams()
                        all_users_ann = get_all_users()
                        target_type = st.selectbox(t("ann_target"), ["all","team","user"],
                            format_func=lambda x:{"all":"📢 전체","team":"👥 특정 팀","user":"👤 특정 사용자"}[x],
                            key="ann_target_type")
                        target_id = None
                        if target_type == "team" and all_teams_ann:
                            sel_team = st.selectbox(t("ann_team_sel"), all_teams_ann, format_func=lambda x: x["name"], key="ann_target_team")
                            target_id = sel_team["id"] if sel_team else None
                        elif target_type == "user" and all_users_ann:
                            sel_user = st.selectbox(t("ann_user_sel"), all_users_ann, format_func=lambda x: f'{x["name"]} ({x.get("email","")})', key="ann_target_user")
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
                                    st.success(t("ann_sent"))
                                    st.rerun()
                                except Exception as e:
                                    st.error(t("error_msg").format(str(e)))
                            else:
                                st.warning(t("ann_title_empty"))

                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    filter_type = st.selectbox(t("ann_filter_type"), ["전체","notice","work_order","urgent"],
                        format_func=lambda x:{"전체":"전체","notice":"🔵 공지사항","work_order":"🟠 업무지시","urgent":"🚨 긴급공지"}.get(x,x),
                        key="ann_filter_type")
                with fc2:
                    filter_period = st.selectbox("기간", ["전체","이번달","이번주"], key="ann_filter_period")
                with fc3:
                    filter_search = st.text_input(t("ann_filter_search"), placeholder=t("ann_search_ph"), key="ann_filter_search")

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
                    st.info(t("ann_none"))
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
                            st.markdown(f'<div style="color:#1e293b; background:#f8fafc; border-radius:6px; padding:10px 14px; margin:4px 0; font-size:0.95rem; line-height:1.7;">{ann["content"]}</div>', unsafe_allow_html=True)

                            if not is_read:
                                if st.button(t("ann_read_btn"), key=f"read_ann_{ann['id']}"):
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
                st.info(t("role_current").format(role_label(user_role)))

                org_tab1, org_tab2, org_tab3 = st.tabs(["👥 팀 관리", "🏖️ 휴가/병가 관리", "📋 업무지시"])

                with org_tab1:
                    all_teams_org = get_all_teams()
                    all_users_org = get_all_users()
                    umap_org = {u["id"]: u["name"] for u in all_users_org}

                    if is_high:
                        with st.expander(t("org_new_team"), expanded=False):
                            new_team_name = st.text_input(t("org_team_name"), key="new_team_name")
                            new_team_desc = st.text_input(t("org_team_desc"), key="new_team_desc")
                            leader_candidates = [u for u in all_users_org if u.get("role_v2") in ("team_leader","user","director","group_leader","superadmin")]
                            sel_leader = st.selectbox("팀장 지정", [None]+leader_candidates,
                                format_func=lambda x: "지정 안함" if x is None else x["name"],
                                key="new_team_leader")
                            if st.button(t("org_create_team"), key="create_team_btn"):
                                if new_team_name:
                                    supabase.table("teams").insert({
                                        "name": new_team_name,
                                        "description": new_team_desc,
                                        "leader_id": sel_leader["id"] if sel_leader else None
                                    }).execute()
                                    st.success(t("team_created").format(new_team_name))
                                    st.rerun()
                                else:
                                    st.warning(t("org_team_name_empty"))

                    if not all_teams_org:
                        st.info(t("work_no_teams"))
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
                                                new_role = st.selectbox(t("profile_role"),
                                                    _all_roles,
                                                    index=_all_roles.index(m.get("role_v2","user")) if m.get("role_v2","user") in _all_roles else 0,
                                                    key=f"role_sel_{m['id']}",
                                                    format_func=lambda x: role_label(x),
                                                    label_visibility="collapsed")
                                        with mc3:
                                            if is_high:
                                                if st.button(t("save_btn"), key=f"save_role_{m['id']}"):
                                                    supabase.table("users").update({"role_v2": new_role}).eq("id", m["id"]).execute()
                                                    st.success(t("role_changed").format(m['name'])); st.rerun()
                                else:
                                    st.caption(t("work_no_member"))

                                if is_high:
                                    st.divider()
                                    unassigned_users = [u for u in all_users_org if not u.get("team_id")]
                                    if unassigned_users:
                                        add_member = st.selectbox("팀원 추가",
                                            [None]+unassigned_users,
                                            format_func=lambda x: "선택..." if x is None else f'{x["name"]} ({x.get("email","")})',
                                            key=f"add_member_{team['id']}")
                                        if st.button(t("add_btn"), key=f"add_btn_{team['id']}"):
                                            if add_member:
                                                supabase.table("users").update({"team_id": team["id"]}).eq("id", add_member["id"]).execute()
                                                st.success(t("member_added").format(add_member['name'], team['name'])); st.rerun()

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
                            leave_start = st.date_input(t("leave_start"), key="leave_start")
                        with lc3:
                            leave_end = st.date_input(t("leave_end"), key="leave_end")
                        leave_reason = st.text_input(t("leave_reason"), key="leave_reason")
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
                                st.success(t("leave_submitted"))
                                st.rerun()
                            else:
                                st.warning(t("leave_date_error"))

                    st.subheader("📋 내 신청 현황")
                    my_leaves = supabase.table("leave_requests").select("*").eq("user_id", user["id"]).order("created_at", desc=True).limit(20).execute().data or []
                    if not my_leaves:
                        st.info(t("leave_none"))
                    else:
                        for lv in my_leaves:
                            lv_icon = leave_type_map.get(lv["type"],"📝")
                            st.markdown(f"{lv_icon} **{lv['start_date']} ~ {lv['end_date']}**  {status_map.get(lv['status'],'?')}  |  {lv.get('reason','')}")

                    if is_lead:
                        st.divider()
                        st.subheader(t("leave_pending"))
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
                            st.info(t("leave_pending_none"))
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
                                            st.caption(t("leave_reason_label").format(lv['reason']))
                                    with pa2:
                                        if st.button(t("leave_approve"), key=f"approve_leave_{lv['id']}"):
                                            supabase.table("leave_requests").update({
                                                "status": "approved",
                                                "approved_by": user["id"],
                                                "approved_at": datetime.now().isoformat()
                                            }).eq("id", lv["id"]).execute()
                                            st.success(t("leave_approved")); st.rerun()
                                    with pa3:
                                        if st.button(t("leave_reject"), key=f"reject_leave_{lv['id']}"):
                                            supabase.table("leave_requests").update({
                                                "status": "rejected",
                                                "approved_by": user["id"],
                                                "approved_at": datetime.now().isoformat()
                                            }).eq("id", lv["id"]).execute()
                                            st.warning(t("leave_rejected")); st.rerun()

                with org_tab3:
                    if is_lead:
                        st.subheader("📤 업무지시 발송")
                        with st.container(border=True):
                            wo_title = st.text_input(t("work_order_title"), key="wo_title_inp")
                            wo_content = st.text_area(t("work_order_content"), height=120, key="wo_content_inp")
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
                                    st.warning(t("ann_title_empty"))

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
                admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5, admin_tab6, admin_tab7, admin_tab8, admin_tab9, admin_tab10, admin_tab11, admin_tab12, admin_tab13 = st.tabs([
                    t("admin_team"), t("admin_assign"), t("admin_token"), t("admin_email"), t("admin_log"), "💬 채팅 토큰", "📡 채널 모니터링", "🧠 키워드 학습",
                    "🏢 업체(Tenant) 관리", "🤝 위탁관리자 관리", "📣 알림 발송 센터", "📋 라이선스 신청 관리", "🗂️ 동의서 보관함"
                ])

                # 팀 현황
                with admin_tab1:
                    all_users_data = supabase.table("users").select("*").execute()
                    all_reps = supabase.table("reports").select("*").execute()

                    # ── 전체 / 그룹별 보기 탭 ──
                    view_tab1, view_tab2 = st.tabs(["👥 전체 사용자 현황", "🏢 그룹별 사용자 현황"])

                    with view_tab1:
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
                                _role_label_str = role_label(u.get("role_v2","user"))
                                summary.append({
                                    t("profile_role"): _role_label_str,
                                    t("profile_name"): u["name"] + "  (" + u.get("email","") + ")",
                                    "이번달": len(mr),
                                    "목표": tgt,
                                    "달성률": f"{rt}%",
                                    "누적": len(ur),
                                    "드래곤토큰": f"{ti['used_count']}/{MONTHLY_DRAGON_LIMIT+ti.get('extra_tokens',0)}회"
                                })
                            st.caption(f"전체 사용자 {len(summary)}명")
                            df_summary = pd.DataFrame(summary)
                            st.dataframe(df_summary, use_container_width=True)
                            # CSV 다운로드
                            csv_summary = df_summary.to_csv(index=False, encoding="utf-8-sig")
                            st.download_button(
                                label="📥 전체 사용자 현황 CSV 다운로드",
                                data=csv_summary.encode("utf-8-sig"),
                                file_name=f"DragonEyes_전체사용자_{date.today().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                use_container_width=True,
                            )

                    with view_tab2:
                        # 그룹 역할 정의
                        group_options = {
                            "전체 보기": None,
                            "👑 전체 관리자 (superadmin)": ["superadmin"],
                            "🔱 제1 그룹 (그룹장+디렉터)": ["group_leader", "director"],
                            "🔱 제2 그룹 (그룹장+디렉터)": ["group_leader_2", "director_2"],
                            "🔱 제3 그룹 (그룹장+디렉터)": ["group_leader_3", "director_3"],
                            "🔱 제4 그룹 (그룹장+디렉터)": ["group_leader_4", "director_4"],
                            "👔 팀장": ["team_leader"],
                            "👤 일반사용자": ["user"],
                        }

                        selected_group = st.selectbox(
                            "🔍 그룹 선택",
                            options=list(group_options.keys()),
                            key="admin_group_filter"
                        )

                        if all_users_data.data and all_reps.data:
                            df_r2 = pd.DataFrame(all_reps.data)
                            df_r2["created_at"] = pd.to_datetime(df_r2["created_at"])
                            this_month = date.today().strftime("%Y-%m")
                            df_r2["month"] = df_r2["created_at"].dt.strftime("%Y-%m")

                            # 필터링
                            target_roles = group_options[selected_group]
                            if target_roles:
                                filtered_users = [u for u in all_users_data.data if u.get("role_v2","user") in target_roles]
                            else:
                                filtered_users = all_users_data.data

                            if not filtered_users:
                                st.info("해당 그룹에 사용자가 없습니다.")
                            else:
                                st.caption(f"**{selected_group}** — {len(filtered_users)}명")

                                # 헤더
                                hc = st.columns([2, 2, 1, 1, 1, 1, 1.5])
                                hc[0].markdown("**이름**")
                                hc[1].markdown("**역할**")
                                hc[2].markdown("**이번달**")
                                hc[3].markdown("**목표**")
                                hc[4].markdown("**달성률**")
                                hc[5].markdown("**누적**")
                                hc[6].markdown("**드래곤토큰**")
                                st.divider()

                                for u in filtered_users:
                                    ur = df_r2[df_r2["user_id"]==u["id"]]
                                    mr = ur[ur["month"]==this_month]
                                    tgt = u.get("monthly_target",10)
                                    rt = min(int(len(mr)/tgt*100),100) if tgt>0 else 0
                                    ti = get_token_info(u["id"])
                                    rate_color = "#22c55e" if rt>=100 else ("#f59e0b" if rt>=50 else "#ef4444")
                                    r_ico = role_icon(u.get("role_v2","user"))

                                    rc = st.columns([2, 2, 1, 1, 1, 1, 1.5])
                                    rc[0].write(f"{r_ico} **{u['name']}**")
                                    rc[1].caption(u.get("email",""))
                                    rc[2].write(f"{len(mr)}건")
                                    rc[3].write(f"{tgt}건")
                                    rc[4].markdown(f"<span style='color:{rate_color};font-weight:700'>{rt}%</span>", unsafe_allow_html=True)
                                    rc[5].write(f"{len(ur)}건")
                                    rc[6].write(f"{ti['used_count']}/{MONTHLY_DRAGON_LIMIT+ti.get('extra_tokens',0)}회")

                                # 요약 통계
                                st.divider()
                                total_month = sum(len(df_r2[(df_r2["user_id"]==u["id"]) & (df_r2["month"]==this_month)]) for u in filtered_users)
                                total_all = sum(len(df_r2[df_r2["user_id"]==u["id"]]) for u in filtered_users)
                                avg_rate = sum(
                                    min(int(len(df_r2[(df_r2["user_id"]==u["id"]) & (df_r2["month"]==this_month)]) / max(u.get("monthly_target",10),1) * 100), 100)
                                    for u in filtered_users
                                ) // max(len(filtered_users), 1)

                                sc1, sc2, sc3, sc4 = st.columns(4)
                                sc1.metric("👥 인원", f"{len(filtered_users)}명")
                                sc2.metric("📅 이번달 합계", f"{total_month}건")
                                sc3.metric("📊 평균 달성률", f"{avg_rate}%")
                                sc4.metric("📁 누적 합계", f"{total_all}건")

                    st.divider()
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
                                    st.error(t("error_msg").format(str(e)))
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

                with admin_tab7:
                    st.subheader(t("ch_monitor_title"))
                    st.caption(t("ch_monitor_caption"))

                    channels = get_watched_channels()

                    if not channels:
                        st.info(t("ch_no_channels"))
                    else:
                        st.success(f"총 {len(channels)}개 채널 모니터링 중")

                        # 요약 통계
                        mc1, mc2, mc3 = st.columns(3)
                        mc1.metric(t("ch_stat_channels"), len(channels))
                        mc2.metric(t("ch_stat_avg"), f"{sum(c['avg_severity'] for c in channels)/len(channels):.1f}")
                        mc3.metric(t("ch_stat_total"), sum(c['risk_count'] for c in channels))

                        st.divider()

                        # 채널 목록
                        for ch in channels:
                            sev_color = "🚨" if ch['avg_severity'] >= 4 else "🔴" if ch['avg_severity'] >= 3 else "🟠"
                            with st.expander(f"{sev_color} {ch['channel_name']} | 위험탐지 {ch['risk_count']}회 | 평균심각도 {ch['avg_severity']}"):
                                cc1, cc2, cc3, cc4 = st.columns([3,1,1,1])
                                with cc1:
                                    st.markdown(f"**채널ID:** `{ch['channel_id']}`")
                                    st.caption(f"최초: {str(ch['first_detected_at'])[:10]} | 최근: {str(ch['last_detected_at'])[:10]}")
                                with cc2:
                                    st.markdown(f"[▶️ 채널 보기](https://www.youtube.com/channel/{ch['channel_id']})")
                                with cc3:
                                    if st.button(t("ch_scan"), key=f"scan_{ch['id']}", use_container_width=True):
                                        with st.spinner(f"{ch['channel_name']} 스캔 중..."):
                                            scan_results = scan_watched_channel(
                                                ch['channel_id'], ch['channel_name'],
                                                assigned_to=user["id"]
                                            )
                                        if scan_results:
                                            risky_scan = [r for r in scan_results if r['severity'] >= 2]
                                            st.success(f"{len(scan_results)}개 영상 스캔 완료 — 위험 {len(risky_scan)}개")
                                            for r in risky_scan:
                                                st.markdown(f"- 🚨 [{r['title'][:50]}]({r['url']}) | 심각도:{r['severity']}")
                                        else:
                                            st.info("새 영상 없음")
                                with cc4:
                                    if st.button(t("ch_delete"), key=f"del_ch_{ch['id']}", use_container_width=True):
                                        supabase.table("watched_channels").delete().eq("id", ch["id"]).execute()
                                        st.rerun()

                        st.divider()

                        # 전체 스캔 버튼
                        if st.button(t("ch_scan_all"), type="primary", use_container_width=True):
                            total_risky = 0
                            prog = st.progress(0)
                            for i, ch in enumerate(channels):
                                with st.spinner(f"{ch['channel_name']} 스캔 중... ({i+1}/{len(channels)})"):
                                    scan_results = scan_watched_channel(ch['channel_id'], ch['channel_name'], assigned_to=user["id"])
                                    risky_scan = [r for r in scan_results if r['severity'] >= 2]
                                    total_risky += len(risky_scan)
                                prog.progress((i+1)/len(channels))
                            st.success(f"✅ 전체 스캔 완료 — 위험 콘텐츠 {total_risky}개 발견")

                with admin_tab8:
                    st.subheader("🧠 키워드 자동 학습 현황")
                    st.caption("심각도 3 이상 보고서에서 자동 추출된 위험 키워드입니다. 자동 검색 시 활용됩니다.")

                    try:
                        kw_data = supabase.table("learned_keywords").select("*").order("use_count", desc=True).execute().data or []

                        if not kw_data:
                            st.info("아직 학습된 키워드가 없습니다. 심각도 3 이상 보고서를 작성하면 자동으로 키워드가 학습됩니다.")
                        else:
                            # 통계
                            kc1, kc2, kc3 = st.columns(3)
                            kc1.metric("총 학습 키워드", f"{len(kw_data)}개")
                            kc2.metric("평균 사용 횟수", f"{sum(k['use_count'] for k in kw_data)/len(kw_data):.1f}회")
                            kc3.metric("최다 사용", f"{max(k['use_count'] for k in kw_data)}회")

                            st.divider()

                            # 키워드 목록
                            import pandas as pd
                            df_kw = pd.DataFrame([{
                                "키워드": k["keyword"],
                                "분류": k.get("category",""),
                                "심각도": k.get("severity",""),
                                "사용횟수": k["use_count"],
                                "최근사용": str(k.get("last_used_at",""))[:10],
                            } for k in kw_data])
                            st.dataframe(df_kw, use_container_width=True)

                            # CSV 다운로드
                            csv_kw = df_kw.to_csv(index=False, encoding="utf-8-sig")
                            st.download_button("📥 키워드 목록 CSV 다운로드", data=csv_kw.encode("utf-8-sig"),
                                file_name=f"learned_keywords_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv")

                            st.divider()

                            # 개별 삭제
                            st.markdown("**🗑️ 키워드 삭제**")
                            del_kw = st.selectbox("삭제할 키워드 선택", ["선택하세요"] + [k["keyword"] for k in kw_data])
                            if st.button("🗑️ 선택 키워드 삭제", key="del_kw_btn"):
                                if del_kw != "선택하세요":
                                    supabase.table("learned_keywords").delete().eq("keyword", del_kw).execute()
                                    st.success(f"✅ '{del_kw}' 삭제됐습니다!")
                                    st.rerun()

                            if st.button("🗑️ 전체 키워드 초기화", key="clear_kw_btn", type="secondary"):
                                supabase.table("learned_keywords").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
                                st.success("✅ 전체 키워드가 초기화됐습니다!")
                                st.rerun()
                    except Exception as e:
                        st.error(f"키워드 학습 데이터 불러오기 오류: {str(e)}")

                # ══════════════════════════════
                # 🏢 업체(Tenant) 관리 탭
                # ══════════════════════════════
                with admin_tab9:
                    st.subheader("🏢 업체(Tenant) 관리")
                    st.caption("라이선스 업체를 등록하고 관리합니다. 업체당 관리자 1명 + 사용자 3~5명 허용.")

                    # 신규 업체 등록
                    with st.expander("➕ 신규 업체 등록", expanded=False):
                        tc1, tc2 = st.columns(2)
                        with tc1:
                            new_tenant_name = st.text_input("업체명 *", key="new_tenant_name")
                            new_tenant_email = st.text_input("담당자 이메일", key="new_tenant_email")
                            new_tenant_phone = st.text_input("담당자 연락처", key="new_tenant_phone")
                        with tc2:
                            new_tenant_plan = st.selectbox("라이선스 플랜", ["basic", "standard", "premium"],
                                format_func=lambda x: {"basic":"🥉 Basic (3명)", "standard":"🥈 Standard (5명)", "premium":"🥇 Premium (무제한)"}[x],
                                key="new_tenant_plan")
                            new_tenant_max = st.number_input("최대 사용자 수", min_value=1, max_value=100, value=5, key="new_tenant_max")
                            new_tenant_start = st.date_input("라이선스 시작일", key="new_tenant_start")
                            new_tenant_end = st.date_input("라이선스 종료일", key="new_tenant_end")
                        if st.button("✅ 업체 등록", type="primary", key="create_tenant_btn"):
                            if new_tenant_name:
                                try:
                                    supabase.table("tenants").insert({
                                        "name": new_tenant_name,
                                        "license_plan": new_tenant_plan,
                                        "max_users": new_tenant_max,
                                        "license_start": str(new_tenant_start),
                                        "license_end": str(new_tenant_end),
                                        "contact_email": new_tenant_email,
                                        "contact_phone": new_tenant_phone,
                                        "is_active": True,
                                    }).execute()
                                    st.success(f"✅ '{new_tenant_name}' 업체 등록 완료!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"오류: {str(e)}")
                            else:
                                st.warning("업체명을 입력해주세요.")

                    # 업체 목록
                    all_tenants = get_all_tenants()
                    st.caption(f"전체 등록 업체: {len(all_tenants)}개")

                    if not all_tenants:
                        st.info("등록된 업체가 없습니다.")
                    else:
                        # 요약 통계
                        active_cnt = len([t for t in all_tenants if t.get("is_active")])
                        ts1, ts2, ts3 = st.columns(3)
                        ts1.metric("전체 업체", f"{len(all_tenants)}개")
                        ts2.metric("활성 업체", f"{active_cnt}개")
                        ts3.metric("비활성", f"{len(all_tenants)-active_cnt}개")
                        st.divider()

                        for tenant in all_tenants:
                            tenant_users = get_tenant_users(tenant["id"])
                            admin_users = [u for u in tenant_users if u.get("is_tenant_admin")]
                            status_badge = "✅ 활성" if tenant.get("is_active") else "❌ 비활성"
                            plan_badge = {"basic":"🥉","standard":"🥈","premium":"🥇"}.get(tenant.get("license_plan","basic"),"🥉")

                            with st.expander(f"{plan_badge} **{tenant['name']}** | {status_badge} | 사용자 {len(tenant_users)}/{tenant.get('max_users',5)}명"):
                                ec1, ec2, ec3 = st.columns(3)
                                ec1.write(f"**플랜:** {tenant.get('license_plan','basic')}")
                                ec2.write(f"**이메일:** {tenant.get('contact_email','-')}")
                                ec3.write(f"**연락처:** {tenant.get('contact_phone','-')}")
                                st.caption(f"라이선스: {tenant.get('license_start','-')} ~ {tenant.get('license_end','-')}")

                                # 업체 관리자 지정
                                st.divider()
                                st.markdown("**👤 업체 관리자 지정**")
                                all_users_t = supabase.table("users").select("*").execute().data or []
                                unassigned = [u for u in all_users_t if not u.get("tenant_id")]
                                current_admin = admin_users[0]["name"] if admin_users else "미지정"
                                st.caption(f"현재 관리자: {current_admin}")

                                if unassigned:
                                    sel_admin = st.selectbox("관리자로 지정할 사용자",
                                        [None] + unassigned,
                                        format_func=lambda x: "선택..." if x is None else f'{x["name"]} ({x.get("email","")})',
                                        key=f"tenant_admin_{tenant['id']}")
                                    if st.button("👤 관리자 지정", key=f"set_admin_{tenant['id']}"):
                                        if sel_admin:
                                            supabase.table("users").update({
                                                "tenant_id": tenant["id"],
                                                "is_tenant_admin": True,
                                                "role_v2": "tenant_admin"
                                            }).eq("id", sel_admin["id"]).execute()
                                            st.success(f"✅ {sel_admin['name']}님이 {tenant['name']} 관리자로 지정됐습니다!")
                                            st.rerun()

                                # 업체 사용자 목록
                                if tenant_users:
                                    st.divider()
                                    st.markdown("**👥 소속 사용자**")
                                    for u in tenant_users:
                                        uc1, uc2, uc3 = st.columns([3, 2, 1])
                                        uc1.write(f"{'👑' if u.get('is_tenant_admin') else '👤'} {u['name']} ({u.get('email','')})")
                                        uc2.caption(role_label(u.get("role_v2","user")))
                                        with uc3:
                                            if st.button("제거", key=f"remove_tenant_user_{u['id']}"):
                                                supabase.table("users").update({"tenant_id": None, "is_tenant_admin": False}).eq("id", u["id"]).execute()
                                                st.rerun()

                                # 활성/비활성 토글
                                st.divider()
                                ta1, ta2 = st.columns(2)
                                with ta1:
                                    toggle_label = "❌ 비활성화" if tenant.get("is_active") else "✅ 활성화"
                                    if st.button(toggle_label, key=f"toggle_tenant_{tenant['id']}"):
                                        supabase.table("tenants").update({"is_active": not tenant.get("is_active")}).eq("id", tenant["id"]).execute()
                                        st.rerun()

                # ══════════════════════════════
                # 🤝 위탁관리자 관리 탭
                # ══════════════════════════════
                with admin_tab10:
                    st.subheader("🤝 위탁관리자(Agency) 관리")
                    st.caption("컨설팅 업체 또는 에이전시를 위탁관리자로 등록하고 담당 업체를 배정합니다.")

                    # 신규 위탁관리자 등록
                    with st.expander("➕ 위탁관리자 등록", expanded=False):
                        ag1, ag2 = st.columns(2)
                        with ag1:
                            new_agency_name = st.text_input("에이전시명 *", key="new_agency_name")
                            new_agency_email = st.text_input("이메일", key="new_agency_email")
                            new_agency_phone = st.text_input("연락처", key="new_agency_phone")
                        with ag2:
                            all_users_ag = supabase.table("users").select("*").execute().data or []
                            sel_agency_user = st.selectbox("담당 사용자 계정 연결",
                                [None] + all_users_ag,
                                format_func=lambda x: "선택..." if x is None else f'{x["name"]} ({x.get("email","")})',
                                key="new_agency_user")
                        if st.button("✅ 위탁관리자 등록", type="primary", key="create_agency_btn"):
                            if new_agency_name:
                                try:
                                    result = supabase.table("agencies").insert({
                                        "name": new_agency_name,
                                        "user_id": sel_agency_user["id"] if sel_agency_user else None,
                                        "contact_email": new_agency_email,
                                        "contact_phone": new_agency_phone,
                                        "is_active": True,
                                    }).execute()
                                    # 연결된 사용자 role을 agency_admin으로 변경
                                    if sel_agency_user:
                                        supabase.table("users").update({"role_v2": "agency_admin"}).eq("id", sel_agency_user["id"]).execute()
                                    st.success(f"✅ '{new_agency_name}' 위탁관리자 등록 완료!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"오류: {str(e)}")
                            else:
                                st.warning("에이전시명을 입력해주세요.")

                    # 위탁관리자 목록
                    all_agencies = get_all_agencies()
                    st.caption(f"전체 위탁관리자: {len(all_agencies)}개")
                    all_tenants_ag = get_all_tenants()
                    tenant_map_ag = {t["id"]: t["name"] for t in all_tenants_ag}
                    umap_ag = {u["id"]: u["name"] for u in (supabase.table("users").select("id,name").execute().data or [])}

                    if not all_agencies:
                        st.info("등록된 위탁관리자가 없습니다.")
                    else:
                        for agency in all_agencies:
                            # 담당 업체 목록 조회
                            at_data = supabase.table("agency_tenants").select("tenant_id").eq("agency_id", agency["id"]).execute().data or []
                            assigned_tenant_ids = [x["tenant_id"] for x in at_data]
                            assigned_tenants = [t for t in all_tenants_ag if t["id"] in assigned_tenant_ids]
                            manager_name = umap_ag.get(agency.get("user_id",""), "미연결")

                            with st.expander(f"🤝 **{agency['name']}** | 담당자: {manager_name} | 담당 업체: {len(assigned_tenants)}개"):
                                ac1, ac2 = st.columns(2)
                                ac1.write(f"**이메일:** {agency.get('contact_email','-')}")
                                ac2.write(f"**연락처:** {agency.get('contact_phone','-')}")

                                # 담당 업체 배정
                                st.divider()
                                st.markdown("**🏢 담당 업체 배정**")
                                unassigned_tenants = [t for t in all_tenants_ag if t["id"] not in assigned_tenant_ids]
                                if unassigned_tenants:
                                    sel_tenant = st.selectbox("업체 선택",
                                        [None] + unassigned_tenants,
                                        format_func=lambda x: "선택..." if x is None else x["name"],
                                        key=f"assign_tenant_{agency['id']}")
                                    if st.button("➕ 업체 배정", key=f"assign_btn_{agency['id']}"):
                                        if sel_tenant:
                                            try:
                                                supabase.table("agency_tenants").insert({
                                                    "agency_id": agency["id"],
                                                    "tenant_id": sel_tenant["id"]
                                                }).execute()
                                                st.success(f"✅ {sel_tenant['name']} 배정 완료!")
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"오류: {str(e)}")

                                # 배정된 업체 목록
                                if assigned_tenants:
                                    st.markdown("**현재 담당 업체:**")
                                    for at in assigned_tenants:
                                        atc1, atc2 = st.columns([4, 1])
                                        atc1.write(f"🏢 {at['name']} | {at.get('contact_email','-')}")
                                        with atc2:
                                            if st.button("제거", key=f"remove_at_{agency['id']}_{at['id']}"):
                                                supabase.table("agency_tenants").delete().eq("agency_id", agency["id"]).eq("tenant_id", at["id"]).execute()
                                                st.rerun()

                # ══════════════════════════════
                # 📣 알림 발송 센터 탭
                # ══════════════════════════════
                with admin_tab11:
                    st.subheader("📣 알림 발송 센터")
                    st.caption("이메일 및 SMS로 사용자에게 알림을 발송합니다. 대상을 개인/업체/달성률/전체로 선택할 수 있습니다.")

                    # 발송 대상 선택
                    nc1, nc2 = st.columns([2, 3])
                    with nc1:
                        notif_target_type = st.selectbox("📋 발송 대상",
                            ["individual", "tenant", "achievement", "all"],
                            format_func=lambda x: {
                                "individual": "👤 개인별",
                                "tenant": "🏢 업체별",
                                "achievement": "📊 달성률별",
                                "all": "📢 전체"
                            }[x],
                            key="notif_target_type")

                        notif_channel = st.selectbox("📡 발송 채널",
                            ["email", "sms", "both"],
                            format_func=lambda x: {"email":"📧 이메일만", "sms":"📱 SMS만", "both":"📧📱 이메일+SMS"}[x],
                            key="notif_channel")

                    with nc2:
                        # 대상별 추가 옵션
                        notif_target_id = None
                        all_users_notif = supabase.table("users").select("*").execute().data or []
                        all_tenants_notif = get_all_tenants()

                        if notif_target_type == "individual":
                            sel_notif_user = st.selectbox("사용자 선택",
                                [None] + all_users_notif,
                                format_func=lambda x: "선택..." if x is None else f'{x["name"]} ({x.get("email","")})',
                                key="notif_sel_user")
                            notif_target_id = sel_notif_user["id"] if sel_notif_user else None
                            if sel_notif_user:
                                # 해당 사용자 현황 미리보기
                                ur = supabase.table("reports").select("id,created_at").eq("user_id", sel_notif_user["id"]).execute().data or []
                                this_m = date.today().strftime("%Y-%m")
                                m_cnt = len([r for r in ur if str(r.get("created_at",""))[:7] == this_m])
                                tgt = sel_notif_user.get("monthly_target", 10)
                                rt = min(int(m_cnt/tgt*100), 100) if tgt > 0 else 0
                                st.info(f"📊 {sel_notif_user['name']} | 이번달 {m_cnt}/{tgt}건 | 달성률 {rt}%")

                        elif notif_target_type == "tenant":
                            sel_notif_tenant = st.selectbox("업체 선택",
                                [None] + all_tenants_notif,
                                format_func=lambda x: "선택..." if x is None else x["name"],
                                key="notif_sel_tenant")
                            notif_target_id = sel_notif_tenant["id"] if sel_notif_tenant else None
                            if sel_notif_tenant:
                                t_users = get_tenant_users(sel_notif_tenant["id"])
                                st.info(f"🏢 {sel_notif_tenant['name']} | 소속 사용자 {len(t_users)}명에게 발송")

                        elif notif_target_type == "achievement":
                            ach_op = st.selectbox("달성률 조건",
                                ["below_50", "below_80", "below_100", "above_100"],
                                format_func=lambda x: {
                                    "below_50": "50% 미만",
                                    "below_80": "80% 미만",
                                    "below_100": "100% 미만",
                                    "above_100": "100% 달성"
                                }[x],
                                key="notif_ach_op")
                            notif_target_id = ach_op
                            # 해당하는 사용자 미리보기
                            this_m = date.today().strftime("%Y-%m")
                            all_reps_n = supabase.table("reports").select("user_id,created_at").execute().data or []
                            target_users_preview = []
                            for u in all_users_notif:
                                ur = [r for r in all_reps_n if r["user_id"] == u["id"] and str(r.get("created_at",""))[:7] == this_m]
                                tgt = u.get("monthly_target", 10)
                                rt = min(int(len(ur)/tgt*100), 100) if tgt > 0 else 0
                                threshold = {"below_50": rt < 50, "below_80": rt < 80, "below_100": rt < 100, "above_100": rt >= 100}
                                if threshold.get(ach_op, False):
                                    target_users_preview.append(f"{u['name']} ({rt}%)")
                            st.info(f"📊 해당 사용자 {len(target_users_preview)}명: {', '.join(target_users_preview[:5])}{'...' if len(target_users_preview) > 5 else ''}")

                        elif notif_target_type == "all":
                            st.info(f"📢 전체 사용자 {len(all_users_notif)}명에게 발송됩니다.")

                    st.divider()

                    # 메시지 작성
                    notif_subject = st.text_input("📌 제목 *", key="notif_subject", placeholder="예: [DragonEyes] 이번달 업무 현황 안내")
                    notif_body = st.text_area("📝 내용 *", height=150, key="notif_body",
                        placeholder="예: 안녕하세요. 이번달 업무 달성률을 확인해주세요.\n\n[DragonEyes 모니터링 시스템]")

                    # 템플릿 빠른 선택
                    st.caption("💡 빠른 템플릿:")
                    tpl1, tpl2, tpl3 = st.columns(3)
                    with tpl1:
                        if st.button("📊 달성률 독려", key="tpl1"):
                            st.session_state["notif_subject"] = "[DragonEyes] 이번달 업무 목표 달성 독려"
                            st.session_state["notif_body"] = "안녕하세요.\n\n이번달 업무 목표 달성을 위해 꾸준한 모니터링 활동 부탁드립니다.\n드래곤아이즈 시스템에 접속하여 배정된 콘텐츠를 확인해 주세요.\n\n감사합니다.\n[DragonEyes 관리팀]"
                            st.rerun()
                    with tpl2:
                        if st.button("📋 보고서 제출 요청", key="tpl2"):
                            st.session_state["notif_subject"] = "[DragonEyes] 보고서 미제출 안내"
                            st.session_state["notif_body"] = "안녕하세요.\n\n배정된 콘텐츠에 대한 보고서가 아직 제출되지 않았습니다.\n빠른 시일 내에 DragonEyes 시스템에 접속하여 보고서를 제출해 주시기 바랍니다.\n\n감사합니다.\n[DragonEyes 관리팀]"
                            st.rerun()
                    with tpl3:
                        if st.button("🔔 시스템 공지", key="tpl3"):
                            st.session_state["notif_subject"] = "[DragonEyes] 시스템 공지사항"
                            st.session_state["notif_body"] = "안녕하세요.\n\nDragonEyes 모니터링 시스템 관련 공지사항을 안내드립니다.\n\n[내용을 입력해주세요]\n\n감사합니다.\n[DragonEyes 관리팀]"
                            st.rerun()

                    st.divider()

                    # 발송 미리보기 및 실행
                    if notif_subject and notif_body:
                        with st.expander("📄 발송 미리보기"):
                            target_label = {
                                "individual": f"👤 개인: {umap_ag.get(str(notif_target_id), '선택 안됨') if notif_target_type == 'individual' else '-'}",
                                "tenant": f"🏢 업체: {next((t['name'] for t in all_tenants_notif if t['id'] == notif_target_id), '선택 안됨') if notif_target_type == 'tenant' else '-'}",
                                "achievement": f"📊 달성률 조건: {notif_target_id}",
                                "all": "📢 전체 사용자"
                            }.get(notif_target_type, "-")
                            st.markdown(f"**발송 대상:** {target_label}")
                            st.markdown(f"**채널:** {'📧 이메일' if notif_channel == 'email' else '📱 SMS' if notif_channel == 'sms' else '📧📱 이메일+SMS'}")
                            st.markdown(f"**제목:** {notif_subject}")
                            st.markdown(f"**내용:**\n{notif_body}")

                        send_col1, send_col2 = st.columns(2)
                        with send_col1:
                            if st.button("📧 발송 실행", type="primary", use_container_width=True, key="send_notif_btn"):
                                if notif_target_type == "individual" and not notif_target_id:
                                    st.warning("발송 대상을 선택해주세요.")
                                elif notif_target_type == "tenant" and not notif_target_id:
                                    st.warning("업체를 선택해주세요.")
                                else:
                                    ok = send_notification(
                                        sent_by_id=user["id"],
                                        target_type=notif_target_type,
                                        target_id=notif_target_id,
                                        channel=notif_channel,
                                        subject=notif_subject,
                                        body=notif_body
                                    )
                                    if ok:
                                        st.success("✅ 발송 요청이 저장됐습니다! (실제 발송은 이메일/SMS 연동 설정 후 자동 처리)")
                                    else:
                                        st.error("발송 저장 중 오류가 발생했습니다.")
                        with send_col2:
                            if st.button("🗑️ 초기화", use_container_width=True, key="clear_notif_btn"):
                                for k in ["notif_subject", "notif_body"]:
                                    if k in st.session_state:
                                        del st.session_state[k]
                                st.rerun()

                    # 발송 이력
                    st.divider()
                    st.markdown("### 📜 최근 발송 이력")
                    try:
                        notif_logs = supabase.table("notifications").select("*").order("sent_at", desc=True).limit(30).execute().data or []
                        if notif_logs:
                            for nl in notif_logs:
                                nl_sent_by = umap_ag.get(nl.get("sent_by",""), "알 수 없음")
                                nl_date = str(nl.get("sent_at",""))[:16]
                                ch_icon = {"email":"📧","sms":"📱","both":"📧📱"}.get(nl.get("channel","email"),"📧")
                                ttype = {"individual":"👤","tenant":"🏢","achievement":"📊","all":"📢"}.get(nl.get("target_type","all"),"📢")
                                st.markdown(f"{ch_icon} **{nl.get('subject','')}** | {ttype} | {nl_sent_by} | {nl_date} | `{nl.get('status','pending')}`")
                        else:
                            st.info("발송 이력이 없습니다.")
                    except Exception as e:
                        st.error(f"이력 조회 오류: {str(e)}")

                # ══════════════════════════════
                # 📋 라이선스 신청 관리 탭
                # ══════════════════════════════
                with admin_tab12:
                    st.subheader("📋 라이선스 신청 관리")
                    st.caption("위탁관리자가 신청한 신규 업체 라이선스를 검토하고 동의 메일을 발송합니다.")

                    status_map_admin = {
                        "pending": "⏳ 검토중",
                        "approved": "✅ 승인됨",
                        "consent_sent": "📧 동의메일 발송",
                        "consented": "✍️ 동의완료",
                        "active": "🟢 활성화",
                        "rejected": "❌ 반려"
                    }

                    # 필터
                    lf1, lf2 = st.columns(2)
                    with lf1:
                        filter_status = st.selectbox("상태 필터",
                            ["전체", "pending", "approved", "consent_sent", "consented", "active", "rejected"],
                            format_func=lambda x: "전체" if x == "전체" else status_map_admin.get(x, x),
                            key="license_filter_status")
                    with lf2:
                        filter_search = st.text_input("업체명 검색", key="license_search", placeholder="업체명 입력...")

                    try:
                        lr_query = supabase.table("license_requests").select("*").order("created_at", desc=True)
                        if filter_status != "전체":
                            lr_query = lr_query.eq("status", filter_status)
                        all_requests = lr_query.execute().data or []

                        if filter_search:
                            all_requests = [r for r in all_requests if filter_search.lower() in r.get("company_name","").lower()]

                        # 요약
                        rs1, rs2, rs3, rs4, rs5 = st.columns(5)
                        rs1.metric("전체", len(all_requests))
                        rs2.metric("⏳ 검토중", len([r for r in all_requests if r["status"]=="pending"]))
                        rs3.metric("📧 동의대기", len([r for r in all_requests if r["status"] in ["approved","consent_sent"]]))
                        rs4.metric("✍️ 동의완료", len([r for r in all_requests if r["status"]=="consented"]))
                        rs5.metric("🟢 활성화", len([r for r in all_requests if r["status"]=="active"]))
                        st.divider()

                        umap_lr = {u["id"]: u["name"] for u in (supabase.table("users").select("id,name").execute().data or [])}
                        agency_map_lr = {a["id"]: a["name"] for a in get_all_agencies()}

                        if not all_requests:
                            st.info("신청 내역이 없습니다.")
                        else:
                            for req in all_requests:
                                status_badge = status_map_admin.get(req["status"], "?")
                                agency_name = agency_map_lr.get(req.get("agency_id",""), "직접신청")
                                req_date = str(req.get("created_at",""))[:10]

                                with st.expander(f"{status_badge} **{req['company_name']}** | {agency_name} | {req_date} | 관리자: {req.get('admin_name','')}"):
                                    # ─── 📅 라이선스 정보 (승인됐거나 활성화된 경우만) ───
                                    if req.get("license_start_date") and req.get("license_end_date"):
                                        from datetime import date as _date_disp
                                        try:
                                            _start = _date_disp.fromisoformat(req["license_start_date"][:10])
                                            _end = _date_disp.fromisoformat(req["license_end_date"][:10])
                                            _today = _date_disp.today()
                                            _days_left = (_end - _today).days

                                            # 잔여 기간 색상 + 메시지
                                            if _days_left < 0:
                                                _badge = "⚫ 만료"
                                                _color = "#6c757d"
                                                _msg = f"❌ {abs(_days_left)}일 전 만료됨"
                                            elif _days_left <= 30:
                                                _badge = "🔴 긴급"
                                                _color = "#dc3545"
                                                _msg = f"⚠️ 긴급: {_days_left}일 후 만료 — 즉시 갱신 필요"
                                            elif _days_left <= 90:
                                                _badge = "🟠 갱신 협상 시기"
                                                _color = "#fd7e14"
                                                _msg = f"⚠️ {_days_left}일 후 만료 — 갱신 진행 권장"
                                            elif _days_left <= 180:
                                                _badge = "🟡 예산 편성 시기"
                                                _color = "#ffc107"
                                                _msg = f"💡 {_days_left}일 후 만료 — 갱신 검토 필요"
                                            else:
                                                _badge = "🟢 정상"
                                                _color = "#28a745"
                                                _msg = f"✅ {_days_left}일 남음"

                                            st.markdown(
                                                f"""<div style="background:{_color}15;border-left:4px solid {_color};padding:12px 16px;border-radius:6px;margin-bottom:12px;">
                                                <div style="font-size:14px;color:{_color};font-weight:600;margin-bottom:4px;">📅 라이선스 상태: {_badge}</div>
                                                <div style="font-size:13px;color:#333;">{_msg}</div>
                                                <div style="font-size:12px;color:#666;margin-top:6px;">기간: {_start.isoformat()} ~ {_end.isoformat()} ({req.get('license_months','-')}개월) | 금액: {int(req.get('contract_amount') or 0):,}원 ({_pay_label(req.get('payment_type',''))})</div>
                                                </div>""",
                                                unsafe_allow_html=True
                                            )
                                            if req.get("payment_memo"):
                                                st.caption(f"💬 {req['payment_memo']}")
                                        except Exception as _lic_err:
                                            st.caption(f"라이선스 정보 표시 오류: {str(_lic_err)}")

                                    # 업체 정보
                                    lrc1, lrc2 = st.columns(2)
                                    with lrc1:
                                        st.markdown("**🏢 업체 정보**")
                                        st.write(f"업체명: {req.get('company_name','')}")
                                        st.write(f"사업자번호: {req.get('business_number','-')}")
                                        st.write(f"주소: {req.get('company_address','-')}")
                                        st.write(f"대표전화: {req.get('company_phone','-')}")
                                        st.write(f"플랜: {req.get('license_plan','basic')} | 사용자: {req.get('requested_users',5)}명")
                                    with lrc2:
                                        st.markdown("**👤 업체 관리자 정보**")
                                        st.write(f"이름: {req.get('admin_name','')}")
                                        st.write(f"이메일: {req.get('admin_email','')}")
                                        st.write(f"연락처: {req.get('admin_phone','')}")
                                        st.write(f"직함: {req.get('admin_title','-')}")
                                    if req.get("purpose"):
                                        st.caption(f"사용목적: {req['purpose']}")

                                    # ─── ♿ 장애인 정보 표시 ───
                                    if req.get("disability_office") or req.get("disability_org"):
                                        st.markdown("**♿ 장애인 고용 정보**")
                                        di1, di2 = st.columns(2)
                                        with di1:
                                            if req.get("disability_office"):
                                                st.write(f"관할 공단: {req['disability_office']}")
                                        with di2:
                                            if req.get("disability_org"):
                                                st.write(f"소속 단체: {req['disability_org']}")

                                    # ─── 📎 첨부파일 표시 ───
                                    biz_path = req.get("business_cert_path")
                                    add_files = req.get("additional_files") or []
                                    if biz_path or add_files:
                                        st.markdown("**📎 첨부 파일**")
                                        # 사업자등록증 다운로드 링크
                                        if biz_path:
                                            try:
                                                signed = supabase.storage.from_("license-documents").create_signed_url(biz_path, 3600)
                                                signed_url = signed.get("signedURL") or signed.get("signed_url") or ""
                                                if signed_url:
                                                    st.markdown(f"📄 사업자등록증 → [📥 다운로드]({signed_url})")
                                                else:
                                                    st.warning(f"📄 사업자등록증 (경로: {biz_path}) — 다운로드 링크 생성 실패")
                                            except Exception as dl_err:
                                                st.warning(f"📄 사업자등록증 다운로드 오류: {str(dl_err)}")
                                        # 추가 파일 다운로드 링크
                                        if add_files:
                                            st.caption(f"📂 추가 첨부 ({len(add_files)}건)")
                                            for af in add_files:
                                                af_path = af.get("path") if isinstance(af, dict) else None
                                                af_name = af.get("name","파일") if isinstance(af, dict) else "파일"
                                                if af_path:
                                                    try:
                                                        af_signed = supabase.storage.from_("license-documents").create_signed_url(af_path, 3600)
                                                        af_url = af_signed.get("signedURL") or af_signed.get("signed_url") or ""
                                                        if af_url:
                                                            st.markdown(f"  • {af_name} → [📥 다운로드]({af_url})")
                                                        else:
                                                            st.write(f"  • {af_name} (다운로드 실패)")
                                                    except Exception:
                                                        st.write(f"  • {af_name} (오류)")

                                    st.divider()

                                    # 액션 버튼
                                    if req["status"] == "pending":
                                        st.markdown("---")
                                        st.markdown("### 📅 라이선스 기간 설정 (승인 시 필수)")
                                        lc1, lc2, lc3 = st.columns([2, 1, 2])
                                        with lc1:
                                            from datetime import date as _date, timedelta as _td
                                            lic_start = st.date_input(
                                                "시작일 *",
                                                value=_date.today(),
                                                key=f"lic_start_{req['id']}"
                                            )
                                        with lc2:
                                            lic_months = st.number_input(
                                                "개월 수 *",
                                                min_value=1, max_value=36, value=12, step=1,
                                                key=f"lic_months_{req['id']}"
                                            )
                                        with lc3:
                                            # 종료일 자동 계산 (개월수 - 1일)
                                            try:
                                                _y = lic_start.year
                                                _m = lic_start.month + lic_months
                                                while _m > 12:
                                                    _m -= 12
                                                    _y += 1
                                                _calc_end = lic_start.replace(year=_y, month=_m) - _td(days=1)
                                                st.text_input(
                                                    "종료일 (자동 계산)",
                                                    value=_calc_end.isoformat(),
                                                    disabled=True,
                                                    key=f"lic_end_disp_{req['id']}"
                                                )
                                            except Exception:
                                                _calc_end = lic_start + _td(days=30 * lic_months)
                                                st.text_input(
                                                    "종료일 (자동 계산)",
                                                    value=_calc_end.isoformat(),
                                                    disabled=True,
                                                    key=f"lic_end_disp_{req['id']}"
                                                )

                                        st.markdown("### 💰 계약 정보 (매출 관리용)")
                                        cc1, cc2 = st.columns([2, 1])
                                        with cc1:
                                            # 콤마 자동 포맷팅을 위해 text_input 사용
                                            contract_amount_str = st.text_input(
                                                "계약 금액 (원) *",
                                                value=st.session_state.get(f"contract_amt_str_{req['id']}", ""),
                                                placeholder="예: 3,600,000",
                                                key=f"contract_amt_str_{req['id']}",
                                                help="숫자 입력 시 자동으로 콤마가 표시됩니다 (VAT 포함/별도는 메모에 기재)"
                                            )
                                            # 입력값에서 숫자만 추출하여 콤마 포맷 미리보기
                                            _digits_only = "".join(ch for ch in (contract_amount_str or "") if ch.isdigit())
                                            try:
                                                contract_amount = int(_digits_only) if _digits_only else 0
                                                if contract_amount > 0:
                                                    st.caption(f"💵 입력 금액: **{contract_amount:,}원**")
                                                else:
                                                    st.caption("⚠️ 금액을 입력해주세요")
                                            except Exception:
                                                contract_amount = 0
                                                st.caption("⚠️ 숫자만 입력해주세요")
                                        with cc2:
                                            payment_type = st.selectbox(
                                                "납입 종류 *",
                                                options=["monthly", "annual", "lump_sum"],
                                                format_func=lambda x: {"monthly":"📅 월납", "annual":"🗓️ 연납", "lump_sum":"💵 일시납"}[x],
                                                key=f"pay_type_{req['id']}"
                                            )
                                        payment_memo = st.text_input(
                                            "계약 메모 (선택)",
                                            placeholder="예: VAT 별도, 선납 할인, 분할납부 등",
                                            key=f"pay_memo_{req['id']}"
                                        )

                                        st.markdown("---")
                                        ac1, ac2, ac3 = st.columns(3)
                                        with ac1:
                                            admin_memo = st.text_input("관리자 메모", key=f"memo_{req['id']}", placeholder="검토 의견")
                                        with ac2:
                                            if st.button("✅ 승인", key=f"approve_{req['id']}", type="primary"):
                                                # 검증
                                                if contract_amount <= 0:
                                                    st.error("⚠️ 계약 금액을 입력해주세요. (매출 관리에 필요)")
                                                else:
                                                    supabase.table("license_requests").update({
                                                        "status": "approved",
                                                        "approved_at": datetime.now().isoformat(),
                                                        "approved_by": user["id"],
                                                        "admin_memo": st.session_state.get(f"memo_{req['id']}",""),
                                                        "license_start_date": lic_start.isoformat(),
                                                        "license_end_date": _calc_end.isoformat(),
                                                        "license_months": int(lic_months),
                                                        "contract_amount": int(contract_amount),
                                                        "payment_type": payment_type,
                                                        "payment_memo": payment_memo,
                                                    }).eq("id", req["id"]).execute()
                                                    st.success(f"✅ 승인됐습니다! 라이선스 기간: {lic_start} ~ {_calc_end} ({lic_months}개월) / 금액: {contract_amount:,}원")
                                                    st.rerun()
                                        with ac3:
                                            if st.button("❌ 반려", key=f"reject_{req['id']}"):
                                                supabase.table("license_requests").update({
                                                    "status": "rejected",
                                                    "admin_memo": st.session_state.get(f"memo_{req['id']}",""),
                                                }).eq("id", req["id"]).execute()
                                                st.warning("반려됐습니다.")
                                                st.rerun()

                                    elif req["status"] == "approved":
                                        st.markdown("**📧 동의 메일 발송**")
                                        consent_url = f"https://dragoneyes-appaqljjwd63ayd8n8vlts.streamlit.app/?req_id={req['id']}"
                                        mail_preview = f"""안녕하세요, {req.get('admin_name','')}님.

DragonEyes 모니터링 시스템 사용 신청이 승인되었습니다.

아래 링크를 클릭하여 서비스 이용 약관 및 조건을 확인하시고 동의해 주시면 라이선스가 즉시 활성화됩니다.

▶ 동의 페이지: {consent_url}

감사합니다.
DragonEyes 시스템 관리팀"""
                                        st.code(consent_url, language=None)
                                        with st.expander("📄 발송 메일 미리보기"):
                                            st.text(mail_preview)
                                        if st.button("📧 동의 메일 발송", key=f"send_consent_{req['id']}", type="primary"):
                                            try:
                                                supabase.table("hq_messages").insert({
                                                    "from_user_id": user["id"],
                                                    "from_name": "DragonEyes 관리팀",
                                                    "from_email": "kingcas7@gmail.com",
                                                    "subject": f"[DragonEyes] 서비스 이용 동의 요청 — {req['company_name']}",
                                                    "body": mail_preview,
                                                    "recipient": req.get("admin_email",""),
                                                }).execute()
                                                supabase.table("license_requests").update({
                                                    "status": "consent_sent",
                                                    "consent_sent_at": datetime.now().isoformat(),
                                                }).eq("id", req["id"]).execute()
                                                st.success(f"✅ {req.get('admin_email','')}으로 동의 메일 발송 저장됨!")
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"발송 오류: {str(e)}")

                                    elif req["status"] == "consented":
                                        st.success("✍️ 업체 관리자가 동의를 완료했습니다!")
                                        # 동의 기록 확인
                                        consent_recs = supabase.table("consent_records").select("*").eq("request_id", req["id"]).execute().data or []
                                        consent_items_map = {ci["id"]: ci["title"] for ci in (supabase.table("consent_items").select("id,title").execute().data or [])}
                                        if consent_recs:
                                            for cr in consent_recs:
                                                icon = "✅" if cr.get("consented") else "❌"
                                                st.caption(f"{icon} {consent_items_map.get(cr.get('consent_item_id',''), '?')} — {str(cr.get('consented_at',''))[:16]}")

                                        st.divider()
                                        st.markdown("**🟢 라이선스 활성화**")
                                        act1, act2 = st.columns(2)
                                        with act1:
                                            act_start = st.date_input("라이선스 시작일", key=f"act_start_{req['id']}")
                                            act_end = st.date_input("라이선스 종료일", key=f"act_end_{req['id']}")
                                        with act2:
                                            if st.button("🟢 라이선스 활성화", key=f"activate_{req['id']}", type="primary"):
                                                try:
                                                    # 업체 생성
                                                    new_tenant = supabase.table("tenants").insert({
                                                        "name": req["company_name"],
                                                        "license_plan": req.get("license_plan","basic"),
                                                        "max_users": req.get("requested_users", 5),
                                                        "is_active": True,
                                                        "contact_email": req.get("company_email",""),
                                                        "contact_phone": req.get("company_phone",""),
                                                        "license_start": str(act_start),
                                                        "license_end": str(act_end),
                                                    }).execute()
                                                    new_tenant_id = new_tenant.data[0]["id"]

                                                    # agency_tenants 연결
                                                    if req.get("agency_id"):
                                                        supabase.table("agency_tenants").insert({
                                                            "agency_id": req["agency_id"],
                                                            "tenant_id": new_tenant_id,
                                                        }).execute()

                                                    # 신청 상태 활성화
                                                    supabase.table("license_requests").update({
                                                        "status": "active",
                                                        "activated_at": datetime.now().isoformat(),
                                                        "tenant_id": new_tenant_id,
                                                    }).eq("id", req["id"]).execute()

                                                    st.success(f"🎉 {req['company_name']} 라이선스가 활성화됐습니다!")
                                                    st.rerun()
                                                except Exception as e:
                                                    st.error(f"활성화 오류: {str(e)}")

                                    elif req["status"] == "active":
                                        tenant_id = req.get("tenant_id")
                                        if tenant_id:
                                            t_users = get_tenant_users(tenant_id)
                                            st.success(f"🟢 활성화됨 | 소속 사용자 {len(t_users)}명")

                    except Exception as e:
                        st.error(f"신청 목록 조회 오류: {str(e)}")

                # ══════════════════════════════
                # 🗂️ 동의서 보관함 탭
                # ══════════════════════════════
                with admin_tab13:
                    st.subheader("🗂️ 동의서 보관함")
                    st.caption("모든 사용자의 최종사용자 이용약관 동의 기록이 자동으로 보관됩니다.")

                    try:
                        # 통계
                        all_users_consent = supabase.table("users").select("id,name,email,role_v2,terms_agreed,terms_agreed_at,terms_version").execute().data or []
                        agreed_users = [u for u in all_users_consent if u.get("terms_agreed")]
                        not_agreed = [u for u in all_users_consent if not u.get("terms_agreed")]

                        cs1, cs2, cs3, cs4 = st.columns(4)
                        cs1.metric("전체 사용자", f"{len(all_users_consent)}명")
                        cs2.metric("✅ 동의 완료", f"{len(agreed_users)}명")
                        cs3.metric("⏳ 미동의", f"{len(not_agreed)}명")
                        cs4.metric("현재 약관 버전", TERMS_VERSION)
                        st.divider()

                        # 필터
                        cf1, cf2, cf3 = st.columns(3)
                        with cf1:
                            consent_filter = st.selectbox("동의 상태",
                                ["전체", "동의완료", "미동의"],
                                key="consent_filter")
                        with cf2:
                            consent_search = st.text_input("이름/이메일 검색", key="consent_search")
                        with cf3:
                            # CSV 다운로드
                            import pandas as pd
                            consent_records = supabase.table("user_consents").select("*").order("consented_at", desc=True).execute().data or []
                            umap_c = {u["id"]: u for u in all_users_consent}
                            df_consent = pd.DataFrame([{
                                "이름": umap_c.get(r.get("user_id",""),{}).get("name",""),
                                "이메일": r.get("email",""),
                                "역할": role_label(umap_c.get(r.get("user_id",""),{}).get("role_v2","user")),
                                "동의버전": r.get("consent_version",""),
                                "동의일시": str(r.get("consented_at",""))[:16],
                            } for r in consent_records])
                            if not df_consent.empty:
                                csv_c = df_consent.to_csv(index=False, encoding="utf-8-sig")
                                st.download_button(
                                    "📥 동의서 목록 CSV",
                                    data=csv_c.encode("utf-8-sig"),
                                    file_name=f"동의서보관함_{date.today().strftime('%Y%m%d')}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )

                        # 동의 완료 목록
                        st.markdown("#### ✅ 동의 완료 사용자")
                        display_agreed = agreed_users
                        if consent_filter == "미동의":
                            display_agreed = []
                        if consent_search:
                            display_agreed = [u for u in display_agreed if consent_search in u.get("name","") or consent_search in u.get("email","")]

                        if display_agreed:
                            ch1, ch2, ch3, ch4, ch5 = st.columns([2, 2.5, 1.5, 1.5, 1])
                            ch1.markdown("**이름**")
                            ch2.markdown("**이메일**")
                            ch3.markdown("**역할**")
                            ch4.markdown("**동의일시**")
                            ch5.markdown("**버전**")
                            st.divider()
                            for u in display_agreed:
                                uc1, uc2, uc3, uc4, uc5 = st.columns([2, 2.5, 1.5, 1.5, 1])
                                uc1.write(f"✅ {u.get('name','')}")
                                uc2.caption(u.get("email",""))
                                uc3.caption(role_label(u.get("role_v2","user")))
                                uc4.caption(str(u.get("terms_agreed_at",""))[:16])
                                uc5.caption(u.get("terms_version","-"))
                        elif consent_filter != "미동의":
                            st.info("동의 완료 사용자가 없습니다.")

                        # 미동의 목록
                        if consent_filter != "동의완료":
                            st.divider()
                            st.markdown("#### ⏳ 미동의 사용자")
                            display_not = not_agreed
                            if consent_search:
                                display_not = [u for u in display_not if consent_search in u.get("name","") or consent_search in u.get("email","")]
                            if display_not:
                                for u in display_not:
                                    nc1, nc2, nc3, nc4 = st.columns([2, 2.5, 2, 1.5])
                                    nc1.write(f"⏳ {u.get('name','')}")
                                    nc2.caption(u.get("email",""))
                                    nc3.caption(role_label(u.get("role_v2","user")))
                                    with nc4:
                                        # 동의 독려 버튼
                                        if st.button("📧 동의 독려", key=f"nudge_{u['id']}"):
                                            nudge_body = "안녕하세요 " + u.get("name","") + "님.\n\nDragonEyes 시스템 이용을 위해 로그인 후 이용약관에 동의해 주시기 바랍니다.\n\n감사합니다."
                                            send_notification(user["id"], "individual", u["id"], "email",
                                                "[DragonEyes] 이용약관 동의 요청",
                                                nudge_body)
                                            st.success("✅ " + u.get("name","") + "님에게 독려 메일 발송!")
                            else:
                                st.success("🎉 모든 사용자가 동의를 완료했습니다!")

                        # 상세 동의 기록
                        st.divider()
                        with st.expander("📜 전체 동의 기록 (상세)", expanded=False):
                            if consent_records:
                                st.caption(f"총 {len(consent_records)}건")
                                for r in consent_records[:50]:
                                    u_info = umap_c.get(r.get("user_id",""), {})
                                    st.markdown(f"✅ **{u_info.get('name',r.get('name','?'))}** `{r.get('email','')}` | 버전 {r.get('consent_version','')} | {str(r.get('consented_at',''))[:16]}")
                            else:
                                st.info("동의 기록이 없습니다.")

                        # 약관 버전 관리
                        st.divider()
                        with st.expander("⚙️ 약관 버전 관리 (전체 재동의 요청)", expanded=False):
                            st.warning(f"현재 버전: **{TERMS_VERSION}** | 새 버전으로 업데이트하면 모든 사용자가 다음 로그인 시 재동의해야 합니다.")
                            st.code(f'TERMS_VERSION = "{TERMS_VERSION}"', language="python")
                            st.caption("버전 변경은 app.py의 TERMS_VERSION 상수를 수정 후 배포하세요.")

                    except Exception as e:
                        st.error(f"동의서 조회 오류: {str(e)}")

                # 동의 항목 관리
                with st.expander("⚙️ 동의 항목 관리 (시스템관리자 전용)", expanded=False):
                    try:
                        ci_list = supabase.table("consent_items").select("*").order("order_num").execute().data or []
                        st.caption(f"현재 동의 항목 {len(ci_list)}개")
                        for ci in ci_list:
                            cic1, cic2 = st.columns([5, 1])
                            cic1.markdown(f"**{ci['order_num']}. {ci['title']}** {'[필수]' if ci['is_required'] else '[선택]'}")
                            cic1.caption(ci['content'][:80] + "...")
                            with cic2:
                                toggle = "❌ 비활성화" if ci.get("is_active") else "✅ 활성화"
                                if st.button(toggle, key=f"ci_toggle_{ci['id']}"):
                                    supabase.table("consent_items").update({"is_active": not ci.get("is_active")}).eq("id", ci["id"]).execute()
                                    st.rerun()
                    except Exception as e:
                        st.error(f"동의 항목 조회 오류: {str(e)}")