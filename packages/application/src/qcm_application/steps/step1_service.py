"""Step 1 ingestion, extraction, OCR routing, text repair, and artifact orchestration."""

from dataclasses import asdict, dataclass
import json
from typing import Any, Protocol

from qcm_application.artifact_service import checksum_bytes
from qcm_domain.artifacts import validate_source_file_size
from qcm_domain.documents import (
    PageExtractionMethod,
    classify_page_text,
    resolve_extraction_plan,
)
from qcm_shared.contracts import ArtifactType, QualityStatus, RetentionPolicy, TerminalEventType, TerminalLevel
from qcm_shared.step1_contracts import (
    STEP1_SCHEMA_VERSION,
    Step1Config,
    Step1DetectionSummary,
    Step1PageResult,
    Step1QualitySummary,
    Step1Result,
    Step1RunCommand,
)
from qcm_shared.storage_contracts import ArtifactWriteRequest
from qcm_shared.task_contracts import TerminalEventCreate


class ExtractedPage(Protocol):
    page_number: int
    text: str


class PdfTextExtractor(Protocol):
    def extract_pages(
        self,
        source_content: bytes,
        *,
        page_range: tuple[int, int] | None = None,
    ) -> tuple[ExtractedPage, ...]:
        ...


class OcrEngine(Protocol):
    def extract_page_text(self, source_content: bytes, *, page_number: int) -> str:
        ...


class TextRepairResult(Protocol):
    text: str
    warnings: tuple[str, ...]


class TextQualityFixer(Protocol):
    def repair(self, text: str, *, page_number: int, model_id: str | None = None) -> TextRepairResult:
        ...


class Step1ArtifactSink(Protocol):
    def write(self, request: ArtifactWriteRequest) -> str:
        ...


class Step1TerminalSink(Protocol):
    def append(self, event: TerminalEventCreate) -> Any:
        ...


@dataclass(frozen=True, slots=True)
class Step1ArtifactRecord:
    artifact_id: str
    request: ArtifactWriteRequest


class InMemoryStep1ArtifactSink:
    def __init__(self) -> None:
        self.records: list[Step1ArtifactRecord] = []

    def write(self, request: ArtifactWriteRequest) -> str:
        self.records.append(Step1ArtifactRecord(artifact_id=request.artifact_id, request=request))
        return request.artifact_id


class Step1Service:
    def __init__(
        self,
        *,
        extractor: PdfTextExtractor,
        ocr: OcrEngine,
        text_fixer: TextQualityFixer,
        artifact_sink: Step1ArtifactSink | None = None,
        terminal_sink: Step1TerminalSink | None = None,
    ) -> None:
        self.extractor = extractor
        self.ocr = ocr
        self.text_fixer = text_fixer
        self.artifact_sink = artifact_sink
        self.terminal_sink = terminal_sink

    def run(self, command: Step1RunCommand) -> Step1Result:
        validate_source_file_size(len(command.source_content))
        self._emit(command, TerminalLevel.INFO, TerminalEventType.STEP_STARTED, "Step 1 extraction started")

        page_range = _page_range(command.config)
        extracted_pages = self.extractor.extract_pages(command.source_content, page_range=page_range)
        if not extracted_pages:
            raise ValueError("No pages were available for Step 1 extraction")

        signals = tuple(classify_page_text(page.page_number, page.text) for page in extracted_pages)
        detection = resolve_extraction_plan(
            signals,
            command.config.extraction_mode,
            override_reason=command.config.override_reason,
        )
        signal_by_page = {signal.page_number: signal for signal in signals}
        raw_by_page = {page.page_number: page.text for page in extracted_pages}

        pages: list[Step1PageResult] = []
        artifact_ids: list[str] = []
        for decision in detection.page_decisions:
            raw_text = raw_by_page[decision.page_number]
            if decision.method == PageExtractionMethod.OCR:
                raw_text = self.ocr.extract_page_text(command.source_content, page_number=decision.page_number)
            warnings: list[str] = []
            corrected_text = raw_text.strip()
            if command.config.text_fixer_enabled:
                repair = self.text_fixer.repair(
                    raw_text,
                    page_number=decision.page_number,
                    model_id=command.config.text_fixer_model,
                )
                corrected_text = repair.text
                warnings.extend(repair.warnings)
            if not corrected_text:
                warnings.append(f"Page {decision.page_number} produced no corrected text")

            page_result = Step1PageResult(
                page_number=decision.page_number,
                extraction_method=decision.method.value,
                raw_text=raw_text,
                corrected_text=corrected_text,
                meaningful_chars=signal_by_page[decision.page_number].meaningful_chars,
                warnings=tuple(warnings),
            )
            pages.append(page_result)
            artifact_ids.append(self._write_page_artifact(command, page_result))

        detection_summary = Step1DetectionSummary(
            requested_mode=detection.requested_mode.value,
            resolved_mode=detection.resolved_mode.value,
            manual_override=detection.manual_override,
            override_reason=detection.override_reason,
            page_decisions=tuple(asdict(decision) | {"method": decision.method.value} for decision in detection.page_decisions),
            warnings=detection.warnings,
        )
        quality = _quality_summary(pages, detection_summary)
        result = Step1Result(
            user_id=command.user_id,
            project_id=command.project_id,
            run_id=command.run_id,
            source_file_id=command.source_file_id,
            source_filename=command.source_filename,
            detection=detection_summary,
            quality=quality,
            pages=tuple(pages),
            artifact_ids=tuple(artifact_ids),
        )
        artifact_ids.extend(self._write_result_artifacts(command, result))
        final_result = Step1Result(
            user_id=result.user_id,
            project_id=result.project_id,
            run_id=result.run_id,
            source_file_id=result.source_file_id,
            source_filename=result.source_filename,
            detection=result.detection,
            quality=result.quality,
            pages=result.pages,
            artifact_ids=tuple(artifact_ids),
        )
        level = TerminalLevel.WARNING if quality.warnings else TerminalLevel.SUCCESS
        self._emit(
            command,
            level,
            TerminalEventType.STEP_COMPLETED,
            "Step 1 extraction completed",
            {"quality_status": quality.status.value, "resolved_mode": detection_summary.resolved_mode},
        )
        return final_result

    def _write_page_artifact(self, command: Step1RunCommand, page: Step1PageResult) -> str:
        content = page.corrected_text.encode("utf-8")
        return self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step1-page-{page.page_number:04d}",
            artifact_type=ArtifactType.PAGE_TEXT,
            filename=f"page-{page.page_number:04d}.txt",
            content_type="text/plain; charset=utf-8",
            content=content,
            retention_policy=RetentionPolicy.INTERMEDIATE_CLEANUP,
            version_number=1,
        )

    def _write_result_artifacts(self, command: Step1RunCommand, result: Step1Result) -> list[str]:
        return [
            self._write_artifact(
                command,
                artifact_id=f"{command.run_id}-step1-text",
                artifact_type=ArtifactType.STEP1_TEXT,
                filename="step1-corrected-text.txt",
                content_type="text/plain; charset=utf-8",
                content=result.combined_text.encode("utf-8"),
                retention_policy=RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
                version_number=1,
            ),
            self._write_artifact(
                command,
                artifact_id=f"{command.run_id}-step1-detection-report",
                artifact_type=ArtifactType.DEBUG_INTERNAL,
                filename="step1-detection-report.json",
                content_type="application/json",
                content=_json_bytes(asdict(result.detection)),
                retention_policy=RetentionPolicy.DEBUG_SHORT_LIVED,
                version_number=1,
            ),
            self._write_artifact(
                command,
                artifact_id=f"{command.run_id}-step1-quality-report",
                artifact_type=ArtifactType.DEBUG_INTERNAL,
                filename="step1-quality-report.json",
                content_type="application/json",
                content=_json_bytes(asdict(result.quality) | {"status": result.quality.status.value}),
                retention_policy=RetentionPolicy.DEBUG_SHORT_LIVED,
                version_number=1,
            ),
        ]

    def _write_artifact(
        self,
        command: Step1RunCommand,
        *,
        artifact_id: str,
        artifact_type: ArtifactType,
        filename: str,
        content_type: str,
        content: bytes,
        retention_policy: RetentionPolicy,
        version_number: int,
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
            schema_version=STEP1_SCHEMA_VERSION,
            retention_policy=retention_policy,
            source_artifact_ids=[command.source_file_id],
        )
        if self.artifact_sink is not None:
            return self.artifact_sink.write(request)
        return request.artifact_id

    def _emit(
        self,
        command: Step1RunCommand,
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


def _page_range(config: Step1Config) -> tuple[int, int] | None:
    if config.page_range_start is None and config.page_range_end is None:
        return None
    return (config.page_range_start or 1, config.page_range_end or config.page_range_start or 1)


def _quality_summary(pages: list[Step1PageResult], detection: Step1DetectionSummary) -> Step1QualitySummary:
    warnings = list(detection.warnings)
    failures: list[str] = []
    ocr_count = sum(1 for page in pages if page.extraction_method == "ocr")
    direct_count = len(pages) - ocr_count
    if ocr_count:
        warnings.append(f"OCR was used for {ocr_count} page(s); review extracted text quality")
    for page in pages:
        warnings.extend(page.warnings)
    total_chars = sum(len(page.corrected_text) for page in pages)
    if total_chars == 0:
        failures.append("Step 1 produced no corrected text")
    status = QualityStatus.FAILED if failures else QualityStatus.PASSED_WITH_WARNINGS if warnings else QualityStatus.PASSED
    return Step1QualitySummary(
        status=status,
        total_pages=len(pages),
        total_corrected_chars=total_chars,
        ocr_page_count=ocr_count,
        direct_page_count=direct_count,
        warnings=tuple(dict.fromkeys(warnings)),
        failures=tuple(failures),
    )


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
