"""Worker handler for AI Auto Run planning and evaluation tasks."""

from typing import Any

from qcm_application.ai_autorun_service import AiAutoRunService
from qcm_shared.ai_autorun_contracts import AI_AUTORUN_TASK_KIND, AiAutoRunPageInput, AiAutoRunStartCommand
from qcm_shared.contracts import TaskStatus
from qcm_shared.provider_contracts import ModelSelection, ProviderKey
from qcm_worker.handlers import TASK_HANDLERS, register_handler


def _command_from_payload(payload: dict[str, Any]) -> AiAutoRunStartCommand:
    model = payload.get("model_selection") or {}
    return AiAutoRunStartCommand(
        user_id=payload.get("user_id", ""),
        project_id=payload.get("project_id", ""),
        run_id=payload.get("run_id", ""),
        ai_run_id=payload.get("ai_run_id", ""),
        pages=tuple(
            AiAutoRunPageInput(
                page_number=int(item.get("page_number", 0)),
                text=item.get("text", ""),
                source_artifact_id=item.get("source_artifact_id"),
            )
            for item in payload.get("pages") or ()
        ),
        model_selection=ModelSelection(
            provider=ProviderKey(model.get("provider", "openrouter")),
            primary_model_id=model.get("primary_model_id", "configured-by-admin"),
            fallback_model_ids=tuple(model.get("fallback_model_ids") or ()),
        ),
        idempotency_key=payload.get("idempotency_key", payload.get("ai_run_id", "")),
        correlation_id=payload.get("correlation_id", payload.get("ai_run_id", "")),
        user_constraints=dict(payload.get("user_constraints") or {}),
    )


def ai_autorun_handler(payload: dict[str, Any]) -> dict[str, Any]:
    result = AiAutoRunService().plan(_command_from_payload(payload))
    status = (
        TaskStatus.COMPLETED_WITH_WARNINGS.value
        if result.warnings or result.status.value == "manual_intervention_required"
        else TaskStatus.COMPLETED.value
    )
    if result.safe_stop_reason:
        status = TaskStatus.FAILED.value
    return {
        "status": status,
        "message": "AI Auto Run plan evaluated",
        "result": {
            "ai_run_id": result.ai_run_id,
            "ai_status": result.status.value,
            "artifact_ids": list(result.artifact_ids),
            "warnings": list(result.warnings),
            "safe_stop_reason": result.safe_stop_reason,
        },
    }


def register_ai_autorun_handler() -> None:
    if AI_AUTORUN_TASK_KIND not in TASK_HANDLERS:
        register_handler(AI_AUTORUN_TASK_KIND, ai_autorun_handler)
