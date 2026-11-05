create table if not exists public.aura_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now()
);

create table if not exists public.aura_devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  device_name text not null,
  last_seen_at timestamptz not null default now(),
  capabilities jsonb not null default '{}'::jsonb
);

create table if not exists public.aura_model_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  device_id uuid references public.aura_devices(id) on delete set null,
  status text not null check (status in ('queued','running','paused','completed','failed','stopped')),
  step bigint not null default 0,
  loss double precision,
  started_at timestamptz,
  finished_at timestamptz,
  metrics jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.aura_conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'New chat',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.aura_profiles enable row level security;
alter table public.aura_devices enable row level security;
alter table public.aura_model_runs enable row level security;
alter table public.aura_conversations enable row level security;

create policy "profile owner can read" on public.aura_profiles for select to authenticated using ((select auth.uid()) = user_id);
create policy "profile owner can insert" on public.aura_profiles for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "profile owner can update" on public.aura_profiles for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

create policy "device owner all" on public.aura_devices for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "run owner all" on public.aura_model_runs for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "conversation owner all" on public.aura_conversations for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

create index if not exists aura_devices_user_seen_idx on public.aura_devices(user_id, last_seen_at desc);
create index if not exists aura_model_runs_user_created_idx on public.aura_model_runs(user_id, created_at desc);
create index if not exists aura_conversations_user_updated_idx on public.aura_conversations(user_id, updated_at desc);

grant select, insert, update on public.aura_profiles to authenticated;
grant select, insert, update, delete on public.aura_devices to authenticated;
grant select, insert, update, delete on public.aura_model_runs to authenticated;
grant select, insert, update, delete on public.aura_conversations to authenticated;
