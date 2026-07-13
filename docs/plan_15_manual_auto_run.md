# Plan 15 Manual Auto Run Notes

Status: implemented as a deterministic Manual Auto Run foundation.

Implemented:

- Shared Manual Auto Run contracts for snapshots, step configs, validation, records, control actions, and workflow task kind.
- Application service for canonical visible-step validation, idempotent start, owner-scoped control, and workflow task creation.
- Worker handler for `manual_autorun` that validates snapshots and plans sequential child step task payloads.
- API route factory for validate/start/pause/resume/retry/cancel Manual Auto Run endpoints.
- Frontend side panel, local UI-only Auto Run store, typed API helpers, control actions, and green started notification.
- Pipeline integration with an Auto Run button and notification surface.
- Plan 15 verifier and unit tests for validation, Step 6 legacy mapping rejection, idempotent start, owner-scoped control, and worker sequential planning.

Deferred to later plans:

- Durable child task enqueue/execution orchestration against a production task repository.
- Live persisted default import from localStorage/YAML suggestion sources.
- Browser/e2e validation once frontend dependencies are installed.
- Final report artifact generation after real child task completion.

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
python -B -m unittest discover tests
```

Result: all commands passed locally after Plan 15 implementation. Vite/TypeScript browser build was not run because `apps/web/node_modules` is not installed in this workspace.

Next plan: Plan 16 AI Auto Run.
