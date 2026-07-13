# Migrations

Plan 03 adds the initial Supabase/Postgres migration set.

Migrations are applied in dependency order:

1. `0001_profiles_projects.sql`
2. `0002_runs_tasks_artifacts.sql`
3. `0003_step_specific.sql`
4. `0004_legacy_import_validation.sql`

The SQL is designed for Supabase/Postgres and keeps multi-user ownership explicit from the first
table. Every application table enables and forces RLS, private storage authorization remains DB
metadata-driven, and legacy imports quarantine unsafe records rather than dropping data.
