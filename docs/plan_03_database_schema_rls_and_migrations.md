# Plan 03 Database Schema, RLS, And Migrations Notes

Status: implemented as migration files and static verification.

Implemented:

- `0001_profiles_projects.sql`: auth profile mirror, admin approval status, user/model preferences, projects, timestamp helper, admin helper, owner/admin RLS.
- `0002_runs_tasks_artifacts.sql`: source files, documents, pages, runs, step/cycle runs, configuration snapshots, tasks, attempts, terminal events, artifacts, versions, quality evaluations, LLM/provider usage, audit events, indexes, append-only protections, task claim/heartbeat/cancel helpers.
- `0003_step_specific.sql`: Manual Auto Run, AI Auto Run, document maps, private reference DBs, Step 3 legacy mode mapping, audit event enum, legacy import batches.
- `0004_legacy_import_validation.sql`: legacy import staging, quarantine, validation function, quarantine report, RLS.
- Static migration verifier for required enums, tables, RLS/force RLS, ownership columns, shared contract columns, append-only policy markers, task helper markers, file-size cap, idempotency, storage-key uniqueness, terminal cursor, and Step 3 mode mapping.

Deferred to later plans:

- Live Supabase execution and database-specific integration testing.
- Repository implementations and API data access.
- Storage bucket policies and signed URL issuing APIs.
- Full two-user denial suite against a real database.

Verification:

```powershell
python -B tools/verify_foundation.py
python -B tools/verify_migrations.py
python -B -m unittest discover tests
```

Result: all commands passed.

Next plan: Plan 04 Storage, Artifacts, File-Size Limits, And Cleanup.
