"""Vision-based OCR engine using OpenRouter multimodal models.

Implements the OcrEngine Protocol: extract_page_text(pdf_bytes, page_number) -> str.
Renders the PDF page as a PNG image, sends it to an OpenRouter vision-capable model
(e.g., openai/gpt-4o-mini), and returns the extracted text.
"""

from __future__ import annotations

import base64
import logging

from qcm_infrastructure.pdf.base import TextRepairResult

try:
    from qcm_infrastructure.pdf.pdf_page_renderer import render_page_png
except ImportError:  # pragma: no cover
    render_page_png = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_VISION_OCR_PROMPT = (
    "You are an OCR assistant. Extract ALL text from this document page image exactly as it appears. "
    "Preserve the original layout, numbering, and formatting. "
    "Return only the extracted text, no explanation or commentary."
)


class OpenRouterVisionOcr:
    """Implements the OcrEngine Protocol from step1_service."""

    def __init__(self, adapter, *, model_id: str = "openai/gpt-4o-mini", dpi: int = 200) -> None:
        self.adapter = adapter
        self.model_id = model_id
        self.dpi = dpi

    def extract_page_text(self, source_content: bytes, *, page_number: int) -> str:
        if self.adapter is None or render_page_png is None:
            return ""

        try:
            png_bytes = render_page_png(source_content, page_number, dpi=self.dpi)
            if not png_bytes:
                logger.warning("Vision OCR: failed to render page %s to PNG", page_number)
                return ""

            image_b64 = base64.b64encode(png_bytes).decode("ascii")
            text = self.adapter.complete_vision(
                _VISION_OCR_PROMPT,
                image_b64,
                model_id=self.model_id,
                correlation_id=f"vision-ocr-page-{page_number}",
                max_tokens=8000,
                temperature=0.1,
            )
            return text.strip()
        except Exception as exc:
            logger.warning("Vision OCR failed for page %s: %s", page_number, exc)
            return ""