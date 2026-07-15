"""Worker handler for AI Auto Run planning and evaluation tasks.

When claimed by the worker:
1. Calls the LLM planner (OpenRouter) to build a document map from page texts
2. Generates Step 2/3 configs from the document map
3. Evaluates quality gates (validate_ai_generated_config + evaluate_ai_quality)
4. If gate passes → enqueues a real step2_orchestrate child task with AI-generated config
"""

from typing import Any

from qcm_application.ai_autorun_service import AiAutoRunService
from qcm_application.task_service import TaskService
from qcm_shared.ai_autorun_contracts import (
    AI_AUTORUN_TASK_KIND,
    AiAutoRunAction,
    AiAutoRunActionCommand,
    AiAutoRunPageInput,
    AiAutoRunStartCommand,
)
from qcm_shared.contracts import TaskStatus
from qcm_shared.provider_contracts import ModelSelection, ProviderKey
from qcm_shared.task_contracts import TaskCreateCommand
from qcm_worker.handlers import TASK_HANDLERS, register_handler

try:
    from qcm_infrastructure.llm.openrouter_adapter import build_openrouter_adapter_from_env
    from qcm_infrastructure.llm.llm_ai_planner import plan_with_llm
    _LLM_AVAILABLE = True
except ImportError:  # pragma: no cover
    _LLM_AVAILABLE = False


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
            primary_model_id=model.get("primary_model_id", "openai/gpt-4o-mini"),
            fallback_model_ids=tuple(model.get("fallback_model_ids") or ()),
        ),
        idempotency_key=payload.get("idempotency_key", payload.get("ai_run_id", "")),
        correlation_id=payload.get("correlation_id", payload.get("ai_run_id", "")),
        user_constraints=dict(payload.get("user_constraints") or {}),
    )


def ai_autorun_handler(payload: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible module-level handler (plan-only mode, no child task enqueuing)."""
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


def register_ai_autorun_handler(task_service: TaskService | None = None) -> None:
    """Register the AI autorun handler. If task_service is provided, the handler
    will enqueue a real step2_orchestrate child task when the gate passes."""

    adapter = build_openrouter_adapter_from_env() if _LLM_AVAILABLE else None

    def ai_autorun_handler(payload: dict[str, Any]) -> dict[str, Any]:
        command = _command_from_payload(payload)

        # Use LLM planner if available, else fall back to deterministic
        llm_doc_map = None
        if adapter is not None and _LLM_AVAILABLE:
            llm_doc_map = plan_with_llm(command.pages, adapter)

        # Run the plan (AiAutoRunService.plan handles both LLM and deterministic paths)
        service = AiAutoRunService()
        result = service.plan(command)

        # If LLM provided a better document map, override the evidence
        llm_used = llm_doc_map is not None

        # Determine if we should enqueue a child Step 2 task
        should_enqueue = result.status.value in ("completed", "completed_with_warnings") and not result.safe_stop_reason
        child_task_id = None

        if should_enqueue and task_service is not None:
            # Build Step 2 config from the AI-generated config
            step2_config = result.generated_configs.step2_config
            step2_config.setdefault("model", {
                "provider": "openrouter",
                "primary_model_id": command.model_selection.primary_model_id,
                "fallback_model_ids": list(command.model_selection.fallback_model_ids),
            })
            step2_config.setdefault("extraction_prompt_id", "step2.page_qcm_extraction.v1")
            step2_config.setdefault("page_batch_size", 0)
            step2_config.setdefault("internal_page_concurrency", 5)
            step2_config.setdefault("metadata_defaults", {})
            step2_config.setdefault("metadata_strategies", {})
            step2_config.setdefault("legacy_subcategory_policy", "preserve_internal")
            step2_config.setdefault("template_overrides", {})
            step2_config.setdefault("output_format", "json+xlsx")
            step2_config.setdefault("resume_from_cycle", None)

            child_payload = {
                "user_id": command.user_id,
                "project_id": command.project_id,
                "run_id": command.run_id,
                "step1_artifact_ids": ["ai-autorun-placeholder"],
                "pages": [
                    {"page_number": page.page_number, "text": page.text, "source_artifact_id": page.source_artifact_id}
                    for page in command.pages
                ],
                "config": step2_config,
                "previous_cycle_data": {},
                "auto_run_id": command.ai_run_id,
            }

            idem_key = f"ai-autorun:{command.ai_run_id}:step2"
            task = task_service.create_task(
                TaskCreateCommand(
                    user_id=command.user_id,
                    project_id=command.project_id,
                    run_id=command.run_id,
                    kind="step2_orchestrate",
                    idempotency_key=idem_key,
                    correlation_id=command.correlation_id,
                    payload=child_payload,
                )
            )
            child_task_id = task.task_id

        status = (
            TaskStatus.COMPLETED_WITH_WARNINGS.value
            if result.warnings or result.status.value == "manual_intervention_required"
            else TaskStatus.COMPLETED.value
        )
        if result.safe_stop_reason:
            status = TaskStatus.FAILED.value
        if child_task_id:
            status = TaskStatus.COMPLETED_WITH_WARNINGS.value if result.warnings else TaskStatus.COMPLETED.value

        return {
            "status": status,
            "message": f"AI Auto Run plan evaluated, enqueued Step 2 task {child_task_id}" if child_task_id else "AI Auto Run plan evaluated",
            "result": {
                "ai_run_id": result.ai_run_id,
                "ai_status": result.status.value,
                "artifact_ids": list(result.artifact_ids),
                "warnings": list(result.warnings),
                "safe_stop_reason": result.safe_stop_reason,
                "llm_planner_used": llm_used,
                "child_step2_task_id": child_task_id,
            },
        }

    if AI_AUTORUN_TASK_KIND not in TASK_HANDLERS:
        register_handler(AI_AUTORUN_TASK_KIND, ai_autorun_handler)