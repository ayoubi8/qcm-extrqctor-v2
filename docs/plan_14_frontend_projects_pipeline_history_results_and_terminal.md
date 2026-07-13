# Plan 14 Frontend Projects, Pipeline, History, Results, And Terminal Notes

Status: implemented as a server-state-ready frontend workflow foundation.

Implemented:

- Typed frontend API client for project creation, upload init, task create/cancel, project snapshot reconciliation, terminal replay, artifact signed URLs, and download handoff.
- Project launcher and History restore components for create/restore workflows.
- Visible pipeline state definitions, step registry, step list, config panel wrapper, and local UI-only Zustand store.
- Step config surface wiring for Step 1, combined Step 2, future Step 3 correction, and future Step 4 similarity match.
- Result hub, run selector, artifact version viewer, and signed URL download handoff.
- Terminal replay hook using TanStack Query cursor polling fallback and a terminal panel that keeps local fallback events for offline preview.
- App shell now renders the Plan 14 workflow surface instead of the Plan 13 placeholder cards.
- Static visual workflow matrix and Plan 14 verifier covering project launcher, history restore, pipeline, results, artifacts, terminal replay, and offline preview states.

Deferred to later plans:

- Live generated OpenAPI client once the API schema is available from an installed FastAPI app.
- Browser screenshot/e2e runs once frontend dependencies are installed.
- Production server endpoints for `/projects/{project_id}/snapshot` beyond the typed frontend contract.
- Full file upload transfer to storage after upload initialization.

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
python -B -m unittest discover tests
```

Result: all commands passed locally after Plan 14 implementation. Vite/TypeScript browser build was not run because `apps/web/node_modules` is not installed in this workspace.

Next plan: Plan 15 Manual Auto Run.
