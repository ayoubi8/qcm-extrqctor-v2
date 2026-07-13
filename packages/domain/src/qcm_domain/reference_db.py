"""User-private reference database and similarity matching domain rules."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

DEFAULT_MATCH_THRESHOLD = 0.75
DEFAULT_TEXT_WEIGHT = 0.7
DEFAULT_CORRECTION_WEIGHT = 0.3
DEFAULT_GREEN_BAND = 0.90
DEFAULT_YELLOW_BAND = 0.75


class SimilarityMatchMode(StrEnum):
    TEXT_ONLY = "text_only"
    FULL = "full"
    WEIGHTED = "weighted"


@dataclass(frozen=True, slots=True)
class ReferenceDatabase:
    reference_db_id: str
    user_id: str
    name: str
    qcm_count: int
    created_at: str | None = None

    def __post_init__(self) -> None:
        if not self.reference_db_id or not self.user_id or not self.name:
            raise ValueError("ReferenceDatabase requires id, owner, and name")
        if self.qcm_count < 0:
            raise ValueError("ReferenceDatabase qcm_count cannot be negative")


def normalize_match_mode(value: SimilarityMatchMode | str) -> SimilarityMatchMode:
    try:
        return value if isinstance(value, SimilarityMatchMode) else SimilarityMatchMode(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported similarity match mode: {value}") from exc


def validate_match_threshold(value: float) -> float:
    threshold = float(value)
    if threshold < 0 or threshold > 1:
        raise ValueError("Similarity threshold must be between 0 and 1")
    return threshold


def validate_match_weights(text_weight: float, correction_weight: float) -> tuple[float, float]:
    text = float(text_weight)
    correction = float(correction_weight)
    if text < 0 or correction < 0:
        raise ValueError("Similarity weights cannot be negative")
    total = text + correction
    if total <= 0:
        raise ValueError("At least one similarity weight must be positive")
    return (text / total, correction / total)


def similarity_band(score: float, *, green: float = DEFAULT_GREEN_BAND, yellow: float = DEFAULT_YELLOW_BAND) -> str:
    if score >= green:
        return "green"
    if score >= yellow:
        return "yellow"
    return "red"


def qcm_identity(qcm: dict[str, Any], fallback_index: int = 0) -> str:
    return str(qcm.get("uid") or qcm.get("ID") or qcm.get("Num") or qcm.get("number") or fallback_index)
