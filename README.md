# QCM Extractor Re-Engineered

This directory contains the clean implementation workspace for the re-engineered QCM system.

Plan 01 created the repository foundation. Plan 02 added auth and tenancy contracts.
Plan 03 added concrete database migration files. Plan 04 added storage/artifact foundations.
Plan 05 added backend/API/provider foundations. Plan 06 added durable tasks and terminal foundations.
Plan 07 added Step 1 ingestion, extraction, OCR routing, text repair, artifacts, and quality summaries.
Plan 08 added the combined visible Step 2 orchestrator.
Plan 09 added page-by-page QCM processing inside combined Step 2.
Plan 10 added metadata, Cas Clinique, template validation, and finalization internals.
Plan 11 added future Step 3 correction processing.
Plan 12 added future Step 4 similarity match compatibility.
Plan 13 added the frontend design system and application shell.
Plan 14 added frontend projects, pipeline, history, results, and terminal workflow foundations.
Plan 15 added Manual Auto Run foundations.
Plan 16 added AI Auto Run foundations.
Plan 17 added infrastructure, deployment, observability, and free-tier operations foundations.
Plan 18 added testing, security, migration, and release gate foundations.

- Layered Python packages for domain, application, infrastructure, and shared contracts.
- App entry points for API, worker, and web.
- Versioned prompt and artifact schema directories.
- Tests and verification scripts for structure, contracts, and import boundaries.
- Provider-free auth context, approval status, owner guards, Supabase auth adapter boundary, and frontend auth gate.
- Supabase/Postgres migrations for profiles, projects, runs, tasks, terminal events, artifacts, usage, audit, automation, reference DBs, and legacy import quarantine.
- Private storage key rules, file-size validation, artifact registry coverage, signed URL ownership flow, retention cleanup helpers, and storage adapter boundaries.
- Domain errors, API contracts, repository ports, config snapshots, provider registry/fallback, OpenRouter adapter boundary, and project/config route factories.
- Task state machine, idempotent queue service, worker runner, retry/lease/heartbeat/cancel behavior, and cursor-based terminal replay.
- Step 1 page-level direct/OCR/mixed detection, deterministic adapter boundaries, worker/API/frontend contracts, artifact write requests, and quality reports.
- Unified Step 2 task orchestration across internal QCM page, metadata, format, and finalize cycles with artifact, quality, worker, API, and frontend contracts.
- Frozen Step 2 page task inputs, previous/current/next context windows, QCM UID normalization, split repair, duplicate prevention, page checkpoint artifacts, and page quality metrics.
- Metadata provenance, multi-page Cas Clinique grouping, legacy subcategory compatibility, template validation, final JSON/XLSX payload builders, and advanced Step 2 metadata contracts.
- Canonical correction modes, legacy Step 6 mode mapping, candidate-page scoring, page/auto/vision correction services, corrected JSON/XLSX artifact contracts, and Step 3 correction API/worker/frontend foundations.
- Legacy-compatible Step 8 similarity defaults, user-private reference DB ownership, text/full/weighted matching wrapper, export-existing artifacts, and Step 4 API/worker/frontend foundations.
- Dark QCM Extractor design tokens, CSS variables, reusable UI primitives, auth/app/project shell components, responsive sidebar/topbar layout, accessibility hooks, and a visual regression matrix.
- Typed frontend API client, project launcher, History restore, visible pipeline, step config wrapper, run selector, result hub, artifact viewer, signed URL handoff, and terminal replay hook.
- Manual Auto Run snapshot contracts, validation, idempotent start/control service, workflow handler, API route, frontend side panel, and green started notification.
- AI Auto Run document-map/config/evidence contracts, model authorization checks, safety gates, workflow handler, API route, floating window, and planner/evaluator prompts.
- Vercel/Supabase/Hugging Face deployment manifests, environment schema, health/readiness/metrics routes, structured logging, budget gates, CI, and operations runbooks.
- Synthetic fixture policy, release gate config, security matrix, legacy import validator, e2e/visual plans, rollout/rollback docs, and final acceptance report scaffold.

No legacy production code is modified by this rebuild. Existing project files outside this directory are references only.

## Layout

```text
apps/
  api/        lightweight authenticated API boundary
  worker/     durable task executor boundary
  web/        React/Vite application shell
packages/
  domain/     provider-free entities and value objects
  application/use cases, ports, orchestration contracts
  infrastructure/db, storage, OCR, LLM, and provider adapters
  shared/     API DTOs, enums, config defaults, registries
prompts/      versioned prompt templates and registry notes
artifact-schemas/
  v1/         JSON schema contracts for persisted artifacts
migrations/   future Supabase/Postgres migrations
tests/        foundation, contract, and boundary tests
tools/        local verification helpers
```

## Local Verification

The current foundation and auth-tenancy pass is verifiable without installing network dependencies:

```powershell
python tools/verify_foundation.py
python tools/verify_migrations.py
python tools/verify_storage.py
python tools/verify_backend.py
python tools/verify_tasks.py
python tools/verify_step1.py
python tools/verify_step2.py
python tools/verify_step2_pages.py
python tools/verify_step2_metadata.py
python tools/verify_step3_correction.py
python tools/verify_step4_similarity.py
python tools/verify_frontend_shell.py
python tools/verify_frontend_workflow.py
python tools/verify_manual_autorun.py
python tools/verify_ai_autorun.py
python tools/verify_infrastructure.py
python tools/verify_release.py
python -m unittest discover tests
```

Future plans will install and exercise FastAPI, Pydantic, pytest, Vitest, Playwright, and Supabase-specific tooling.
