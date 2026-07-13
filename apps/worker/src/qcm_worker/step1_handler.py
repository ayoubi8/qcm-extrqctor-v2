"""Worker handler for Step 1 extraction tasks."""

from typing import Any

from qcm_application.steps.step1_service import InMemoryStep1ArtifactSink, Step1Service
from qcm_infrastructure.pdf import FakeOcrEngine, FakePdfTextExtractor, IdentityTextQualityFixer
from qcm_shared.contracts import QualityStatus, TaskStatus
from qcm_shared.step1_contracts import STEP1_TASK_KIND, Step1Config, Step1RunCommand
from qcm_worker.handlers import TASK_HANDLERS, register_handler


def build_step1_service(payload: dict[str, Any], artifact_sink: InMemoryStep1ArtifactSink | None = None) -> Step1Service:
    direct_pages = payload.get("direct_pages") or payload.get("pages") or []
    ocr_pages = payload.get("ocr_pages") or {}
    if isinstance(direct_pages, dict):
        direct_pages = {int(page): text for page, text in direct_pages.items()}
    if isinstance(ocr_pages, dict):
        ocr_pages = {int(page): text for page, text in ocr_pages.items()}
    return Step1Service(
        extractor=FakePdfTextExtractor(direct_pages),
        ocr=FakeOcrEngine(ocr_pages),
        text_fixer=IdentityTextQualityFixer(),
        artifact_sink=artifact_sink or InMemoryStep1ArtifactSink(),
    )


def step1_handler(payload: dict[str, Any]) -> dict[str, Any]:
    config_payload = payload.get("config") or {}
    source = payload.get("source_content", b"")
    if isinstance(source, str):
        source = source.encode("utf-8")
    command = Step1RunCommand(
        user_id=payload.get("user_id", ""),
        project_id=payload.get("project_id", ""),
        run_id=payload.get("run_id", ""),
        source_file_id=payload.get("source_file_id", "source-pdf"),
        source_filename=payload.get("source_filename", "source.pdf"),
        source_content=source,
        config=Step1Config(
            extraction_mode=config_payload.get("extraction_mode", "automatic"),
            override_reason=config_payload.get("override_reason"),
            page_range_start=config_payload.get("page_range_start"),
            page_range_end=config_payload.get("page_range_end"),
            text_fixer_enabled=bool(config_payload.get("text_fixer_enabled", True)),
            text_fixer_model=config_payload.get("text_fixer_model"),
        ),
        task_id=payload.get("task_id"),
        attempt_id=payload.get("attempt_id"),
        correlation_id=payload.get("correlation_id"),
    )
    sink = InMemoryStep1ArtifactSink()
    result = build_step1_service(payload, sink).run(command)
    task_status = (
        TaskStatus.COMPLETED_WITH_WARNINGS.value
        if result.quality.status in {QualityStatus.PASSED_WITH_WARNINGS, QualityStatus.MANUAL_REVIEW_REQUIRED}
        else TaskStatus.COMPLETED.value
    )
    return {
        "status": task_status,
        "message": "Step 1 extraction completed",
        "result": {
            "resolved_mode": result.detection.resolved_mode,
            "quality_status": result.quality.status.value,
            "artifact_count": len(result.artifact_ids),
        },
    }


def register_step1_handler() -> None:
    if STEP1_TASK_KIND not in TASK_HANDLERS:
        register_handler(STEP1_TASK_KIND, step1_handler)
