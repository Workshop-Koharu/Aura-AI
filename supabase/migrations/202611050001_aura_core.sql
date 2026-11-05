create table if not exists public.aura_profiles (
 user_id uuid primary key references auth.users(id) on delete cascade,
 display_name text, avatar_url text, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.aura_conversations (
 id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
 title text not null default 'New chat', model_id text not null default 'aura-from-scratch',
 created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index if not exists aura_conversations_user_updated_idx on public.aura_conversations(user_id, updated_at desc);
create table if not exists public.aura_messages (
 id uuid primary key default gen_random_uuid(), conversation_id uuid not null references public.aura_conversations(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 role text not null check (role in ('system','user','assistant')), content text not null,
 attachments jsonb not null default '[]'::jsonb, usage jsonb not null default '{}'::jsonb, created_at timestamptz not null default now()
);
create index if not exists aura_messages_conversation_created_idx on public.aura_messages(conversation_id, created_at);
create table if not exists public.aura_api_keys (
 id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
 name text not null, key_hash text not null unique, last_used_at timestamptz, expires_at timestamptz, revoked_at timestamptz,
 created_at timestamptz not null default now()
);
create index if not exists aura_api_keys_user_created_idx on public.aura_api_keys(user_id, created_at desc);
alter table public.aura_profiles enable row level security;
alter table public.aura_conversations enable row level security;
alter table public.aura_messages enable row level security;
alter table public.aura_api_keys enable row level security;
create policy "profile owner read" on public.aura_profiles for select to authenticated using ((select auth.uid()) = user_id);
create policy "profile owner insert" on public.aura_profiles for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "profile owner update" on public.aura_profiles for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "conversation owner read" on public.aura_conversations for select to authenticated using ((select auth.uid()) = user_id);
create policy "conversation owner insert" on public.aura_conversations for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "conversation owner update" on public.aura_conversations for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "conversation owner delete" on public.aura_conversations for delete to authenticated using ((select auth.uid()) = user_id);
create policy "message owner read" on public.aura_messages for select to authenticated using ((select auth.uid()) = user_id);
create policy "message owner insert" on public.aura_messages for insert to authenticated with check ((select auth.uid()) = user_id and exists (select 1 from public.aura_conversations c where c.id = conversation_id and c.user_id = (select auth.uid())));
create policy "message owner delete" on public.aura_messages for delete to authenticated using ((select auth.uid()) = user_id);
create policy "api key owner read" on public.aura_api_keys for select to authenticated using ((select auth.uid()) = user_id);
create policy "api key owner insert" on public.aura_api_keys for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "api key owner update" on public.aura_api_keys for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
