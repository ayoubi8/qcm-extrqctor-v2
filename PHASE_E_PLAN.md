# Phase E Implementation Plan — Real OpenRouter LLM Calls + Real PDF Text Extraction

## The Problem (What's Broken Today)

The worker **does** dequeue and complete tasks (Phase D verified that). But every handler uses **fake adapters** that return deterministic test data — not real results from your actual PDF or an actual LLM:

| Component | Today | What It Should Do |
|---|---|---|
| `FakePdfTextExtractor` | Returns canned text from a `dict[int, str]` you pass in the payload | Read a real uploaded PDF and extract text page-by-page |
| `FakeOcrEngine` | Returns `"OCR text for page N"` | Run actual OCR on scanned pages (tesseract or LLM-based) |
| `IdentityTextQualityFixer` | Just `.strip()`s the text | Send the text to OpenRouter for LLM-based repair |
| `OpenRouterAdapter.complete_json` | Raises `PROVIDER_FAILURE` if no HTTP client injected (which it never is) | Make a real `POST` to `https://openrouter.ai/api/v1/chat/completions` with `OPENROUTER_API_KEY` |
| Step 2 orchestrator | Hard-codes `"configured-by-admin"` as the model id | Uses the real `ModelSelection` from the task config |
| Step 2 page extraction | Has no LLM call at all — it regex-parses the inline page text | Calls OpenRouter with the QCM extraction prompt, parses the JSON response |
| Step 1 handler | Expects `direct_pages` / `pages` / `source_content` inline in the task payload | Should fetch the uploaded source PDF from Supabase Storage using `source_file_id` |

**Bottom line:** the pipeline "completes" but produces meaningless output. No real PDF is read, no LLM is called, and no real QCM data is extracted.

---

## What Your VPS Already Has

- `httpx` installed (used by PostgREST + Storage adapters)
- `OPENROUTER_API_KEY` is referenced in `.env.example` but **not in `/etc/qcm-extractor-api.env`** — you need to add it
- The `qcm-artifacts-private` Supabase Storage bucket has the uploaded PDFs (Phase C stores them at `users/{uid}/projects/{pid}/project/artifacts/source_pdf/{aid}/v0001/{filename}`)
- The `source_files` table has the `storage_key` for each upload
- `OPENROUTER_API_KEY` needs to be added to the VPS env file

---

## What I Will Build (Step by Step)

### E1. Real PDF text extractor (`pypdf`)

**What:** A new `PypdfTextExtractor` that reads a PDF's bytes and extracts text from each page.

**How:** New file `packages/infrastructure/src/qcm_infrastructure/pdf/pypdf_extractor.py`:
- Uses `pypdf.PdfReader` to open the PDF from `source_content: bytes` (in-memory, no temp file)
- Iterates `reader.pages`, calls `page.extract_text()` on each
- Returns `tuple[PdfPageText(page_number=i+1, text=...), ...]`
- Honors `page_range` (start, end) — only extracts pages in that range
- Handles empty/encrypted PDFs gracefully (returns empty tuple → Step 1 raises "No pages were available")

**Why:** `pypdf` is pure-Python, lightweight (~1 MB), has no native deps (unlike pymupdf), and is already referenced in the plans as the Step 1 extractor. It works on Ubuntu without any system packages. Install via `pip install pypdf`.

**VPS requirement:** `pip install pypdf` (no apt packages needed).

---

### E2. OpenRouter adapter wired with a real httpx client

**What:** Make `OpenRouterAdapter.complete_json` actually call OpenRouter instead of raising `PROVIDER_FAILURE`.

**How:** The adapter already has the full request/response logic (`openrouter_adapter.py:31-78`). It just needs an `httpx.Client` injected. I'll:
- Change `OpenRouterSettings.api_key_ref` to `api_key` (the actual key, not a ref)
- In the worker's `build_step1_service` / `step2_orchestrator_handler`, construct an `httpx.Client` with the `OPENROUTER_API_KEY` from env, create an `OpenRouterAdapter(settings, http_client=client)`, register it in a `ProviderRegistry`, and pass the registry to services that need LLM calls
- Add the `Authorization: Bearer {api_key}` header and `HTTP-Referer` / `X-Title` headers (OpenRouter requires these for free-tier identification)

**Why:** The adapter code is already correct — it just never gets a client. This is the smallest change that makes LLM calls work. The `OPENROUTER_API_KEY` goes in the env file (server-side only, never exposed to the frontend).

**VPS requirement:** Add `OPENROUTER_API_KEY=sk-or-v1-...` to `/etc/qcm-extractor-api.env`.

---

### E3. Real text repair via OpenRouter (replaces `IdentityTextQualityFixer`)

**What:** A new `OpenRouterTextFixer` that sends page text to the LLM for OCR-error repair.

**How:** New file `packages/infrastructure/src/qcm_infrastructure/pdf/openrouter_text_fixer.py`:
- Implements the `TextQualityFixer` Protocol (`repair(text, page_number, model_id) -> TextRepairResult`)
- Builds a prompt: "You are an OCR repair assistant. Fix common OCR errors in the following text while preserving the original meaning. Return only the repaired text, no explanation."
- Calls `OpenRouterAdapter.complete_json` (or a simpler text completion method)
- Returns `TextRepairResult(text=repaired, changed=original != repaired, provider="openrouter", model_id=model_id)`
- If `text_fixer_enabled` is False in the config, Step 1 doesn't call this at all (already handled by the service)

**Why:** Plan 07 specifies LLM-based text repair. Today the "fixer" just strips whitespace — useless for real OCR'd pages that have `rn` → `m` errors, broken columns, etc. This makes Step 1's quality gate meaningful.

---

### E4. Step 1 handler: fetch source PDF from Supabase Storage

**What:** The Step 1 handler currently expects `source_content` and `direct_pages` inline in the task payload. It should instead fetch the uploaded PDF from Supabase Storage using the `source_file_id`.

**How:** Modify `apps/worker/src/qcm_worker/step1_handler.py`:
- Look up `source_file_id` from the payload
- Query the `source_files` table via PostgREST to get the `storage_key`
- Download the file bytes from Supabase Storage via `GET /storage/v1/object/{bucket}/{key}`
- Pass those bytes to `PypdfTextExtractor.extract_pages(source_content=pdf_bytes)`
- If `direct_pages` is present in the payload (test mode), use those instead of downloading (keeps tests green)

**Why:** Today the handler never touches the uploaded PDF — it reads fake text from the payload. This connects the upload flow (Phase C) to the extraction flow (Phase E). Without this, Step 1 has no access to the real file.

**New infrastructure:** `SupabaseStorageDownloader` — a small helper in the worker that downloads object bytes from Storage via `httpx.GET /storage/v1/object/{bucket}/{key}` (service-role auth). Could also add a `get_object(key) -> bytes` method to `SupabaseStorageRestAdapter`.

---

### E5. Step 2 handler: real LLM-based QCM extraction

**What:** The Step 2 orchestrator's page cycle should call OpenRouter with each page's text and parse QCM questions/propositions from the LLM's JSON response.

**How:** This is the biggest piece. The Step 2 page cycle (`step2_pages.py`) currently uses a regex parser (`_QUESTION_RE`, `_PROPOSITION_RE`) to extract QCMs from raw text. The plan calls for an LLM-based extraction prompt (`step2.page_qcm_extraction.v1`).

I'll add an LLM-backed extraction path:
- Build a prompt from the page text: "Extract QCM questions from the following page. Return JSON: `{\"questions\": [{\"number\": 1, \"text\": \"...\", \"propositions\": [{\"letter\": \"A\", \"text\": \"...\"}]}]}`"
- Call `OpenRouterAdapter.complete_json` with the prompt
- Parse the response JSON into `PageExtractionDraft.qcms`
- Keep the regex parser as a fallback / for comparison (the service already has quality gates)

**Why:** The regex parser can't handle real-world PDFs — questions span lines, propositions have complex formatting, and the page text from pypdf is often garbled. LLM extraction is what the plans specify and what the legacy system did. This is the core value-producing step of the entire pipeline.

**Scope guard:** I'll wire the LLM call into the page cycle, but I **won't** rewrite the orchestrator, metadata, format, or finalize cycles — those work fine as-is (they operate on the QCM records produced by the page cycle). The change is surgical: swap the regex extraction for an LLM call.

---

### E6. Wire real adapters in the worker's `main.py`

**What:** The worker's `build_worker_task_service` and handler registration need to also build and inject the real adapters.

**How:** Modify `apps/worker/src/qcm_worker/main.py`:
- When `OPENROUTER_API_KEY` is present in env: build `httpx.Client`, `OpenRouterAdapter`, `ProviderRegistry`, `PypdfTextExtractor`, `SupabaseStorageRestAdapter` (for downloads), and pass them to the handlers
- When `OPENROUTER_API_KEY` is absent: fall back to the fake adapters (keeps local tests green)
- The handlers will check: if a real extractor/provider is available, use it; otherwise use the fake

**Why:** Today the worker constructs everything with fakes hardcoded. This makes the worker use real adapters in production while keeping the local/contract path working.

---

## Data Flow (After Phase E)

```
User uploads real PDF (Phase C) → stored in Supabase Storage
  ↓
User triggers Step 1 run → task created with source_file_id
  ↓
Worker claims task:
  1. Fetches source_file_id from source_files table → gets storage_key
  2. Downloads PDF bytes from Supabase Storage
  3. PypdfTextExtractor.extract_pages(pdf_bytes) → real page text
  4. Step 1 service classifies pages (direct/OCR/mixed)
  5. If text_fixer_enabled: OpenRouterTextFixer.repair(page_text) → LLM fixes OCR errors
  6. Step 1 produces step1_text artifacts (still in-memory sink for now)
  ↓
Worker completes Step 1 task → "Step 1 extraction completed"
  ↓
User triggers Step 2 run → task created with step1_artifact_ids + page texts
  ↓
Worker claims task:
  1. Step 2 orchestrator runs the page cycle
  2. For each page: builds extraction prompt → calls OpenRouter LLM → parses QCM JSON
  3. Metadata/format/finalize cycles process the extracted QCMs
  4. Step 2 produces step2_final_json artifact (in-memory sink)
  ↓
Worker completes Step 2 task → "Combined Step 2 completed"
```

---

## Files I Will Create/Modify

| File | Action | Purpose |
|---|---|---|
| `packages/infrastructure/.../pdf/pypdf_extractor.py` | **New** | Real PDF text extraction via pypdf |
| `packages/infrastructure/.../pdf/openrouter_text_fixer.py` | **New** | LLM-based text repair via OpenRouter |
| `packages/infrastructure/.../storage/rest_adapter.py` | **Modify** | Add `get_object(key) -> bytes` for downloads |
| `packages/infrastructure/.../llm/openrouter_adapter.py` | **Modify** | Accept real `api_key` + inject `httpx.Client` |
| `apps/worker/.../step1_handler.py` | **Modify** | Fetch PDF from Storage, use PypdfTextExtractor + real text fixer |
| `apps/worker/.../step2_orchestrator_handler.py` | **Modify** | Inject LLM-based extraction into the page cycle |
| `apps/worker/.../main.py` | **Modify** | Build + inject real adapters when env present |
| `requirements.txt` | **Modify** | Add `pypdf>=4.0` |
| `tests/test_step1_real_pdf.py` | **New** | Test pypdf extractor with a tiny test PDF |
| `tests/test_openrouter_adapter_mock.py` | **New** | Test OpenRouter adapter with mocked httpx |

---

## What Will NOT Be Fixed in Phase E

- **Artifact persistence from handlers** — handlers still write to `InMemory*ArtifactSink`. The artifacts aren't saved to Supabase Storage/DB yet. This is a separate concern (the sink needs to be replaced with a storage-backed sink) and is deferred to a follow-up. Phase E makes the **processing** real; persistence of results is the next step.
- **Step 3/4 real LLM calls** — Step 3 (correction) and Step 4 (similarity) also have model config placeholders. I'll wire them to use the same OpenRouter adapter, but their prompts and logic are more complex and may need separate work. This phase focuses on Step 1 + Step 2 (the core extraction pipeline).
- **OCR via tesseract** — the plans mention tesseract for OCR, but installing tesseract on the VPS requires `apt-get install tesseract-ocr` + language packs. For Phase E I'll use LLM-based OCR as a fallback (send the page image to a vision model via OpenRouter) rather than installing system packages. Tesseract can be added later if needed.

---

## Deployment Steps (After I Implement + Push)

```bash
# On the VPS
cd /opt/qcm-extractor-api/current
sudo git -c safe.directory=/opt/qcm-extractor-api/current pull origin main

# Install pypdf
.venv/bin/pip install pypdf

# Add OpenRouter API key to env
sudo nano /etc/qcm-extractor-api.env
# Add: OPENROUTER_API_KEY=sk-or-v1-...

# Restart both API and worker
sudo systemctl restart qcm-extractor-api
sudo systemctl restart qcm-extractor-worker

# Verify
curl http://127.0.0.1:8000/health
sudo systemctl is-active qcm-extractor-worker
```

No Supabase changes needed. No new tables. No new Storage buckets. Just `pip install pypdf` + the `OPENROUTER_API_KEY` env var.