"""Static verification for Plan 03 migration files.

This is intentionally dependency-free. Live Supabase/Postgres execution and two-user RLS tests are
added once a database is available, but this catches the contract and ownership shape locally.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"

MIGRATION_FILES = [
    "0001_profiles_projects.sql",
    "0002_runs_tasks_artifacts.sql",
    "0003_step_specific.sql",
    "0004_legacy_import_validation.sql",
]

EXPECTED_ENUMS = {
    "app_role",
    "profile_status",
    "project_status",
    "file_status",
    "document_kind",
    "pipeline_status",
    "product_step_key",
    "internal_cycle_key",
    "run_status",
    "task_status",
    "task_attempt_status",
    "task_kind",
    "terminal_level",
    "terminal_event_type",
    "artifact_type",
    "retention_policy",
    "quality_status",
    "provider_limit_event",
    "step3_correction_mode",
    "automation_status",
    "audit_event_type",
}

EXPECTED_TABLES = {
    "profiles",
    "user_preferences",
    "model_preferences",
    "projects",
    "source_files",
    "documents",
    "pages",
    "pipeline_runs",
    "product_step_runs",
    "internal_cycle_runs",
    "configuration_snapshots",
    "tasks",
    "task_attempts",
    "terminal_events",
    "artifacts",
    "artifact_versions",
    "quality_evaluations",
    "llm_requests",
    "model_fallback_attempts",
    "usage_records",
    "audit_events",
    "auto_runs",
    "ai_auto_runs",
    "document_maps",
    "reference_databases",
    "legacy_import_batches",
    "step3_correction_mode_aliases",
    "legacy_import_staging",
    "legacy_import_quarantine",
}

PROJECT_OWNED_TABLES = {
    "projects",
    "source_files",
    "documents",
    "pages",
    "pipeline_runs",
    "product_step_runs",
    "internal_cycle_runs",
    "configuration_snapshots",
    "tasks",
    "task_attempts",
    "terminal_events",
    "artifacts",
    "artifact_versions",
    "quality_evaluations",
    "llm_requests",
    "model_fallback_attempts",
    "usage_records",
    "auto_runs",
    "ai_auto_runs",
    "document_maps",
}

USER_OWNED_TABLES = {
    "profiles",
    "user_preferences",
    "model_preferences",
    "reference_databases",
    "legacy_import_batches",
    "legacy_import_staging",
    "legacy_import_quarantine",
}

APPEND_ONLY_TABLES = {
    "configuration_snapshots",
    "task_attempts",
    "terminal_events",
    "artifact_versions",
    "usage_records",
    "audit_events",
}

SHARED_CONTRACT_COLUMNS = {
    "tasks": {
        "task_id",
        "user_id",
        "project_id",
        "run_id",
        "kind",
        "status",
        "idempotency_key",
        "lease_expires_at",
        "heartbeat_at",
        "attempt",
        "max_attempts",
        "payload",
        "created_at",
        "updated_at",
        "available_at",
        "started_at",
        "finished_at",
    },
    "task_attempts": {
        "attempt_id",
        "task_id",
        "attempt_number",
        "status",
        "started_at",
        "finished_at",
        "worker_id",
        "error_code",
        "safe_error_message",
    },
    "terminal_events": {
        "event_id",
        "user_id",
        "project_id",
        "run_id",
        "task_id",
        "attempt_id",
        "level",
        "event_type",
        "message",
        "safe_payload",
        "created_at",
    },
    "artifacts": {
        "artifact_id",
        "user_id",
        "project_id",
        "run_id",
        "artifact_type",
        "latest_version_id",
        "created_at",
        "updated_at",
    },
    "artifact_versions": {
        "artifact_version_id",
        "artifact_id",
        "version_number",
        "storage_key",
        "content_type",
        "checksum",
        "size_bytes",
        "schema_version",
        "retention_policy",
        "source_artifact_ids",
        "created_at",
    },
    "configuration_snapshots": {
        "snapshot_id",
        "schema_version",
        "source_precedence",
        "resolved_values",
        "secret_refs",
        "created_by",
        "run_id",
        "created_at",
    },
    "quality_evaluations": {
        "evaluation_id",
        "artifact_id",
        "run_id",
        "status",
        "metrics",
        "warnings",
        "failures",
        "manual_review_required",
        "evidence_artifact_ids",
    },
    "usage_records": {
        "usage_id",
        "user_id",
        "project_id",
        "run_id",
        "task_id",
        "provider",
        "model_id",
        "operation",
        "tokens_in",
        "tokens_out",
        "cost_estimate",
        "provider_limit_event",
        "created_at",
    },
    "audit_events": {
        "audit_event_id",
        "actor_user_id",
        "actor_role",
        "event_type",
        "target_type",
        "target_id",
        "project_id",
        "safe_payload",
        "correlation_id",
        "created_at",
    },
}


def read_all_sql() -> str:
    return "\n".join((MIGRATIONS / name).read_text(encoding="utf-8") for name in MIGRATION_FILES)


def table_body(sql: str, table: str) -> str:
    pattern = re.compile(
        rf"create table if not exists public\.{re.escape(table)}\s*\((.*?)\n\);",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(sql)
    if not match:
        raise AssertionError(f"Missing table body for {table}")
    return match.group(1).lower()


def assert_migration_files() -> None:
    missing = [name for name in MIGRATION_FILES if not (MIGRATIONS / name).exists()]
    if missing:
        raise AssertionError(f"Missing migration files: {missing}")
    for name in MIGRATION_FILES:
        text = (MIGRATIONS / name).read_text(encoding="utf-8").strip().lower()
        if not text.startswith("begin;") or not text.endswith("commit;"):
            raise AssertionError(f"{name} must start with begin; and end with commit;")


def assert_enums(sql: str) -> None:
    for enum_name in EXPECTED_ENUMS:
        if f"create type public.{enum_name} as enum" not in sql.lower():
            raise AssertionError(f"Missing enum {enum_name}")


def assert_tables(sql: str) -> None:
    lower = sql.lower()
    for table in EXPECTED_TABLES:
        if f"create table if not exists public.{table}" not in lower:
            raise AssertionError(f"Missing table {table}")


def assert_rls(sql: str) -> None:
    lower = sql.lower()
    for table in EXPECTED_TABLES:
        if f"alter table public.{table} enable row level security" not in lower:
            raise AssertionError(f"{table} does not enable RLS")
        if f"alter table public.{table} force row level security" not in lower:
            raise AssertionError(f"{table} does not force RLS")


def assert_ownership_columns(sql: str) -> None:
    for table in PROJECT_OWNED_TABLES:
        body = table_body(sql, table)
        for column in ("user_id", "project_id"):
            if column not in body:
                raise AssertionError(f"{table} missing {column}")
    for table in USER_OWNED_TABLES:
        body = table_body(sql, table)
        if "user_id" not in body:
            raise AssertionError(f"{table} missing user_id")


def assert_contract_columns(sql: str) -> None:
    for table, columns in SHARED_CONTRACT_COLUMNS.items():
        body = table_body(sql, table)
        missing = [column for column in columns if column not in body]
        if missing:
            raise AssertionError(f"{table} missing shared contract columns: {missing}")


def assert_append_only(sql: str) -> None:
    lower = sql.lower()
    for table in APPEND_ONLY_TABLES:
        if f"{table} no client update" not in lower:
            raise AssertionError(f"{table} missing no-client-update RLS policy")
    if "create or replace function public.prevent_update()" not in lower:
        raise AssertionError("Missing prevent_update trigger function")


def assert_task_helpers(sql: str) -> None:
    lower = sql.lower()
    required = [
        "create or replace function public.claim_next_task",
        "for update skip locked",
        "lease_expires_at = now() + interval '120 seconds'",
        "create or replace function public.heartbeat_task",
        "create or replace function public.cancel_task",
        "worker_claimed_task",
    ]
    for marker in required:
        if marker not in lower:
            raise AssertionError(f"Missing task helper marker: {marker}")


def assert_security_markers(sql: str) -> None:
    lower = sql.lower()
    markers = [
        "size_bytes >= 0 and size_bytes <= 52428800",
        "unique (user_id, project_id, idempotency_key)",
        "unique (user_id, project_id, storage_key)",
        "generated always as identity",
        "page_text",
        "vision_ai",
        "auto_detect",
        "all_pages",
        "legacy_import_quarantine",
        "signed_url_created",
    ]
    for marker in markers:
        if marker not in lower:
            raise AssertionError(f"Missing security/schema marker: {marker}")


def verify() -> None:
    assert_migration_files()
    sql = read_all_sql()
    assert_enums(sql)
    assert_tables(sql)
    assert_rls(sql)
    assert_ownership_columns(sql)
    assert_contract_columns(sql)
    assert_append_only(sql)
    assert_task_helpers(sql)
    assert_security_markers(sql)


def main() -> int:
    verify()
    print("Plan 03 migrations verified statically")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
