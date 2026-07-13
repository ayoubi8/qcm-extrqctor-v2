"""Visible Step 2 orchestrator for the old Step 2-5 internal cycles."""

from dataclasses import asdict, dataclass
import json
from typing import Any, Protocol

from qcm_application.artifact_service import checksum_bytes
from qcm_application.steps.step2_finalize import Step2FinalizeService
from qcm_application.steps.step2_format import Step2FormatService, format_result_payload
from qcm_application.steps.step2_metadata import Step2MetadataService, metadata_result_payload
from qcm_application.steps.step2_pages import Step2PageCycleService
from qcm_domain.enums import InternalCycleKey
from qcm_domain.steps.step2_contracts import COMBINED_STEP2_CYCLE_ORDER, cycles_from
from qcm_shared.contracts import ArtifactType, QualityStatus, RetentionPolicy, TerminalEventType, TerminalLevel
from qcm_shared.step2_contracts import (
    STEP2_SCHEMA_VERSION,
    Step2CycleSummary,
    Step2QualitySummary,
    Step2Result,
    Step2RunCommand,
)
from qcm_shared.storage_contracts import ArtifactWriteRequest
from qcm_shared.task_contracts import TerminalEventCreate


class Step2ArtifactSink(Protocol):
    def write(self, request: ArtifactWriteRequest) -> str:
        ...


class Step2TerminalSink(Protocol):
    def append(self, event: TerminalEventCreate) -> Any:
        ...


@dataclass(frozen=True, slots=True)
class Step2ArtifactRecord:
    artifact_id: str
    request: ArtifactWriteRequest


class InMemoryStep2ArtifactSink:
    def __init__(self) -> None:
        self.records: list[Step2ArtifactRecord] = []

    def write(self, request: ArtifactWriteRequest) -> str:
        self.records.append(Step2ArtifactRecord(artifact_id=request.artifact_id, request=request))
        return request.artifact_id


@dataclass(slots=True)
class Step2WorkingState:
    qcms: list[dict[str, Any]]
    template: dict[str, Any] | None
    formatted_qcms: list[dict[str, Any]]
    artifact_ids: list[str]
    metadata_provenance: list[dict[str, Any]]
    clinical_groups: list[dict[str, Any]]
    template_validation: dict[str, Any] | None = None
    final_json_artifact_id: str | None = None
    final_xlsx_artifact_id: str | None = None


class Step2Orchestrator:
    def __init__(
        self,
        *,
        artifact_sink: Step2ArtifactSink | None = None,
        terminal_sink: Step2TerminalSink | None = None,
        page_cycle_service: Step2PageCycleService | None = None,
        metadata_service: Step2MetadataService | None = None,
        format_service: Step2FormatService | None = None,
        finalize_service: Step2FinalizeService | None = None,
    ) -> None:
        self.artifact_sink = artifact_sink
        self.terminal_sink = terminal_sink
        self.page_cycle_service = page_cycle_service or Step2PageCycleService()
        self.metadata_service = metadata_service or Step2MetadataService()
        self.format_service = format_service or Step2FormatService()
        self.finalize_service = finalize_service or Step2FinalizeService()

    def run(self, command: Step2RunCommand) -> Step2Result:
        _validate_entry(command)
        self._emit(command, TerminalLevel.INFO, TerminalEventType.STEP_STARTED, "Combined Step 2 started")
        state = _initial_state(command)
        cycle_summaries: list[Step2CycleSummary] = []

        if command.config.resume_from_cycle:
            cycle_summaries.extend(_preserved_cycle_summaries(command.config.resume_from_cycle, command.previous_cycle_data))

        for cycle in cycles_from(command.config.resume_from_cycle):
            self._emit(
                command,
                TerminalLevel.INFO,
                TerminalEventType.SYSTEM_MESSAGE,
                "Step 2 internal cycle started",
                {"internal_cycle": cycle.value},
            )
            summary = self._run_cycle(command, state, cycle)
            cycle_summaries.append(summary)
            self._emit(
                command,
                TerminalLevel.SUCCESS if not summary.warnings else TerminalLevel.WARNING,
                TerminalEventType.SYSTEM_MESSAGE,
                "Step 2 internal cycle completed",
                {"internal_cycle": cycle.value, "qcm_count": summary.qcm_count},
            )

        quality = _quality_summary(command, state, cycle_summaries)
        result = Step2Result(
            user_id=command.user_id,
            project_id=command.project_id,
            run_id=command.run_id,
            cycles=tuple(cycle_summaries),
            quality=quality,
            qcms=tuple(state.formatted_qcms or state.qcms),
            artifact_ids=tuple(state.artifact_ids),
            final_json_artifact_id=state.final_json_artifact_id,
            final_xlsx_artifact_id=state.final_xlsx_artifact_id,
        )
        quality_artifact_id = self._write_quality_report(command, result)
        state.artifact_ids.append(quality_artifact_id)
        level = TerminalLevel.WARNING if quality.warnings else TerminalLevel.SUCCESS
        self._emit(
            command,
            level,
            TerminalEventType.STEP_COMPLETED,
            "Combined Step 2 completed",
            {"quality_status": quality.status.value, "total_qcms": quality.total_qcms},
        )
        return Step2Result(
            user_id=result.user_id,
            project_id=result.project_id,
            run_id=result.run_id,
            cycles=result.cycles,
            quality=result.quality,
            qcms=result.qcms,
            artifact_ids=tuple(state.artifact_ids),
            final_json_artifact_id=result.final_json_artifact_id,
            final_xlsx_artifact_id=result.final_xlsx_artifact_id,
        )

    def _run_cycle(
        self,
        command: Step2RunCommand,
        state: Step2WorkingState,
        cycle: InternalCycleKey,
    ) -> Step2CycleSummary:
        if cycle == InternalCycleKey.STEP2_QCM_PAGES:
            return self._run_qcm_pages(command, state)
        if cycle == InternalCycleKey.STEP2_METADATA:
            return self._run_metadata(command, state)
        if cycle == InternalCycleKey.STEP2_FORMAT:
            return self._run_format(command, state)
        if cycle == InternalCycleKey.STEP2_FINALIZE:
            return self._run_finalize(command, state)
        raise ValueError(f"Unsupported combined Step 2 cycle: {cycle.value}")

    def _run_qcm_pages(self, command: Step2RunCommand, state: Step2WorkingState) -> Step2CycleSummary:
        page_cycle = self.page_cycle_service.run(command)
        artifact_ids: list[str] = []
        for output in page_cycle.page_outputs:
            artifact_ids.append(
                self._write_artifact(
                    command,
                    artifact_id=f"{command.run_id}-step2-page-{output.page_number:04d}-qcms",
                    artifact_type=ArtifactType.STEP2_PAGE_QCM_JSON,
                    filename=f"page-{output.page_number:04d}-qcms.json",
                    content_type="application/json",
                    content=_json_bytes(asdict(output)),
                    retention_policy=RetentionPolicy.INTERMEDIATE_CLEANUP,
                )
            )
        if not page_cycle.qcms:
            raise ValueError("Combined Step 2 requires at least one QCM candidate from Step 1 text")
        state.qcms = [dict(qcm) for qcm in page_cycle.qcms]
        state.artifact_ids.extend(artifact_ids)
        return Step2CycleSummary(
            cycle_key=InternalCycleKey.STEP2_QCM_PAGES.value,
            status="completed_with_warnings" if page_cycle.warnings else "completed",
            qcm_count=len(state.qcms),
            artifact_ids=tuple(artifact_ids),
            warnings=page_cycle.warnings,
        )

    def _run_metadata(self, command: Step2RunCommand, state: Step2WorkingState) -> Step2CycleSummary:
        _require_qcms(state, InternalCycleKey.STEP2_METADATA)
        result = self.metadata_service.run(command, state.qcms)
        state.qcms = [dict(qcm) for qcm in result.qcms]
        state.metadata_provenance = [asdict(item) for item in result.provenance]
        state.clinical_groups = [asdict(item) for item in result.clinical_groups]
        artifact_id = self._write_debug_cycle_artifact(command, InternalCycleKey.STEP2_METADATA, metadata_result_payload(result))
        state.artifact_ids.append(artifact_id)
        return Step2CycleSummary(
            cycle_key=InternalCycleKey.STEP2_METADATA.value,
            status="completed_with_warnings" if result.warnings else "completed",
            qcm_count=len(state.qcms),
            artifact_ids=(artifact_id,),
            warnings=result.warnings,
        )

    def _run_format(self, command: Step2RunCommand, state: Step2WorkingState) -> Step2CycleSummary:
        _require_qcms(state, InternalCycleKey.STEP2_FORMAT)
        result = self.format_service.run(command, state.qcms)
        state.template = dict(result.template)
        state.formatted_qcms = [dict(qcm) for qcm in result.formatted_qcms]
        state.template_validation = asdict(result.validation)
        artifact_id = self._write_debug_cycle_artifact(command, InternalCycleKey.STEP2_FORMAT, format_result_payload(result))
        state.artifact_ids.append(artifact_id)
        return Step2CycleSummary(
            cycle_key=InternalCycleKey.STEP2_FORMAT.value,
            status="completed_with_warnings" if result.warnings else "completed",
            qcm_count=len(state.qcms),
            artifact_ids=(artifact_id,),
            warnings=result.warnings,
        )

    def _run_finalize(self, command: Step2RunCommand, state: Step2WorkingState) -> Step2CycleSummary:
        _require_qcms(state, InternalCycleKey.STEP2_FINALIZE)
        if not state.formatted_qcms:
            state.formatted_qcms = [dict(qcm) for qcm in self.format_service.run(command, state.qcms).formatted_qcms]
        result = self.finalize_service.run(command, state.formatted_qcms)
        state.formatted_qcms = [dict(qcm) for qcm in result.final_qcms]
        final_json_id = self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step2-final-json",
            artifact_type=ArtifactType.STEP2_FINAL_JSON,
            filename="combined-step2-final.json",
            content_type="application/json",
            content=result.final_json_content,
            retention_policy=RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        )
        state.final_json_artifact_id = final_json_id
        state.artifact_ids.append(final_json_id)
        artifact_ids = [final_json_id]
        if result.final_xlsx_content is not None:
            final_xlsx_id = self._write_artifact(
                command,
                artifact_id=f"{command.run_id}-step2-final-xlsx",
                artifact_type=ArtifactType.STEP2_FINAL_XLSX,
                filename="combined-step2-final.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                content=result.final_xlsx_content,
                retention_policy=RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
            )
            state.final_xlsx_artifact_id = final_xlsx_id
            state.artifact_ids.append(final_xlsx_id)
            artifact_ids.append(final_xlsx_id)
        return Step2CycleSummary(
            cycle_key=InternalCycleKey.STEP2_FINALIZE.value,
            status="completed_with_warnings" if result.warnings else "completed",
            qcm_count=len(state.formatted_qcms),
            artifact_ids=tuple(artifact_ids),
            warnings=result.warnings,
        )

    def _write_quality_report(self, command: Step2RunCommand, result: Step2Result) -> str:
        payload = {
            "quality": asdict(result.quality) | {"status": result.quality.status.value},
            "cycles": [asdict(cycle) for cycle in result.cycles],
        }
        artifact_id = self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step2-quality-report",
            artifact_type=ArtifactType.DEBUG_INTERNAL,
            filename="combined-step2-quality-report.json",
            content_type="application/json",
            content=_json_bytes(payload),
            retention_policy=RetentionPolicy.DEBUG_SHORT_LIVED,
        )
        result_artifacts = result.artifact_ids
        if artifact_id not in result_artifacts:
            # Keep artifact order centralized in state for the returned value.
            pass
        return artifact_id

    def _write_debug_cycle_artifact(self, command: Step2RunCommand, cycle: InternalCycleKey, payload: Any) -> str:
        return self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-{cycle.value}",
            artifact_type=ArtifactType.DEBUG_INTERNAL,
            filename=f"{cycle.value}.json",
            content_type="application/json",
            content=_json_bytes(payload),
            retention_policy=RetentionPolicy.DEBUG_SHORT_LIVED,
        )

    def _write_artifact(
        self,
        command: Step2RunCommand,
        *,
        artifact_id: str,
        artifact_type: ArtifactType,
        filename: str,
        content_type: str,
        content: bytes,
        retention_policy: RetentionPolicy,
        version_number: int = 1,
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
            version_number=version_number,
            checksum=checksum_bytes(content),
            schema_version=STEP2_SCHEMA_VERSION,
            retention_policy=retention_policy,
            source_artifact_ids=list(command.step1_artifact_ids),
        )
        if self.artifact_sink is not None:
            return self.artifact_sink.write(request)
        return request.artifact_id

    def _emit(
        self,
        command: Step2RunCommand,
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


def _validate_entry(command: Step2RunCommand) -> None:
    if not command.user_id or not command.project_id or not command.run_id:
        raise ValueError("Combined Step 2 requires owner, project, and run identifiers")
    if not command.step1_artifact_ids:
        raise ValueError("Combined Step 2 requires completed Step 1 artifact identifiers")
    if not command.pages:
        raise ValueError("Combined Step 2 requires Step 1 page text")
    if command.config.resume_from_cycle:
        cycles_from(command.config.resume_from_cycle)


def _initial_state(command: Step2RunCommand) -> Step2WorkingState:
    previous = command.previous_cycle_data
    return Step2WorkingState(
        qcms=[dict(item) for item in previous.get("qcms", [])],
        template=dict(previous["template"]) if isinstance(previous.get("template"), dict) else None,
        formatted_qcms=[dict(item) for item in previous.get("formatted_qcms", [])],
        artifact_ids=list(previous.get("artifact_ids", [])),
        metadata_provenance=[dict(item) for item in previous.get("metadata_provenance", [])],
        clinical_groups=[dict(item) for item in previous.get("clinical_groups", [])],
        template_validation=dict(previous["template_validation"]) if isinstance(previous.get("template_validation"), dict) else None,
        final_json_artifact_id=previous.get("final_json_artifact_id"),
        final_xlsx_artifact_id=previous.get("final_xlsx_artifact_id"),
    )


def _preserved_cycle_summaries(resume_from_cycle: str, previous_cycle_data: dict[str, Any]) -> list[Step2CycleSummary]:
    start = cycles_from(resume_from_cycle)[0]
    summaries: list[Step2CycleSummary] = []
    for cycle in COMBINED_STEP2_CYCLE_ORDER:
        if cycle == start:
            break
        summaries.append(
            Step2CycleSummary(
                cycle_key=cycle.value,
                status="preserved",
                qcm_count=len(previous_cycle_data.get("qcms", [])),
                artifact_ids=tuple(previous_cycle_data.get("artifact_ids", [])),
            )
        )
    return summaries


def _require_qcms(state: Step2WorkingState, cycle: InternalCycleKey) -> None:
    if not state.qcms:
        raise ValueError(f"{cycle.value} requires QCM candidates from the page extraction cycle")


def _quality_summary(
    command: Step2RunCommand,
    state: Step2WorkingState,
    cycles: list[Step2CycleSummary],
) -> Step2QualitySummary:
    warnings: list[str] = []
    failures: list[str] = []
    for cycle in cycles:
        warnings.extend(cycle.warnings)
        if cycle.failure:
            failures.append(cycle.failure)
    if not state.final_json_artifact_id:
        failures.append("Combined Step 2 did not produce final JSON")
    status = QualityStatus.FAILED if failures else QualityStatus.PASSED_WITH_WARNINGS if warnings else QualityStatus.PASSED
    return Step2QualitySummary(
        status=status,
        total_pages=len(command.pages),
        total_qcms=len(state.formatted_qcms or state.qcms),
        warnings=tuple(dict.fromkeys(warnings)),
        failures=tuple(dict.fromkeys(failures)),
    )


def _default_template() -> dict[str, Any]:
    return {
        "Num": 0,
        "Text": "",
        "A": "",
        "B": "",
        "C": "",
        "D": "",
        "E": "",
        "Correct": "",
        "Year": "",
        "categoryName": "",
        "subcategoryName": "",
        "Source": "",
        "Tag": [],
        "Cas": "",
    }


def _map_to_template(qcm: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    mapped = dict(template)
    field_map = {
        "Num": ("number", "Num", "id", "num"),
        "Text": ("text", "Text", "question", "questionText"),
        "Correct": ("correction", "Correct", "answer"),
        "categoryName": ("module", "categoryName", "module_detected"),
        "subcategoryName": ("subcategory", "subcategoryName"),
        "Year": ("year", "Year"),
        "Source": ("source", "Source"),
        "Tag": ("tag", "Tag"),
        "Cas": ("cas", "Cas", "clinical_case"),
    }
    for target, candidates in field_map.items():
        if target not in mapped:
            continue
        for source in candidates:
            value = qcm.get(source)
            if value not in (None, "", []):
                mapped[target] = value
                break
    propositions = qcm.get("propositions") or {}
    for key in ("A", "B", "C", "D", "E"):
        if key in mapped:
            mapped[key] = qcm.get(key) or propositions.get(key) or propositions.get(key.lower()) or mapped[key]
    cas_value = qcm.get("cas") or qcm.get("Cas")
    if cas_value and "Cas" not in mapped:
        mapped["Cas"] = cas_value
    return mapped


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _xlsx_placeholder_bytes(qcms: list[dict[str, Any]]) -> bytes:
    rows = ["Num,Text"]
    for qcm in qcms:
        text = str(qcm.get("Text", "")).replace('"', '""')
        rows.append(f'{qcm.get("Num", "")},"{text}"')
    return ("\n".join(rows) + "\n").encode("utf-8")
