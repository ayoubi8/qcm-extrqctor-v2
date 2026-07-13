"""Combined visible Step 2 orchestration DTOs."""

from dataclasses import dataclass, field
from typing import Any

from qcm_shared.contracts import QualityStatus

STEP2_TASK_KIND = "step2_orchestrate"
STEP2_SCHEMA_VERSION = "step2-combined.v1"
STEP2_PAGE_PROMPT_ID = "step2.page_qcm_extraction.v1"
STEP2_PAGE_SCHEMA_VERSION = "step2-page-qcm.v1"
STEP2_METADATA_PROMPT_ID = "step2.metadata_cas_clinique.v1"
STEP2_FORMAT_SCHEMA_VERSION = "step2-format.v1"


@dataclass(frozen=True, slots=True)
class Step2ModelConfig:
    provider: str = "openrouter"
    primary_model_id: str = "configured-by-admin"
    fallback_model_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step2Config:
    page_batch_size: int = 0
    internal_page_concurrency: int = 5
    extraction_prompt_id: str = STEP2_PAGE_PROMPT_ID
    metadata_defaults: dict[str, str] = field(default_factory=dict)
    metadata_strategies: dict[str, str] = field(default_factory=dict)
    legacy_subcategory_policy: str = "preserve_internal"
    template_name: str = "default"
    template_overrides: dict[str, Any] = field(default_factory=dict)
    output_format: str = "json+xlsx"
    model: Step2ModelConfig = field(default_factory=Step2ModelConfig)
    resume_from_cycle: str | None = None

    def __post_init__(self) -> None:
        if self.page_batch_size < 0:
            raise ValueError("Step 2 page_batch_size cannot be negative")
        if self.internal_page_concurrency < 1:
            raise ValueError("Step 2 internal_page_concurrency must be at least 1")
        if self.output_format not in {"json", "json+xlsx"}:
            raise ValueError("Step 2 output_format must be json or json+xlsx")
        if self.legacy_subcategory_policy not in {"preserve_internal", "export", "drop"}:
            raise ValueError("Unsupported legacy subcategory policy")


@dataclass(frozen=True, slots=True)
class Step2SourcePage:
    page_number: int
    text: str
    source_artifact_id: str | None = None

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("Step 2 source page numbers start at 1")


@dataclass(frozen=True, slots=True)
class Step2RunCommand:
    user_id: str
    project_id: str
    run_id: str
    step1_artifact_ids: tuple[str, ...]
    pages: tuple[Step2SourcePage, ...]
    config: Step2Config = field(default_factory=Step2Config)
    previous_cycle_data: dict[str, Any] = field(default_factory=dict)
    task_id: str | None = None
    attempt_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class Step2PageTaskInput:
    page_number: int
    previous_page_text: str | None
    current_page_text: str
    next_page_text: str | None
    source_artifact_id: str | None
    model: Step2ModelConfig
    prompt_id: str
    schema_version: str = STEP2_PAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("Step 2 page task page_number starts at 1")
        if not self.current_page_text.strip():
            raise ValueError("Step 2 page task requires current page text")


@dataclass(frozen=True, slots=True)
class Step2SplitRepairReport:
    merged_count: int
    duplicate_count: int
    orphan_proposition_pages: tuple[int, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step2PageQualityMetrics:
    page_number: int
    qcm_count: int
    incomplete_qcm_count: int
    proposition_count: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step2PageTaskOutput:
    page_number: int
    qcms: tuple[dict[str, Any], ...]
    split_report: Step2SplitRepairReport
    quality_metrics: Step2PageQualityMetrics
    prompt_id: str
    schema_version: str = STEP2_PAGE_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class Step2MetadataProvenance:
    field_name: str
    strategy: str
    source: str
    value: str | None
    qcm_uid: str | None = None


@dataclass(frozen=True, slots=True)
class Step2ClinicalGroup:
    group_id: str
    label: str
    narrative: str
    qcm_uids: tuple[str, ...]
    page_numbers: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Step2MetadataResult:
    qcms: tuple[dict[str, Any], ...]
    provenance: tuple[Step2MetadataProvenance, ...]
    clinical_groups: tuple[Step2ClinicalGroup, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step2TemplateValidation:
    template_name: str
    valid: bool
    missing_required_fields: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step2FormatResult:
    template: dict[str, Any]
    formatted_qcms: tuple[dict[str, Any], ...]
    validation: Step2TemplateValidation
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step2FinalizeResult:
    final_qcms: tuple[dict[str, Any], ...]
    final_json_content: bytes
    final_xlsx_content: bytes | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step2CycleSummary:
    cycle_key: str
    status: str
    qcm_count: int
    artifact_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    failure: str | None = None


@dataclass(frozen=True, slots=True)
class Step2QualitySummary:
    status: QualityStatus
    total_pages: int
    total_qcms: int
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step2Result:
    user_id: str
    project_id: str
    run_id: str
    cycles: tuple[Step2CycleSummary, ...]
    quality: Step2QualitySummary
    qcms: tuple[dict[str, Any], ...]
    artifact_ids: tuple[str, ...]
    final_json_artifact_id: str | None = None
    final_xlsx_artifact_id: str | None = None
