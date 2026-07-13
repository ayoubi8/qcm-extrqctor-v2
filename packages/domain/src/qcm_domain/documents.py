"""Document and page extraction domain rules for Step 1."""

from dataclasses import dataclass
from qcm_domain.compat import StrEnum

DIRECT_TEXT_THRESHOLD = 200


class ExtractionMode(StrEnum):
    AUTOMATIC = "automatic"
    DIRECT = "direct"
    OCR = "ocr"
    MIXED = "mixed"


class PageExtractionMethod(StrEnum):
    DIRECT = "direct"
    OCR = "ocr"


@dataclass(frozen=True, slots=True)
class PageTextSignal:
    page_number: int
    extracted_text: str
    meaningful_chars: int
    direct_text_detected: bool

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("Page numbers start at 1")
        if self.meaningful_chars < 0:
            raise ValueError("Meaningful character count cannot be negative")


@dataclass(frozen=True, slots=True)
class PageExtractionDecision:
    page_number: int
    method: PageExtractionMethod
    meaningful_chars: int
    reason: str


@dataclass(frozen=True, slots=True)
class DocumentDetectionReport:
    requested_mode: ExtractionMode
    resolved_mode: ExtractionMode
    manual_override: bool
    override_reason: str | None
    page_decisions: tuple[PageExtractionDecision, ...]
    warnings: tuple[str, ...] = ()


def meaningful_character_count(text: str) -> int:
    """Count characters that indicate usable text, excluding whitespace and OCR noise."""

    return sum(1 for char in text if char.isalnum())


def classify_page_text(page_number: int, text: str) -> PageTextSignal:
    count = meaningful_character_count(text)
    return PageTextSignal(
        page_number=page_number,
        extracted_text=text,
        meaningful_chars=count,
        direct_text_detected=count > DIRECT_TEXT_THRESHOLD,
    )


def _coerce_mode(value: ExtractionMode | str) -> ExtractionMode:
    try:
        return value if isinstance(value, ExtractionMode) else ExtractionMode(value)
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in ExtractionMode)
        raise ValueError(f"Unsupported extraction mode '{value}'. Expected one of: {allowed}") from exc


def resolve_extraction_plan(
    signals: tuple[PageTextSignal, ...],
    requested_mode: ExtractionMode | str,
    *,
    override_reason: str | None = None,
) -> DocumentDetectionReport:
    if not signals:
        raise ValueError("Step 1 requires at least one page signal")
    mode = _coerce_mode(requested_mode)
    manual_override = mode != ExtractionMode.AUTOMATIC
    if manual_override and not (override_reason or "").strip():
        raise ValueError("Manual extraction overrides require an override reason")

    warnings: list[str] = []
    if mode == ExtractionMode.AUTOMATIC:
        has_direct = any(signal.direct_text_detected for signal in signals)
        has_ocr = any(not signal.direct_text_detected for signal in signals)
        if has_direct and has_ocr:
            resolved = ExtractionMode.MIXED
        elif has_direct:
            resolved = ExtractionMode.DIRECT
        else:
            resolved = ExtractionMode.OCR
    else:
        resolved = mode

    decisions: list[PageExtractionDecision] = []
    for signal in signals:
        if resolved == ExtractionMode.DIRECT:
            method = PageExtractionMethod.DIRECT
            reason = "manual_direct_override" if manual_override else "direct_text_threshold_met"
            if signal.meaningful_chars <= DIRECT_TEXT_THRESHOLD:
                warnings.append(f"Page {signal.page_number} has weak direct text but direct mode was selected")
        elif resolved == ExtractionMode.OCR:
            method = PageExtractionMethod.OCR
            reason = "manual_ocr_override" if manual_override else "direct_text_threshold_not_met"
        else:
            method = PageExtractionMethod.DIRECT if signal.direct_text_detected else PageExtractionMethod.OCR
            reason = "page_direct_text_threshold_met" if signal.direct_text_detected else "page_requires_ocr"

        decisions.append(
            PageExtractionDecision(
                page_number=signal.page_number,
                method=method,
                meaningful_chars=signal.meaningful_chars,
                reason=reason,
            )
        )

    return DocumentDetectionReport(
        requested_mode=mode,
        resolved_mode=resolved,
        manual_override=manual_override,
        override_reason=override_reason,
        page_decisions=tuple(decisions),
        warnings=tuple(dict.fromkeys(warnings)),
    )
