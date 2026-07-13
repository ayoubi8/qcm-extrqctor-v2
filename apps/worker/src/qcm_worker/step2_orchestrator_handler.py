"""Worker handler for the combined visible Step 2 orchestrator."""

from typing import Any

from qcm_application.steps.step2_orchestrator import InMemoryStep2ArtifactSink, Step2Orchestrator
from qcm_shared.contracts import QualityStatus, TaskStatus
from qcm_shared.step2_contracts import (
    STEP2_TASK_KIND,
    Step2Config,
    Step2ModelConfig,
    Step2RunCommand,
    Step2SourcePage,
)
from qcm_worker.handlers import TASK_HANDLERS, register_handler


def _config_from_payload(payload: dict[str, Any]) -> Step2Config:
    raw = payload.get("config") or {}
    model = raw.get("model") or {}
    return Step2Config(
        page_batch_size=int(raw.get("page_batch_size", 0)),
        internal_page_concurrency=int(raw.get("internal_page_concurrency", 5)),
        extraction_prompt_id=raw.get("extraction_prompt_id", "step2.page_qcm_extraction.v1"),
        metadata_defaults=dict(raw.get("metadata_defaults") or {}),
        metadata_strategies=dict(raw.get("metadata_strategies") or {}),
        legacy_subcategory_policy=raw.get("legacy_subcategory_policy", "preserve_internal"),
        template_name=raw.get("template_name", "default"),
        template_overrides=dict(raw.get("template_overrides") or {}),
        output_format=raw.get("output_format", "json+xlsx"),
        model=Step2ModelConfig(
            provider=model.get("provider", "openrouter"),
            primary_model_id=model.get("primary_model_id", "configured-by-admin"),
            fallback_model_ids=tuple(model.get("fallback_model_ids") or ()),
        ),
        resume_from_cycle=raw.get("resume_from_cycle"),
    )


def _pages_from_payload(payload: dict[str, Any]) -> tuple[Step2SourcePage, ...]:
    pages = []
    for item in payload.get("pages") or []:
        pages.append(
            Step2SourcePage(
                page_number=int(item.get("page_number", item.get("page", 0))),
                text=item.get("text", ""),
                source_artifact_id=item.get("source_artifact_id"),
            )
        )
    return tuple(pages)


def step2_orchestrator_handler(payload: dict[str, Any]) -> dict[str, Any]:
    sink = InMemoryStep2ArtifactSink()
    command = Step2RunCommand(
        user_id=payload.get("user_id", ""),
        project_id=payload.get("project_id", ""),
        run_id=payload.get("run_id", ""),
        step1_artifact_ids=tuple(payload.get("step1_artifact_ids") or ()),
        pages=_pages_from_payload(payload),
        config=_config_from_payload(payload),
        previous_cycle_data=dict(payload.get("previous_cycle_data") or {}),
        task_id=payload.get("task_id"),
        attempt_id=payload.get("attempt_id"),
        correlation_id=payload.get("correlation_id"),
    )
    result = Step2Orchestrator(artifact_sink=sink).run(command)
    status = (
        TaskStatus.COMPLETED_WITH_WARNINGS.value
        if result.quality.status in {QualityStatus.PASSED_WITH_WARNINGS, QualityStatus.MANUAL_REVIEW_REQUIRED}
        else TaskStatus.COMPLETED.value
    )
    return {
        "status": status,
        "message": "Combined Step 2 completed",
        "result": {
            "quality_status": result.quality.status.value,
            "total_qcms": result.quality.total_qcms,
            "cycle_count": len(result.cycles),
            "artifact_count": len(result.artifact_ids),
        },
    }


def register_step2_orchestrator_handler() -> None:
    if STEP2_TASK_KIND not in TASK_HANDLERS:
        register_handler(STEP2_TASK_KIND, step2_orchestrator_handler)
