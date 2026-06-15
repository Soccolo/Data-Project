-- ─────────────────────────────────────────────────────────────────────
-- Dara production schema
-- Paste this into the Supabase SQL Editor in one go. Safe to re-run.
-- Run AFTER setting up Supabase Auth (no extra config needed there —
-- the auth.users table is created automatically).
-- ─────────────────────────────────────────────────────────────────────

-- ── Extensions ───────────────────────────────────────────────────────
create extension if not exists "pgcrypto";

-- ── Users (one row per Supabase Auth user) ───────────────────────────
create table if not exists public.users (
  id           uuid primary key references auth.users(id) on delete cascade,
  username     text unique not null,
  email        text not null,
  kind         text not null default 'dating'  check (kind in ('dating','couples','both')),
  tier         text not null default 'free'    check (tier in ('free','pro','x')),
  basics       jsonb not null default '{}'::jsonb,
  profile      jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists users_username_lower_idx on public.users (lower(username));
create index if not exists users_kind_idx on public.users (kind);

-- ── Photos (separate table so we can paginate / lazy-load) ───────────
-- The actual image bytes live in Supabase Storage. This table holds
-- the storage path + metadata + order. One photo per row.
create table if not exists public.photos (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.users(id) on delete cascade,
  storage_path text not null,
  position     int  not null default 0,
  media_type   text not null default 'image/jpeg',
  width        int,
  height       int,
  created_at   timestamptz not null default now()
);
create index if not exists photos_user_position_idx on public.photos (user_id, position);

-- ── User state (passes, dailyCount; meets live in their own table) ───
create table if not exists public.user_state (
  user_id      uuid primary key references public.users(id) on delete cascade,
  passed_ids   uuid[] not null default '{}',
  daily_count  jsonb not null default '{"date": null, "count": 0}'::jsonb,
  updated_at   timestamptz not null default now()
);

-- ── Meets (dating proposals) ─────────────────────────────────────────
create table if not exists public.meets (
  id             uuid primary key default gen_random_uuid(),
  proposer_id    uuid not null references public.users(id) on delete cascade,
  recipient_id   uuid not null references public.users(id) on delete cascade,
  proposer_name  text not null,
  recipient_name text not null,
  time_str       text not null,
  place          text not null,
  message        text,
  status         text not null default 'pending' check (status in ('pending','accepted','declined')),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);
create index if not exists meets_recipient_idx on public.meets (recipient_id);
create index if not exists meets_proposer_idx  on public.meets (proposer_id);

-- ── Conflict sessions (couples mediation) ────────────────────────────
create table if not exists public.conflict_sessions (
  id               uuid primary key default gen_random_uuid(),
  inviter_id       uuid not null references public.users(id) on delete cascade,
  inviter_username text not null,
  inviter_name     text not null,
  invitee_id       uuid not null references public.users(id) on delete cascade,
  invitee_username text not null,
  invitee_name     text not null,
  topic            text not null,
  status           text not null default 'invited'
                   check (status in ('invited','declined','intake','mediating','complete','safety-stopped')),
  safety_reason    text,
  intake           jsonb not null default '{"inviter":{"messages":[],"summary":null,"safetyFlag":null,"complete":false},"invitee":{"messages":[],"summary":null,"safetyFlag":null,"complete":false}}'::jsonb,
  mediation        jsonb not null default '{"messages":[],"inviterWantsWrap":false,"inviteeWantsWrap":false,"wrappedAt":null,"wrappedReason":null}'::jsonb,
  takeaways        jsonb not null default '{"inviter":null,"invitee":null}'::jsonb,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);
create index if not exists conflict_sessions_inviter_idx on public.conflict_sessions (inviter_id);
create index if not exists conflict_sessions_invitee_idx on public.conflict_sessions (invitee_id);
create index if not exists conflict_sessions_updated_idx on public.conflict_sessions (updated_at desc);

-- Touch updated_at on row changes
create or replace function public.touch_updated_at() returns trigger as $$
begin new.updated_at := now(); return new; end;
$$ language plpgsql;

drop trigger if exists trg_users_touch on public.users;
create trigger trg_users_touch before update on public.users
for each row execute function public.touch_updated_at();

drop trigger if exists trg_user_state_touch on public.user_state;
create trigger trg_user_state_touch before update on public.user_state
for each row execute function public.touch_updated_at();

drop trigger if exists trg_meets_touch on public.meets;
create trigger trg_meets_touch before update on public.meets
for each row execute function public.touch_updated_at();

drop trigger if exists trg_conflict_sessions_touch on public.conflict_sessions;
create trigger trg_conflict_sessions_touch before update on public.conflict_sessions
for each row execute function public.touch_updated_at();

-- ─────────────────────────────────────────────────────────────────────
-- ROW-LEVEL SECURITY
-- This is the part the artifact couldn't have. It enforces, at the DB
-- level, who can read what. Even a malicious client can't query
-- another user's intake messages.
-- ─────────────────────────────────────────────────────────────────────

alter table public.users             enable row level security;
alter table public.photos            enable row level security;
alter table public.user_state        enable row level security;
alter table public.meets             enable row level security;
alter table public.conflict_sessions enable row level security;

-- ── users: anyone authenticated can read the public profile fields
-- of any user (needed for matching, profile viewing, invites by username).
-- Writes are self-only.
drop policy if exists users_select_all on public.users;
create policy users_select_all on public.users
  for select to authenticated using (true);

drop policy if exists users_insert_self on public.users;
create policy users_insert_self on public.users
  for insert to authenticated with check (id = auth.uid());

drop policy if exists users_update_self on public.users;
create policy users_update_self on public.users
  for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists users_delete_self on public.users;
create policy users_delete_self on public.users
  for delete to authenticated using (id = auth.uid());

-- ── photos: anyone authed can read; only owner can write/delete
drop policy if exists photos_select_all on public.photos;
create policy photos_select_all on public.photos
  for select to authenticated using (true);

drop policy if exists photos_write_self on public.photos;
create policy photos_write_self on public.photos
  for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

-- ── user_state: only the user can read or write their own state.
-- Passes/daily counts are private.
drop policy if exists user_state_self on public.user_state;
create policy user_state_self on public.user_state
  for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

-- ── meets: only proposer or recipient can read. Either party can update
-- (for accept/decline). Only proposer can create.
drop policy if exists meets_select_party on public.meets;
create policy meets_select_party on public.meets
  for select to authenticated
  using (proposer_id = auth.uid() or recipient_id = auth.uid());

drop policy if exists meets_insert_proposer on public.meets;
create policy meets_insert_proposer on public.meets
  for insert to authenticated
  with check (proposer_id = auth.uid());

drop policy if exists meets_update_party on public.meets;
create policy meets_update_party on public.meets
  for update to authenticated
  using (proposer_id = auth.uid() or recipient_id = auth.uid())
  with check (proposer_id = auth.uid() or recipient_id = auth.uid());

-- ── conflict sessions: only the two named parties can see or modify.
-- This is the privacy guarantee the artifact couldn't enforce.
drop policy if exists cs_select_party on public.conflict_sessions;
create policy cs_select_party on public.conflict_sessions
  for select to authenticated
  using (inviter_id = auth.uid() or invitee_id = auth.uid());

drop policy if exists cs_insert_inviter on public.conflict_sessions;
create policy cs_insert_inviter on public.conflict_sessions
  for insert to authenticated
  with check (inviter_id = auth.uid());

drop policy if exists cs_update_party on public.conflict_sessions;
create policy cs_update_party on public.conflict_sessions
  for update to authenticated
  using (inviter_id = auth.uid() or invitee_id = auth.uid())
  with check (inviter_id = auth.uid() or invitee_id = auth.uid());

-- ─────────────────────────────────────────────────────────────────────
-- STORAGE BUCKETS
-- Run these in the SQL editor too, or set up via the Storage UI.
-- The bucket policies mirror the photos table RLS.
-- ─────────────────────────────────────────────────────────────────────

insert into storage.buckets (id, name, public)
values ('dara-photos', 'dara-photos', false)
on conflict (id) do nothing;

-- Anyone authed can read photos (matches the photos table RLS).
-- The bucket is "private" but the policy below grants read to all authed users.
drop policy if exists "photos_read_authed" on storage.objects;
create policy "photos_read_authed" on storage.objects
  for select to authenticated
  using (bucket_id = 'dara-photos');

-- Only the photo owner can upload/update/delete. Photos are stored
-- under paths like {user_id}/{photo_id}.jpg so we can check ownership
-- by inspecting the first path segment.
drop policy if exists "photos_write_self" on storage.objects;
create policy "photos_write_self" on storage.objects
  for all to authenticated
  using (bucket_id = 'dara-photos' and (storage.foldername(name))[1] = auth.uid()::text)
  with check (bucket_id = 'dara-photos' and (storage.foldername(name))[1] = auth.uid()::text);

-- ─────────────────────────────────────────────────────────────────────
-- AUTO-PROVISION PROFILE ON SIGN-UP
-- When Supabase Auth creates a new auth.users row (e.g. email+password
-- sign-up), create the matching public.users profile automatically. The
-- username starts as a safe placeholder; onboarding lets the user pick a
-- real one. SECURITY DEFINER lets the trigger insert past RLS.
-- ─────────────────────────────────────────────────────────────────────

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, username, email)
  values (
    new.id,
    'user_' || substr(replace(new.id::text, '-', ''), 1, 8),
    coalesce(new.email, '')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
