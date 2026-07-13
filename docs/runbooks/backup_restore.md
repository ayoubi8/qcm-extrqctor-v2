# Backup And Restore Runbook

Backup scope:

- Supabase Postgres data.
- private storage bucket objects.
- prompt registry.
- migrations and deployment config.

Minimum drill:

1. Export database schema and data from staging.
2. Export object manifest for `qcm-artifacts-private`.
3. Restore into a fresh staging Supabase project.
4. Re-apply RLS and storage policies.
5. Verify one restored project, run, artifact, and terminal timeline.

Production note:

- Enable PITR when the selected Supabase plan supports it.
- Treat all exported files as private user data.
