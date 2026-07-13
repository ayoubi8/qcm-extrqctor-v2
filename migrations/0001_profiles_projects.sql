begin;

create extension if not exists pgcrypto;

do $$
begin
  create type public.app_role as enum ('user', 'admin', 'service', 'worker');
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.profile_status as enum (
    'pending_approval',
    'active',
    'suspended',
    'deletion_requested',
    'deleted'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.project_status as enum (
    'active',
    'archived',
    'deletion_requested',
    'deleted'
  );
exception when duplicate_object then null;
end $$;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace function public.is_active_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.profiles p
    where p.user_id = auth.uid()
      and p.role = 'admin'
      and p.status = 'active'
  );
$$;

create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique check (email = lower(email)),
  display_name text,
  role public.app_role not null default 'user',
  status public.profile_status not null default 'pending_approval',
  approved_by uuid references public.profiles(user_id),
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    (status = 'active' and approved_at is not null)
    or status <> 'active'
    or role = 'admin'
  )
);

create table if not exists public.user_preferences (
  preference_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  preference_key text not null,
  value jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, preference_key)
);

create table if not exists public.model_preferences (
  model_preference_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  provider text not null default 'openrouter' check (provider = 'openrouter'),
  primary_model_id text not null,
  fallback_model_ids text[] not null default '{}'::text[],
  scope text not null default 'default' check (
    scope in ('default', 'step1', 'step2', 'step3', 'step4', 'ai_auto_run')
  ),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, provider, scope)
);

create table if not exists public.projects (
  project_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  name text not null,
  status public.project_status not null default 'active',
  legacy_project_key text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz,
  unique (user_id, project_id)
);

create index if not exists idx_projects_user_status_updated
on public.projects (user_id, status, updated_at desc);

create trigger trg_profiles_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

create trigger trg_user_preferences_updated_at
before update on public.user_preferences
for each row execute function public.set_updated_at();

create trigger trg_model_preferences_updated_at
before update on public.model_preferences
for each row execute function public.set_updated_at();

create trigger trg_projects_updated_at
before update on public.projects
for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.profiles force row level security;
alter table public.user_preferences enable row level security;
alter table public.user_preferences force row level security;
alter table public.model_preferences enable row level security;
alter table public.model_preferences force row level security;
alter table public.projects enable row level security;
alter table public.projects force row level security;

create policy "profiles owner select"
on public.profiles
for select
to authenticated
using (user_id = auth.uid() or public.is_active_admin());

create policy "profiles owner update"
on public.profiles
for update
to authenticated
using (user_id = auth.uid() or public.is_active_admin())
with check (user_id = auth.uid() or public.is_active_admin());

create policy "profiles no client delete"
on public.profiles
for delete
to authenticated
using (false);

create policy "user_preferences owner select"
on public.user_preferences
for select
to authenticated
using (user_id = auth.uid() or public.is_active_admin());

create policy "user_preferences owner insert"
on public.user_preferences
for insert
to authenticated
with check (user_id = auth.uid());

create policy "user_preferences owner update"
on public.user_preferences
for update
to authenticated
using (user_id = auth.uid())
with check (user_id = auth.uid());

create policy "user_preferences no client delete"
on public.user_preferences
for delete
to authenticated
using (false);

create policy "model_preferences owner select"
on public.model_preferences
for select
to authenticated
using (user_id = auth.uid() or public.is_active_admin());

create policy "model_preferences owner insert"
on public.model_preferences
for insert
to authenticated
with check (user_id = auth.uid());

create policy "model_preferences owner update"
on public.model_preferences
for update
to authenticated
using (user_id = auth.uid())
with check (user_id = auth.uid());

create policy "model_preferences no client delete"
on public.model_preferences
for delete
to authenticated
using (false);

create policy "projects owned select"
on public.projects
for select
to authenticated
using (user_id = auth.uid() or public.is_active_admin());

create policy "projects owned insert"
on public.projects
for insert
to authenticated
with check (user_id = auth.uid());

create policy "projects owned update"
on public.projects
for update
to authenticated
using (user_id = auth.uid() and status <> 'deleted')
with check (user_id = auth.uid());

create policy "projects no client delete"
on public.projects
for delete
to authenticated
using (false);

comment on table public.profiles is
'Supabase Auth profile mirror. New users start pending approval; app access requires active status.';
comment on table public.projects is
'Owner-scoped project root. All project-owned tables carry user_id and project_id and reference this composite key.';

commit;
