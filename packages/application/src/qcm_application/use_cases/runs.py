"""Run/task use cases for API task creation boundaries."""

from datetime import datetime, timezone
from uuid import uuid4

from qcm_shared.api_contracts import ConfigResolveCommand, RunStepCommand, RunStepResponse
from qcm_shared.contracts import Task, TaskStatus

from qcm_application.config_snapshot import draft_configuration_snapshot


def create_step_task(
    command: RunStepCommand,
    *,
    task_repository,
    created_by: str,
) -> RunStepResponse:
    config_command = ConfigResolveCommand(
        user_id=command.user_id,
        project_id=command.project_id,
        run_id=command.run_id,
        correlation_id=command.correlation_id,
        system_defaults={},
        run_overrides=command.config_overrides,
    )
    snapshot = draft_configuration_snapshot(config_command, created_by=created_by)
    now = datetime.now(timezone.utc).isoformat()
    task = Task(
        task_id=str(uuid4()),
        user_id=command.user_id,
        project_id=command.project_id,
        run_id=command.run_id,
        kind=command.step_key.value,
        status=TaskStatus.QUEUED,
        idempotency_key=command.idempotency_key,
        attempt=0,
        max_attempts=3,
        payload={
            "step_key": command.step_key.value,
            "configuration_hash": snapshot.config_hash,
            "config_overrides": command.config_overrides,
        },
        created_at=now,
        updated_at=now,
        available_at=now,
    )
    return RunStepResponse(task=task_repository.create_task(task), config_snapshot=snapshot)
