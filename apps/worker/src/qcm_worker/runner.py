"""Worker runner for durable tasks."""

from qcm_application.task_service import TaskService
from qcm_shared.contracts import TaskStatus
from qcm_shared.task_contracts import (
    TaskClaimRequest,
    TaskCompletionCommand,
    TaskFailureCommand,
    TaskHeartbeatCommand,
)
from qcm_worker.handlers import TASK_HANDLERS


class WorkerRunner:
    def __init__(self, *, worker_id: str, task_service: TaskService) -> None:
        self.worker_id = worker_id
        self.task_service = task_service

    def run_once(self) -> bool:
        claim = self.task_service.claim_next(TaskClaimRequest(worker_id=self.worker_id, supported_kinds=tuple(TASK_HANDLERS)))
        if claim is None:
            return False
        task = claim.task
        attempt = claim.attempt
        handler = TASK_HANDLERS.get(task.kind)
        if handler is None:
            self.task_service.fail(
                TaskFailureCommand(
                    task_id=task.task_id,
                    attempt_id=attempt.attempt_id,
                    worker_id=self.worker_id,
                    error_code="missing_handler",
                    safe_error_message="No worker handler is registered for this task kind",
                    retryable=False,
                    correlation_id=task.correlation_id or task.task_id,
                )
            )
            return True
        try:
            self.task_service.heartbeat(
                TaskHeartbeatCommand(
                    task_id=task.task_id,
                    worker_id=self.worker_id,
                    correlation_id=task.correlation_id or task.task_id,
                )
            )
            result = handler(task.payload)
            status = result.get("status", TaskStatus.COMPLETED.value)
            self.task_service.complete(
                TaskCompletionCommand(
                    task_id=task.task_id,
                    attempt_id=attempt.attempt_id,
                    worker_id=self.worker_id,
                    status=status,
                    correlation_id=task.correlation_id or task.task_id,
                    safe_message=result.get("message"),
                )
            )
        except Exception as exc:
            self.task_service.fail(
                TaskFailureCommand(
                    task_id=task.task_id,
                    attempt_id=attempt.attempt_id,
                    worker_id=self.worker_id,
                    error_code=exc.__class__.__name__,
                    safe_error_message=str(exc) or "Worker task failed",
                    retryable=getattr(exc, "retryable", True),
                    correlation_id=task.correlation_id or task.task_id,
                )
            )
        return True
