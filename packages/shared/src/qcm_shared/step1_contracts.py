"""Step 1 ingestion, extraction, OCR, and quality DTOs."""

from dataclasses import dataclass, field
from typing import Any

from qcm_shared.contracts import QualityStatus

STEP1_TASK_KIND = "step1_extract"
STEP1_SCHEMA_VERSION = "step1.v1"


@dataclass(frozen=True, slots=True)
class Step1Config:
    extraction_mode: str = "automatic"
    override_reason: str | None = None
    page_range_start: int | None = None
    page_range_end: int | None = None
    text_fixer_enabled: bool = True
    text_fixer_model: str | None = None

    def __post_init__(self) -> None:
        if self.page_range_start is None and self.page_range_end is None:
            return
        if self.page_range_start is None or self.page_range_end is None:
            raise ValueError("Page range requires both start and end")
        if self.page_range_start < 1 or self.page_range_end < self.page_range_start:
            raise ValueError("Invalid Step 1 page range")


@dataclass(frozen=True, slots=True)
class Step1RunCommand:
    user_id: str
    project_id: str
    run_id: str
    source_file_id: str
    source_filename: str
    source_content: bytes
    config: Step1Config = field(default_factory=Step1Config)
    task_id: str | None = None
    attempt_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class Step1PageResult:
    page_number: int
    extraction_method: str
    raw_text: str
    corrected_text: str
    meaningful_chars: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step1DetectionSummary:
    requested_mode: str
    resolved_mode: str
    manual_override: bool
    override_reason: str | None
    page_decisions: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step1QualitySummary:
    status: QualityStatus
    total_pages: int
    total_corrected_chars: int
    ocr_page_count: int
    direct_page_count: int
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step1Result:
    user_id: str
    project_id: str
    run_id: str
    source_file_id: str
    source_filename: str
    detection: Step1DetectionSummary
    quality: Step1QualitySummary
    pages: tuple[Step1PageResult, ...]
    artifact_ids: tuple[str, ...]

    @property
    def combined_text(self) -> str:
        return "\n\n".join(page.corrected_text for page in self.pages)
