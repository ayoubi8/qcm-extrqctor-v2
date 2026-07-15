"""Worker handler for Manual Auto Run workflow tasks.

When claimed by the worker, enqueues real child step tasks (step1_extract,
step2_orchestrate, etc.) via the TaskService so the worker processes them
in pipeline order.
"""

from typing import Any
from uuid import uuid4

from qcm_application.autorun_service import CANONICAL_STEP_ORDER, ManualAutoRunService
from qcm_application.task_service import TaskService
from qcm_shared.autorun_contracts import (
    MANUAL_AUTORUN_TASK_KIND,
    MANUAL_AUTORUN_SCHEMA_VERSION,
    ManualAutoRunSnapshot,
    ManualAutoRunStepConfig,
)
from qcm_shared.contracts import TaskStatus
from qcm_shared.task_contracts import TaskCreateCommand
from qcm_worker.handlers import TASK_HANDLERS, register_handler


def _snapshot_from_payload(payload: dict[str, Any]) -> ManualAutoRunSnapshot:
    raw = payload.get("snapshot") or {}
    return ManualAutoRunSnapshot(
        schema_version=raw.get("schema_version", MANUAL_AUTORUN_SCHEMA_VERSION),
        selected_steps=tuple(
            ManualAutoRunStepConfig(
                step_key=item.get("step_key", ""),
                task_kind=item.get("task_kind", ""),
                enabled=bool(item.get("enabled", True)),
                config=dict(item.get("config") or {}),
            )
            for item in raw.get("selected_steps") or ()
        ),
        saved_defaults=dict(raw.get("saved_defaults") or {}),
        project_overrides=dict(raw.get("project_overrides") or {}),
        resource_limits=dict(raw.get("resource_limits") or {}),
    )


def _build_child_payload(step_key: str, step_config: dict, payload: dict[str, Any]) -> dict[str, Any]:
    """Build a task payload appropriate for the step's handler."""
    base = {
        "user_id": payload.get("user_id", ""),
        "project_id": payload.get("project_id", ""),
        "run_id": payload.get("run_id", ""),
        "source_file_id": payload.get("source_file_id", ""),
        "source_filename": payload.get("source_filename", "source.pdf"),
        "config": step_config,
        "auto_run_id": payload.get("auto_run_id", ""),
    }
    if step_key == "step2":
        base["step1_artifact_ids"] = ["auto-run-step1-placeholder"]
        base["pages"] = []
        base["previous_cycle_data"] = {}
    elif step_key == "step3-correction":
        base["step2_artifact_ids"] = []
        base["qcms"] = []
        base["pages"] = []
    elif step_key == "step4-similarity":
        base["source_artifact_ids"] = []
        base["source_qcms"] = []
        base["reference_qcms"] = []
        base["existing_matches"] = []
    return base


def manual_autorun_handler(payload: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible module-level handler (plan-only mode, no child task enqueuing)."""
    snapshot = _snapshot_from_payload(payload)
    validation = ManualAutoRunService().validate(snapshot.selected_steps)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    child_tasks = [
        {"step_key": step.step_key, "task_kind": step.task_kind}
        for step in validation.normalized_steps
    ]
    return {
        "status": TaskStatus.COMPLETED_WITH_WARNINGS.value if validation.warnings else TaskStatus.COMPLETED.value,
        "message": "Manual Auto Run sequence planned",
        "result": {
            "auto_run_id": payload.get("auto_run_id", ""),
            "step_order": [step_key for step_key, _ in CANONICAL_STEP_ORDER],
            "child_tasks": child_tasks,
            "warnings": list(validation.warnings),
        },
    }


def register_manual_autorun_handler(task_service: TaskService | None = None) -> None:
    """Register the manual autorun handler. If task_service is provided, the handler
    will enqueue real child step tasks; otherwise it falls back to plan-only mode."""

    def manual_autorun_handler(payload: dict[str, Any]) -> dict[str, Any]:
        snapshot = _snapshot_from_payload(payload)
        validation = ManualAutoRunService().validate(snapshot.selected_steps)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        child_task_ids: list[str] = []
        child_tasks_info: list[dict] = []

        if task_service is not None:
            auto_run_id = payload.get("auto_run_id", "")
            for step in validation.normalized_steps:
                child_payload = _build_child_payload(step.step_key, step.config, payload)
                idem_key = f"auto:{auto_run_id}:{step.step_key}" if auto_run_id else f"auto:{step.step_key}:{uuid4()}"
                task = task_service.create_task(
                    TaskCreateCommand(
                        user_id=payload.get("user_id", ""),
                        project_id=payload.get("project_id", ""),
                        run_id=payload.get("run_id", ""),
                        kind=step.task_kind,
                        idempotency_key=idem_key,
                        correlation_id=payload.get("correlation_id", auto_run_id),
                        payload=child_payload,
                    )
                )
                child_task_ids.append(task.task_id)
                child_tasks_info.append({"step_key": step.step_key, "task_kind": step.task_kind, "task_id": task.task_id})
        else:
            child_tasks_info = [
                {"step_key": step.step_key, "task_kind": step.task_kind}
                for step in validation.normalized_steps
            ]

        return {
            "status": TaskStatus.COMPLETED_WITH_WARNINGS.value if validation.warnings else TaskStatus.COMPLETED.value,
            "message": f"Manual Auto Run enqueued {len(child_task_ids)} child step tasks" if child_task_ids else "Manual Auto Run sequence planned",
            "result": {
                "auto_run_id": payload.get("auto_run_id", ""),
                "step_order": [step_key for step_key, _ in CANONICAL_STEP_ORDER],
                "child_task_ids": child_task_ids,
                "child_tasks": child_tasks_info,
                "warnings": list(validation.warnings),
            },
        }

    if MANUAL_AUTORUN_TASK_KIND not in TASK_HANDLERS:
        register_handler(MANUAL_AUTORUN_TASK_KIND, manual_autorun_handler)