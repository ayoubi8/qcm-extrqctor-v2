# Plan 18 Testing, Security, Migration, And Release Notes

Status: implemented as final release-gate scaffolding.

Implemented:

- Synthetic/public golden fixture manifest and explicit private fixture policy.
- Security matrix for two-user denial, signed URL owner checks, reference DB privacy, task ownership, terminal replay, storage paths, AI no-raw-reasoning, and secret redaction.
- E2E and visual regression plan manifests for Playwright/browser execution once Node dependencies are installed.
- Legacy import validator for owner assignment, checksum enforcement, unsupported artifact quarantine, absolute private path quarantine, timestamp preservation warnings, and subcategory preservation warnings.
- Release gate configuration aggregating all implemented verifier commands and manual staging gates.
- Release docs for security acceptance, migration acceptance, staged rollout, rollback, and final acceptance.
- CI workflow now includes the release gate verifier.
- Plan 18 verifier and unit tests for release config, migration validation, fixture policy, security gates, and acceptance docs.

Deferred beyond this local implementation:

- Live Supabase RLS/storage tests against a staging project.
- Browser e2e/visual execution after `apps/web/node_modules` is installed.
- Private fixture approval and secure handling if real PDFs are used.
- Staging backup/restore drill and final production go/no-go.

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
python -B tools/verify_release.py
python -B -m unittest discover tests
```

Result: all commands passed locally after Plan 18 implementation. Vite/TypeScript browser build was not run because `apps/web/node_modules` is not installed in this workspace.

Next step: release readiness review and optional live staging validation.
