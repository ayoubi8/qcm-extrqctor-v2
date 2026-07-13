"""Provider-free AI Auto Run document map and evidence validators."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AiAutoRunGate(StrEnum):
    PASSED = "passed"
    MANUAL_INTERVENTION = "manual_intervention"
    SAFE_STOP = "safe_stop"


@dataclass(frozen=True, slots=True)
class AiDocumentMapPage:
    page_number: int
    role: str
    confidence: float
    evidence_summary: str

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("AI document map pages start at 1")
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("AI document map confidence must be between 0 and 1")
        assert_safe_summary(self.evidence_summary)


@dataclass(frozen=True, slots=True)
class AiDocumentMap:
    pages: tuple[AiDocumentMapPage, ...]

    def __post_init__(self) -> None:
        if not self.pages:
            raise ValueError("AI Auto Run document map requires at least one page")
        page_numbers = [page.page_number for page in self.pages]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError("AI document map page numbers must be unique")


RAW_REASONING_MARKERS = (
    "chain of thought",
    "hidden reasoning",
    "private reasoning",
    "internal reasoning",
    "scratchpad",
)


def assert_safe_summary(value: str) -> None:
    lowered = value.lower()
    if any(marker in lowered for marker in RAW_REASONING_MARKERS):
        raise ValueError("AI Auto Run summaries cannot expose raw reasoning")


def validate_ai_generated_config(config: dict[str, Any], *, required_keys: tuple[str, ...]) -> tuple[str, ...]:
    missing = tuple(key for key in required_keys if key not in config)
    return tuple(f"Missing generated config key: {key}" for key in missing)


def evaluate_ai_quality(*, document_map: AiDocumentMap, config_errors: tuple[str, ...]) -> tuple[AiAutoRunGate, tuple[str, ...]]:
    warnings: list[str] = []
    if config_errors:
        return AiAutoRunGate.SAFE_STOP, config_errors
    low_confidence = [page.page_number for page in document_map.pages if page.confidence < 0.55]
    if low_confidence:
        warnings.append(f"Manual review requested for low confidence pages: {low_confidence}")
        return AiAutoRunGate.MANUAL_INTERVENTION, tuple(warnings)
    return AiAutoRunGate.PASSED, ()
