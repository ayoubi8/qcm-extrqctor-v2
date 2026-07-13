"""PDF, OCR, and text-repair adapter contracts."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PdfPageText:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class TextRepairResult:
    text: str
    changed: bool
    warnings: tuple[str, ...] = ()
    provider: str | None = None
    model_id: str | None = None


class PdfTextExtractor(Protocol):
    def extract_pages(
        self,
        source_content: bytes,
        *,
        page_range: tuple[int, int] | None = None,
    ) -> tuple[PdfPageText, ...]:
        ...


class OcrEngine(Protocol):
    def extract_page_text(self, source_content: bytes, *, page_number: int) -> str:
        ...


class TextQualityFixer(Protocol):
    def repair(self, text: str, *, page_number: int, model_id: str | None = None) -> TextRepairResult:
        ...
