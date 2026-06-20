// ============================================================
// 드래곤아이즈 캠페인 설문 — 정적 HTML 응답 페이지 메인 로직
// ============================================================

(function () {
  "use strict";

  // ── Supabase 초기화 ──────────────────────────────────────
  const cfg = window.DRAGONEYES_CONFIG || {};
  const supa = window.supabase.createClient(
    cfg.SUPABASE_URL,
    cfg.SUPABASE_ANON_KEY,
    {
      auth: { persistSession: false, autoRefreshToken: false },
      global: { fetch: window.fetch.bind(window) },
    }
  );

  // ── DOM 헬퍼 ─────────────────────────────────────────────
  const $ = (s) => document.querySelector(s);
  const show = (id) => $(id).classList.remove("hidden");
  const hide = (id) => $(id).classList.add("hidden");
  const text = (id, v) => { $(id).textContent = v ?? "—"; };

  function showState(name, msg) {
    ["#state-loading","#state-error","#state-already-done",
     "#state-form","#state-success"].forEach(id => hide(id));
    show("#state-" + name);
    if (name === "error" && msg) text("#error-message", msg);
  }

  // ── URL에서 토큰 추출 ─────────────────────────────────────
  function getToken() {
    const u = new URL(window.location.href);
    return u.searchParams.get("token")
        || u.searchParams.get("survey_token")
        || "";
  }

  // ── 학년대별 임계값/봉사시간 ──────────────────────────────
  const BAND_META = {
    elementary: { threshold: 20, hours: 4, kr: "초등" },
    middle:     { threshold: 30, hours: 5, kr: "중학" },
    high:       { threshold: 50, hours: 8, kr: "고등" },
  };

  // ── 시간 측정 ────────────────────────────────────────────
  let _startTime = null;

  // ── 1) 설문 정보 로드 ────────────────────────────────────
  async function loadSurvey(token) {
    if (!token) {
      showState("error", "URL에 token 파라미터가 없습니다.");
      return null;
    }

    const { data, error } = await supa.rpc("get_survey_by_token", {
      p_token: token,
    });

    if (error) {
      console.error(error);
      showState("error", "서버 오류: " + error.message);
      return null;
    }
    if (!data || !data.valid) {
      showState("error", data?.error === "revoked"
        ? "이 설문 링크는 무효화되었습니다."
        : "유효하지 않은 토큰입니다.");
      return null;
    }
    return data;
  }

  // ── 2) 배포자 정보 prefill ───────────────────────────────
  function fillDistributor(stu) {
    text("#d-school", stu.school_name || "—");
    text("#d-grade",  stu.grade ? stu.grade + "학년" : "—");
    text("#d-class",  stu.class_no ? stu.class_no + "반" : "—");
    text("#d-name",   stu.name || "—");
  }

  // ── 3) 문항 동적 렌더링 ───────────────────────────────────
  const SECTION_HEADERS = {
    1: "1. 온라인 이용 실태",
    3: "2. 인식과 태도",
    7: "3. 경험",
    10: "4. 디지털 그루밍",
    12: "5. 대응과 신고",
    16: "6. 저작권 인식",
    22: "7. 정책 평가",
    25: "8. 참여 의지",
    26: "9. 자유 의견",
  };

  function renderQuestions(questions) {
    const root = $("#questions-container");
    root.innerHTML = "";

    questions.forEach((q) => {
      // 섹션 헤더
      if (SECTION_HEADERS[q.qno]) {
        const h = document.createElement("h3");
        h.className = "text-base font-bold text-de-dark mt-6 pb-2 border-b-2 border-de-primary";
        h.textContent = "■ " + SECTION_HEADERS[q.qno];
        root.appendChild(h);
      }

      const card = document.createElement("div");
      card.className = "bg-white rounded-lg border border-slate-200 p-4 shadow-sm";

      // 문항 텍스트
      const qHeader = document.createElement("div");
      qHeader.className = "font-semibold text-slate-800 mb-3";
      qHeader.innerHTML = `Q${q.qno}. ${escapeHtml(q.text)}` +
        (q.qtype === "multi_choice"
          ? ` <span class="text-xs text-slate-500 font-normal">(여러 개 선택 가능)</span>` : "") +
        (q.required ? ` <span class="text-red-500">*</span>` : "");
      card.appendChild(qHeader);

      const qName = `q_${q.qno}`;
      const opts = q.options || [];

      if (q.qtype === "long_text") {
        const ta = document.createElement("textarea");
        ta.name = qName;
        ta.rows = 4;
        ta.maxLength = 1000;
        ta.placeholder = "자유롭게 작성해주세요...";
        ta.className = "w-full px-3 py-2 border border-slate-300 rounded text-sm";
        card.appendChild(ta);
      } else if (q.qtype === "multi_choice") {
        opts.forEach((opt) => {
          const lbl = document.createElement("label");
          lbl.className = "flex items-center gap-2 py-1.5 cursor-pointer hover:bg-slate-50 px-2 rounded";
          lbl.innerHTML = `
            <input type="checkbox" name="${qName}" value="${escapeHtml(opt)}"
                   class="w-4 h-4 text-de-primary" />
            <span class="text-sm text-slate-700">${escapeHtml(opt)}</span>`;
          card.appendChild(lbl);
        });
      } else {
        // single_choice / scale
        opts.forEach((opt) => {
          const lbl = document.createElement("label");
          lbl.className = "flex items-center gap-2 py-1.5 cursor-pointer hover:bg-slate-50 px-2 rounded";
          lbl.innerHTML = `
            <input type="radio" name="${qName}" value="${escapeHtml(opt)}"
                   class="w-4 h-4 text-de-primary" />
            <span class="text-sm text-slate-700">${escapeHtml(opt)}</span>`;
          card.appendChild(lbl);
        });
      }

      root.appendChild(card);
    });
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ── 4) 응답 수집 ──────────────────────────────────────────
  function collectAnswers(questions) {
    const answers = {};
    const missing = [];

    questions.forEach((q) => {
      const qName = `q_${q.qno}`;
      let val = null;

      if (q.qtype === "long_text") {
        const el = document.querySelector(`textarea[name="${qName}"]`);
        val = el?.value.trim() || "";
      } else if (q.qtype === "multi_choice") {
        const checks = document.querySelectorAll(
          `input[name="${qName}"]:checked`);
        val = Array.from(checks).map(c => c.value);
      } else {
        const radio = document.querySelector(
          `input[name="${qName}"]:checked`);
        val = radio?.value || null;
      }

      answers[q.qno] = val;

      // 필수 미응답 체크
      if (q.required) {
        if (val === null || val === ""
            || (Array.isArray(val) && val.length === 0)) {
          missing.push(q.qno);
        }
      }
    });
    return { answers, missing };
  }

  // ── 5) 응답자 정보 ────────────────────────────────────────
  function collectRespondent() {
    return {
      name:   $("#r-name").value.trim(),
      age:    parseInt($("#r-age").value, 10) || null,
      gender: $("#r-gender").value || null,
      region: $("#r-region").value || null,
    };
  }

  // ── 6) 제출 ──────────────────────────────────────────────
  async function onSubmit(token, surveyData) {
    const btn = $("#btn-submit");
    const help = $("#submit-help");
    const resp = collectRespondent();

    // 응답자 정보 검증
    if (!resp.name) return alert("응답자 성명을 입력해주세요.");
    if (!resp.age) return alert("응답자 나이를 입력해주세요.");
    if (!resp.gender) return alert("응답자 성별을 선택해주세요.");
    if (!resp.region) return alert("거주지역을 선택해주세요.");

    // 응답 검증
    const { answers, missing } = collectAnswers(surveyData.questions);
    if (missing.length > 0) {
      alert(`미응답 문항이 있습니다: Q${missing.slice(0, 8).join(", Q")}`
        + (missing.length > 8 ? ` 외 ${missing.length - 8}개` : ""));
      // 첫 미응답으로 스크롤
      const first = document.querySelector(`[name="q_${missing[0]}"]`);
      first?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    // 무결성 — 너무 빠른 제출 차단
    const elapsed = _startTime ? Math.round((Date.now() - _startTime) / 1000) : null;
    if (elapsed && elapsed < 60) {
      if (!confirm("응답이 너무 빠릅니다. 그대로 제출하시면 무효 처리될 수 있습니다. 계속하시겠습니까?")) {
        return;
      }
    }

    btn.disabled = true;
    btn.textContent = "📤 제출 중...";
    help.textContent = "잠시만 기다려주세요...";

    const { data, error } = await supa.rpc("submit_external_response", {
      p_token: token,
      p_respondent_name:   resp.name,
      p_respondent_age:    resp.age,
      p_respondent_gender: resp.gender,
      p_respondent_region: resp.region,
      p_answers:           answers,
      p_completion_seconds: elapsed,
      p_integrity_score:    null,
      p_ip:                 null,
      p_user_agent:         navigator.userAgent.slice(0, 200),
    });

    if (error || !data?.ok) {
      btn.disabled = false;
      btn.textContent = "✅ 설문 완료 · 제출";
      help.textContent = "제출 후에는 수정할 수 없습니다.";
      alert("제출 실패: " + (error?.message || data?.error || "알 수 없는 오류"));
      return;
    }

    // 성공 화면
    const band = surveyData.survey.target_band;
    const meta = BAND_META[band] || { threshold: "—", hours: "—", kr: "—" };
    text("#success-student",   surveyData.student.name || "—");
    text("#success-count",     data.new_count);
    text("#success-threshold", meta.threshold);
    text("#success-band",
         `${meta.kr}학년대 · ${meta.threshold}명 응답 시 ${meta.hours}시간 자동 발급`);
    showState("success");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ── 메인 ──────────────────────────────────────────────────
  async function main() {
    const token = getToken();
    const data = await loadSurvey(token);
    if (!data) return;

    fillDistributor(data.student);
    renderQuestions(data.questions);

    // 헤더 제목 업데이트
    if (data.survey?.title) {
      document.title = data.survey.title + " — 드래곤아이즈";
    }

    showState("form");
    _startTime = Date.now();

    $("#btn-submit").addEventListener("click", () => onSubmit(token, data));
  }

  // 다운로드/캡처 차단 (선택)
  document.addEventListener("contextmenu", (e) => e.preventDefault());
  document.addEventListener("keydown", (e) => {
    const k = (e.key || "").toLowerCase();
    if ((e.ctrlKey || e.metaKey) && ["s", "p"].includes(k)) e.preventDefault();
  });

  main();
})();
