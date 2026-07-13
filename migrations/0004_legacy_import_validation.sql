begin;

create table if not exists public.legacy_import_staging (
  staging_id uuid primary key default gen_random_uuid(),
  legacy_import_batch_id uuid not null,
  user_id uuid not null,
  legacy_project_key text,
  legacy_path text not null,
  manifest jsonb not null default '{}'::jsonb,
  checksum text,
  status public.run_status not null default 'pending',
  validation_errors text[] not null default '{}'::text[],
  quarantine_reason text,
  created_at timestamptz not null default now(),
  unique (user_id, staging_id),
  foreign key (user_id, legacy_import_batch_id)
    references public.legacy_import_batches(user_id, legacy_import_batch_id)
    on delete cascade
);

create table if not exists public.legacy_import_quarantine (
  quarantine_id uuid primary key default gen_random_uuid(),
  legacy_import_batch_id uuid not null,
  user_id uuid not null,
  legacy_path text not null,
  reason text not null,
  safe_payload jsonb not null default '{}'::jsonb,
  artifact_id uuid,
  created_at timestamptz not null default now(),
  unique (user_id, quarantine_id),
  foreign key (user_id, legacy_import_batch_id)
    references public.legacy_import_batches(user_id, legacy_import_batch_id)
    on delete cascade,
  foreign key (user_id, artifact_id)
    references public.artifacts(user_id, artifact_id)
);

create index if not exists idx_legacy_import_staging_batch
on public.legacy_import_staging (user_id, legacy_import_batch_id, status);
create index if not exists idx_legacy_import_staging_project_key
on public.legacy_import_staging (user_id, legacy_project_key);
create index if not exists idx_legacy_import_quarantine_batch
on public.legacy_import_quarantine (user_id, legacy_import_batch_id, created_at desc);

create or replace function public.validate_legacy_import_batch(p_batch_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_batch public.legacy_import_batches;
  v_missing_checksum integer;
  v_duplicate_paths integer;
  v_quarantined integer;
  v_summary jsonb;
begin
  select *
  into v_batch
  from public.legacy_import_batches
  where legacy_import_batch_id = p_batch_id
  for update;

  if not found then
    raise exception 'legacy import batch not found: %', p_batch_id;
  end if;

  select count(*)
  into v_missing_checksum
  from public.legacy_import_staging
  where legacy_import_batch_id = p_batch_id
    and (checksum is null or checksum = '');

  select coalesce(sum(path_count - 1), 0)
  into v_duplicate_paths
  from (
    select legacy_path, count(*) as path_count
    from public.legacy_import_staging
    where legacy_import_batch_id = p_batch_id
    group by legacy_path
    having count(*) > 1
  ) duplicates;

  insert into public.legacy_import_quarantine (
    legacy_import_batch_id, user_id, legacy_path, reason, safe_payload
  )
  select
    legacy_import_batch_id,
    user_id,
    legacy_path,
    'missing_checksum',
    jsonb_build_object('legacy_project_key', legacy_project_key)
  from public.legacy_import_staging
  where legacy_import_batch_id = p_batch_id
    and (checksum is null or checksum = '')
  on conflict do nothing;

  select count(*)
  into v_quarantined
  from public.legacy_import_quarantine
  where legacy_import_batch_id = p_batch_id;

  v_summary = jsonb_build_object(
    'missing_checksum_count', v_missing_checksum,
    'duplicate_path_count', v_duplicate_paths,
    'quarantined_count', v_quarantined,
    'validated_at', now()
  );

  update public.legacy_import_batches
  set summary = coalesce(summary, '{}'::jsonb) || v_summary,
      status = case when v_quarantined > 0 then 'completed_with_warnings'::public.run_status else 'completed'::public.run_status end,
      finished_at = now()
  where legacy_import_batch_id = p_batch_id;

  insert into public.audit_events (
    actor_user_id, actor_role, event_type, target_type, target_id, project_id,
    safe_payload, correlation_id
  ) values (
    v_batch.user_id, 'admin', 'legacy_import_validated', 'legacy_import_batch',
    p_batch_id::text, null, v_summary, p_batch_id::text
  );

  return v_summary;
end;
$$;

create or replace view public.legacy_import_quarantine_report as
select
  q.quarantine_id,
  q.legacy_import_batch_id,
  q.user_id,
  q.legacy_path,
  q.reason,
  q.safe_payload,
  q.artifact_id,
  q.created_at
from public.legacy_import_quarantine q;

alter table public.legacy_import_staging enable row level security;
alter table public.legacy_import_staging force row level security;
alter table public.legacy_import_quarantine enable row level security;
alter table public.legacy_import_quarantine force row level security;

create policy "legacy_import_staging owner select" on public.legacy_import_staging
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "legacy_import_staging admin insert" on public.legacy_import_staging
for insert to authenticated with check (public.is_active_admin());
create policy "legacy_import_staging admin update" on public.legacy_import_staging
for update to authenticated using (public.is_active_admin()) with check (public.is_active_admin());

create policy "legacy_import_quarantine owner select" on public.legacy_import_quarantine
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "legacy_import_quarantine admin insert" on public.legacy_import_quarantine
for insert to authenticated with check (public.is_active_admin());
create policy "legacy_import_quarantine no client update" on public.legacy_import_quarantine
for update to authenticated using (false) with check (false);
create policy "legacy_import_quarantine no client delete" on public.legacy_import_quarantine
for delete to authenticated using (false);

comment on table public.legacy_import_staging is
'Admin-only staging for legacy manifests before owner-safe import.';
comment on table public.legacy_import_quarantine is
'Read-only quarantine for unsafe legacy folders/files. Data is not silently dropped.';
comment on function public.validate_legacy_import_batch(uuid) is
'Validates staged legacy rows for missing checksums, duplicate paths, and quarantine reporting.';

commit;
