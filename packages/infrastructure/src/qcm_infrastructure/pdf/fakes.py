"""Deterministic PDF/OCR adapters used by tests and local verification."""

from qcm_infrastructure.pdf.base import PdfPageText, TextRepairResult


class FakePdfTextExtractor:
    def __init__(self, pages: dict[int, str] | list[str] | tuple[str, ...]) -> None:
        if isinstance(pages, dict):
            self.pages = dict(sorted(pages.items()))
        else:
            self.pages = {index + 1: text for index, text in enumerate(pages)}

    def extract_pages(
        self,
        source_content: bytes,
        *,
        page_range: tuple[int, int] | None = None,
    ) -> tuple[PdfPageText, ...]:
        selected = self.pages.items()
        if page_range is not None:
            start, end = page_range
            selected = [(page, text) for page, text in selected if start <= page <= end]
        return tuple(PdfPageText(page_number=page, text=text) for page, text in selected)


class FakeOcrEngine:
    def __init__(self, pages: dict[int, str] | None = None, *, default_prefix: str = "OCR text for page") -> None:
        self.pages = pages or {}
        self.default_prefix = default_prefix
        self.calls: list[int] = []

    def extract_page_text(self, source_content: bytes, *, page_number: int) -> str:
        self.calls.append(page_number)
        return self.pages.get(page_number, f"{self.default_prefix} {page_number}")


class IdentityTextQualityFixer:
    def repair(self, text: str, *, page_number: int, model_id: str | None = None) -> TextRepairResult:
        return TextRepairResult(text=text.strip(), changed=text != text.strip(), model_id=model_id)


class ReplacementTextQualityFixer:
    def __init__(self, replacements: dict[str, str]) -> None:
        self.replacements = replacements

    def repair(self, text: str, *, page_number: int, model_id: str | None = None) -> TextRepairResult:
        corrected = text
        for source, target in self.replacements.items():
            corrected = corrected.replace(source, target)
        warnings = () if corrected else (f"Page {page_number} is empty after text repair",)
        return TextRepairResult(
            text=corrected.strip(),
            changed=corrected != text,
            warnings=warnings,
            provider="local-fake",
            model_id=model_id,
        )
