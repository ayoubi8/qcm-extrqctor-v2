# Plan 09 Combined Step 2 QCM Page Processing Notes

Status: implemented as a deterministic page-by-page QCM extraction cycle inside the visible Step 2 orchestrator.

Implemented:

- QCM domain helpers for stable `{page}_{number}_{position}` UIDs, proposition normalization, completeness checks, duplicate keys, and deterministic merges.
- Frozen Step 2 page-task input/output contracts with previous/current/next page context, prompt id, schema version, split repair report, and page quality metrics.
- Internal page cycle service that builds first/middle/last page context windows, parses local QCM candidates, captures orphan propositions, reconstructs split QCMs across page boundaries, deduplicates by source page and number, and reports warnings.
- Combined Step 2 orchestrator integration so the `step2_qcm_pages` internal cycle now writes page checkpoint artifacts from page-task outputs.
- Worker/frontend contract fields for internal page concurrency and extraction prompt id while keeping batch controls out of the visible product flow.
- Prompt registry entry for `step2.page_qcm_extraction.v1`.
- Plan 09 verifier and unit tests for context windows, parser behavior, split reconstruction, duplicate prevention, artifacts, and worker/orchestrator compatibility.

Deferred to later plans:

- Live provider-backed semantic extraction and model fallback attempts for each page.
- Golden fixture expansion with real PDFs and OCR outputs.
- Provider-limit-aware concurrent worker scheduling beyond the frozen page input contract.
- Deep metadata and Cas Clinique processing, which remains Plan 10.

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
python -B -m unittest discover tests
```

Result: all commands passed locally after Plan 09 implementation.

Next plan: Plan 10 Combined Step 2 Metadata, Cas Clinique, And Structuring.
