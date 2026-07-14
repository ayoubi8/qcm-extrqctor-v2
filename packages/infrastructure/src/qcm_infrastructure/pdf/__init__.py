"""PDF extraction infrastructure adapters."""

from qcm_infrastructure.pdf.base import OcrEngine, PdfPageText, PdfTextExtractor, TextQualityFixer, TextRepairResult
from qcm_infrastructure.pdf.fakes import FakeOcrEngine, FakePdfTextExtractor, IdentityTextQualityFixer, ReplacementTextQualityFixer

__all__ = [
    "FakeOcrEngine",
    "FakePdfTextExtractor",
    "IdentityTextQualityFixer",
    "OcrEngine",
    "PdfPageText",
    "PdfTextExtractor",
    "ReplacementTextQualityFixer",
    "TextQualityFixer",
    "TextRepairResult",
]