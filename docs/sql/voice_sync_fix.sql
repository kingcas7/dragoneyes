-- 보이스 클로드 동기화 테이블 보안 강화 (2026-08-10 전체 점검 후속)
-- Supabase 대시보드 → SQL Editor 에서 이 내용을 붙여넣고 Run 하세요.
--
-- 기존 정책(voice_sync_all)은 anon 키만 있으면 누구나 타인 데이터를
-- 통째로 삭제·변조하거나 무제한 삽입할 수 있었음.
-- → 삭제 불허 + 데이터 크기 제한(2MB)으로 교체.

drop policy if exists voice_sync_all on voice_sync;

create policy voice_sync_select on voice_sync
  for select using (true);

create policy voice_sync_insert on voice_sync
  for insert with check (length(data) < 2000000);

create policy voice_sync_update on voice_sync
  for update using (true) with check (length(data) < 2000000);

-- delete 정책을 만들지 않음 = anon 키로는 삭제 불가
