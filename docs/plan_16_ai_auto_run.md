# Plan 16 AI Auto Run Notes

Status: implemented as a deterministic AI Auto Run foundation.

Implemented:

- Domain validators for AI document maps, page evidence summaries, generated config validation, quality gates, and raw-reasoning redaction enforcement.
- Shared AI Auto Run contracts for start/action commands, generated configs, results, records, statuses, and the `ai_autorun` task kind.
- Application service that validates authorized models, builds deterministic document maps, generates Step 2 and future Step 3 config JSON, writes AI Auto Run document-map/config/evidence artifacts, supports idempotent start, and owner-scoped actions.
- Worker handler for `ai_autorun` planner/evaluator execution.
- API route factory for AI Auto Run start/retry/cancel/continue actions.
- Floating frontend AI Auto Run window with model/config controls, minimized state, launch/retry/cancel actions, and explicit evidence-only messaging.
- Versioned AI Auto Run planner/evaluator prompt specs and prompt registry entries.
- Plan 16 verifier and unit tests for safe summaries, manual intervention gates, artifact writes, unauthorized model blocking, owner-scoped actions, worker status mapping, prompts, and UI hooks.

Deferred to later plans:

- Live OpenRouter provider calls and persisted prompt/response storage with admin-only access.
- Production task orchestration that launches downstream Step 1/2/3 tasks from AI-generated configs.
- Browser/e2e validation once frontend dependencies are installed.
- Usage/cost persistence beyond provider contract boundaries.

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
python -B -m unittest discover tests
```

Result: all commands passed locally after Plan 16 implementation. Vite/TypeScript browser build was not run because `apps/web/node_modules` is not installed in this workspace.

Next plan: Plan 17 Infrastructure, Deployment, Observability, And Free Tier.
