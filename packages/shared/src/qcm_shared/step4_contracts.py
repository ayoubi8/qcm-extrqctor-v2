"""Future Step 4 Similarity Match compatibility DTOs."""

from dataclasses import dataclass
from typing import Any

from qcm_shared.contracts import QualityStatus

STEP4_TASK_KIND = "step4_similarity_match"
STEP4_SCHEMA_VERSION = "step4-similarity.v1"


@dataclass(frozen=True, slots=True)
class Step4SimilarityConfig:
    reference_db_id: str
    mode: str = "text_only"
    threshold: float = 0.75
    text_weight: float = 0.7
    correction_weight: float = 0.3
    color_green: float = 0.90
    color_yellow: float = 0.75
    export_existing: bool = False
    export_min_similarity: float | None = None
    export_max_similarity: float | None = None
    export_qcm_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReferenceDbCreateCommand:
    user_id: str
    reference_db_id: str
    name: str
    qcms: tuple[dict[str, Any], ...]
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class Step4SimilarityRunCommand:
    user_id: str
    project_id: str
    run_id: str
    source_artifact_ids: tuple[str, ...]
    source_qcms: tuple[dict[str, Any], ...]
    reference_qcms: tuple[dict[str, Any], ...]
    config: Step4SimilarityConfig
    existing_matches: tuple[dict[str, Any], ...] = ()
    task_id: str | None = None
    attempt_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class Step4MatchSummary:
    total_source_qcms: int
    matched_qcms: int
    green_matches: int
    yellow_matches: int
    red_matches: int
    average_similarity: float
    threshold: float
    mode: str


@dataclass(frozen=True, slots=True)
class Step4SimilarityQuality:
    status: QualityStatus
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step4SimilarityResult:
    user_id: str
    project_id: str
    run_id: str
    matches: tuple[dict[str, Any], ...]
    exported_matches: tuple[dict[str, Any], ...]
    summary: Step4MatchSummary
    quality: Step4SimilarityQuality
    artifact_ids: tuple[str, ...]
    match_json_artifact_id: str | None = None
    match_xlsx_artifact_id: str | None = None
    export_artifact_id: str | None = None
