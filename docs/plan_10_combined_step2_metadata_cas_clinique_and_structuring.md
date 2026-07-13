# Plan 10 Combined Step 2 Metadata, Cas Clinique, And Structuring Notes

Status: implemented as deterministic metadata, template, and finalization internals inside the visible Step 2 orchestrator.

Implemented:

- Domain template rules for the default final QCM schema and required-field validation.
- Shared contracts for metadata provenance, clinical groups, template validation, formatted rows, and final JSON/XLSX payloads.
- Internal metadata service that applies manual/default metadata, records provenance, preserves legacy subcategory compatibility, detects Cas Clinique labels, and carries clinical groups across pages.
- Internal format service that validates the active template and maps enriched QCM records into final row shape.
- Internal finalize service that builds final JSON and deterministic XLSX-compatible byte payloads.
- Combined Step 2 orchestrator integration for old Step 3 metadata, old Step 4 format, and old Step 5 finalization cycles.
- Advanced Step 2 metadata frontend contract/component foundation.
- Prompt registry entry for `step2.metadata_cas_clinique.v1`.
- Plan 10 verifier and unit tests for provenance, multi-page clinical cases, legacy subcategory policy, template validation, final JSON/XLSX, and orchestrator compatibility.

Deferred to later plans:

- Live provider-backed metadata extraction and confidence scoring.
- Production XLSX workbook generation with styling.
- Persisted template library and user-uploaded template import.
- Full Results/History UI rendering for metadata provenance and clinical groups.

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
python -B -m unittest discover tests
```

Result: all commands passed locally after Plan 10 implementation.

Next plan: Plan 11 Step 6 Correction Processing.
