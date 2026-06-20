// ─────────────────────────────────────────────────────────────
// Supabase 설정 — 실 배포 시 본인 프로젝트 값으로 교체
// (anon key는 공개 가능 — RLS로 보호되며 함수만 호출 가능)
// ─────────────────────────────────────────────────────────────
window.DRAGONEYES_CONFIG = {
  SUPABASE_URL: "https://xtqgxtdflemuphkzmzti.supabase.co",
  SUPABASE_ANON_KEY: "YOUR_SUPABASE_ANON_KEY_HERE"  // ⚠️ Supabase Dashboard → Settings → API → anon public 키
};
