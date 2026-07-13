# Plan 05 Backend Domain, API, And Provider Foundation Notes

Status: implemented as backend contracts, use-case boundaries, provider adapters, and verification.

Implemented:

- Stable domain error codes and API-safe error normalization.
- API DTO contracts for project creation, step task creation, config resolution, pagination, model lists, and config snapshots.
- Provider contracts for OpenRouter-only model selection, fallback attempts, structured JSON calls, usage/cost metadata, authorization, and prompt specs.
- Repository ports for projects, tasks, configuration snapshots, model preferences, provider attempts, usage, and audit.
- Config snapshot drafting with approved precedence and raw-secret rejection.
- Provider registry and model fallback service with unauthorized-model skipping, retryable provider failure handling, attempt records, usage tokens, and fallback tracking.
- OpenRouter-compatible adapter boundary with JSON extraction and safe provider error normalization.
- Supabase repository adapter shells for later persistence wiring.
- API route factories for projects and config/model endpoints plus API error helper.
- Plan 05 verifier and unit tests for error shape, config precedence, fallback simulation, unauthorized model rejection, and OpenRouter adapter parsing.

Deferred to later plans:

- Live provider calls and SDK installation.
- Persisting repository adapters against Supabase.
- Durable task lifecycle implementation, worker claiming, retries, and terminal streaming.
- Real OpenAPI client generation for the frontend.
- Feature-specific Step 1/2/3/4 execution.

Verification:

```powershell
python -B tools/verify_foundation.py
python -B tools/verify_migrations.py
python -B tools/verify_storage.py
python -B tools/verify_backend.py
python -B -m unittest discover tests
```

Result: all commands passed.

Next plan: Plan 06 Persistent Tasks, Workers, And Terminal Events.
