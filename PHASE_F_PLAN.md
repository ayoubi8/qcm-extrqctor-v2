# Phase F Implementation Plan — Manual Auto Run + AI Auto Run: Actually Running Child Tasks

## The Problem

### Manual Auto Run
When a user clicks "Start" in the Manual Auto Run panel, the flow is:

1. Frontend calls `POST /projects/{id}/manual-autoruns` → `ManualAutoRunService.start()` creates a `manual_autorun` task and a record (in-memory).
2. The worker dequeues the `manual_autorun` task and calls `manual_autorun_handler(payload)`.
3. The handler **only plans** the child steps — it builds a list of child task dicts and returns them in the result dict. **It never actually creates the child step tasks.**
4. The `manual_autorun` task completes with status "planned" and nothing else happens.

**Bottom line:** Manual Auto Run is a planning stub. It says "here's what I would run" and then stops. No Step 1/2/3/4 tasks are ever created or executed.

### AI Auto Run
When a user clicks "Launch" in the AI Auto Run window:

1. Frontend calls `POST /projects/{id}/ai-autoruns` → `AiAutoRunService.start()` creates an `ai_autorun` task.
2. The worker dequeues the `ai_autorun` task and calls `ai_autorun_handler(payload)`.
3. The handler calls `AiAutoRunService().plan(command)` which:
   - Builds a **deterministic rule-based** document map (keyword matching: "correction" → correction role, "question" → question role, else → context)
   - Generates a Step 2 + Step 3 config from the user constraints (just dict construction — no LLM call)
   - Writes evidence/config artifacts to an in-memory sink
   - Returns a result with artifact IDs and status
4. The task completes — but **no LLM was called**, **no Step 2/3 tasks are enqueued**, and the document map is just keyword matching, not AI analysis.

**Bottom line:** AI Auto Run is a deterministic stub. No planner/evaluator prompts are used, no LLM is called, and no downstream pipeline tasks are launched.

---

## What I Will Build

### F1. Manual Auto Run: actually enqueue child step tasks

**What:** When the `manual_autorun` handler runs, instead of just returning a plan, it should **create real child tasks** for each selected step (step1_extract, step2_orchestrate, etc.) via the `TaskService`, and the worker will then pick them up and execute them in order.

**How:** Rewrite `apps/worker/src/qcm_worker/autorun_handler.py`:
1. The handler receives the `manual_autorun` task payload (user_id, project_id, run_id, snapshot with selected steps).
2. **NEW:** Import `TaskService` and `TaskCreateCommand` into the handler. Build a `TaskService` instance (same Supabase-backed one the runner uses).
3. For each **enabled step** in the snapshot (in canonical order: step1 → step2 → step3 → step4):
   - Create a child task via `task_service.create_task(TaskCreateCommand(kind=step.task_kind, payload={...step config...}))`.
   - The child task gets inserted into the Supabase `tasks` table with status `queued`.
   - The worker's poll loop will claim and execute it on the next cycle (the `manual_autorun` task itself completes after enqueuing all children).
4. Include `source_file_id` from the manual autorun payload in each child task's payload so Step 1 knows which PDF to fetch.
5. Return the list of created child task IDs in the result.

**The key change:** The handler must have access to `TaskService` (or a task creator function). I'll pass it via the handler registration — the worker `main.py` already builds a `TaskService` with Supabase repos; I'll make the handler accept it as a closure variable.

**Why:** This transforms Manual Auto Run from "prints a plan and exits" to "creates N queued step tasks and exits" — the worker then processes them one by one, exactly as if the user had clicked each step's "Run" button manually.

**Idempotency:** If the `manual_autorun` task is retried (worker crashes mid-enqueue), the child tasks' idempotency keys prevent duplicates (each gets a key like `auto:{auto_run_id}:{step_key}`).

---

### F2. Worker runner: pass `TaskService` to handlers that need it

**What:** The current `WorkerRunner.run_once()` calls `handler(task.payload)` with just the payload dict. Some handlers (Manual Auto Run, AI Auto Run) need access to `TaskService` to create child tasks.

**How:** Two options — I'll go with the simplest:
- **Option A (chosen):** Make the handler a closure that captures `TaskService`. The `register_*_handler()` functions in `main.py` pre-inject the `TaskService` into the handler closure. This requires no change to `WorkerRunner` — it just calls `handler(payload)` as before.
- ~~Option B: Change `WorkerRunner.run_once()` to pass `task_service` as a second argument. Requires changing all handler signatures. More invasive.~~

**Implementation with Option A:**
- `register_manual_autorun_handler(task_service)` — takes the `TaskService`, builds a closure `handler(payload)` that calls the inner logic with `task_service` available to create child tasks.
- `register_ai_autorun_handler(task_service, openrouter_adapter)` — takes both, builds a closure.
- `main.py` calls `register_manual_autorun_handler(self.task_service)` instead of `register_manual_autorun_handler()`.

**Why:** Minimal change to the runner. The handler closure captures what it needs; the runner doesn't know or care.

---

### F3. Manual Auto Run child task payloads

**What:** Each child task needs a proper payload so the step handler can actually do its work.

**How:** For each selected step, build a payload based on the step type:
- **step1_extract**: `{user_id, project_id, run_id, source_file_id, source_filename, config: step.config}`
  - `source_file_id` comes from the manual autorun payload (the user's uploaded PDF)
- **step2_orchestrate**: `{user_id, project_id, run_id, step1_artifact_ids: [], pages: [], config: step.config}`
  - `step1_artifact_ids` starts empty (in a future phase, the child tasks would chain: when step1 completes, step2 could read step1's artifacts — but for now, each step runs independently with inline data or empty arrays)
- **step3_correction**: `{user_id, project_id, run_id, step2_artifact_ids: [], qcms: [], pages: [], config: step.config}`
- **step4_similarity_match**: `{user_id, project_id, run_id, source_artifact_ids: [], source_qcms: [], reference_qcms: [], existing_matches: [], config: step.config}`

**Why:** These is the same payload structure the step API routes already build when a user clicks "Run" on a single step. The handler just constructs them programmatically instead of receiving them from an HTTP request.

**Sequencing note:** In this phase, all child tasks are enqueued **simultaneously** (not sequentially). The worker processes them in queue order (priority desc, then creation asc), and since they all have priority 0 and are created in step order, the worker will process step1 before step2, etc. A future enhancement could make the autorun handler wait for each child to complete before enqueuing the next — but that requires a stateful orchestration loop in the worker, which is more complex. For now, "fire all at once in order" is the MVP behavior.

---

### F4. AI Auto Run: use OpenRouter for document map generation

**What:** Replace the deterministic `build_document_map()` (keyword matching) with a real LLM call to OpenRouter using the planner prompt.

**How:** Modify `ai_autorun_handler.py` and/or `AiAutoRunService.plan()`:
1. When `OPENROUTER_API_KEY` is available, build a planner prompt from the page texts:
   - "You are an AI document planner. Analyze the following pages from a QCM exam PDF. Classify each page as 'question', 'correction', or 'context'. Return JSON: `{\"pages\": [{\"page_number\": 1, \"role\": \"question\", \"confidence\": 0.9, \"summary\": \"Contains QCM questions about...\"}]}`"
2. Call `OpenRouterAdapter.complete_json()` with the prompt and `openai/gpt-4o-mini`.
3. Parse the JSON response into `AiDocumentMapPage` objects.
4. Fall back to the deterministic `build_document_map()` if the LLM call fails or returns invalid JSON.

**Why:** The whole point of "AI Auto Run" is that the LLM analyzes the document and decides the optimal configuration — not keyword matching. This makes the document map meaningful (the LLM can see "page 3 is an answer key" vs "page 5 is a case study").

**Safety gates (already in the domain layer):** `validate_ai_generated_config()` and `evaluate_ai_quality()` run on the LLM output. If the config is invalid or confidence is too low, the service returns `MANUAL_INTERVENTION_REQUIRED` or `SAFE_STOP` — these gates already work, they just haven't been tested with real LLM output.

---

### F5. AI Auto Run: use the planner/evaluator prompts

**What:** Load the planner and evaluator prompt templates from `prompts/ai_autorun/planner.v1.md` and `evaluator.v1.md` and inject the page data into them before calling OpenRouter.

**How:**
- Read the prompt files at worker startup (or on each call — they're tiny).
- The planner prompt tells the LLM to produce a document map + config JSON.
- The evaluator prompt tells the LLM to evaluate the quality of the generated plan.
- Build the full prompt by replacing a `{pages}` placeholder with the actual page texts.
- Call `complete_json()` and parse the response.

**Why:** The prompts already exist (`prompts/ai_autorun/planner.v1.md`, `evaluator.v1.md`) but are never loaded. Using them fulfills Plan 16's contract and makes the AI Auto Run actually "AI" — the LLM decides the document structure and generates the Step 2/3 configs.

---

### F6. AI Auto Run: enqueue downstream Step 2 task

**What:** After the AI Auto Run plan is evaluated, if the gate passes, enqueue a real `step2_orchestrate` task with the AI-generated config.

**How:** In `ai_autorun_handler`, after `AiAutoRunService.plan()` returns:
1. If `result.status` is `COMPLETED` or `COMPLETED_WITH_WARNINGS` (gate passed):
   - Create a `step2_orchestrate` child task via `task_service.create_task()` with:
     - `kind = "step2_orchestrate"`
     - `payload = {user_id, project_id, run_id, pages: [...], config: result.generated_configs.step2_config, model_selection: ...}`
2. If `result.status` is `MANUAL_INTERVENTION_REQUIRED` or `FAILED`:
   - Don't enqueue any child tasks; the AI Auto Run task just completes with the warning/error.
3. Return the child task IDs in the result.

**Why:** Today the AI Auto Run generates a config but never uses it. This wires the AI-generated config into a real Step 2 task that the worker will pick up and execute with the LLM QCM extractor (Phase E).

---

## Files I Will Create/Modify

| File | Action | Purpose |
|---|---|---|
| `apps/worker/.../autorun_handler.py` | **Modify** | Enqueue real child step tasks via TaskService |
| `apps/worker/.../ai_autorun_handler.py` | **Modify** | LLM planner call + enqueue Step 2 task with AI config |
| `apps/worker/.../main.py` | **Modify** | Pass TaskService + OpenRouter adapter to handler registrations |
| `packages/application/.../ai_autorun_service.py` | **Modify** | Add LLM-backed `plan_with_llm()` method (with deterministic fallback) |
| `packages/infrastructure/.../llm/llm_ai_planner.py` | **New** | LLM-based document map planner (loads prompt, calls OpenRouter, parses response) |

---

## Data Flow (After Phase F)

### Manual Auto Run
```
User selects steps [step1, step2] + clicks "Start"
  ↓
API: ManualAutoRunService.start() → creates manual_autorun task
  ↓
Worker claims manual_autorun task
  ↓
Handler: for each enabled step:
  → task_service.create_task(kind="step1_extract", payload={source_file_id, config})
  → task_service.create_task(kind="step2_orchestrate", payload={pages, config})
  ↓
manual_autorun task completes ("enqueued 2 child tasks")
  ↓
Worker claims step1_extract task → runs Step 1 (pypdf + vision OCR) → completes
Worker claims step2_orchestrate task → runs Step 2 (LLM QCM extraction) → completes
  ↓
User sees Step 1 + Step 2 tasks appear in snapshot → both move to "completed"
```

### AI Auto Run
```
User provides pages + model + constraints → clicks "Launch"
  ↓
API: AiAutoRunService.start() → creates ai_autorun task
  ↓
Worker claims ai_autorun task
  ↓
Handler:
  1. Loads planner prompt from prompts/ai_autorun/planner.v1.md
  2. Calls OpenRouter with page texts → LLM returns document map + config JSON
  3. Evaluates quality (validate_ai_generated_config + evaluate_ai_quality)
  4. If gate passed → creates step2_orchestrate child task with AI-generated config
  5. Completes ai_autorun task
  ↓
Worker claims step2_orchestrate task → runs Step 2 with AI optimized config → completes
  ↓
User sees AI Auto Run + Step 2 tasks appear in snapshot
```

---

## What Will NOT Be Fixed in Phase F

- **Sequential execution with dependency chaining** — all child tasks are enqueued at once; Step 2 doesn't wait for Step 1 to complete before starting. Sequential orchestration (wait for each child, check result, then enqueue next) requires a stateful loop in the worker that monitors child task status — this is more complex and deferred. The MVP behavior "fire all at once in order" works because the worker processes in queue order.
- **Auto Run record persistence** — `ManualAutoRunRecord` and `AiAutoRunRecord` still live in in-memory repositories. Persisting them to Postgres (`auto_runs` / `ai_auto_runs` tables) is deferred.
- **Manual Auto Run control (pause/resume/retry)** — the control endpoint updates the in-memory record's status, but since the child tasks are already enqueued in Supabase, "pausing" doesn't stop them. True pause/resume would need to cancel pending child tasks in the queue. Deferred.
- **AI Auto Run evaluator prompt** — the evaluator prompt exists but implementing the full evaluator loop (evaluate → retry → finalize) is deferred. For now, the planner runs and the gate validates statically; the evaluator is a no-op.

---

## Verification Plan

1. **Manual Auto Run E2E on VPS:**
   - Register → promote → create project → upload PDF
   - Start Manual Auto Run with steps [step1, step2]
   - Poll snapshot → verify: manual_autorun task completes, then step1_extract task appears + completes, then step2_orchestrate task appears + completes
2. **AI Auto Run E2E on VPS:**
   - Register → promote → create project → upload PDF → run Step 1 (get page text)
   - Start AI Auto Run with page texts → poll → verify: ai_autorun task completes, step2 task appears with AI-generated config + completes
3. **Local tests stay green** (handlers fall back to fakes when no env/adapter)

---

## Deployment (After Implementation)

```bash
cd /opt/qcm-extractor-api/current
sudo git -c safe.directory=/opt/qcm-extractor-api/current pull origin main
sudo systemctl restart qcm-extractor-worker
```

No new pip packages. No new env vars. No Supabase changes. Just pull + restart worker.