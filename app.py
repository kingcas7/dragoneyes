import streamlit as st
import anthropic
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from supabase import create_client
from datetime import date, datetime, timedelta
import pandas as pd

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

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
</style>
""", unsafe_allow_html=True)

DAILY_DRAGON_LIMIT = 2
MONTHLY_DRAGON_LIMIT = 20

# 대화형 AI 제한
CHAT_DAILY_LIMIT = 40
CHAT_WEEKLY_LIMIT = 100
CHAT_MONTHLY_LIMIT = 400

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
    "chat_history": [],  # 대화형 AI 히스토리
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
    """평일(월~금) 여부 확인"""
    return datetime.now().weekday() < 5  # 0=월, 4=금, 5=토, 6=일

def get_chat_token_info(user_id):
    """월간 채팅 토큰 정보"""
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
    """오늘 사용한 채팅 턴 수"""
    today = date.today().isoformat()
    res = supabase.table("chat_logs").select("id").eq("user_id", user_id).gte("created_at", today).execute()
    return len(res.data)

def get_chat_week_count(user_id):
    """이번 주 월요일부터 오늘까지 사용한 턴 수"""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    res = supabase.table("chat_logs").select("id").eq("user_id", user_id).gte("created_at", monday.isoformat()).execute()
    return len(res.data)

def can_use_chat(user_id):
    """채팅 사용 가능 여부 및 현황"""
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
    """채팅 1턴 사용 처리"""
    ym = date.today().strftime("%Y-%m")
    info = get_chat_token_info(user_id)
    supabase.table("chat_tokens").update({
        "used_count": info["used_count"] + 1,
        "updated_at": datetime.now().isoformat()
    }).eq("user_id", user_id).eq("year_month", ym).execute()

def add_chat_extra_tokens(user_id, amount):
    """관리자가 추가 토큰 배정"""
    ym = date.today().strftime("%Y-%m")
    info = get_chat_token_info(user_id)
    supabase.table("chat_tokens").update({
        "extra_tokens": info.get("extra_tokens", 0) + amount,
        "updated_at": datetime.now().isoformat()
    }).eq("user_id", user_id).eq("year_month", ym).execute()

def chat_with_ai(messages_history, user_message, lang="ko"):
    """대화형 AI 호출 (히스토리 3턴 유지)"""
    system_prompt = {
        "ko": """당신은 Dragon J Holdings의 드래곤파더입니다. DragonEyes 팀의 든든한 AI 동반자입니다.
아동 온라인 안전, 그루밍 패턴, 보고서 작성 등 업무 질문은 물론, 일상 대화, 고민 상담, 잡담, 유머, 퀴즈 등 어떤 주제든 자유롭게 대화할 수 있습니다.
팀원들이 즐겁고 편안하게 일할 수 있도록 친근하고 따뜻하게 대화해주세요.""",
        "en": """You are DragonFather, the friendly AI companion of Dragon J Holdings DragonEyes team.
You can help with child safety work, grooming patterns, and reports — but also chat freely about anything: daily life, jokes, trivia, advice, or casual conversation.
Be warm, fun, and supportive. Help the team enjoy their work.""",
        "ja": """あなたはDragon J Holdings DragonEyesチームの頼れるAIコンパニオン、ドラゴンファーザーです。
子どもの安全業務はもちろん、日常会話、悩み相談、雑談、ユーモア、クイズなど、どんな話題でも自由に話せます。
チームメンバーが楽しく快適に仕事できるよう、親しみやすく温かく接してください。"""
    }
    # 최근 3턴만 유지
    recent = messages_history[-6:] if len(messages_history) > 6 else messages_history
    recent.append({"role": "user", "content": user_message[:300]})  # 질문 300자 제한

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=system_prompt.get(lang, system_prompt["ko"]),
        messages=recent
    )
    return msg.content[0].text

def translate_to_english(text):
    """한국어/일본어 텍스트를 영어로 자동 번역"""
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

        # 한국어/일본어인 경우 영어 번역 자동 생성
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
        # 1000개 초과 시 오래된 것 삭제
        all_urls = supabase.table("analyzed_urls").select("id").order("analyzed_at", desc=False).execute()
        if len(all_urls.data) > 1000:
            old_ids = [r["id"] for r in all_urls.data[:len(all_urls.data)-1000]]
            for oid in old_ids:
                supabase.table("analyzed_urls").delete().eq("id", oid).execute()
    except Exception:
        pass

# ── 토큰 관련 ──
def get_token_info(user_id):
    ym = date.today().strftime("%Y-%m")
    res = supabase.table("dragon_tokens").select("*").eq("user_id", user_id).eq("year_month", ym).execute()
    if res.data:
        return res.data[0]
    # 없으면 생성
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
    for cat in ["그루밍", "성인", "부적절", "스팸", "안전"]:
        if cat in text:
            return cat
    return "미분류"

def sev_icon(s):
    return {1:"✅", 2:"🟡", 3:"🟠", 4:"🔴", 5:"🚨"}.get(s, "❓")

def search_type_label(st_val):
    return {
        "dragon_general": "🐉 일반추천",
        "dragon_roblox":  "🎮 Roblox추천",
        "dragon_minecraft":"⛏️ Minecraft추천",
        "keyword":        "🔍 키워드탐색",
    }.get(st_val, st_val)

def go_to(page, from_tab=None):
    st.session_state.prev_page = st.session_state.current_page
    if from_tab is not None:
        st.session_state.active_tab = from_tab
    st.session_state.current_page = page

def go_back():
    st.session_state.current_page = st.session_state.prev_page
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
    prompts = {
        "general": """아동 안전 모니터링을 위해 유튜브에서 검색할 키워드 10개를 한 줄에 하나씩 출력해주세요.
아동 그루밍, 미성년자 접촉 시도, 청소년 대상 부적절 콘텐츠를 찾을 수 있는 한국어 키워드여야 합니다.
설명 없이 키워드만 출력하세요.""",
        "roblox": """Roblox 게임 플랫폼 아동 안전 모니터링을 위해 유튜브에서 검색할 키워드 10개를 한 줄에 하나씩 출력해주세요.
Roblox에서 발생하는 아동 그루밍, 미성년자 접촉 시도를 찾을 수 있는 한국어 키워드여야 합니다.
설명 없이 키워드만 출력하세요.""",
        "minecraft": """Minecraft 게임 플랫폼 아동 안전 모니터링을 위해 유튜브에서 검색할 키워드 10개를 한 줄에 하나씩 출력해주세요.
Minecraft에서 발생하는 아동 그루밍, 미성년자 접촉 시도를 찾을 수 있는 한국어 키워드여야 합니다.
설명 없이 키워드만 출력하세요.""",
    }
    msg = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=512,
        messages=[{"role": "user", "content": prompts[platform]}]
    )
    return parse_keywords(msg.content[0].text)

def search_and_analyze(keyword, max_results=5, analyzed_urls=None, search_type="keyword", assigned_to=None):
    if analyzed_urls is None:
        analyzed_urls = set()
    sr = youtube.search().list(
        part="snippet", q=keyword, type="video",
        maxResults=max_results+3, relevanceLanguage="ko"
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
        desc = item["snippet"].get("description","")[:200]
        channel = item["snippet"]["channelTitle"]
        msg = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=300,
            messages=[{"role":"user","content":f"""아동 안전 모니터링 전문가로서 분석해주세요.
제목: {title}
설명: {desc}
채널: {channel}
형식:
심각도: (1~5)
분류: (안전/스팸/부적절/성인/그루밍)
이유: (한 줄)"""}]
        )
        rt = msg.content[0].text
        sev = extract_severity(rt)
        cat = extract_category(rt)
        mark_url_analyzed(url, title, search_type, assigned_to)
        results.append({
            "id": vid, "title": title, "channel": channel,
            "url": url, "keyword": keyword, "analysis": rt,
            "severity": sev, "category": cat, "search_type": search_type
        })
        analyzed_urls.add(url)
    return results

# ══════════════════════════════
# 로그인 화면
# ══════════════════════════════
if st.session_state.user is None:
    # 로그인 화면 언어 선택
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
    is_admin = user.get("role") == "admin"
    page = st.session_state.current_page

    # ── 상단 헤더 ──
    h1, h2, hf, h6, h7, h8 = st.columns([3, 1, 2, 1, 1, 1])
    with h1:
        st.title(t("app_title"))
    with h2:
        st.metric(t("this_month"), f"{st.session_state.report_count}{t('unit_reports')}")
    with hf:
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.markdown('<div style="font-size:2rem; text-align:center; line-height:1.2">🇰🇷</div>', unsafe_allow_html=True)
            if st.button("한국어", use_container_width=True, key="flag_ko"):
                st.session_state.lang = "ko"; st.rerun()
        with fc2:
            st.markdown('<div style="font-size:2rem; text-align:center; line-height:1.2">🇺🇸</div>', unsafe_allow_html=True)
            if st.button("English", use_container_width=True, key="flag_en"):
                st.session_state.lang = "en"; st.rerun()
        with fc3:
            st.markdown('<div style="font-size:2rem; text-align:center; line-height:1.2">🇯🇵</div>', unsafe_allow_html=True)
            if st.button("日本語", use_container_width=True, key="flag_ja"):
                st.session_state.lang = "ja"; st.rerun()
    with h6:
        if st.button(t("home"), use_container_width=True):
            go_home(); st.rerun()
    with h7:
        if st.button(t("write_report"), use_container_width=True):
            open_report_form(from_tab=st.session_state.active_tab); st.rerun()
    with h8:
        if st.button(t("logout")):
            st.query_params.clear()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    st.divider()

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
            content_en = r.get("content_en", "")
            lang = st.session_state.get("lang", "ko")
            orig_flag = "🇰🇷" if lang == "ko" else ("🇯🇵" if lang == "ja" else "🇺🇸")

            if result_en:
                # 병기 표시
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
    # 홈 랜딩 페이지
    # ══════════════════════════════
    elif page == "home_landing":
        lang = st.session_state.get("lang", "ko")

        # ── 인사말 + 드래곤파더 나란히 ──
        left_col, right_col = st.columns([1, 1])

        with left_col:
            st.subheader(t("greeting", user['name']))
            st.divider()
            token_info = can_use_dragon(user["id"])
            all_my = supabase.table("reports").select("id,severity,created_at").eq("user_id", user["id"]).execute()
            df_my = pd.DataFrame(all_my.data) if all_my.data else pd.DataFrame()
            this_month = date.today().strftime("%Y-%m")

            m1, m2 = st.columns(2)
            month_cnt = len(df_my[df_my["created_at"].str[:7] == this_month]) if not df_my.empty else 0
            target = user.get("monthly_target", 10)
            rate = min(int(month_cnt / target * 100), 100) if target > 0 else 0
            m1.metric(t("month_report"), f"{month_cnt}{t('unit_reports')}", t("goal", target))
            m2.metric(t("achievement"), f"{rate}%")
            m3, m4 = st.columns(2)
            m3.metric(t("dragon_token"), t("token_remain", token_info['monthly_remaining']))
            m4.metric("📜 " + t("tab_history"), f"{len(st.session_state.search_results) + len(st.session_state.recommend_results)}" + t("pending_list"))
            st.progress(rate / 100)

            st.divider()
            st.subheader(t("shortcut"))
            g1, g2 = st.columns(2)
            with g1:
                if st.button(t("tab_text"), use_container_width=True):
                    st.session_state.current_page = "home"; st.rerun()
                if st.button(t("tab_dragon"), use_container_width=True):
                    st.session_state.current_page = "home"; st.rerun()
            with g2:
                if st.button(t("tab_youtube"), use_container_width=True):
                    st.session_state.current_page = "home"; st.rerun()
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
                        if st.button(t("write_btn"), key=f"home_rep_{d['id']}"):
                            open_report_form(d["url"], "", 1, "안전", "YouTube", from_tab=4)
                            st.session_state.current_page = "report_form"; st.rerun()

        # ── 드래곤파더 채팅 (오른쪽) ──
        with right_col:
            st.markdown("""
            <style>
            div[data-testid="stVerticalBlock"]:has(> div > div > #dragonfather_anchor) {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                border: 1px solid #e94560;
                border-radius: 12px;
                box-shadow: 0 4px 24px rgba(233,69,96,0.35), 0 0 40px rgba(15,52,96,0.5);
                padding: 1.2rem 1rem 0.5rem 1rem;
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown('<span id="dragonfather_anchor"></span>', unsafe_allow_html=True)

            chat_info = can_use_chat(user["id"])
            st.subheader("🐲 드래곤파더")
            ct1, ct2, ct3 = st.columns(3)
            ct1.metric("오늘", f"{chat_info.get('today_used',0)}/{CHAT_DAILY_LIMIT}")
            ct2.metric("이번주", f"{chat_info.get('week_used',0)}/{CHAT_WEEKLY_LIMIT}")
            ct3.metric("이번달", f"{chat_info.get('monthly_used',0)}/{chat_info.get('monthly_limit', CHAT_MONTHLY_LIMIT)}")

            chat_box = st.container(height=320)
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
                if reason == "weekend":
                    st.warning("😊 주말에는 쉽니다. 월요일에 만나요!")
                elif reason == "daily":
                    st.warning(f"오늘 한도({CHAT_DAILY_LIMIT}턴) 도달")
                elif reason == "weekly":
                    st.warning(f"이번 주 한도({CHAT_WEEKLY_LIMIT}턴) 도달")
                elif reason == "monthly":
                    st.warning("이번 달 한도 도달. 관리자에게 추가 요청하세요.")

            ic1, ic2 = st.columns([5, 1])
            with ic1:
                home_input = st.chat_input(
                    "드래곤파더에게 질문하세요... (300자)" if chat_info["ok"] else "사용 불가",
                    max_chars=300,
                    disabled=not chat_info["ok"],
                    key="home_chat_input"
                )
            with ic2:
                if st.button("🗑️", help="대화 초기화", key="clear_chat_home"):
                    st.session_state.chat_history = []; st.rerun()

            if home_input and chat_info["ok"]:
                st.session_state.chat_history.append({"role": "user", "content": home_input})
                with st.spinner("🐲 드래곤파더가 답변 중..."):
                    try:
                        api_history = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.chat_history[:-1]
                        ]
                        response = chat_with_ai(api_history, home_input, lang)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        supabase.table("chat_logs").insert({
                            "user_id": user["id"],
                            "message": home_input,
                            "response": response,
                            "tokens_used": 1
                        }).execute()
                        use_chat_token(user["id"])
                        st.rerun()
                    except Exception as e:
                        st.session_state.chat_history.pop()
                        st.error(f"오류: {str(e)}")

    # ══════════════════════════════
    # 홈 대시보드
    # ══════════════════════════════
    elif page == "home":

        # ── 채팅창 (탭 위 고정) ──
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

            # 대화 내용
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

            # 사용 불가 안내
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

            # 입력창 + 초기화
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

        tab_labels = [t("tab_text"), t("tab_youtube"), t("tab_keyword"),
                      t("tab_dragon"), t("tab_history"), t("tab_reports"), t("tab_stats"), "🐲 드래곤파더"]
        if is_admin:
            tab_labels.append(t("tab_admin"))
        tabs = st.tabs(tab_labels)
        tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab_chat = tabs[0],tabs[1],tabs[2],tabs[3],tabs[4],tabs[5],tabs[6],tabs[7]
        tab8 = tabs[8] if is_admin else None

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

            btn1, btn2, btn3 = st.columns(3)
            with btn1:
                run_general = st.button(t("dragon_general"), use_container_width=True, disabled=not token_info["ok"])
            with btn2:
                run_roblox = st.button(t("dragon_roblox"), use_container_width=True, disabled=not token_info["ok"])
            with btn3:
                run_minecraft = st.button(t("dragon_minecraft"), use_container_width=True, disabled=not token_info["ok"])

            selected_platform = None
            selected_label = ""
            selected_type = ""
            if run_general:
                selected_platform = "general"; selected_label = "🐉 일반"; selected_type = "dragon_general"
            elif run_roblox:
                selected_platform = "roblox"; selected_label = "🎮 Roblox"; selected_type = "dragon_roblox"
            elif run_minecraft:
                selected_platform = "minecraft"; selected_label = "⛏️ Minecraft"; selected_type = "dragon_minecraft"

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
                    existing_urls = {r["url"] for r in existing}
                    merged = all_results + [r for r in existing if r["url"] not in {x["url"] for x in all_results}]
                    st.session_state.recommend_results = merged
                    use_dragon_token(user["id"])
                    st.success(f"완료! {selected_label} — {len(all_results)}개 중 주의 필요 {len(risky)}개 발견")
                except Exception as e:
                    st.error(f"오류: {str(e)}")

            if st.session_state.recommend_results:
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

            # 필터
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                ftype = st.selectbox(t("filter_type"), ["전체","🐉 일반추천","🎮 Roblox추천","⛏️ Minecraft추천","🔍 키워드탐색"])
            with fc2:
                freported = st.selectbox(t("filter_reported"), ["전체",t("reported"),t("not_reported")])
            with fc3:
                fdate = st.date_input(t("after_date"), value=None, key="hist_date")

            # 관리자는 전체, 일반은 자신 것만
            if is_admin:
                hist = supabase.table("analyzed_urls").select("*").order("analyzed_at", desc=True).limit(1000).execute()
            else:
                hist = supabase.table("analyzed_urls").select("*").eq("assigned_to", user["id"]).order("analyzed_at", desc=True).limit(1000).execute()

            data = hist.data if hist.data else []

            # 필터 적용
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

            # 담당자 이름 캐시
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

            # 전체 보고서 (모든 사용자 열람 가능)
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

                # 정렬
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

                # 관리자 일괄 발송 버튼
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
                        # 관리자: 개별 이메일 발송 버튼
                        if is_admin:
                            if st.button("📧 발송", key=f"email_{r['id']}"):
                                st.session_state[f"show_email_{r['id']}"] = True
                    with cd:
                        if can_edit_r:
                            if st.button("🗑️ 삭제", key=f"del_{r['id']}"):
                                if delete_report(r["id"]): st.rerun()

                    # 개별 이메일 발송 UI (인라인)
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

                                # 병기 미리보기
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

        # ── 관리자 ──
        # ── 대화형 AI 채팅 ──
        with tab_chat:
            st.subheader("🐲 드래곤파더")
            lang = st.session_state.get("lang", "ko")

            # 사용 현황
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

            # 사용 불가 사유
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

            # 대화 히스토리 표시
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

            # 입력창
            if chat_info["ok"]:
                user_input = st.chat_input("드래곤파더에게 질문하세요... (최대 300자)", max_chars=300)
                if user_input:
                    # 히스토리에 사용자 메시지 추가
                    st.session_state.chat_history.append({"role": "user", "content": user_input})

                    with st.spinner("🐲 드래곤파더가 답변 중..."):
                        try:
                            # API 호출용 히스토리 (최근 6개 = 3턴)
                            api_history = [
                                {"role": m["role"], "content": m["content"]}
                                for m in st.session_state.chat_history[:-1]
                            ]
                            response = chat_with_ai(api_history, user_input, lang)

                            # 응답 히스토리에 추가
                            st.session_state.chat_history.append({"role": "assistant", "content": response})

                            # DB 저장 + 토큰 차감
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

            # 대화 초기화 버튼
            if st.session_state.chat_history:
                if st.button("🗑️ 대화 초기화", key="clear_chat"):
                    st.session_state.chat_history = []
                    st.rerun()

        if is_admin and tab8:
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
                            summary.append({
                                "이름": u["name"],
                                "이번달": len(mr),
                                "목표": tgt,
                                "달성률": f"{rt}%",
                                "누적": len(ur),
                                "드래곤토큰": f"{ti['used_count']}/{MONTHLY_DRAGON_LIMIT+ti.get('extra_tokens',0)}회"
                            })
                        st.dataframe(pd.DataFrame(summary), use_container_width=True)

                    st.subheader("💬 팀원에게 코멘트")
                    all_users_data2 = supabase.table("users").select("*").execute()
                    tu_name = st.selectbox(t("select_member"), [u["name"] for u in all_users_data2.data])
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

                    # 미배정 목록
                    unassigned = supabase.table("analyzed_urls").select("*").is_("assigned_to", "null").order("analyzed_at", desc=True).limit(100).execute()
                    # 1주일 경과 미작성 목록
                    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                    overdue = supabase.table("analyzed_urls").select("*").eq("reported", False).lt("analyzed_at", week_ago).order("analyzed_at", desc=True).limit(100).execute()

                    assign_target = st.selectbox("배정할 담당자", [u["name"] for u in (all_users_data3.data or [])], key="assign_target")
                    assign_user_id = next((u["id"] for u in (all_users_data3.data or []) if u["name"]==assign_target), None)

                    st.markdown(f"**미배정 목록 ({len(unassigned.data)}건)**")
                    selected_unassigned = []
                    for d in (unassigned.data or []):
                        col_a, col_b = st.columns([5,1])
                        with col_a:
                            st.caption(f"{search_type_label(d.get('search_type',''))} | {str(d.get('analyzed_at',''))[:10]} | {d.get('title','')[:40]}")
                        with col_b:
                            if st.button("배정", key=f"assign_{d['id']}"):
                                supabase.table("analyzed_urls").update({
                                    "assigned_to": assign_user_id,
                                    "assigned_at": datetime.now().isoformat()
                                }).eq("id", d["id"]).execute()
                                st.success(f"{assign_target}님께 배정됨"); st.rerun()

                    st.divider()
                    st.markdown(f"**⚠️ 1주일 경과 미작성 목록 ({len(overdue.data)}건)**")
                    for d in (overdue.data or []):
                        col_a, col_b = st.columns([5,1])
                        with col_a:
                            current_assignee = umap.get(d.get("assigned_to",""), t("unassigned"))
                            st.caption(f"{search_type_label(d.get('search_type',''))} | 담당: {current_assignee} | {str(d.get('analyzed_at',''))[:10]} | {d.get('title','')[:40]}")
                        with col_b:
                            if st.button("재배정", key=f"reassign_{d['id']}"):
                                supabase.table("analyzed_urls").update({
                                    "assigned_to": assign_user_id,
                                    "assigned_at": datetime.now().isoformat()
                                }).eq("id", d["id"]).execute()
                                st.success(f"{assign_target}님께 재배정됨"); st.rerun()

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
                            st.write(f"**{u['name']}** — 이번달 {ti['used_count']}/{total}회 사용")
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

                    # 수신자 추가
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

                    # 수신자 목록
                    st.subheader("등록된 수신자 목록")
                    recs = supabase.table("email_recipients").select("*").order("created_at", desc=False).execute()
                    type_label = {"agency":"🏢 기관","client":"👤 의뢰인","lawyer":"⚖️ 변호사"}
                    for rc in (recs.data or []):
                        rc1, rc2, rc3 = st.columns([5, 1, 1])
                        with rc1:
                            status = "✅ 활성" if rc.get("active") else "❌ 비활성"
                            st.markdown(f"**{rc['name']}** {type_label.get(rc.get('type',''),'')} | {rc['email']} | {status}")
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
                            st.write(f"**{u['name']}** — 이번달 {ct['used_count']}/{total}턴 | 오늘 {today_used}/{CHAT_DAILY_LIMIT}턴 | 이번주 {week_used}/{CHAT_WEEKLY_LIMIT}턴")
                        with cc2:
                            extra = st.number_input("추가", min_value=0, max_value=500, value=0, key=f"chat_tok_{u['id']}", label_visibility="collapsed")
                        with cc3:
                            if st.button("배정", key=f"chat_tok_btn_{u['id']}"):
                                if extra > 0:
                                    add_chat_extra_tokens(u["id"], extra)
                                    st.success(f"{u['name']}님께 {extra}턴 추가됨"); st.rerun()
                        st.divider()

                    # 채팅 로그 최근 50건
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