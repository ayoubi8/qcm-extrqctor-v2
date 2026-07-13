"""Future Step 3 correction mode and page-scoring domain rules."""

from dataclasses import dataclass
from qcm_domain.compat import StrEnum
import re

DEFAULT_CORRECTION_CANDIDATE_THRESHOLD = 15
DEFAULT_INCLUDE_CORRECTION_NEIGHBORS = True
CORRECTION_PATTERN_SUGGESTION_COUNT = 4


class CorrectionMode(StrEnum):
    PAGE_DETECTION = "page_detection"
    VISION = "vision"
    AUTO_DETECTION = "auto_detection"


LEGACY_CORRECTION_MODE_MAP = {
    "page_text": CorrectionMode.PAGE_DETECTION,
    "vision_ai": CorrectionMode.VISION,
    "auto_detect": CorrectionMode.AUTO_DETECTION,
    "all_pages": CorrectionMode.AUTO_DETECTION,
}

_ANSWER_PATTERN = re.compile(r"(?:^|\s|\||;)(\d{1,3})\s*[:.\-\)]\s*([A-Ea-e]{1,5})(?=\s|\||;|$)")
_CORRECTION_KEYWORDS = ("corrige", "corrigé", "correction", "réponse", "reponse", "answer", "rep.")


@dataclass(frozen=True, slots=True)
class CorrectionPageSignal:
    page_number: int
    credible_pattern_count: int
    keyword_count: int
    score: int
    suggested: bool

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("Correction page numbers start at 1")


def normalize_correction_mode(value: CorrectionMode | str) -> CorrectionMode:
    if isinstance(value, CorrectionMode):
        return value
    mapped = LEGACY_CORRECTION_MODE_MAP.get(value, value)
    try:
        return mapped if isinstance(mapped, CorrectionMode) else CorrectionMode(mapped)
    except ValueError as exc:
        raise ValueError(f"Unsupported Step 3 correction mode: {value}") from exc


def normalize_answer(value: str) -> str:
    answer = "".join(char for char in str(value).upper() if char in "ABCDE")
    return "".join(dict.fromkeys(answer))[:5]


def extract_correction_map_from_text(text: str) -> dict[str, str]:
    corrections: dict[str, str] = {}
    for question_number, answer in _ANSWER_PATTERN.findall(text):
        normalized = normalize_answer(answer)
        if normalized:
            corrections[str(int(question_number))] = normalized
    return corrections


def score_correction_page(
    *,
    page_number: int,
    text: str,
    threshold: int = DEFAULT_CORRECTION_CANDIDATE_THRESHOLD,
) -> CorrectionPageSignal:
    lowered = text.lower()
    keyword_count = sum(1 for keyword in _CORRECTION_KEYWORDS if keyword in lowered)
    pattern_count = len(extract_correction_map_from_text(text))
    score = pattern_count * 3 + keyword_count * 5
    suggested = score >= threshold or pattern_count > CORRECTION_PATTERN_SUGGESTION_COUNT
    return CorrectionPageSignal(
        page_number=page_number,
        credible_pattern_count=pattern_count,
        keyword_count=keyword_count,
        score=score,
        suggested=suggested,
    )


def parse_page_selection(value: str | list[int] | tuple[int, ...] | None) -> tuple[int, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, (list, tuple)):
        pages = [int(item) for item in value]
    else:
        pages = []
        for part in str(value).replace(";", ",").split(","):
            token = part.strip()
            if not token:
                continue
            if ":" in token:
                start, end = token.split(":", 1)
                pages.extend(range(int(start), int(end) + 1))
            elif "-" in token:
                start, end = token.split("-", 1)
                pages.extend(range(int(start), int(end) + 1))
            else:
                pages.append(int(token))
    return tuple(sorted({page for page in pages if page > 0}))


def include_neighbor_pages(selected_pages: tuple[int, ...], *, min_page: int, max_page: int) -> tuple[int, ...]:
    expanded: set[int] = set(selected_pages)
    for page in selected_pages:
        if page > min_page:
            expanded.add(page - 1)
        if page < max_page:
            expanded.add(page + 1)
    return tuple(sorted(expanded))
