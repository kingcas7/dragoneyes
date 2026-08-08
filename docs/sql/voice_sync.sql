-- 보이스 클로드 기기 간 동기화 테이블
-- Supabase 대시보드 → SQL Editor 에서 이 내용을 붙여넣고 Run 하세요.
--
-- 대화 내용(data)은 사용자의 "동기화 암호"로 AES-GCM 암호화되어 저장되므로
-- anon 키로 테이블을 읽어도 내용을 볼 수 없습니다.

create table if not exists voice_sync (
  sync_key   text primary key,          -- sha256(동기화 암호) — 계정 식별자
  data       text not null,             -- AES-GCM 암호화된 대화 데이터 (base64)
  updated_at timestamptz default now()
);

alter table voice_sync enable row level security;

-- anon 키로 읽기/쓰기 허용 (내용은 클라이언트에서 암호화됨)
drop policy if exists voice_sync_all on voice_sync;
create policy voice_sync_all on voice_sync
  for all using (true) with check (true);
