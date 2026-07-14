"""Render PDF pages as PNG images using pypdfium2.

Pure Python with pre-built wheels — no system packages required.
Used by the vision OCR adapter to extract text from scanned/image-based PDF pages.
"""

from __future__ import annotations

import io

try:
    import pypdfium2 as pdfium
except ImportError:  # pragma: no cover - dependency-light verification path
    pdfium = None  # type: ignore[assignment]


def render_page_png(pdf_bytes: bytes, page_number: int, *, dpi: int = 200) -> bytes:
    """Render a single PDF page as PNG image bytes.

    Args:
        pdf_bytes: Raw PDF file content.
        page_number: 1-indexed page number to render.
        dpi: Resolution for rendering (higher = better quality, larger payload).

    Returns:
        PNG image bytes, or empty bytes on failure.
    """
    if pdfium is None:
        raise RuntimeError("pypdfium2 is required for PDF page rendering")
    if not pdf_bytes:
        return b""
    if page_number < 1:
        return b""

    try:
        pdf = pdfium.PdfDocument(io.BytesIO(pdf_bytes))
        page_index = page_number - 1
        if page_index >= len(pdf):
            return b""
        page = pdf[page_index]
        scale = dpi / 72.0
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return b""


def page_count(pdf_bytes: bytes) -> int:
    """Return the number of pages in the PDF."""
    if pdfium is None:
        return 0
    try:
        pdf = pdfium.PdfDocument(io.BytesIO(pdf_bytes))
        return len(pdf)
    except Exception:
        return 0