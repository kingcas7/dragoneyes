"""DragonEyes 시각장애인 접근성 모듈 (2026-06-08 신규)

Web Speech API 기반 음성 안내 + 키보드 단축키 + 사용자 선호 저장.
WCAG 2.1 AA · KWCAG 2.2 · ARIA 1.2 표준 지향.

설계 출처: docs/v2.1_pending_additions.md §음성 안내 시스템
설정 저장: users.preferences JSONB 컬럼
    예: {"voice_guide_enabled": true, "voice_speed": 1.0, "voice_lang": "ko-KR"}

핵심 원칙
1. 기본값 OFF — 사용자가 직접 토글
2. 분리 페이지 없음 — 같은 페이지에서 모드 활성화
3. 자동 감지 없음 — 사용자 선택권 존중
4. 모든 사용자에게 동일한 시스템 — 선택의 자유

주요 함수
- init_state()          — session_state 초기화 (idempotent)
- announce(text)        — 즉시 음성 발화 (off면 no-op)
- render_toolbar(...)   — 사이드 컨트롤 위젯 (토글·속도)
- load_from_user(u)     — DB → session_state
- save_to_user(sb, uid) — session_state → DB
- inject_shortcuts()    — Alt+A/M/H 단축키 (1회 inject)
"""

from __future__ import annotations

import json
from typing import Any, Optional

import streamlit as st
import streamlit.components.v1 as components


# ══════════════════════════════════════════════════════════════
# 1. session_state 초기화
# ══════════════════════════════════════════════════════════════
def init_state() -> None:
    """음성 안내 관련 session_state 키를 초기화. 멱등."""
    st.session_state.setdefault("voice_guide_enabled", False)
    st.session_state.setdefault("voice_speed", 1.0)
    st.session_state.setdefault("voice_lang", "ko-KR")


# ══════════════════════════════════════════════════════════════
# 2. DB ↔ session_state 동기화
# ══════════════════════════════════════════════════════════════
def load_from_user(user_dict: Optional[dict]) -> None:
    """로그인 직후 users.preferences → session_state.

    Supabase JSONB 컬럼은 dict로 반환되지만, str 형태로 올 가능성도 방어.
    """
    init_state()
    prefs: Any = (user_dict or {}).get("preferences") or {}
    if isinstance(prefs, str):
        try:
            prefs = json.loads(prefs)
        except Exception:
            prefs = {}
    if not isinstance(prefs, dict):
        return
    if "voice_guide_enabled" in prefs:
        st.session_state["voice_guide_enabled"] = bool(prefs["voice_guide_enabled"])
    if "voice_speed" in prefs:
        try:
            v = float(prefs["voice_speed"])
            st.session_state["voice_speed"] = max(0.5, min(2.0, v))
        except Exception:
            pass
    if "voice_lang" in prefs:
        st.session_state["voice_lang"] = str(prefs["voice_lang"])


def save_to_user(supabase, user_id) -> None:
    """session_state → users.preferences (Supabase upsert).

    preferences 컬럼이 없으면 무음 실패 (마이그레이션 미적용 환경 보호).
    """
    if not supabase or not user_id:
        return
    prefs = {
        "voice_guide_enabled": bool(st.session_state.get("voice_guide_enabled", False)),
        "voice_speed": float(st.session_state.get("voice_speed", 1.0)),
        "voice_lang": str(st.session_state.get("voice_lang", "ko-KR")),
    }
    try:
        # 기존 preferences가 있으면 merge가 안전하지만, 현재는 음성만 저장.
        # 향후 항목 추가 시 select → merge → update 패턴으로 확장.
        supabase.table("users").update({"preferences": prefs}).eq("id", user_id).execute()
    except Exception:
        # preferences 컬럼 없거나 권한 문제 — 조용히 패스 (UI엔 영향 없음)
        pass


# ══════════════════════════════════════════════════════════════
# 3. TTS — 한 번 발화
# ══════════════════════════════════════════════════════════════
def announce(text: str, *, lang: Optional[str] = None, interrupt: bool = True) -> None:
    """텍스트를 즉시 음성으로 발화. voice_guide_enabled=False면 no-op.

    Args:
        text: 발화할 텍스트 (빈 문자열은 무시).
        lang: 언어 코드 (기본 session_state['voice_lang'] = 'ko-KR').
        interrupt: True면 진행 중인 발화를 중단하고 새로 시작.

    구현 메모:
        Streamlit components.html은 매번 새 iframe을 만든다.
        height=0으로 시각적 영향을 제거하고, SpeechSynthesisUtterance만 호출.
        Web Speech API는 첫 발화에 사용자 제스처가 필요할 수 있음(브라우저 정책).
        → 토글 ON 동작이 사용자 제스처 역할을 함.
    """
    if not text:
        return
    if not st.session_state.get("voice_guide_enabled"):
        return
    speed = float(st.session_state.get("voice_speed", 1.0))
    lang = lang or st.session_state.get("voice_lang", "ko-KR")
    js_text = json.dumps(str(text))
    js_lang = json.dumps(str(lang))
    js_interrupt = json.dumps(bool(interrupt))
    # 부모 컨텍스트에 등록된 _dragoneyesSpeak 호출 (iframe 격리 회피).
    # inject_shortcuts()에서 미리 등록됨. 없으면 직접 호출(폴백).
    components.html(
        f"""
        <script>
        (function() {{
            try {{
                const w = window.parent || window;
                // 1순위: 부모 컨텍스트의 _dragoneyesSpeak (iframe sandbox 회피)
                if (typeof w._dragoneyesSpeak === 'function') {{
                    w._dragoneyesSpeak({js_text}, {js_lang}, {speed}, {js_interrupt});
                    return;
                }}
                // 폴백: iframe 내 직접 호출 (브라우저 정책으로 차단될 수 있음)
                if (!('speechSynthesis' in w)) return;
                if ({js_interrupt}) {{
                    w.speechSynthesis.cancel();
                }}
                const u = new w.SpeechSynthesisUtterance({js_text});
                u.lang = {js_lang};
                u.rate = {speed};
                u.pitch = 1.0;
                u.volume = 1.0;
                w.speechSynthesis.speak(u);
            }} catch (e) {{
                console.error('DragonEyes TTS error:', e);
            }}
        }})();
        </script>
        """,
        height=0,
    )


# ══════════════════════════════════════════════════════════════
# 4. 사용자 토글 위젯
# ══════════════════════════════════════════════════════════════
def render_toolbar(
    *,
    supabase=None,
    user_id=None,
    key_prefix: str = "a11y",
    compact: bool = False,
) -> None:
    """페이지 상단에 음성 안내 컨트롤 렌더링.

    한 줄 구조: [🔊 음성 안내 토글] [속도 슬라이더] [단축키 안내]

    토글·속도 변경 시 즉시 DB에 저장 (supabase + user_id 제공된 경우).

    Args:
        supabase: Supabase 클라이언트 (None이면 DB 저장 생략).
        user_id: users.id (None이면 DB 저장 생략, session만 유지).
        key_prefix: 위젯 key 충돌 방지용 prefix.
        compact: True면 도움말 텍스트 생략.
    """
    init_state()
    prev_enabled = bool(st.session_state.get("voice_guide_enabled", False))
    prev_speed = float(st.session_state.get("voice_speed", 1.0))

    # 한 줄 컴팩트 레이아웃: [라벨] [토글] [상태 배지]
    cols = st.columns([1, 2, 2.5])
    with cols[0]:
        st.markdown("**♿ 접근성**")
    with cols[1]:
        enabled = st.toggle(
            "🔊 음성 안내",
            value=prev_enabled,
            key=f"{key_prefix}_voice_toggle",
            help="시각장애인용 음성 안내. 토글을 켜면 음성으로 안내합니다.",
        )
    with cols[2]:
        # 현재 상태 배지 — 토글 옆에서 즉시 확인
        if prev_enabled:
            st.markdown(
                '<div style="background:#dcfce7;color:#166534;padding:6px 12px;'
                'border-radius:6px;font-weight:700;font-size:0.95rem;text-align:center;">'
                '🔊 ON (켜짐) ✅</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:#f3f4f6;color:#6b7280;padding:6px 12px;'
                'border-radius:6px;font-weight:600;font-size:0.95rem;text-align:center;">'
                '🔇 OFF (꺼짐)</div>',
                unsafe_allow_html=True,
            )

    # 토글 변화 감지 — ON/OFF 양쪽 모두 음성 안내 + 시각 토스트 + 즉시 rerun
    if enabled != prev_enabled:
        if enabled:
            # OFF → ON: state 변경 후 안내 발화
            st.session_state["voice_guide_enabled"] = True
            if supabase is not None and user_id:
                save_to_user(supabase, user_id)
            # 시각 피드백 — 화면 상단 토스트 (음성 안 들려도 시각으로 확인)
            try:
                st.toast("🔊 음성 안내가 켜졌습니다 (ON)", icon="✅")
            except Exception:
                pass
            announce("음성 서비스가 준비되었습니다.")
        else:
            # ON → OFF: 먼저 종료 안내 (아직 voice_guide_enabled=True 상태) →
            # 그 다음 state를 False로 변경 → 마지막 호출이 무사히 발화됨
            announce("음성 서비스를 종료합니다.")
            st.session_state["voice_guide_enabled"] = False
            if supabase is not None and user_id:
                save_to_user(supabase, user_id)
            try:
                st.toast("🔇 음성 안내가 꺼졌습니다 (OFF)", icon="🔕")
            except Exception:
                pass
        # 명시적 rerun — expander 라벨이 같은 rerun에 박혀 있어서
        # 토글 변경 직후 라벨 갱신을 보장하기 위함.
        # 자동 발화 iframe은 사라질 수 있지만 음성 테스트 버튼으로 보장 가능.
        st.rerun()

    # ── ON 상태일 때만 추가 컨트롤 노출 (속도 + 음성 테스트) ──
    if st.session_state.get("voice_guide_enabled"):
        sub_cols = st.columns([3, 2])
        with sub_cols[0]:
            speed = st.slider(
                "음성 속도",
                min_value=0.5, max_value=2.0,
                value=prev_speed, step=0.1,
                key=f"{key_prefix}_voice_speed",
                help="0.5배(느림) ~ 2.0배(빠름)",
            )
            if abs(speed - prev_speed) > 1e-3:
                st.session_state["voice_speed"] = speed
                if supabase is not None and user_id:
                    save_to_user(supabase, user_id)
                announce(f"속도 {speed:.1f}배.")
        with sub_cols[1]:
            st.caption("⌨️ Alt+A·M·H 단축키")

    # ── 🔊 음성 테스트 (토글 ON일 때만 노출) ──
    #    iframe 직접 발화 + 부모 함수 호출 두 가지 동시 시도 → 진단 가능.
    if st.session_state.get("voice_guide_enabled"):
        if st.button(
            "🔊 음성 테스트 (눌러서 발화)",
            key=f"{key_prefix}_voice_test",
            type="primary",
            use_container_width=True,
            help="여러 방식으로 발화 시도하고 결과를 콘솔에 출력합니다.",
        ):
            # ① 부모 함수 경유 + ② iframe 내 직접 호출 + ③ 진단 메시지 모두 시도
            _speed = float(st.session_state.get("voice_speed", 1.0))
            _lang = str(st.session_state.get("voice_lang", "ko-KR"))
            _test_text = (
                "안녕하세요. 드래곤아이즈 음성 안내 테스트입니다. "
                "이 메시지가 들리시면 음성 서비스가 정상 작동하는 것입니다."
            )
            import json as _json
            components.html(
                f"""
                <div id="a11y-test-result" style="font-family:monospace;font-size:11px;
                     padding:6px;background:#f0f9ff;border:1px solid #0284c7;border-radius:4px;
                     color:#0c4a6e;">
                    🔍 진단 중...
                </div>
                <script>
                (function() {{
                    const log = (msg) => {{
                        const el = document.getElementById('a11y-test-result');
                        if (el) el.innerHTML += '<br>' + msg;
                        console.log('[DragonEyes A11y]', msg);
                    }};
                    const text = {_json.dumps(_test_text)};
                    const lang = {_json.dumps(_lang)};
                    const rate = {_speed};

                    // 진단 정보
                    const w = window.parent || window;
                    log('🌐 SpeechSynthesis 지원: ' + ('speechSynthesis' in w));
                    log('🔧 _dragoneyesSpeak 등록: ' + (typeof w._dragoneyesSpeak));
                    log('🔉 voices 개수: ' + (w.speechSynthesis?.getVoices?.()?.length || 0));

                    let attempted = false;

                    // 방법 ①: 부모 컨텍스트 함수 호출
                    try {{
                        if (typeof w._dragoneyesSpeak === 'function') {{
                            w._dragoneyesSpeak(text, lang, rate, true);
                            log('✅ [방법1] 부모 _dragoneyesSpeak 호출 성공');
                            attempted = true;
                        }} else {{
                            log('⚠️ [방법1] _dragoneyesSpeak 함수 없음');
                        }}
                    }} catch (e) {{
                        log('❌ [방법1] 에러: ' + e.message);
                    }}

                    // 방법 ②: iframe 내 직접 호출 (sandbox 정책으로 차단될 수도)
                    try {{
                        if ('speechSynthesis' in w) {{
                            const u = new w.SpeechSynthesisUtterance(text);
                            u.lang = lang;
                            u.rate = rate;
                            u.onstart = () => log('🎤 발화 시작');
                            u.onend = () => log('✅ 발화 완료');
                            u.onerror = (e) => log('❌ 발화 에러: ' + e.error);
                            w.speechSynthesis.speak(u);
                            log('✅ [방법2] 직접 speak 호출');
                            attempted = true;
                        }}
                    }} catch (e) {{
                        log('❌ [방법2] 에러: ' + e.message);
                    }}

                    if (!attempted) {{
                        log('🚫 모든 발화 시도 실패. 브라우저가 Web Speech API를 차단했거나 지원하지 않음.');
                    }}
                }})();
                </script>
                """,
                height=200,
            )
            st.caption(
                "📋 위 박스의 진단 결과를 확인하세요. "
                "발화 시작·완료 메시지가 보이면 음성이 정상 작동한 것입니다. "
                "안 들리면 OS 출력 장치(스피커/이어폰) 확인."
            )


# ══════════════════════════════════════════════════════════════
# 5. 키보드 단축키 inject (한 번)
# ══════════════════════════════════════════════════════════════
def inject_shortcuts() -> None:
    """Alt+A: 음성 토글로 스크롤·포커스, Alt+M: 메뉴, Alt+H: 도움말.

    Streamlit iframe 격리 때문에 위젯 클릭 자동화는 한계가 있어,
    Alt+A는 토글 위젯으로 포커스를 이동시켜 사용자가 Space로 켤 수 있게 함.

    중복 inject 방지를 위해 window.__a11yShortcutsInstalled 플래그 사용.
    """
    components.html(
        """
        <script>
        (function() {
            try {
                const w = window.parent || window;
                if (w.__a11yShortcutsInstalled) return;
                w.__a11yShortcutsInstalled = true;

                // ── 부모 컨텍스트에 _dragoneyesSpeak 함수 등록 ──
                //    iframe 격리 안에서 호출 시 차단되는 SpeechSynthesisUtterance를
                //    부모 페이지 컨텍스트에서 실행해 사용자 제스처 정책을 통과.
                w._dragoneyesSpeak = function(text, lang, rate, interrupt) {
                    try {
                        if (!('speechSynthesis' in w)) {
                            console.warn('speechSynthesis API not supported');
                            return;
                        }
                        if (interrupt !== false) {
                            w.speechSynthesis.cancel();
                        }
                        const u = new w.SpeechSynthesisUtterance(text);
                        u.lang = lang || 'ko-KR';
                        u.rate = (typeof rate === 'number' && rate > 0) ? rate : 1.0;
                        u.pitch = 1.0;
                        u.volume = 1.0;
                        w.speechSynthesis.speak(u);
                    } catch (e) {
                        console.error('DragonEyes TTS error:', e);
                    }
                };

                // ── 키보드 단축키 (Alt+A/M/H) ──
                w.document.addEventListener('keydown', function(e) {
                    if (!e.altKey) return;
                    const key = (e.key || '').toLowerCase();
                    if (key === 'a') {
                        // 첫 'voice' 관련 토글 또는 첫 토글로 이동
                        const tg =
                            w.document.querySelector('[aria-label*="음성"], [data-testid*="stToggle"]') ||
                            w.document.querySelector('label[data-baseweb="checkbox"]');
                        if (tg) {
                            tg.scrollIntoView({block: 'center', behavior: 'smooth'});
                            const focusable = tg.querySelector('input, button') || tg;
                            try { focusable.focus(); } catch (_) {}
                        }
                        e.preventDefault();
                    } else if (key === 'm') {
                        const main = w.document.querySelector(
                            '[role="main"], main, [data-testid="stHeader"], [data-testid="stMain"]'
                        );
                        if (main) {
                            main.scrollIntoView({block: 'start', behavior: 'smooth'});
                            try { main.focus && main.focus(); } catch (_) {}
                        }
                        e.preventDefault();
                    } else if (key === 'h') {
                        const evt = new CustomEvent('dragoneyes:help-requested');
                        w.dispatchEvent(evt);
                        e.preventDefault();
                    }
                }, true);
            } catch (e) {
                console.error('DragonEyes shortcuts inject error:', e);
            }
        })();
        </script>
        """,
        height=0,
    )


# ══════════════════════════════════════════════════════════════
# 6. ARIA 보조 — 시각 요소에 보조 텍스트 부여
# ══════════════════════════════════════════════════════════════
def aria_landmark(label: str) -> None:
    """페이지 진입 시 invisible aria-live 영역에 안내문구 inject.

    스크린리더(NVDA·JAWS·VoiceOver)가 자동으로 읽도록.
    음성 안내 토글과 무관하게 항상 동작 (스크린리더 표준).
    """
    if not label:
        return
    js_label = json.dumps(str(label))
    components.html(
        f"""
        <div role="status" aria-live="polite" aria-atomic="true"
             style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden;">
            <script>
            (function() {{
                try {{
                    const el = document.currentScript.parentElement;
                    el.textContent = {js_label};
                }} catch (e) {{}}
            }})();
            </script>
        </div>
        """,
        height=0,
    )
