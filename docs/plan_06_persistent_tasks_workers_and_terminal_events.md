# Plan 06 Persistent Tasks, Workers, And Terminal Events Notes

Status: implemented as durable task, worker, and terminal contracts/services with local verification.

Implemented:

- Task state machine with valid transitions, terminal states, queue states, retry backoff, lease expiry helpers, and terminal level normalization.
- Shared DTOs for task creation, claim, heartbeat, cancel, completion, failure, terminal event creation, and terminal cursor pages.
- Application `TaskService` for idempotent task creation, claiming, heartbeat, cancellation, completion, retry/failure, and terminal replay.
- In-memory task/terminal repositories mirroring database semantics for local tests: idempotency, priority claim order, attempts, leases, and cursor replay.
- Worker runner that claims a task, heartbeats, executes registered handlers, completes successful work, and records retryable/non-retryable failures.
- API route factories for `POST /tasks`, `POST /tasks/{id}/cancel`, and `GET /projects/{id}/terminal`.
- Frontend terminal DTO/API/component foundation for cursor-based replay.
- Plan 06 verifier and tests for invalid transitions, idempotency, priority, retry, cancel safety, terminal replay, and worker execution.

Deferred to later plans:

- Live Postgres queue execution through `claim_next_task`.
- Supabase Realtime subscription wiring.
- Full frontend replacement of the old ephemeral terminal panel.
- Step-specific worker handlers and checkpointed artifact writes.
- HF/Vercel deployment runtime tuning.

Verification:

```powershell
python -B tools/verify_foundation.py
python -B tools/verify_migrations.py
python -B tools/verify_storage.py
python -B tools/verify_backend.py
python -B tools/verify_tasks.py
python -B -m unittest discover tests
```

Result: all commands passed.

Next plan: Plan 07 Step 1 Ingestion, Extraction, And OCR Correction.
