"""Worker handler for Manual Auto Run workflow tasks."""

from typing import Any

from qcm_application.autorun_service import CANONICAL_STEP_ORDER, ManualAutoRunService
from qcm_shared.autorun_contracts import (
    MANUAL_AUTORUN_TASK_KIND,
    MANUAL_AUTORUN_SCHEMA_VERSION,
    ManualAutoRunSnapshot,
    ManualAutoRunStepConfig,
)
from qcm_shared.contracts import TaskStatus
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


def manual_autorun_handler(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = _snapshot_from_payload(payload)
    validation = ManualAutoRunService().validate(snapshot.selected_steps)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    child_tasks = [
        {
            "step_key": step.step_key,
            "task_kind": step.task_kind,
            "payload": {
                "user_id": payload.get("user_id", ""),
                "project_id": payload.get("project_id", ""),
                "run_id": payload.get("run_id", ""),
                "config": step.config,
                "auto_run_id": payload.get("auto_run_id", ""),
            },
        }
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


def register_manual_autorun_handler() -> None:
    if MANUAL_AUTORUN_TASK_KIND not in TASK_HANDLERS:
        register_handler(MANUAL_AUTORUN_TASK_KIND, manual_autorun_handler)
