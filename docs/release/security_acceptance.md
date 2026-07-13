# Security Acceptance

Required before production:

- two-user denial suite passes for projects, runs, tasks, terminal events, artifacts, configs, reference DBs, Manual Auto Run, and AI Auto Run.
- signed URLs are issued only after owner/admin authorization.
- private storage paths begin with owner id.
- no raw AI reasoning is persisted or displayed.
- service-role credentials are server-only.
- logs redact secret-like fields.

Live staging gates:

- Supabase RLS policy test.
- Supabase Storage policy test.
- Realtime channel authorization test.
