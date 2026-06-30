-- ════════════════════════════════════════════════════════════════
--  DragonEyes 추천 인벤토리 (사전생성 풀 + 원자적 FIFO 배정)
--  Supabase SQL Editor에서 1회 실행. service_role 키 불필요(앱은 anon RPC만 사용).
-- ════════════════════════════════════════════════════════════════

-- 1) 추천 인벤토리 테이블 — AI 분석까지 끝낸 '완성품'을 미리 쌓아두는 재고
create table if not exists public.recommendation_inventory (
    id          bigint generated always as identity primary key,
    url         text not null unique,           -- 중복 방지(같은 영상 1회만)
    title       text,
    channel     text,
    analysis    text,                            -- ★비싼 AI 분석값 보존
    severity    int  default 0,
    category    text,
    search_type text,                            -- dragon_general / dragon_roblox / dragon_minecraft / dragon_gambling
    created_at  timestamptz not null default now(),
    claimed_by  uuid,                            -- NULL = 미배정(재고), 값 = 배정완료
    claimed_at  timestamptz
);

-- 미배정분을 플랫폼·오래된순으로 빠르게 찾기 위한 부분 인덱스
create index if not exists idx_recinv_unclaimed
    on public.recommendation_inventory (search_type, created_at)
    where claimed_by is null;

-- RLS on: 앱은 아래 SECURITY DEFINER 함수(RPC)로만 접근. 직접 테이블 접근 차단.
alter table public.recommendation_inventory enable row level security;

-- 2) 원자적 FIFO claim — 동시 클릭 경합 방지(FOR UPDATE SKIP LOCKED)
create or replace function public.claim_recommendations(
    p_user_id     uuid,
    p_search_type text,
    p_limit       int
)
returns setof public.recommendation_inventory
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  update public.recommendation_inventory inv
     set claimed_by = p_user_id,
         claimed_at = now()
   where inv.id in (
       select id from public.recommendation_inventory
        where claimed_by is null
          and (p_search_type is null or search_type = p_search_type)
        order by created_at asc
        limit greatest(coalesce(p_limit, 0), 0)
        for update skip locked
   )
  returning inv.*;
end;
$$;
grant execute on function public.claim_recommendations(uuid, text, int) to anon, authenticated;

-- 3) 인벤토리 적재 — 앱이 분석 후 1건씩 넣기(중복 url은 무시)
create or replace function public.add_to_inventory(
    p_url text, p_title text, p_channel text, p_analysis text,
    p_severity int, p_category text, p_search_type text
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.recommendation_inventory
      (url, title, channel, analysis, severity, category, search_type)
  values (p_url, p_title, p_channel, p_analysis,
          coalesce(p_severity, 0), p_category, p_search_type)
  on conflict (url) do nothing;
end;
$$;
grant execute on function public.add_to_inventory(text,text,text,text,int,text,text) to anon, authenticated;

-- 4) 미배정(재고) 개수 — 앱 top-up 판정용
create or replace function public.inventory_unclaimed_count(p_search_type text default null)
returns int
language sql
security definer
set search_path = public
as $$
  select count(*)::int from public.recommendation_inventory
   where claimed_by is null
     and (p_search_type is null or search_type = p_search_type);
$$;
grant execute on function public.inventory_unclaimed_count(text) to anon, authenticated;
