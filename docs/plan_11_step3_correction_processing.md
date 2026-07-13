# Plan 11 Future Step 3 Correction Processing Notes

Status: implemented as a deterministic future Step 3 correction foundation adapted from legacy Step 6.

Implemented:

- Domain correction rules for canonical modes `page_detection`, `vision`, and `auto_detection`.
- Frozen legacy mode adapter: `page_text` to `page_detection`, `vision_ai` to `vision`, and `auto_detect`/`all_pages` to `auto_detection`.
- Correction page scorer with default threshold 15, neighbor inclusion policy, and the more-than-4 correction-pattern suggestion rule.
- Shared Step 3 correction command/config/page/suggestion/quality/result contracts.
- Application correction service that suggests pages, extracts A-E correction maps, applies corrections with force-overwrite policy, writes raw/map/corrected JSON/corrected XLSX/quality artifacts, emits terminal events, and marks review-needed states.
- Mode behavior for page detection, auto detection, and deterministic vision detections/fallback.
- Worker handler for `step3_correction`.
- API route factory for `POST /projects/{project_id}/steps/step3-correction/run`.
- Frontend Step 3 correction API/types/config panel foundation.
- Prompt registry entries for page detection, vision, and auto detection correction prompts.
- Plan 11 verifier and unit tests for legacy mapping, suggestions, editable pages, overwrite behavior, vision detections, artifacts, quality, and worker status mapping.

Deferred to later plans:

- Live provider-backed vision/PDF rendering and marked-page confidence scoring.
- Production XLSX generation with workbook styling.
- Full Results/History UI rendering for correction versions and manual review items.
- AI Auto Run serialization and generated correction config integration.

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
python -B -m unittest discover tests
```

Result: all commands passed locally after Plan 11 implementation.

Next plan: Plan 12 Step 8 Compatibility.
