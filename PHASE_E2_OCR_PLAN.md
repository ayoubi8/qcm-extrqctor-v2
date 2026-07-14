# Phase E2 Implementation Plan — Vision-Based OCR via OpenRouter

## The Problem

When a PDF page has **little or no extractable text** (scanned document, image-based PDF, or poor quality scan), `pypdf.extract_text()` returns almost nothing. The Step 1 service classifies these pages as needing OCR (fewer than 200 meaningful characters) and calls `self.ocr.extract_page_text(source_content, page_number)`.

Today, that call hits `FakeOcrEngine.extract_page_text()` which returns `"OCR text for page N"` — a meaningless placeholder. **Scanned PDFs produce no real text.**

The fix: render the PDF page as a PNG image and send it to an OpenRouter vision model (e.g., `openai/gpt-4o-mini` which supports vision) with a "extract all text from this image" prompt. The LLM sees the page image and returns the text — acting as a vision-based OCR engine.

---

## How It Works (Architecture)

```
Step1Service classifies pages
  ↓
Page has < 200 meaningful chars → needs OCR
  ↓
Step1Service calls: ocr.extract_page_text(pdf_bytes, page_number=3)
  ↓
OpenRouterVisionOcr:
  1. Opens PDF from bytes with pypdfium2
  2. Renders page 3 as a PNG image (300 DPI)
  3. Base64-encodes the PNG
  4. Builds a vision chat request to OpenRouter:
     "Extract all text from this document page image. Return only the text, no explanation."
     + image_url: "data:image/png;base64,..."
  5. OpenRouter routes to openai/gpt-4o-mini (vision-capable)
  6. Model sees the page image, returns extracted text
  7. OpenRouterVisionOcr returns the text to Step1Service
  ↓
Step1Service uses the OCR'd text for that page
```

---

## What I Will Build (Step by Step)

### O1. PDF page → PNG renderer (`pypdfium2`)

**What:** A helper that renders a single PDF page (by page number) from raw PDF bytes to a PNG image.

**How:** New file `packages/infrastructure/src/qcm_infrastructure/pdf/pdf_page_renderer.py`:
- Uses `pypdfium2` (Google's PDFium wrapper — pure Python with pre-built wheels, no system deps)
- `render_page_png(pdf_bytes: bytes, page_number: int, dpi: int = 200) -> bytes` — returns PNG bytes
- Opens the PDF in-memory, renders the page at the requested DPI, returns PNG bytes
- Handles edge cases: encrypted PDFs, page out of range → returns empty bytes

**Why pypdfium2 over alternatives:**
- `pypdf` can't render images (only extracts text)
- `PyMuPDF` (fitz) requires native compilation or a system package
- `pdf2image` requires `apt install poppler-utils` on the VPS
- `pypdfium2` has pre-built wheels for Linux x86_64 — just `pip install`, no `apt install`

**VPS requirement:** `pip install pypdfium2` only.

---

### O2. Vision message support in `OpenRouterAdapter`

**What:** Add a `complete_vision(prompt, image_base64, model_id, ...)` method to the existing `OpenRouterAdapter` that sends a multimodal (text + image) chat request.

**How:** Modify `packages/infrastructure/src/qcm_infrastructure/llm/openrouter_adapter.py`:
- New method `complete_vision(prompt: str, image_base64: str, model_id, correlation_id, ...) -> str`
- Builds an OpenRouter chat request with multimodal content:
  ```json
  {
    "model": "openai/gpt-4o-mini",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Extract all text from this document page image..."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,{base64_image}"}}
      ]
    }],
    "max_tokens": 4000,
    "temperature": 0.1
  }
  ```
- Sends it via the existing `http_client.post()`
- Extracts the text from `choices[0].message.content`
- Returns the text (not JSON — vision OCR returns raw text)

**Why:** The existing `complete_json` method sends text-only messages and parses JSON. Vision OCR needs a different message format (multimodal) and returns raw text, not JSON. Adding a separate method keeps `complete_json` unchanged for Step 2 QCM extraction.

---

### O3. `OpenRouterVisionOcr` — vision-based OCR engine

**What:** A new class implementing the `OcrEngine` Protocol that uses OpenRouter vision models to extract text from PDF page images.

**How:** New file `packages/infrastructure/src/qcm_infrastructure/pdf/openrouter_vision_ocr.py`:
- `OpenRouterVisionOcr(adapter: OpenRouterAdapter, model_id: str = "openai/gpt-4o-mini", dpi: int = 200)`
- `extract_page_text(source_content: bytes, page_number: int) -> str`:
  1. Calls `pdf_page_renderer.render_page_png(source_content, page_number, dpi)` → PNG bytes
  2. Base64-encodes the PNG: `base64.b64encode(png_bytes).decode("ascii")`
  3. Calls `adapter.complete_vision(prompt, image_base64, model_id, ...)` → text
  4. Returns the text
- On any error (rendering failure, API failure, timeout): returns empty string with a warning logged
- The prompt: "You are an OCR assistant. Extract ALL text from this document page image exactly as it appears. Preserve the original layout, numbering, and formatting. Return only the extracted text, no explanation or commentary."

**Why:** This is the drop-in replacement for `FakeOcrEngine` that implements the same `OcrEngine` Protocol. The Step1Service doesn't need to change — it just calls `ocr.extract_page_text(pdf_bytes, page_number)` and gets real text from the vision model instead of a fake string.

---

### O4. Wire vision OCR into the Step 1 handler

**What:** Replace `ocr = FakeOcrEngine()` in the Step 1 handler's `_build_real_adapters()` with `ocr = OpenRouterVisionOcr(adapter, model_id)` when OpenRouter is available.

**How:** Modify `apps/worker/src/qcm_worker/step1_handler.py`:
- In `_build_real_adapters()`: if `adapter` is not None and `pypdfium2` is importable, use `OpenRouterVisionOcr(adapter, model_id="openai/gpt-4o-mini")`; else fall back to `FakeOcrEngine()`
- The fallback chain: OpenRouter vision OCR → FakeOcrEngine (if no API key or no pypdfium2)
- No change to the Protocol or Step1Service — it's a transparent adapter swap

**Why:** This makes scanned PDFs work end-to-end. When a page has no extractable text, the worker renders it as an image and asks the vision model to read it — producing real text for Step 2 to extract QCMs from.

---

### O5. Add `pypdfium2` to requirements + update the PDF `__init__`

**What:** Update `requirements.txt` and the PDF package's `__init__.py` to export the new adapters.

**How:**
- `requirements.txt`: Add `pypdfium2>=4.0`
- `packages/infrastructure/.../pdf/__init__.py`: Export `OpenRouterVisionOcr` and `render_page_png`
- `packages/infrastructure/.../llm/openrouter_adapter.py`: Export `OpenRouterAdapter.complete_vision`

---

## Files I Will Create/Modify

| File | Action | Purpose |
|---|---|---|
| `packages/infrastructure/.../pdf/pdf_page_renderer.py` | **New** | Render PDF page → PNG via pypdfium2 |
| `packages/infrastructure/.../pdf/openrouter_vision_ocr.py` | **New** | Vision-based OCR via OpenRouter (implements OcrEngine) |
| `packages/infrastructure/.../llm/openrouter_adapter.py` | **Modify** | Add `complete_vision()` method for multimodal messages |
| `apps/worker/.../step1_handler.py` | **Modify** | Swap FakeOcrEngine → OpenRouterVisionOcr in production |
| `packages/infrastructure/.../pdf/__init__.py` | **Modify** | Export new vision OCR classes |
| `requirements.txt` | **Modify** | Add `pypdfium2>=4.0` |

---

## What Will NOT Be Fixed

- **Tesseract installation** — not needed; vision OCR replaces it entirely using the LLM
- **Image preprocessing** (deskew, denoise, binarization) — the vision model handles low-quality images well enough; preprocessing can be added later if needed
- **Multi-page batched vision calls** — each page is sent individually; batching multiple pages in one vision request is a future optimization
- **Step 3/4 vision** — Step 3 correction uses `vision_guide` / `vision_detections` in config, but that's a separate flow from Step 1 OCR; deferred

---

## Verification Plan

1. **Local test**: create a scanned-style PDF (blank pages with reportlab images), run Step 1 with `extraction_mode: "ocr"` → assert the vision OCR adapter is called and returns text
2. **VPS E2E**: upload a real scanned PDF → Step 1 runs → pages with no direct text get vision-OCR'd via OpenRouter → Step 1 completes with real text
3. **All existing tests stay green** (FakeOcrEngine fallback when pypdfium2 not installed)

---

## Deployment (After Implementation)

```bash
cd /opt/qcm-extractor-api/current
sudo git -c safe.directory=/opt/qcm-extractor-api/current pull origin main
.venv/bin/pip install pypdfium2
sudo systemctl restart qcm-extractor-worker
```

No Supabase changes. No new env vars (uses existing `OPENROUTER_API_KEY`). Just `pip install pypdfium2` + worker restart.