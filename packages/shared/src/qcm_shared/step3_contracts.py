"""Future Step 3 correction processing DTOs."""

from dataclasses import dataclass, field
from typing import Any

from qcm_shared.contracts import QualityStatus

STEP3_TASK_KIND = "step3_correction"
STEP3_SCHEMA_VERSION = "step3-correction.v1"
STEP3_PAGE_DETECTION_PROMPT_ID = "step3.correction.page_detection.v1"
STEP3_VISION_PROMPT_ID = "step3.correction.vision.v1"
STEP3_AUTO_DETECTION_PROMPT_ID = "step3.correction.auto_detection.v1"


@dataclass(frozen=True, slots=True)
class Step3CorrectionConfig:
    mode: str = "page_detection"
    selected_pages: tuple[int, ...] = ()
    candidate_threshold: int = 15
    include_neighbors: bool = True
    force_overwrite: bool = False
    vision_guide: str | None = None
    vision_detections: dict[str, str] = field(default_factory=dict)
    model: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.candidate_threshold < 1:
            raise ValueError("Correction candidate threshold must be positive")
        if any(page < 1 for page in self.selected_pages):
            raise ValueError("Correction selected pages start at 1")


@dataclass(frozen=True, slots=True)
class Step3CorrectionPage:
    page_number: int
    text: str
    source_artifact_id: str | None = None

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("Correction source page numbers start at 1")


@dataclass(frozen=True, slots=True)
class Step3CorrectionRunCommand:
    user_id: str
    project_id: str
    run_id: str
    step2_artifact_ids: tuple[str, ...]
    qcms: tuple[dict[str, Any], ...]
    pages: tuple[Step3CorrectionPage, ...]
    config: Step3CorrectionConfig = field(default_factory=Step3CorrectionConfig)
    task_id: str | None = None
    attempt_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class Step3CorrectionSuggestion:
    page_number: int
    score: int
    credible_pattern_count: int
    keyword_count: int
    suggested: bool


@dataclass(frozen=True, slots=True)
class Step3CorrectionQuality:
    status: QualityStatus
    total_qcms: int
    corrected_count: int
    coverage_ratio: float
    manual_review_required: bool
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step3CorrectionResult:
    user_id: str
    project_id: str
    run_id: str
    mode: str
    correction_map: dict[str, str]
    corrected_qcms: tuple[dict[str, Any], ...]
    suggested_pages: tuple[int, ...]
    processed_pages: tuple[int, ...]
    suggestions: tuple[Step3CorrectionSuggestion, ...]
    quality: Step3CorrectionQuality
    artifact_ids: tuple[str, ...]
    raw_artifact_id: str | None = None
    corrected_json_artifact_id: str | None = None
    corrected_xlsx_artifact_id: str | None = None
