begin;

do $$
begin
  create type public.file_status as enum ('uploaded', 'processing', 'ready', 'failed', 'deleted');
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.document_kind as enum ('source_pdf', 'correction_pdf', 'reference_db', 'legacy_import');
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.pipeline_status as enum (
    'pending',
    'running',
    'completed',
    'completed_with_warnings',
    'failed',
    'cancelled'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.product_step_key as enum (
    'step1_text_extraction',
    'step2_qcm_extraction',
    'step3_correction',
    'step4_similarity_match'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.internal_cycle_key as enum (
    'step1_detection',
    'step1_text_quality',
    'step2_qcm_pages',
    'step2_metadata',
    'step2_format',
    'step2_finalize',
    'step3_page_detection',
    'step3_vision',
    'step3_auto_detection',
    'step4_match'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.run_status as enum (
    'pending',
    'running',
    'completed',
    'completed_with_warnings',
    'failed',
    'cancelled',
    'skipped'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.task_status as enum (
    'pending',
    'queued',
    'running',
    'retrying',
    'completed',
    'completed_with_warnings',
    'failed',
    'cancelled',
    'expired',
    'skipped'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.task_attempt_status as enum (
    'running',
    'completed',
    'completed_with_warnings',
    'failed',
    'cancelled',
    'expired'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.task_kind as enum (
    'step1_extract',
    'step1_text_quality',
    'step2_page_qcm',
    'step2_metadata',
    'step2_format',
    'step2_finalize',
    'step3_correction',
    'step4_similarity_match',
    'manual_auto_run',
    'ai_auto_run',
    'legacy_import',
    'cleanup'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.terminal_level as enum ('debug', 'info', 'warning', 'error', 'success');
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.terminal_event_type as enum (
    'run_started',
    'run_completed',
    'step_started',
    'step_completed',
    'task_claimed',
    'task_heartbeat',
    'artifact_written',
    'quality_warning',
    'retry_scheduled',
    'cancel_requested',
    'task_failed',
    'system_message'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.artifact_type as enum (
    'source_pdf',
    'page_text',
    'page_image',
    'step1_text',
    'step2_page_qcm_json',
    'step2_final_json',
    'step2_final_xlsx',
    'step3_correction_json',
    'step3_correction_xlsx',
    'step4_similarity_json',
    'step4_similarity_xlsx',
    'reference_db',
    'ai_autorun_document_map',
    'ai_autorun_config',
    'ai_autorun_evidence',
    'debug_internal',
    'legacy_import'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.retention_policy as enum (
    'source_until_project_delete',
    'final_until_project_delete',
    'intermediate_cleanup',
    'debug_short_lived',
    'audit_retained_redacted',
    'legacy_read_only'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.quality_status as enum (
    'passed',
    'passed_with_warnings',
    'failed',
    'manual_review_required',
    'skipped'
  );
exception when duplicate_object then null;
end $$;

do $$
begin
  create type public.provider_limit_event as enum (
    'none',
    'rate_limited',
    'context_limit',
    'token_limit',
    'file_size_limit',
    'quota_exceeded',
    'provider_unavailable',
    'unknown'
  );
exception when duplicate_object then null;
end $$;

create table if not exists public.source_files (
  source_file_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  original_filename text not null,
  storage_key text not null unique,
  content_type text not null default 'application/pdf',
  size_bytes bigint not null check (size_bytes >= 0 and size_bytes <= 52428800),
  checksum text not null,
  status public.file_status not null default 'uploaded',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, project_id, source_file_id),
  foreign key (user_id, project_id)
    references public.projects(user_id, project_id)
    on delete cascade
);

create table if not exists public.documents (
  document_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  source_file_id uuid not null,
  kind public.document_kind not null default 'source_pdf',
  page_count integer check (page_count is null or page_count >= 0),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, project_id, document_id),
  foreign key (user_id, project_id, source_file_id)
    references public.source_files(user_id, project_id, source_file_id)
    on delete cascade
);

create table if not exists public.pages (
  page_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  document_id uuid not null,
  page_number integer not null check (page_number > 0),
  text_artifact_id uuid,
  image_artifact_id uuid,
  text_quality jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, project_id, page_id),
  unique (document_id, page_number),
  foreign key (user_id, project_id, document_id)
    references public.documents(user_id, project_id, document_id)
    on delete cascade
);

create table if not exists public.pipeline_runs (
  pipeline_run_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  status public.pipeline_status not null default 'pending',
  triggered_by text not null check (
    triggered_by in ('manual', 'manual_auto_run', 'ai_auto_run', 'legacy_import', 'system')
  ),
  source_file_id uuid,
  summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz not null default now(),
  unique (user_id, project_id, pipeline_run_id),
  foreign key (user_id, project_id)
    references public.projects(user_id, project_id)
    on delete cascade,
  foreign key (user_id, project_id, source_file_id)
    references public.source_files(user_id, project_id, source_file_id)
);

create table if not exists public.product_step_runs (
  product_step_run_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  pipeline_run_id uuid not null,
  step_key public.product_step_key not null,
  status public.run_status not null default 'pending',
  configuration_snapshot_id uuid,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, project_id, product_step_run_id),
  unique (user_id, project_id, pipeline_run_id, step_key),
  foreign key (user_id, project_id, pipeline_run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
    on delete cascade
);

create table if not exists public.internal_cycle_runs (
  internal_cycle_run_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  product_step_run_id uuid not null,
  cycle_key public.internal_cycle_key not null,
  status public.run_status not null default 'pending',
  metrics jsonb not null default '{}'::jsonb,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, project_id, internal_cycle_run_id),
  unique (user_id, project_id, product_step_run_id, cycle_key),
  foreign key (user_id, project_id, product_step_run_id)
    references public.product_step_runs(user_id, project_id, product_step_run_id)
    on delete cascade
);

create table if not exists public.configuration_snapshots (
  snapshot_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  run_id uuid not null,
  pipeline_run_id uuid not null,
  schema_version text not null,
  source_precedence text[] not null default '{}'::text[],
  resolved_values jsonb not null default '{}'::jsonb,
  secret_refs jsonb not null default '{}'::jsonb,
  created_by text not null,
  created_at timestamptz not null default now(),
  unique (user_id, project_id, snapshot_id),
  foreign key (user_id, project_id, run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
    on delete cascade,
  foreign key (user_id, project_id, pipeline_run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
    on delete cascade,
  check (run_id = pipeline_run_id)
);

create table if not exists public.tasks (
  task_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  run_id uuid not null,
  product_step_run_id uuid,
  internal_cycle_run_id uuid,
  kind public.task_kind not null,
  status public.task_status not null default 'pending',
  idempotency_key text not null,
  lease_expires_at timestamptz,
  heartbeat_at timestamptz,
  attempt integer not null default 0 check (attempt >= 0),
  max_attempts integer not null default 3 check (max_attempts >= 1),
  payload jsonb not null default '{}'::jsonb,
  priority integer not null default 0,
  correlation_id text not null,
  last_error_code text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  available_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  unique (user_id, project_id, task_id),
  unique (user_id, project_id, idempotency_key),
  foreign key (user_id, project_id, run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
    on delete cascade,
  foreign key (user_id, project_id, product_step_run_id)
    references public.product_step_runs(user_id, project_id, product_step_run_id),
  foreign key (user_id, project_id, internal_cycle_run_id)
    references public.internal_cycle_runs(user_id, project_id, internal_cycle_run_id)
);

create table if not exists public.task_attempts (
  attempt_id uuid primary key default gen_random_uuid(),
  task_id uuid not null,
  user_id uuid not null,
  project_id uuid not null,
  run_id uuid not null,
  attempt_number integer not null check (attempt_number > 0),
  status public.task_attempt_status not null default 'running',
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  worker_id text not null,
  error_code text,
  safe_error_message text,
  created_at timestamptz not null default now(),
  unique (user_id, project_id, attempt_id),
  unique (task_id, attempt_number),
  foreign key (user_id, project_id, task_id)
    references public.tasks(user_id, project_id, task_id)
    on delete cascade,
  foreign key (user_id, project_id, run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
    on delete cascade
);

create table if not exists public.terminal_events (
  event_id uuid primary key default gen_random_uuid(),
  sequence bigint generated always as identity,
  user_id uuid not null,
  project_id uuid not null,
  run_id uuid,
  task_id uuid,
  attempt_id uuid,
  level public.terminal_level not null,
  event_type public.terminal_event_type not null,
  message text not null,
  safe_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (user_id, project_id, event_id),
  foreign key (user_id, project_id)
    references public.projects(user_id, project_id)
    on delete cascade,
  foreign key (user_id, project_id, run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
    on delete cascade,
  foreign key (user_id, project_id, task_id)
    references public.tasks(user_id, project_id, task_id)
    on delete cascade,
  foreign key (user_id, project_id, attempt_id)
    references public.task_attempts(user_id, project_id, attempt_id)
    on delete cascade
);

create table if not exists public.artifacts (
  artifact_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  run_id uuid,
  product_step_run_id uuid,
  internal_cycle_run_id uuid,
  reference_database_id uuid,
  artifact_type public.artifact_type not null,
  latest_version_id uuid,
  name text,
  visibility text not null default 'private' check (visibility in ('private', 'admin_only')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, artifact_id),
  unique (user_id, project_id, artifact_id),
  foreign key (user_id, project_id)
    references public.projects(user_id, project_id)
    on delete cascade,
  foreign key (user_id, project_id, run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
    on delete cascade,
  foreign key (user_id, project_id, product_step_run_id)
    references public.product_step_runs(user_id, project_id, product_step_run_id),
  foreign key (user_id, project_id, internal_cycle_run_id)
    references public.internal_cycle_runs(user_id, project_id, internal_cycle_run_id)
);

create table if not exists public.artifact_versions (
  artifact_version_id uuid primary key default gen_random_uuid(),
  artifact_id uuid not null,
  user_id uuid not null,
  project_id uuid not null,
  run_id uuid,
  version_number integer not null check (version_number > 0),
  storage_key text not null,
  content_type text not null,
  checksum text not null,
  size_bytes bigint not null check (size_bytes >= 0),
  schema_version text not null,
  retention_policy public.retention_policy not null,
  source_artifact_ids uuid[] not null default '{}'::uuid[],
  created_at timestamptz not null default now(),
  unique (user_id, project_id, artifact_version_id),
  unique (artifact_id, version_number),
  unique (user_id, project_id, storage_key),
  foreign key (user_id, project_id, artifact_id)
    references public.artifacts(user_id, project_id, artifact_id)
    on delete cascade,
  foreign key (user_id, project_id, run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
);

alter table public.artifacts
add constraint artifacts_latest_version_fk
foreign key (latest_version_id)
references public.artifact_versions(artifact_version_id)
deferrable initially deferred;

alter table public.pages
add constraint pages_text_artifact_fk
foreign key (user_id, project_id, text_artifact_id)
references public.artifacts(user_id, project_id, artifact_id);

alter table public.pages
add constraint pages_image_artifact_fk
foreign key (user_id, project_id, image_artifact_id)
references public.artifacts(user_id, project_id, artifact_id);

alter table public.product_step_runs
add constraint product_step_runs_configuration_snapshot_fk
foreign key (user_id, project_id, configuration_snapshot_id)
references public.configuration_snapshots(user_id, project_id, snapshot_id);

create table if not exists public.quality_evaluations (
  evaluation_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  artifact_id uuid,
  run_id uuid not null,
  task_id uuid,
  status public.quality_status not null,
  metrics jsonb not null default '{}'::jsonb,
  warnings text[] not null default '{}'::text[],
  failures text[] not null default '{}'::text[],
  manual_review_required boolean not null default false,
  evidence_artifact_ids uuid[] not null default '{}'::uuid[],
  created_at timestamptz not null default now(),
  unique (user_id, project_id, evaluation_id),
  foreign key (user_id, project_id, run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id)
    on delete cascade,
  foreign key (user_id, project_id, artifact_id)
    references public.artifacts(user_id, project_id, artifact_id),
  foreign key (user_id, project_id, task_id)
    references public.tasks(user_id, project_id, task_id)
);

create table if not exists public.llm_requests (
  llm_request_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  run_id uuid,
  task_id uuid,
  provider text not null default 'openrouter' check (provider = 'openrouter'),
  model_id text not null,
  request_purpose text not null,
  prompt_artifact_id uuid,
  response_artifact_id uuid,
  status public.run_status not null default 'pending',
  created_at timestamptz not null default now(),
  finished_at timestamptz,
  unique (user_id, project_id, llm_request_id),
  foreign key (user_id, project_id, run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id),
  foreign key (user_id, project_id, task_id)
    references public.tasks(user_id, project_id, task_id),
  foreign key (user_id, project_id, prompt_artifact_id)
    references public.artifacts(user_id, project_id, artifact_id),
  foreign key (user_id, project_id, response_artifact_id)
    references public.artifacts(user_id, project_id, artifact_id)
);

create table if not exists public.model_fallback_attempts (
  fallback_attempt_id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  project_id uuid not null,
  llm_request_id uuid not null,
  attempt_number integer not null check (attempt_number > 0),
  provider text not null default 'openrouter' check (provider = 'openrouter'),
  model_id text not null,
  status public.run_status not null,
  error_code text,
  safe_error_message text,
  tokens_in integer not null default 0 check (tokens_in >= 0),
  tokens_out integer not null default 0 check (tokens_out >= 0),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  unique (user_id, project_id, fallback_attempt_id),
  unique (llm_request_id, attempt_number),
  foreign key (user_id, project_id, llm_request_id)
    references public.llm_requests(user_id, project_id, llm_request_id)
    on delete cascade
);

create table if not exists public.usage_records (
  usage_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  project_id uuid,
  run_id uuid,
  task_id uuid,
  provider text not null,
  model_id text,
  operation text not null,
  tokens_in integer not null default 0 check (tokens_in >= 0),
  tokens_out integer not null default 0 check (tokens_out >= 0),
  cost_estimate numeric,
  currency text,
  unit_count numeric not null default 0,
  provider_limit_event public.provider_limit_event not null default 'none',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  foreign key (user_id, project_id)
    references public.projects(user_id, project_id)
    on delete cascade,
  foreign key (user_id, project_id, run_id)
    references public.pipeline_runs(user_id, project_id, pipeline_run_id),
  foreign key (user_id, project_id, task_id)
    references public.tasks(user_id, project_id, task_id)
);

create table if not exists public.audit_events (
  audit_event_id uuid primary key default gen_random_uuid(),
  actor_user_id uuid references public.profiles(user_id),
  actor_role public.app_role not null,
  event_type text not null,
  target_type text not null,
  target_id text not null,
  project_id uuid,
  safe_payload jsonb not null default '{}'::jsonb,
  correlation_id text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_source_files_project_created
on public.source_files (user_id, project_id, created_at desc);
create index if not exists idx_documents_source_file
on public.documents (user_id, project_id, source_file_id);
create unique index if not exists idx_pages_document_number
on public.pages (user_id, project_id, document_id, page_number);
create index if not exists idx_pipeline_runs_project_created
on public.pipeline_runs (user_id, project_id, created_at desc);
create index if not exists idx_product_step_runs_lookup
on public.product_step_runs (user_id, project_id, pipeline_run_id, step_key);
create index if not exists idx_internal_cycle_runs_lookup
on public.internal_cycle_runs (user_id, project_id, product_step_run_id, cycle_key);
create index if not exists idx_configuration_snapshots_run_created
on public.configuration_snapshots (user_id, project_id, run_id, created_at desc);
create index if not exists idx_tasks_claim
on public.tasks (status, available_at, priority desc, created_at)
where status in ('queued', 'retrying');
create index if not exists idx_tasks_run_history
on public.tasks (user_id, project_id, run_id, created_at desc);
create unique index if not exists idx_tasks_idempotency
on public.tasks (user_id, project_id, idempotency_key);
create unique index if not exists idx_task_attempts_order
on public.task_attempts (task_id, attempt_number);
create index if not exists idx_terminal_events_cursor
on public.terminal_events (user_id, project_id, sequence);
create index if not exists idx_terminal_events_run
on public.terminal_events (user_id, project_id, run_id, created_at);
create index if not exists idx_artifacts_results
on public.artifacts (user_id, project_id, run_id, artifact_type, updated_at desc);
create unique index if not exists idx_artifact_versions_number
on public.artifact_versions (artifact_id, version_number);
create unique index if not exists idx_artifact_versions_storage_key
on public.artifact_versions (user_id, project_id, storage_key);
create index if not exists idx_quality_evaluations_run
on public.quality_evaluations (user_id, project_id, run_id, created_at desc);
create index if not exists idx_llm_requests_task
on public.llm_requests (user_id, project_id, task_id, created_at desc);
create index if not exists idx_usage_records_user_created
on public.usage_records (user_id, created_at desc);
create index if not exists idx_usage_records_run
on public.usage_records (user_id, project_id, run_id);
create index if not exists idx_audit_events_actor_created
on public.audit_events (actor_user_id, created_at desc);
create index if not exists idx_audit_events_project_created
on public.audit_events (project_id, created_at desc);

create trigger trg_source_files_updated_at
before update on public.source_files
for each row execute function public.set_updated_at();
create trigger trg_documents_updated_at
before update on public.documents
for each row execute function public.set_updated_at();
create trigger trg_pages_updated_at
before update on public.pages
for each row execute function public.set_updated_at();
create trigger trg_pipeline_runs_updated_at
before update on public.pipeline_runs
for each row execute function public.set_updated_at();
create trigger trg_product_step_runs_updated_at
before update on public.product_step_runs
for each row execute function public.set_updated_at();
create trigger trg_internal_cycle_runs_updated_at
before update on public.internal_cycle_runs
for each row execute function public.set_updated_at();
create trigger trg_tasks_updated_at
before update on public.tasks
for each row execute function public.set_updated_at();
create trigger trg_artifacts_updated_at
before update on public.artifacts
for each row execute function public.set_updated_at();

create or replace function public.prevent_update()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  raise exception 'Updates are not allowed on append-only table %', tg_table_name;
end;
$$;

create trigger trg_configuration_snapshots_immutable
before update on public.configuration_snapshots
for each row execute function public.prevent_update();
create trigger trg_task_attempts_append_only
before update on public.task_attempts
for each row execute function public.prevent_update();
create trigger trg_terminal_events_append_only
before update on public.terminal_events
for each row execute function public.prevent_update();
create trigger trg_artifact_versions_append_only
before update on public.artifact_versions
for each row execute function public.prevent_update();
create trigger trg_usage_records_append_only
before update on public.usage_records
for each row execute function public.prevent_update();
create trigger trg_audit_events_append_only
before update on public.audit_events
for each row execute function public.prevent_update();

create or replace function public.claim_next_task(p_worker_id text)
returns public.tasks
language plpgsql
security definer
set search_path = public
as $$
declare
  v_task public.tasks;
  v_attempt_id uuid;
begin
  select *
  into v_task
  from public.tasks
  where status in ('queued', 'retrying')
    and available_at <= now()
  order by priority desc, available_at asc, created_at asc
  for update skip locked
  limit 1;

  if not found then
    return null;
  end if;

  update public.tasks
  set status = 'running',
      attempt = attempt + 1,
      lease_expires_at = now() + interval '120 seconds',
      heartbeat_at = now(),
      started_at = coalesce(started_at, now()),
      updated_at = now()
  where task_id = v_task.task_id
  returning * into v_task;

  insert into public.task_attempts (
    task_id, user_id, project_id, run_id, attempt_number, status, worker_id
  ) values (
    v_task.task_id, v_task.user_id, v_task.project_id, v_task.run_id,
    v_task.attempt, 'running', p_worker_id
  )
  returning attempt_id into v_attempt_id;

  insert into public.terminal_events (
    user_id, project_id, run_id, task_id, attempt_id, level, event_type, message, safe_payload
  ) values (
    v_task.user_id, v_task.project_id, v_task.run_id, v_task.task_id, v_attempt_id,
    'info', 'task_claimed', 'Task claimed by worker',
    jsonb_build_object('worker_id', p_worker_id, 'task_kind', v_task.kind)
  );

  insert into public.audit_events (
    actor_role, event_type, target_type, target_id, project_id, safe_payload, correlation_id
  ) values (
    'worker', 'worker_claimed_task', 'task', v_task.task_id::text, v_task.project_id,
    jsonb_build_object('worker_id', p_worker_id), v_task.correlation_id
  );

  return v_task;
end;
$$;

create or replace function public.heartbeat_task(p_task_id uuid, p_worker_id text)
returns public.tasks
language plpgsql
security definer
set search_path = public
as $$
declare
  v_task public.tasks;
begin
  update public.tasks
  set heartbeat_at = now(),
      lease_expires_at = now() + interval '120 seconds',
      updated_at = now()
  where task_id = p_task_id
    and status = 'running'
  returning * into v_task;

  if not found then
    return null;
  end if;

  insert into public.terminal_events (
    user_id, project_id, run_id, task_id, level, event_type, message, safe_payload
  ) values (
    v_task.user_id, v_task.project_id, v_task.run_id, v_task.task_id,
    'debug', 'task_heartbeat', 'Task heartbeat recorded',
    jsonb_build_object('worker_id', p_worker_id)
  );

  return v_task;
end;
$$;

create or replace function public.cancel_task(p_task_id uuid, p_actor_user_id uuid, p_correlation_id text)
returns public.tasks
language plpgsql
security definer
set search_path = public
as $$
declare
  v_task public.tasks;
begin
  update public.tasks
  set status = 'cancelled',
      finished_at = now(),
      updated_at = now()
  where task_id = p_task_id
    and status in ('pending', 'queued', 'retrying', 'running')
  returning * into v_task;

  if not found then
    return null;
  end if;

  insert into public.terminal_events (
    user_id, project_id, run_id, task_id, level, event_type, message, safe_payload
  ) values (
    v_task.user_id, v_task.project_id, v_task.run_id, v_task.task_id,
    'warning', 'cancel_requested', 'Task cancellation requested',
    jsonb_build_object('actor_user_id', p_actor_user_id)
  );

  insert into public.audit_events (
    actor_user_id, actor_role, event_type, target_type, target_id, project_id,
    safe_payload, correlation_id
  ) values (
    p_actor_user_id, 'user', 'run_cancelled', 'task', v_task.task_id::text, v_task.project_id,
    '{}'::jsonb, p_correlation_id
  );

  return v_task;
end;
$$;

alter table public.source_files enable row level security;
alter table public.source_files force row level security;
alter table public.documents enable row level security;
alter table public.documents force row level security;
alter table public.pages enable row level security;
alter table public.pages force row level security;
alter table public.pipeline_runs enable row level security;
alter table public.pipeline_runs force row level security;
alter table public.product_step_runs enable row level security;
alter table public.product_step_runs force row level security;
alter table public.internal_cycle_runs enable row level security;
alter table public.internal_cycle_runs force row level security;
alter table public.configuration_snapshots enable row level security;
alter table public.configuration_snapshots force row level security;
alter table public.tasks enable row level security;
alter table public.tasks force row level security;
alter table public.task_attempts enable row level security;
alter table public.task_attempts force row level security;
alter table public.terminal_events enable row level security;
alter table public.terminal_events force row level security;
alter table public.artifacts enable row level security;
alter table public.artifacts force row level security;
alter table public.artifact_versions enable row level security;
alter table public.artifact_versions force row level security;
alter table public.quality_evaluations enable row level security;
alter table public.quality_evaluations force row level security;
alter table public.llm_requests enable row level security;
alter table public.llm_requests force row level security;
alter table public.model_fallback_attempts enable row level security;
alter table public.model_fallback_attempts force row level security;
alter table public.usage_records enable row level security;
alter table public.usage_records force row level security;
alter table public.audit_events enable row level security;
alter table public.audit_events force row level security;

create policy "source_files owned project select" on public.source_files
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "source_files owned project insert" on public.source_files
for insert to authenticated with check (user_id = auth.uid());
create policy "source_files owned project update" on public.source_files
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "documents owned project select" on public.documents
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "documents owned project insert" on public.documents
for insert to authenticated with check (user_id = auth.uid());
create policy "documents owned project update" on public.documents
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "pages owned project select" on public.pages
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "pages owned project insert" on public.pages
for insert to authenticated with check (user_id = auth.uid());
create policy "pages owned project update" on public.pages
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "pipeline_runs owned project select" on public.pipeline_runs
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "pipeline_runs owned project insert" on public.pipeline_runs
for insert to authenticated with check (user_id = auth.uid());
create policy "pipeline_runs owned project update" on public.pipeline_runs
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "product_step_runs owned project select" on public.product_step_runs
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "product_step_runs owned project insert" on public.product_step_runs
for insert to authenticated with check (user_id = auth.uid());
create policy "product_step_runs owned project update" on public.product_step_runs
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "internal_cycle_runs owned project select" on public.internal_cycle_runs
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "internal_cycle_runs owned project insert" on public.internal_cycle_runs
for insert to authenticated with check (user_id = auth.uid());
create policy "internal_cycle_runs owned project update" on public.internal_cycle_runs
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "configuration_snapshots owner read append only" on public.configuration_snapshots
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "configuration_snapshots owner insert" on public.configuration_snapshots
for insert to authenticated with check (user_id = auth.uid());
create policy "configuration_snapshots no client update" on public.configuration_snapshots
for update to authenticated using (false) with check (false);
create policy "configuration_snapshots no client delete" on public.configuration_snapshots
for delete to authenticated using (false);

create policy "tasks owned project select" on public.tasks
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "tasks owned project insert" on public.tasks
for insert to authenticated with check (user_id = auth.uid());
create policy "tasks owned project update" on public.tasks
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "task_attempts owner read append only" on public.task_attempts
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "task_attempts no client update" on public.task_attempts
for update to authenticated using (false) with check (false);
create policy "task_attempts no client delete" on public.task_attempts
for delete to authenticated using (false);

create policy "terminal_events owner read append only" on public.terminal_events
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "terminal_events no client update" on public.terminal_events
for update to authenticated using (false) with check (false);
create policy "terminal_events no client delete" on public.terminal_events
for delete to authenticated using (false);

create policy "artifacts owned project select" on public.artifacts
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "artifacts owned project insert" on public.artifacts
for insert to authenticated with check (user_id = auth.uid());
create policy "artifacts owned project update" on public.artifacts
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "artifact_versions owner read append only" on public.artifact_versions
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "artifact_versions owner insert" on public.artifact_versions
for insert to authenticated with check (user_id = auth.uid());
create policy "artifact_versions no client update" on public.artifact_versions
for update to authenticated using (false) with check (false);
create policy "artifact_versions no client delete" on public.artifact_versions
for delete to authenticated using (false);

create policy "quality_evaluations owner read append only" on public.quality_evaluations
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "quality_evaluations owner insert" on public.quality_evaluations
for insert to authenticated with check (user_id = auth.uid());
create policy "quality_evaluations no client update" on public.quality_evaluations
for update to authenticated using (false) with check (false);

create policy "llm_requests owned project select" on public.llm_requests
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "llm_requests owned project insert" on public.llm_requests
for insert to authenticated with check (user_id = auth.uid());
create policy "llm_requests owned project update" on public.llm_requests
for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "model_fallback_attempts owner read append only" on public.model_fallback_attempts
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "model_fallback_attempts owner insert" on public.model_fallback_attempts
for insert to authenticated with check (user_id = auth.uid());
create policy "model_fallback_attempts no client update" on public.model_fallback_attempts
for update to authenticated using (false) with check (false);

create policy "usage_records owner read append only" on public.usage_records
for select to authenticated using (user_id = auth.uid() or public.is_active_admin());
create policy "usage_records owner insert" on public.usage_records
for insert to authenticated with check (user_id = auth.uid());
create policy "usage_records no client update" on public.usage_records
for update to authenticated using (false) with check (false);
create policy "usage_records no client delete" on public.usage_records
for delete to authenticated using (false);

create policy "audit_events actor read" on public.audit_events
for select to authenticated
using (actor_user_id = auth.uid() or public.is_active_admin());
create policy "audit_events no client update" on public.audit_events
for update to authenticated using (false) with check (false);
create policy "audit_events no client delete" on public.audit_events
for delete to authenticated using (false);

comment on table public.terminal_events is 'Append-only project terminal stream ordered by sequence.';
comment on table public.artifact_versions is 'Append-only stored object versions. Storage key is checked through DB ownership before signed URL issuance.';
comment on function public.claim_next_task(text) is 'Worker service function using FOR UPDATE SKIP LOCKED, 120 second lease, audit, attempt, and terminal event writes.';

commit;
