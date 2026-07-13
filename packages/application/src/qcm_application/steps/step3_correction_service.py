"""Future Step 3 correction processing service, adapted from legacy Step 6."""

from dataclasses import asdict, dataclass
import json
from typing import Any, Protocol

from qcm_application.artifact_service import checksum_bytes
from qcm_domain.corrections import (
    CorrectionMode,
    extract_correction_map_from_text,
    include_neighbor_pages,
    normalize_answer,
    normalize_correction_mode,
    score_correction_page,
)
from qcm_shared.contracts import ArtifactType, QualityStatus, RetentionPolicy, TerminalEventType, TerminalLevel
from qcm_shared.step3_contracts import (
    STEP3_AUTO_DETECTION_PROMPT_ID,
    STEP3_PAGE_DETECTION_PROMPT_ID,
    STEP3_SCHEMA_VERSION,
    STEP3_VISION_PROMPT_ID,
    Step3CorrectionQuality,
    Step3CorrectionResult,
    Step3CorrectionRunCommand,
    Step3CorrectionSuggestion,
)
from qcm_shared.storage_contracts import ArtifactWriteRequest
from qcm_shared.task_contracts import TerminalEventCreate


class Step3ArtifactSink(Protocol):
    def write(self, request: ArtifactWriteRequest) -> str:
        ...


class Step3TerminalSink(Protocol):
    def append(self, event: TerminalEventCreate) -> Any:
        ...


@dataclass(frozen=True, slots=True)
class Step3ArtifactRecord:
    artifact_id: str
    request: ArtifactWriteRequest


class InMemoryStep3ArtifactSink:
    def __init__(self) -> None:
        self.records: list[Step3ArtifactRecord] = []

    def write(self, request: ArtifactWriteRequest) -> str:
        self.records.append(Step3ArtifactRecord(artifact_id=request.artifact_id, request=request))
        return request.artifact_id


class Step3CorrectionService:
    def __init__(
        self,
        *,
        artifact_sink: Step3ArtifactSink | None = None,
        terminal_sink: Step3TerminalSink | None = None,
    ) -> None:
        self.artifact_sink = artifact_sink
        self.terminal_sink = terminal_sink

    def run(self, command: Step3CorrectionRunCommand) -> Step3CorrectionResult:
        _validate_command(command)
        mode = normalize_correction_mode(command.config.mode)
        self._emit(command, TerminalLevel.INFO, TerminalEventType.STEP_STARTED, "Step 3 correction started", {"mode": mode.value})

        suggestions = self.suggest_pages(command)
        suggested_pages = tuple(signal.page_number for signal in suggestions if signal.suggested)
        selected_pages = tuple(sorted(command.config.selected_pages))
        processed_pages = _processed_pages(command, mode, selected_pages, suggested_pages)
        correction_map, raw_payload, warnings = self._extract_corrections(command, mode, processed_pages)
        corrected_qcms = _apply_corrections(
            command.qcms,
            correction_map,
            force_overwrite=command.config.force_overwrite,
        )
        quality = _quality(command, corrected_qcms, correction_map, mode, selected_pages, suggested_pages, warnings)

        artifact_ids: list[str] = []
        raw_artifact_id = self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step3-correction-raw",
            artifact_type=ArtifactType.DEBUG_INTERNAL,
            filename="step3-correction-raw.json",
            content_type="application/json",
            content=_json_bytes(raw_payload),
            retention_policy=RetentionPolicy.DEBUG_SHORT_LIVED,
        )
        artifact_ids.append(raw_artifact_id)
        map_artifact_id = self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step3-correction-map",
            artifact_type=ArtifactType.DEBUG_INTERNAL,
            filename="step3-correction-map.json",
            content_type="application/json",
            content=_json_bytes(correction_map),
            retention_policy=RetentionPolicy.DEBUG_SHORT_LIVED,
        )
        artifact_ids.append(map_artifact_id)
        corrected_json_artifact_id = self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step3-corrected-json",
            artifact_type=ArtifactType.STEP3_CORRECTION_JSON,
            filename="step3-corrected-qcms.json",
            content_type="application/json",
            content=_json_bytes(corrected_qcms),
            retention_policy=RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        )
        artifact_ids.append(corrected_json_artifact_id)
        corrected_xlsx_artifact_id = self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step3-corrected-xlsx",
            artifact_type=ArtifactType.STEP3_CORRECTION_XLSX,
            filename="step3-corrected-qcms.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=_xlsx_placeholder_bytes(corrected_qcms),
            retention_policy=RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        )
        artifact_ids.append(corrected_xlsx_artifact_id)
        quality_artifact_id = self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step3-correction-quality",
            artifact_type=ArtifactType.DEBUG_INTERNAL,
            filename="step3-correction-quality.json",
            content_type="application/json",
            content=_json_bytes(asdict(quality) | {"status": quality.status.value}),
            retention_policy=RetentionPolicy.DEBUG_SHORT_LIVED,
        )
        artifact_ids.append(quality_artifact_id)

        result = Step3CorrectionResult(
            user_id=command.user_id,
            project_id=command.project_id,
            run_id=command.run_id,
            mode=mode.value,
            correction_map=correction_map,
            corrected_qcms=tuple(corrected_qcms),
            suggested_pages=suggested_pages,
            processed_pages=processed_pages,
            suggestions=tuple(suggestions),
            quality=quality,
            artifact_ids=tuple(artifact_ids),
            raw_artifact_id=raw_artifact_id,
            corrected_json_artifact_id=corrected_json_artifact_id,
            corrected_xlsx_artifact_id=corrected_xlsx_artifact_id,
        )
        level = TerminalLevel.WARNING if quality.warnings else TerminalLevel.SUCCESS
        self._emit(
            command,
            level,
            TerminalEventType.STEP_COMPLETED,
            "Step 3 correction completed",
            {"quality_status": quality.status.value, "corrected_count": quality.corrected_count},
        )
        return result

    def suggest_pages(self, command: Step3CorrectionRunCommand) -> tuple[Step3CorrectionSuggestion, ...]:
        return tuple(
            Step3CorrectionSuggestion(
                page_number=signal.page_number,
                score=signal.score,
                credible_pattern_count=signal.credible_pattern_count,
                keyword_count=signal.keyword_count,
                suggested=signal.suggested,
            )
            for signal in (
                score_correction_page(
                    page_number=page.page_number,
                    text=page.text,
                    threshold=command.config.candidate_threshold,
                )
                for page in command.pages
            )
        )

    def _extract_corrections(
        self,
        command: Step3CorrectionRunCommand,
        mode: CorrectionMode,
        processed_pages: tuple[int, ...],
    ) -> tuple[dict[str, str], dict[str, Any], list[str]]:
        pages_by_number = {page.page_number: page for page in command.pages}
        warnings: list[str] = []
        raw_payload: dict[str, Any] = {"mode": mode.value, "pages": {}, "prompt_id": _prompt_id(mode)}
        correction_map: dict[str, str] = {}

        if mode == CorrectionMode.VISION and command.config.vision_detections:
            correction_map.update(
                {
                    str(key): normalized
                    for key, value in command.config.vision_detections.items()
                    if (normalized := normalize_answer(value))
                }
            )
            raw_payload["vision_guide"] = command.config.vision_guide
            raw_payload["vision_detections"] = dict(command.config.vision_detections)
            return correction_map, raw_payload, warnings
        if mode == CorrectionMode.VISION:
            warnings.append("Vision adapter is not configured; using marked page text as deterministic fallback")

        for page_number in processed_pages:
            page = pages_by_number.get(page_number)
            if page is None:
                warnings.append(f"Selected correction page {page_number} is unavailable")
                continue
            page_map = extract_correction_map_from_text(page.text)
            raw_payload["pages"][str(page_number)] = {"correction_count": len(page_map), "corrections": page_map}
            correction_map.update(page_map)
        return correction_map, raw_payload, warnings

    def _write_artifact(
        self,
        command: Step3CorrectionRunCommand,
        *,
        artifact_id: str,
        artifact_type: ArtifactType,
        filename: str,
        content_type: str,
        content: bytes,
        retention_policy: RetentionPolicy,
    ) -> str:
        request = ArtifactWriteRequest(
            user_id=command.user_id,
            project_id=command.project_id,
            run_id=command.run_id,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            filename=filename,
            content_type=content_type,
            content=content,
            version_number=1,
            checksum=checksum_bytes(content),
            schema_version=STEP3_SCHEMA_VERSION,
            retention_policy=retention_policy,
            source_artifact_ids=list(command.step2_artifact_ids),
        )
        if self.artifact_sink is not None:
            return self.artifact_sink.write(request)
        return request.artifact_id

    def _emit(
        self,
        command: Step3CorrectionRunCommand,
        level: TerminalLevel,
        event_type: TerminalEventType,
        message: str,
        safe_payload: dict[str, Any] | None = None,
    ) -> None:
        if self.terminal_sink is None:
            return
        self.terminal_sink.append(
            TerminalEventCreate(
                user_id=command.user_id,
                project_id=command.project_id,
                run_id=command.run_id,
                task_id=command.task_id,
                attempt_id=command.attempt_id,
                level=level,
                event_type=event_type,
                message=message,
                safe_payload=safe_payload or {},
            )
        )


def _validate_command(command: Step3CorrectionRunCommand) -> None:
    if not command.user_id or not command.project_id or not command.run_id:
        raise ValueError("Step 3 correction requires owner, project, and run identifiers")
    if not command.step2_artifact_ids:
        raise ValueError("Step 3 correction requires Step 2 final artifact identifiers")
    if not command.qcms:
        raise ValueError("Step 3 correction requires correctable QCM records")


def _processed_pages(
    command: Step3CorrectionRunCommand,
    mode: CorrectionMode,
    selected_pages: tuple[int, ...],
    suggested_pages: tuple[int, ...],
) -> tuple[int, ...]:
    if not command.pages:
        return ()
    min_page = min(page.page_number for page in command.pages)
    max_page = max(page.page_number for page in command.pages)
    if mode == CorrectionMode.AUTO_DETECTION:
        pages = tuple(page.page_number for page in sorted(command.pages, key=lambda item: item.page_number))
    elif selected_pages:
        pages = selected_pages
    else:
        pages = suggested_pages
    if command.config.include_neighbors and pages:
        pages = include_neighbor_pages(pages, min_page=min_page, max_page=max_page)
    available = {page.page_number for page in command.pages}
    return tuple(page for page in pages if page in available)


def _apply_corrections(
    qcms: tuple[dict[str, Any], ...],
    correction_map: dict[str, str],
    *,
    force_overwrite: bool,
) -> list[dict[str, Any]]:
    corrected: list[dict[str, Any]] = []
    for index, qcm in enumerate(qcms, start=1):
        item = dict(qcm)
        question_number = str(item.get("Num") or item.get("number") or index)
        existing = normalize_answer(item.get("Correct", ""))
        incoming = correction_map.get(question_number)
        if incoming and (force_overwrite or not existing):
            item["Correct"] = incoming
        elif existing:
            item["Correct"] = existing
        corrected.append(item)
    return corrected


def _quality(
    command: Step3CorrectionRunCommand,
    corrected_qcms: list[dict[str, Any]],
    correction_map: dict[str, str],
    mode: CorrectionMode,
    selected_pages: tuple[int, ...],
    suggested_pages: tuple[int, ...],
    warnings: list[str],
) -> Step3CorrectionQuality:
    total = len(corrected_qcms)
    corrected_count = sum(1 for qcm in corrected_qcms if normalize_answer(qcm.get("Correct", "")))
    coverage = corrected_count / total if total else 0.0
    review_required = False
    local_warnings = list(warnings)
    if mode == CorrectionMode.PAGE_DETECTION and suggested_pages and not selected_pages:
        review_required = True
        local_warnings.append("Suggested correction pages require human review before trusted application")
    if mode == CorrectionMode.VISION:
        review_required = True
        local_warnings.append("Vision correction detections require manual review")
    if not correction_map:
        review_required = True
        local_warnings.append("No corrections were extracted")
    if corrected_count < total:
        review_required = True
        local_warnings.append(f"{total - corrected_count} QCM(s) remain without corrections")
    status = QualityStatus.MANUAL_REVIEW_REQUIRED if review_required else QualityStatus.PASSED
    return Step3CorrectionQuality(
        status=status,
        total_qcms=total,
        corrected_count=corrected_count,
        coverage_ratio=round(coverage, 4),
        manual_review_required=review_required,
        warnings=tuple(dict.fromkeys(local_warnings)),
    )


def _prompt_id(mode: CorrectionMode) -> str:
    if mode == CorrectionMode.PAGE_DETECTION:
        return STEP3_PAGE_DETECTION_PROMPT_ID
    if mode == CorrectionMode.VISION:
        return STEP3_VISION_PROMPT_ID
    return STEP3_AUTO_DETECTION_PROMPT_ID


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _xlsx_placeholder_bytes(qcms: list[dict[str, Any]]) -> bytes:
    columns = ["Num", "Text", "A", "B", "C", "D", "E", "Correct"]
    rows = [",".join(columns)]
    for qcm in qcms:
        values = []
        for column in columns:
            value = qcm.get(column, "")
            escaped = str(value).replace('"', '""')
            values.append(f'"{escaped}"')
        rows.append(",".join(values))
    return ("\n".join(rows) + "\n").encode("utf-8")
