"""Combined Step 2 internal page-by-page QCM extraction cycle."""

from dataclasses import dataclass
import re
from typing import Any, Protocol

from qcm_domain.qcm import (
    MIN_COMPLETE_PROPOSITIONS,
    QcmRecord,
    merge_duplicate_qcms,
    normalize_qcm_payload,
)
from qcm_shared.step2_contracts import (
    STEP2_PAGE_SCHEMA_VERSION,
    Step2PageQualityMetrics,
    Step2PageTaskInput,
    Step2PageTaskOutput,
    Step2RunCommand,
    Step2SplitRepairReport,
)

_QUESTION_RE = re.compile(r"^\s*(?:\*\*)?(?:Q(?:uestion)?\s*)?(\d+)[\).\:-]\s*(.+)", re.IGNORECASE)
_PROPOSITION_RE = re.compile(r"^\s*[\(\[]?([A-Ea-e])[\)\].:-]\s+(.+)")


@dataclass(frozen=True, slots=True)
class PageExtractionDraft:
    qcms: tuple[dict[str, Any], ...]
    orphan_propositions: dict[str, str]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Step2PageCycleResult:
    page_outputs: tuple[Step2PageTaskOutput, ...]
    qcms: tuple[dict[str, Any], ...]
    split_report: Step2SplitRepairReport
    warnings: tuple[str, ...]


class PageQcmExtractor(Protocol):
    def extract(self, page_input: Step2PageTaskInput) -> PageExtractionDraft:
        ...


class RuleBasedPageQcmExtractor:
    """Deterministic extractor used before the live provider-backed adapter lands."""

    def extract(self, page_input: Step2PageTaskInput) -> PageExtractionDraft:
        qcms: list[dict[str, Any]] = []
        orphan_props: dict[str, str] = {}
        warnings: list[str] = []
        current: dict[str, Any] | None = None
        last_prop_key: str | None = None
        seen_question = False

        for raw_line in page_input.current_page_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            question = _QUESTION_RE.match(line)
            proposition = _PROPOSITION_RE.match(line)

            if question:
                seen_question = True
                if current is not None:
                    qcms.append(current)
                current = {
                    "page": page_input.page_number,
                    "number": int(question.group(1)),
                    "text": question.group(2).strip(),
                    "propositions": {},
                }
                last_prop_key = None
                continue

            if proposition:
                key = proposition.group(1).upper()
                value = proposition.group(2).strip()
                if current is None and not seen_question:
                    orphan_props[key] = value
                elif current is not None:
                    current.setdefault("propositions", {})[key] = value
                    last_prop_key = key
                continue

            if current is None and not seen_question:
                seen_question = True
                current = {
                    "page": page_input.page_number,
                    "number": 0,
                    "text": line,
                    "propositions": {},
                }
                last_prop_key = None
                continue

            if current is not None and last_prop_key:
                current["propositions"][last_prop_key] = f"{current['propositions'][last_prop_key]} {line}".strip()
            elif current is not None:
                current["text"] = f"{current['text']} {line}".strip()
            elif len(line) > 30:
                warnings.append(f"Page {page_input.page_number} has context text before first QCM")

        if current is not None:
            qcms.append(current)
        if not qcms and not orphan_props:
            warnings.append(f"Page {page_input.page_number} produced no QCM candidates")
        return PageExtractionDraft(qcms=tuple(qcms), orphan_propositions=orphan_props, warnings=tuple(dict.fromkeys(warnings)))


class Step2PageCycleService:
    def __init__(self, extractor: PageQcmExtractor | None = None) -> None:
        self.extractor = extractor or RuleBasedPageQcmExtractor()

    def build_page_inputs(self, command: Step2RunCommand) -> tuple[Step2PageTaskInput, ...]:
        ordered_pages = sorted(command.pages, key=lambda item: item.page_number)
        inputs: list[Step2PageTaskInput] = []
        for index, page in enumerate(ordered_pages):
            previous_page = ordered_pages[index - 1] if index > 0 else None
            next_page = ordered_pages[index + 1] if index + 1 < len(ordered_pages) else None
            if not page.text.strip():
                continue
            inputs.append(
                Step2PageTaskInput(
                    page_number=page.page_number,
                    previous_page_text=previous_page.text if previous_page else None,
                    current_page_text=page.text,
                    next_page_text=next_page.text if next_page else None,
                    source_artifact_id=page.source_artifact_id,
                    model=command.config.model,
                    prompt_id=command.config.extraction_prompt_id,
                    schema_version=STEP2_PAGE_SCHEMA_VERSION,
                )
            )
        return tuple(inputs)

    def run(self, command: Step2RunCommand) -> Step2PageCycleResult:
        page_inputs = self.build_page_inputs(command)
        if not page_inputs:
            raise ValueError("Step 2 page QCM cycle requires at least one non-empty page")

        page_records: dict[int, list[QcmRecord]] = {}
        page_warnings: dict[int, list[str]] = {}
        orphan_props_by_page: dict[int, dict[str, str]] = {}

        for page_input in page_inputs:
            draft = self.extractor.extract(page_input)
            records = [
                normalize_qcm_payload(payload, source_page=page_input.page_number, position=index)
                for index, payload in enumerate(draft.qcms)
            ]
            page_records[page_input.page_number] = records
            page_warnings[page_input.page_number] = list(draft.warnings)
            if draft.orphan_propositions:
                orphan_props_by_page[page_input.page_number] = dict(draft.orphan_propositions)

        split_merged_count = _merge_split_qcms(page_records, orphan_props_by_page)
        all_records = [record for page in sorted(page_records) for record in page_records[page]]
        merged_records, duplicate_count = merge_duplicate_qcms(all_records)
        outputs = tuple(
            _page_output(
                page_number=page_input.page_number,
                records=page_records.get(page_input.page_number, []),
                warnings=tuple(page_warnings.get(page_input.page_number, [])),
                prompt_id=page_input.prompt_id,
                orphan_pages=tuple(sorted(orphan_props_by_page)),
                split_merged_count=split_merged_count,
                duplicate_count=duplicate_count,
            )
            for page_input in page_inputs
        )
        warnings = _cycle_warnings(outputs, split_merged_count, duplicate_count)
        split_report = Step2SplitRepairReport(
            merged_count=split_merged_count,
            duplicate_count=duplicate_count,
            orphan_proposition_pages=tuple(sorted(orphan_props_by_page)),
            warnings=warnings,
        )
        return Step2PageCycleResult(
            page_outputs=outputs,
            qcms=tuple(record.to_dict() for record in merged_records),
            split_report=split_report,
            warnings=warnings,
        )


def _merge_split_qcms(
    page_records: dict[int, list[QcmRecord]],
    orphan_props_by_page: dict[int, dict[str, str]],
) -> int:
    merged_count = 0
    for page_number in sorted(page_records):
        next_page = page_number + 1
        if next_page not in orphan_props_by_page or not page_records[page_number]:
            continue
        last_record = page_records[page_number][-1]
        if last_record.complete:
            continue
        orphan_props = orphan_props_by_page[next_page]
        propositions = dict(last_record.propositions)
        for key, value in orphan_props.items():
            propositions.setdefault(key, value)
        page_records[page_number][-1] = QcmRecord(
            uid=last_record.uid,
            page=last_record.page,
            number=last_record.number,
            position=last_record.position,
            text=last_record.text,
            propositions=dict(sorted(propositions.items())),
            correction=last_record.correction,
            source_page=last_record.source_page,
            metadata_detected=last_record.metadata_detected | {"merged_from_page": next_page},
        )
        merged_count += 1
    return merged_count


def _page_output(
    *,
    page_number: int,
    records: list[QcmRecord],
    warnings: tuple[str, ...],
    prompt_id: str,
    orphan_pages: tuple[int, ...],
    split_merged_count: int,
    duplicate_count: int,
) -> Step2PageTaskOutput:
    incomplete_count = sum(1 for record in records if not record.complete)
    proposition_count = sum(len(record.propositions) for record in records)
    metric_warnings = list(warnings)
    if incomplete_count:
        metric_warnings.append(f"Page {page_number} has {incomplete_count} incomplete QCM candidate(s)")
    return Step2PageTaskOutput(
        page_number=page_number,
        qcms=tuple(record.to_dict() for record in records),
        split_report=Step2SplitRepairReport(
            merged_count=split_merged_count,
            duplicate_count=duplicate_count,
            orphan_proposition_pages=orphan_pages,
        ),
        quality_metrics=Step2PageQualityMetrics(
            page_number=page_number,
            qcm_count=len(records),
            incomplete_qcm_count=incomplete_count,
            proposition_count=proposition_count,
            warnings=tuple(dict.fromkeys(metric_warnings)),
        ),
        prompt_id=prompt_id,
        schema_version=STEP2_PAGE_SCHEMA_VERSION,
    )


def _cycle_warnings(
    outputs: tuple[Step2PageTaskOutput, ...],
    split_merged_count: int,
    duplicate_count: int,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if split_merged_count:
        warnings.append(f"Merged {split_merged_count} split QCM candidate(s) across page boundaries")
    if duplicate_count:
        warnings.append(f"Merged {duplicate_count} duplicate QCM candidate(s)")
    for output in outputs:
        warnings.extend(output.quality_metrics.warnings)
    total_qcms = sum(output.quality_metrics.qcm_count for output in outputs)
    complete_qcms = sum(output.quality_metrics.qcm_count - output.quality_metrics.incomplete_qcm_count for output in outputs)
    if total_qcms and complete_qcms == 0:
        warnings.append(f"No QCM candidate reached {MIN_COMPLETE_PROPOSITIONS} propositions")
    return tuple(dict.fromkeys(warnings))
