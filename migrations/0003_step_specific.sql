begin;

do $$
begin
  create type public.step3_correction_mode as enum (
    'page_detection',
    'vision',
    'auto_detection'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.automation_status as enum (
    'draft',
    'validated',
    'running',
    'completed',
    'completed_with_warnings',
    'failed',
    'cancelled',
    'manual_review_required'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.audit_event_type as enum (
    'project_created',
    'project_deleted',
    'signed_url_created',
    'run_started',
    'run_cancelled',
    'run_retried',
    'worker_claimed_task',
    'reference_db_uploaded',
    'reference_db_deleted',
    'admin_access',
    'account_deletion_requested',
    'cross_user_access_denied'
  );
exception when duplicate_object then null;
end $$;

create table if not exists public.auto_runs (
  auto_run_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  pipeline_run_id uuid not null,
  status public.automation_status not null default 'draft',
  selected_steps public.product_step_key[] not null default '{}'::public.product_step_key[],
  configuration_snapshot_id uuid not null,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  unique (user_id, project_id, auto_run_id),
  unique (user_id, project_id, pipeline_run_id),
  foreign key (user_id, project_id, pipeline_run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
    on delete cascade,
  foreign key (user_id, project_id, configuration_snapshot_id)
    references public.configuration_snapshots(user_id, project_id, snapshot_id)
);

create table if not exists public.ai_auto_runs (
  ai_auto_run_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  pipeline_run_id uuid not null,
  status public.automation_status not null default 'draft',
  model_preference_id uuid,
  generated_config_snapshot_id uuid,
  evidence_summary jsonb not null default '{}'::jsonb,
  stop_reason text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  unique (user_id, project_id, ai_auto_run_id),
  unique (user_id, project_id, pipeline_run_id),
  foreign key (user_id, project_id, pipeline_run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
    on delete cascade,
  foreign key (model_preference_id)
    references public.model_preferences(model_preference_id),
  foreign key (user_id, project_id, generated_config_snapshot_id)
    references public.configuration_snapshots(user_id, project_id, snapshot_id)
);

create table if not exists public.document_maps (
  document_map_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  ai_auto_run_id uuid not null,
  artifact_version_id uuid not null,
  summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (user_id, project_id, document_map_id),
  foreign key (user_id, project_id, ai_auto_run_id)
    references public.ai_auto_runs(user_id, project_id, ai_auto_run_id)
    on delete cascade,
  foreign key (user_id, project_id, artifact_version_id)
    references public.artifact_versions(user_id, project_id, artifact_version_id)
);

create table if not exists public.reference_databases (
  reference_database_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  project_id uuid,
  name text not null,
  artifact_id uuid not null,
  schema_version text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz,
  unique (user_id, reference_database_id),
  foreign key (user_id, project_id)
    references public.projects(user_id, project_id)
    on delete set null,
  foreign key (user_id, artifact_id)
    references public.artifacts(user_id, artifact_id)
);

alter table public.artifacts
add constraint artifacts_reference_database_fk
foreign key (user_id, reference_database_id)
references public.reference_databases(user_id, reference_database_id)
deferrable initially deferred;

create table if not exists public.legacy_import_batches (
  legacy_import_batch_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  source_root text not null,
  status public.run_status not null default 'pending',
  summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  finished_at timestamptz,
  unique (user_id, legacy_import_batch_id)
);

create table if not exists public.step3_correction_mode_aliases (
  legacy_mode text primary key,
  canonical_mode public.step3_correction_mode not null,
  created_at timestamptz not null default now(),
  check (
    (legacy_mode = 'page_text' and canonical_mode = 'page_detection')
    or (legacy_mode = 'vision_ai' and canonical_mode = 'vision')
    or (legacy_mode in ('auto_detect', 'all_pages') and canonical_mode = 'auto_detection')
  )
);

insert into public.step3_correction_mode_aliases (legacy_mode, canonical_mode)
values
  ('page_text', 'page_detection'),
  ('vision_ai', 'vision'),
  ('auto_detect', 'auto_detection'),
  ('all_pages', 'auto_detection')
on conflict (legacy_mode) do update
set canonical_mode = excluded.canonical_mode;

create index if not exists idx_auto_runs_pipeline
on public.auto_runs (user_id, project_id, pipeline_run_id);
create index if not exists idx_ai_auto_runs_pipeline
on public.ai_auto_runs (user_id, project_id, pipeline_run_id);
create index if not exists idx_document_maps_ai_run
on public.document_maps (user_id, project_id, ai_auto_run_id);
create index if not exists idx_reference_databases_user
on public.reference_databases (user_id, deleted_at, updated_at desc);
create index if not exists idx_legacy_import_batches_user
on public.legacy_import_batches (user_id, created_at desc);

create trigger trg_reference_databases_updated_at
before update on public.reference_databases
for each row execute function public.set_updated_at();

alter table public.auto_runs enable row level security;
alter table public.auto_runs force row level security;
alter table public.ai_auto_runs enable row level security;
alter table public.ai_auto_runs force row level security;
alter table public.document_maps enable row level security;
alter table public.document_maps force row level security;
alter table public.reference_databases enable row level security;
alter table public.reference_databases force row level security;
alter table public.legacy_import_batches enable row level security;
alter table public.legacy_import_batches force row level security;
alter table public.step3_correction_mode_aliases enable row level security;
alter table public.step3_correction_mode_aliases force row level security;

create policy "auto_runs owned project select" on public.auto_runs
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "auto_runs owned project insert" on public.auto_runs
for insert to authenticated with check (user_id = auth.uid());
create policy "auto_runs owned project update" on public.auto_runs
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "ai_auto_runs owned project select" on public.ai_auto_runs
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "ai_auto_runs owned project insert" on public.ai_auto_runs
for insert to authenticated with check (user_id = auth.uid());
create policy "ai_auto_runs owned project update" on public.ai_auto_runs
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "document_maps owned project select" on public.document_maps
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "document_maps owned project insert" on public.document_maps
for insert to authenticated with check (user_id = auth.uid());

create policy "reference_databases owner select" on public.reference_databases
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "reference_databases owner insert" on public.reference_databases
for insert to authenticated with check (user_id = auth.uid());
create policy "reference_databases owner update" on public.reference_databases
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "legacy_import_batches owner select" on public.legacy_import_batches
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "legacy_import_batches admin insert" on public.legacy_import_batches
for insert to authenticated with check (public.is_active_admin());
create policy "legacy_import_batches admin update" on public.legacy_import_batches
for update to authenticated using (public.is_active_admin()) with check (public.is_active_admin());

create policy "step3_correction_mode_aliases authenticated read" on public.step3_correction_mode_aliases
for select to authenticated using (true);
create policy "step3_correction_mode_aliases no client write" on public.step3_correction_mode_aliases
for all to authenticated using (false) with check (false);

comment on table public.step3_correction_mode_aliases is
'Approved legacy mapping: page_text -> page_detection, vision_ai -> vision, auto_detect/all_pages -> auto_detection.';
comment on table public.ai_auto_runs is
'AI Auto Run records store safe evidence summaries only; private reasoning is never stored or displayed.';
comment on table public.reference_databases is
'Private user-owned reference databases. Shared/public marketplace is deferred.';

commit;
