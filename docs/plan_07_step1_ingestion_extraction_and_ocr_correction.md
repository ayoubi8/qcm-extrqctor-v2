# Plan 07 Step 1 Ingestion, Extraction, And OCR Correction Notes

Status: implemented as a dependency-light Step 1 foundation with deterministic local verification.

Implemented:

- Step 1 domain rules for meaningful character counting, the `> 200` direct-text threshold, automatic direct/OCR/mixed detection, and manual override validation.
- Shared Step 1 command, config, detection, quality, page result, and final result contracts.
- PDF/OCR/text-repair adapter ports plus deterministic fake adapters for tests and worker verification.
- Application Step 1 service that validates the 50 MB source cap, extracts page text, routes OCR pages, runs internal text repair, emits terminal events, writes page/final/report artifact requests, and returns quality summaries.
- Worker handler for `step1_extract` tasks using the existing Plan 06 task registry shape.
- API route factory for `POST /projects/{project_id}/step1/run` that queues a durable Step 1 task.
- Frontend Step 1 config/API contract foundation for automatic/direct/OCR/mixed modes and text repair.
- Plan 07 verifier and unit tests for threshold detection, mixed PDFs, manual overrides, artifact writes, size caps, and worker handler behavior.

Deferred to later plans:

- Real pypdf extraction, PDF rendering, and OCR engine implementations.
- Live provider-backed Step 1.5 text repair, model usage accounting, and fallback telemetry.
- Database-backed Step 1 run/page persistence beyond existing migration contracts.
- Full Results/History UI rendering for Step 1 artifacts.
- Golden fixture corpus expansion and live runtime budget measurements.

Verification:

```powershell
python -B tools/verify_foundation.py
python -B tools/verify_migrations.py
python -B tools/verify_storage.py
python -B tools/verify_backend.py
python -B tools/verify_tasks.py
python -B tools/verify_step1.py
python -B -m unittest discover tests
```

Result: all commands passed locally after Plan 07 implementation.

Next plan: Plan 08 Combined Step 2 Orchestrator And Per-Page QCM Extraction.
