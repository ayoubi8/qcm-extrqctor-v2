"""Worker handler for future Step 3 correction tasks."""

from typing import Any

from qcm_application.steps.step3_correction_service import InMemoryStep3ArtifactSink, Step3CorrectionService
from qcm_domain.corrections import parse_page_selection
from qcm_shared.contracts import QualityStatus, TaskStatus
from qcm_shared.step3_contracts import (
    STEP3_TASK_KIND,
    Step3CorrectionConfig,
    Step3CorrectionPage,
    Step3CorrectionRunCommand,
)
from qcm_worker.handlers import TASK_HANDLERS, register_handler


def _config_from_payload(payload: dict[str, Any]) -> Step3CorrectionConfig:
    raw = payload.get("config") or {}
    return Step3CorrectionConfig(
        mode=raw.get("mode", "page_detection"),
        selected_pages=parse_page_selection(raw.get("selected_pages") or raw.get("pages")),
        candidate_threshold=int(raw.get("candidate_threshold", 15)),
        include_neighbors=bool(raw.get("include_neighbors", True)),
        force_overwrite=bool(raw.get("force_overwrite", False)),
        vision_guide=raw.get("vision_guide"),
        vision_detections=dict(raw.get("vision_detections") or {}),
        model=dict(raw.get("model") or {}),
    )


def _pages_from_payload(payload: dict[str, Any]) -> tuple[Step3CorrectionPage, ...]:
    return tuple(
        Step3CorrectionPage(
            page_number=int(item.get("page_number", item.get("page", 0))),
            text=item.get("text", ""),
            source_artifact_id=item.get("source_artifact_id"),
        )
        for item in payload.get("pages") or ()
    )


def step3_correction_handler(payload: dict[str, Any]) -> dict[str, Any]:
    sink = InMemoryStep3ArtifactSink()
    command = Step3CorrectionRunCommand(
        user_id=payload.get("user_id", ""),
        project_id=payload.get("project_id", ""),
        run_id=payload.get("run_id", ""),
        step2_artifact_ids=tuple(payload.get("step2_artifact_ids") or ()),
        qcms=tuple(dict(item) for item in payload.get("qcms") or ()),
        pages=_pages_from_payload(payload),
        config=_config_from_payload(payload),
        task_id=payload.get("task_id"),
        attempt_id=payload.get("attempt_id"),
        correlation_id=payload.get("correlation_id"),
    )
    result = Step3CorrectionService(artifact_sink=sink).run(command)
    status = (
        TaskStatus.COMPLETED_WITH_WARNINGS.value
        if result.quality.status in {QualityStatus.PASSED_WITH_WARNINGS, QualityStatus.MANUAL_REVIEW_REQUIRED}
        else TaskStatus.COMPLETED.value
    )
    return {
        "status": status,
        "message": "Step 3 correction completed",
        "result": {
            "mode": result.mode,
            "quality_status": result.quality.status.value,
            "corrected_count": result.quality.corrected_count,
            "coverage_ratio": result.quality.coverage_ratio,
            "artifact_count": len(result.artifact_ids),
        },
    }


def register_step3_correction_handler() -> None:
    if STEP3_TASK_KIND not in TASK_HANDLERS:
        register_handler(STEP3_TASK_KIND, step3_correction_handler)
