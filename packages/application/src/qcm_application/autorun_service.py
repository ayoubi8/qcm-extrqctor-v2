"""Manual Auto Run validation, start, and control service."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from qcm_application.ownership import AuthorizationError
from qcm_shared.autorun_contracts import (
    MANUAL_AUTORUN_TASK_KIND,
    ManualAutoRunControlAction,
    ManualAutoRunControlCommand,
    ManualAutoRunRecord,
    ManualAutoRunStartCommand,
    ManualAutoRunStatus,
    ManualAutoRunStepConfig,
    ManualAutoRunValidation,
)
from qcm_shared.task_contracts import TaskCreateCommand

CANONICAL_STEP_ORDER: tuple[tuple[str, str], ...] = (
    ("step1", "step1_extract"),
    ("step2", "step2_orchestrate"),
    ("step3-correction", "step3_correction"),
    ("step4-similarity", "step4_similarity_match"),
)


class TaskCreator(Protocol):
    def create_task(self, command: TaskCreateCommand):
        ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


class InMemoryManualAutoRunRepository:
    def __init__(self) -> None:
        self.records: dict[str, ManualAutoRunRecord] = {}
        self.idempotency: dict[tuple[str, str], str] = {}

    def save(self, record: ManualAutoRunRecord, *, idempotency_key: str | None = None) -> ManualAutoRunRecord:
        self.records[record.auto_run_id] = record
        if idempotency_key:
            self.idempotency[(record.user_id, idempotency_key)] = record.auto_run_id
        return record

    def get_idempotent(self, *, user_id: str, idempotency_key: str) -> ManualAutoRunRecord | None:
        auto_run_id = self.idempotency.get((user_id, idempotency_key))
        return self.records.get(auto_run_id) if auto_run_id else None

    def get_owned(self, *, user_id: str, project_id: str, auto_run_id: str) -> ManualAutoRunRecord:
        record = self.records[auto_run_id]
        if record.user_id != user_id or record.project_id != project_id:
            raise AuthorizationError("Manual Auto Run does not belong to requester")
        return record


class ManualAutoRunService:
    def __init__(
        self,
        *,
        repository: InMemoryManualAutoRunRepository | None = None,
        task_creator: TaskCreator | None = None,
    ) -> None:
        self.repository = repository or InMemoryManualAutoRunRepository()
        self.task_creator = task_creator

    def validate(self, steps: tuple[ManualAutoRunStepConfig, ...]) -> ManualAutoRunValidation:
        enabled = tuple(step for step in steps if step.enabled)
        errors: list[str] = []
        warnings: list[str] = []
        if not enabled:
            errors.append("Manual Auto Run requires at least one enabled step")
        allowed = {step_key: task_kind for step_key, task_kind in CANONICAL_STEP_ORDER}
        seen: set[str] = set()
        normalized: list[ManualAutoRunStepConfig] = []
        for step in enabled:
            if step.step_key in seen:
                errors.append(f"Duplicate Auto Run step: {step.step_key}")
                continue
            seen.add(step.step_key)
            expected_task = allowed.get(step.step_key)
            if expected_task is None:
                errors.append(f"Unsupported Auto Run step: {step.step_key}")
                continue
            if step.task_kind != expected_task:
                errors.append(f"Step {step.step_key} must use task kind {expected_task}")
                continue
            normalized.append(step)
        order_index = {step_key: index for index, (step_key, _) in enumerate(CANONICAL_STEP_ORDER)}
        sorted_steps = tuple(sorted(normalized, key=lambda item: order_index[item.step_key]))
        if tuple(step.step_key for step in normalized) != tuple(step.step_key for step in sorted_steps):
            warnings.append("Manual Auto Run steps were normalized to canonical visible pipeline order")
        return ManualAutoRunValidation(
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
            normalized_steps=sorted_steps,
        )

    def start(self, command: ManualAutoRunStartCommand) -> ManualAutoRunRecord:
        existing = self.repository.get_idempotent(user_id=command.user_id, idempotency_key=command.idempotency_key)
        if existing is not None:
            return existing
        validation = self.validate(command.snapshot.selected_steps)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))
        now = _now()
        child_task_ids: list[str] = []
        record = ManualAutoRunRecord(
            auto_run_id=command.auto_run_id,
            user_id=command.user_id,
            project_id=command.project_id,
            run_id=command.run_id,
            status=ManualAutoRunStatus.QUEUED,
            snapshot=replace(command.snapshot, selected_steps=validation.normalized_steps),
            current_step_key=validation.normalized_steps[0].step_key if validation.normalized_steps else None,
            created_at=now,
            updated_at=now,
        )
        if self.task_creator is not None:
            task = self.task_creator.create_task(
                TaskCreateCommand(
                    user_id=command.user_id,
                    project_id=command.project_id,
                    run_id=command.run_id,
                    kind=MANUAL_AUTORUN_TASK_KIND,
                    idempotency_key=command.idempotency_key,
                    correlation_id=command.correlation_id,
                    payload={
                        "auto_run_id": command.auto_run_id,
                        "user_id": command.user_id,
                        "project_id": command.project_id,
                        "run_id": command.run_id,
                        "snapshot": _snapshot_payload(record.snapshot),
                    },
                )
            )
            child_task_ids.append(task.task_id)
        record = replace(record, child_task_ids=tuple(child_task_ids))
        return self.repository.save(record, idempotency_key=command.idempotency_key)

    def control(self, command: ManualAutoRunControlCommand) -> ManualAutoRunRecord:
        record = self.repository.get_owned(
            user_id=command.user_id,
            project_id=command.project_id,
            auto_run_id=command.auto_run_id,
        )
        action = command.action if isinstance(command.action, ManualAutoRunControlAction) else ManualAutoRunControlAction(command.action)
        target = {
            ManualAutoRunControlAction.PAUSE: ManualAutoRunStatus.PAUSED,
            ManualAutoRunControlAction.RESUME: ManualAutoRunStatus.RUNNING,
            ManualAutoRunControlAction.RETRY: ManualAutoRunStatus.QUEUED,
            ManualAutoRunControlAction.CANCEL: ManualAutoRunStatus.CANCELLED,
        }[action]
        updated = replace(record, status=target, updated_at=_now())
        return self.repository.save(updated)


def _snapshot_payload(snapshot) -> dict:
    return {
        "schema_version": snapshot.schema_version,
        "selected_steps": [
            {"step_key": step.step_key, "task_kind": step.task_kind, "enabled": step.enabled, "config": step.config}
            for step in snapshot.selected_steps
        ],
        "saved_defaults": snapshot.saved_defaults,
        "project_overrides": snapshot.project_overrides,
        "resource_limits": snapshot.resource_limits,
    }
