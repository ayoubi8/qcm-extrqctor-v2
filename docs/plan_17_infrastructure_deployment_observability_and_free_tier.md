# Plan 17 Infrastructure, Deployment, Observability, And Free Tier Notes

Status: implemented as deployment and operations scaffolding.

Implemented:

- Provider deployment manifests for Vercel frontend/short API, Supabase DB/Auth/private Storage/Realtime, and Hugging Face Spaces workers.
- Environment schema and expanded `.env.example` for deploy target, worker id, log level, Sentry, source size cap, Supabase, and OpenRouter secrets.
- Observability package with readiness reports, structured log redaction, and free-tier budget gates.
- API health/readiness/metrics route factory and worker readiness helper.
- GitHub Actions verification workflow.
- Operations runbooks for provider limits, deployment, backup/restore, incident response, and free-tier operations.
- Plan 17 verifier and unit tests for budgets, redaction, readiness, manifests, env schema, provider-limit source links, and runbook coverage.

Provider limit snapshot:

- Vercel Functions limits reviewed from official docs on 2026-07-13.
- Supabase pricing/free quotas reviewed from official pricing page on 2026-07-13.
- Hugging Face Spaces free CPU/sleep behavior reviewed from official docs on 2026-07-13.
- Snapshot is documented in `docs/runbooks/provider_limits_snapshot.md` and must be rechecked before production launch.

Deferred to later plans:

- Live provider project creation and secret injection.
- Actual Vercel/Supabase/HF deployment execution.
- Sentry SDK integration after dependency installation.
- Production backup/PITR enablement after plan selection.

Verification:

```powershell
python -B tools/verify_foundation.py
python -B tools/verify_migrations.py
python -B tools/verify_storage.py
python -B tools/verify_backend.py
python -B tools/verify_tasks.py
python -B tools/verify_step1.py
python -B tools/verify_step2.py
python -B tools/verify_step2_pages.py
python -B tools/verify_step2_metadata.py
python -B tools/verify_step3_correction.py
python -B tools/verify_step4_similarity.py
python -B tools/verify_frontend_shell.py
python -B tools/verify_frontend_workflow.py
python -B tools/verify_manual_autorun.py
python -B tools/verify_ai_autorun.py
python -B tools/verify_infrastructure.py
python -B -m unittest discover tests
```

Result: all commands passed locally after Plan 17 implementation. Vite/TypeScript browser build was not run because `apps/web/node_modules` is not installed in this workspace.

Next plan: Plan 18 Testing, Security, Migration, And Release.
