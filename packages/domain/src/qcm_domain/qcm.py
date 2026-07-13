"""QCM normalization, UID, duplicate, and split-merge domain helpers."""

from dataclasses import dataclass, field
from typing import Any

PROPOSITION_KEYS = ("A", "B", "C", "D", "E")
MIN_COMPLETE_PROPOSITIONS = 3


@dataclass(frozen=True, slots=True)
class QcmRecord:
    uid: str
    page: int
    number: int
    position: int
    text: str
    propositions: dict[str, str] = field(default_factory=dict)
    correction: str | None = None
    source_page: int | None = None
    metadata_detected: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.page < 1 or self.source_page is not None and self.source_page < 1:
            raise ValueError("QCM page numbers start at 1")
        if self.position < 0:
            raise ValueError("QCM position cannot be negative")
        if self.number < 0:
            raise ValueError("QCM number cannot be negative")

    @property
    def complete(self) -> bool:
        return len(self.propositions) >= MIN_COMPLETE_PROPOSITIONS

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "uid": self.uid,
            "page": self.page,
            "number": self.number,
            "position": self.position,
            "text": self.text,
            "propositions": dict(self.propositions),
            "source_page": self.source_page or self.page,
        }
        if self.correction is not None:
            payload["correction"] = self.correction
        if self.metadata_detected:
            payload["metadata_detected"] = dict(self.metadata_detected)
        return payload


def normalize_proposition_key(value: str) -> str:
    key = value.strip().upper()
    if key not in PROPOSITION_KEYS:
        raise ValueError(f"Unsupported proposition key: {value}")
    return key


def stable_qcm_uid(page: int, number: int, position: int) -> str:
    if page < 1:
        raise ValueError("QCM UID page starts at 1")
    if number < 0 or position < 0:
        raise ValueError("QCM UID number and position cannot be negative")
    return f"{page}_{number}_{position}"


def normalize_qcm_payload(payload: dict[str, Any], *, source_page: int, position: int) -> QcmRecord:
    raw_number = payload.get("number", payload.get("Num", 0))
    try:
        number = int(raw_number or 0)
    except (TypeError, ValueError):
        number = 0
    raw_page = payload.get("page", source_page)
    try:
        page = int(raw_page or source_page)
    except (TypeError, ValueError):
        page = source_page
    propositions = normalize_propositions(payload.get("propositions") or {})
    return QcmRecord(
        uid=payload.get("uid") or stable_qcm_uid(page, number, position),
        page=page,
        number=number,
        position=position,
        text=str(payload.get("text", payload.get("Text", ""))).strip(),
        propositions=propositions,
        correction=payload.get("correction") or payload.get("Correct"),
        source_page=source_page,
        metadata_detected=dict(payload.get("metadata_detected") or {}),
    )


def normalize_propositions(values: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in values.items():
        try:
            normalized_key = normalize_proposition_key(str(key))
        except ValueError:
            continue
        text = str(value).strip()
        if text:
            normalized[normalized_key] = text
    return dict(sorted(normalized.items()))


def qcm_dedupe_key(record: QcmRecord) -> tuple[int, int]:
    return (record.page, record.number)


def merge_qcm_records(existing: QcmRecord, incoming: QcmRecord) -> QcmRecord:
    propositions = dict(existing.propositions)
    for key, value in incoming.propositions.items():
        propositions.setdefault(key, value)
    text = existing.text if len(existing.text) >= len(incoming.text) else incoming.text
    correction = existing.correction or incoming.correction
    metadata = dict(incoming.metadata_detected)
    metadata.update(existing.metadata_detected)
    return QcmRecord(
        uid=existing.uid,
        page=existing.page,
        number=existing.number,
        position=existing.position,
        text=text,
        propositions=dict(sorted(propositions.items())),
        correction=correction,
        source_page=existing.source_page,
        metadata_detected=metadata,
    )


def merge_duplicate_qcms(records: list[QcmRecord]) -> tuple[list[QcmRecord], int]:
    merged_by_key: dict[tuple[int, int], QcmRecord] = {}
    duplicate_count = 0
    for record in records:
        key = qcm_dedupe_key(record)
        if key in merged_by_key:
            duplicate_count += 1
            merged_by_key[key] = merge_qcm_records(merged_by_key[key], record)
        else:
            merged_by_key[key] = record
    return sorted(merged_by_key.values(), key=lambda item: (item.page, item.number, item.position)), duplicate_count
