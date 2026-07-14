"""Real PDF text extraction using pypdf.

Reads a PDF from bytes (in-memory, no temp file) and extracts text page-by-page.
Pure Python, no system dependencies. Honors page_range filtering.
"""

from __future__ import annotations

from qcm_infrastructure.pdf.base import PdfPageText

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - dependency-light verification path
    PdfReader = None  # type: ignore[assignment]


class PypdfTextExtractor:
    """Implements the PdfTextExtractor Protocol from step1_service."""

    def __init__(self) -> None:
        if PdfReader is None:
            raise RuntimeError("pypdf is required for real PDF text extraction")

    def extract_pages(
        self,
        source_content: bytes,
        *,
        page_range: tuple[int, int] | None = None,
    ) -> tuple[PdfPageText, ...]:
        import io

        reader = PdfReader(io.BytesIO(source_content))
        pages: list[PdfPageText] = []
        start, end = page_range if page_range is not None else (1, len(reader.pages))
        for page_index in range(start - 1, min(end, len(reader.pages))):
            try:
                text = reader.pages[page_index].extract_text() or ""
            except Exception:
                text = ""
            pages.append(PdfPageText(page_number=page_index + 1, text=text))
        return tuple(pages)