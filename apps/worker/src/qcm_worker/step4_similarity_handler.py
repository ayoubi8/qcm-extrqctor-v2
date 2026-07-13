"""Worker handler for future Step 4 similarity match tasks."""

from typing import Any

from qcm_application.steps.step4_similarity_service import InMemoryStep4ArtifactSink, Step4SimilarityService
from qcm_shared.contracts import QualityStatus, TaskStatus
from qcm_shared.step4_contracts import STEP4_TASK_KIND, Step4SimilarityConfig, Step4SimilarityRunCommand
from qcm_worker.handlers import TASK_HANDLERS, register_handler


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _config_from_payload(payload: dict[str, Any]) -> Step4SimilarityConfig:
    raw = payload.get("config") or {}
    return Step4SimilarityConfig(
        reference_db_id=raw.get("reference_db_id", ""),
        mode=raw.get("mode", "text_only"),
        threshold=float(raw.get("threshold", 0.75)),
        text_weight=float(raw.get("text_weight", 0.7)),
        correction_weight=float(raw.get("correction_weight", 0.3)),
        color_green=float(raw.get("color_green", 0.90)),
        color_yellow=float(raw.get("color_yellow", 0.75)),
        export_existing=bool(raw.get("export_existing", False)),
        export_min_similarity=_optional_float(raw.get("export_min_similarity")),
        export_max_similarity=_optional_float(raw.get("export_max_similarity")),
        export_qcm_ids=tuple(str(item) for item in raw.get("export_qcm_ids") or ()),
    )


def step4_similarity_handler(payload: dict[str, Any]) -> dict[str, Any]:
    sink = InMemoryStep4ArtifactSink()
    command = Step4SimilarityRunCommand(
        user_id=payload.get("user_id", ""),
        project_id=payload.get("project_id", ""),
        run_id=payload.get("run_id", ""),
        source_artifact_ids=tuple(payload.get("source_artifact_ids") or ()),
        source_qcms=tuple(dict(item) for item in payload.get("source_qcms") or ()),
        reference_qcms=tuple(dict(item) for item in payload.get("reference_qcms") or ()),
        existing_matches=tuple(dict(item) for item in payload.get("existing_matches") or ()),
        config=_config_from_payload(payload),
        task_id=payload.get("task_id"),
        attempt_id=payload.get("attempt_id"),
        correlation_id=payload.get("correlation_id"),
    )
    result = Step4SimilarityService(artifact_sink=sink).run(command)
    status = (
        TaskStatus.COMPLETED_WITH_WARNINGS.value
        if result.quality.status == QualityStatus.PASSED_WITH_WARNINGS
        else TaskStatus.COMPLETED.value
    )
    return {
        "status": status,
        "message": "Step 4 similarity matching completed",
        "result": {
            "quality_status": result.quality.status.value,
            "mode": result.summary.mode,
            "matched_qcms": result.summary.matched_qcms,
            "average_similarity": result.summary.average_similarity,
            "artifact_count": len(result.artifact_ids),
            "exported_count": len(result.exported_matches),
        },
    }


def register_step4_similarity_handler() -> None:
    if STEP4_TASK_KIND not in TASK_HANDLERS:
        register_handler(STEP4_TASK_KIND, step4_similarity_handler)
