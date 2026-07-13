"""Durable task queue and terminal application services."""

from dataclasses import replace
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from qcm_domain.tasks import (
    assert_task_transition,
    lease_expires_at,
    retry_available_at,
)
from qcm_shared.config.defaults import TaskRuntimeDefaults
from qcm_shared.contracts import (
    Task,
    TaskAttempt,
    TaskAttemptStatus,
    TaskStatus,
    TerminalEvent,
    TerminalEventType,
    TerminalLevel,
)
from qcm_shared.task_contracts import (
    TaskCancelCommand,
    TaskClaim,
    TaskClaimRequest,
    TaskCompletionCommand,
    TaskCreateCommand,
    TaskFailureCommand,
    TaskHeartbeatCommand,
    TerminalEventCreate,
    TerminalPage,
)


class TaskQueueRepository(Protocol):
    def create_task(self, task: Task) -> Task:
        ...

    def claim_next(self, request: TaskClaimRequest, *, now: datetime) -> TaskClaim | None:
        ...

    def update_task(self, task: Task) -> Task:
        ...

    def get_task(self, task_id: str) -> Task:
        ...

    def update_attempt(self, attempt: TaskAttempt) -> TaskAttempt:
        ...


class TerminalEventRepository(Protocol):
    def append(self, event: TerminalEventCreate) -> TerminalEvent:
        ...

    def list_project_events(self, *, user_id: str, project_id: str, after_sequence: int | None, limit: int) -> TerminalPage:
        ...


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat()


class TaskService:
    def __init__(
        self,
        tasks: TaskQueueRepository,
        terminal: TerminalEventRepository,
        defaults: TaskRuntimeDefaults | None = None,
    ) -> None:
        self.tasks = tasks
        self.terminal = terminal
        self.defaults = defaults or TaskRuntimeDefaults()

    def create_task(self, command: TaskCreateCommand) -> Task:
        now = utc_now()
        task = Task(
            task_id=str(uuid4()),
            user_id=command.user_id,
            project_id=command.project_id,
            run_id=command.run_id,
            kind=command.kind,
            status=TaskStatus.QUEUED,
            idempotency_key=command.idempotency_key,
            attempt=0,
            max_attempts=command.max_attempts,
            payload=command.payload,
            created_at=iso(now),
            updated_at=iso(now),
            available_at=iso(now),
            priority=command.priority,
            correlation_id=command.correlation_id,
        )
        created = self.tasks.create_task(task)
        self.terminal.append(
            TerminalEventCreate(
                user_id=created.user_id,
                project_id=created.project_id,
                run_id=created.run_id,
                task_id=created.task_id,
                level=TerminalLevel.INFO,
                event_type=TerminalEventType.SYSTEM_MESSAGE,
                message="Task queued",
                safe_payload={"task_kind": created.kind},
            )
        )
        return created

    def claim_next(self, request: TaskClaimRequest) -> TaskClaim | None:
        return self.tasks.claim_next(request, now=utc_now())

    def heartbeat(self, command: TaskHeartbeatCommand) -> Task:
        now = utc_now()
        task = self.tasks.get_task(command.task_id)
        if task.status != TaskStatus.RUNNING:
            return task
        updated = replace(
            task,
            heartbeat_at=iso(now),
            lease_expires_at=iso(lease_expires_at(now=now, defaults=self.defaults)),
            updated_at=iso(now),
            correlation_id=command.correlation_id,
        )
        saved = self.tasks.update_task(updated)
        self.terminal.append(
            TerminalEventCreate(
                user_id=saved.user_id,
                project_id=saved.project_id,
                run_id=saved.run_id,
                task_id=saved.task_id,
                level=TerminalLevel.DEBUG,
                event_type=TerminalEventType.TASK_HEARTBEAT,
                message="Task heartbeat recorded",
                safe_payload={"worker_id": command.worker_id},
            )
        )
        return saved

    def cancel(self, command: TaskCancelCommand) -> Task:
        now = utc_now()
        task = self.tasks.get_task(command.task_id)
        assert_task_transition(task.status, TaskStatus.CANCELLED)
        saved = self.tasks.update_task(
            replace(
                task,
                status=TaskStatus.CANCELLED,
                finished_at=iso(now),
                updated_at=iso(now),
                correlation_id=command.correlation_id,
            )
        )
        self.terminal.append(
            TerminalEventCreate(
                user_id=saved.user_id,
                project_id=saved.project_id,
                run_id=saved.run_id,
                task_id=saved.task_id,
                level=TerminalLevel.WARNING,
                event_type=TerminalEventType.CANCEL_REQUESTED,
                message="Task cancellation requested",
                safe_payload={"actor_user_id": command.actor_user_id},
            )
        )
        return saved

    def complete(self, command: TaskCompletionCommand) -> Task:
        now = utc_now()
        task = self.tasks.get_task(command.task_id)
        target = (
            TaskStatus.COMPLETED_WITH_WARNINGS
            if command.status == TaskStatus.COMPLETED_WITH_WARNINGS.value
            else TaskStatus.COMPLETED
        )
        assert_task_transition(task.status, target)
        saved = self.tasks.update_task(
            replace(task, status=target, finished_at=iso(now), updated_at=iso(now), correlation_id=command.correlation_id)
        )
        self.tasks.update_attempt(
            TaskAttempt(
                attempt_id=command.attempt_id,
                task_id=command.task_id,
                attempt_number=saved.attempt,
                status=TaskAttemptStatus.COMPLETED if target == TaskStatus.COMPLETED else TaskAttemptStatus.COMPLETED_WITH_WARNINGS,
                started_at=saved.started_at or iso(now),
                finished_at=iso(now),
                worker_id=command.worker_id,
                user_id=saved.user_id,
                project_id=saved.project_id,
                run_id=saved.run_id,
            )
        )
        self.terminal.append(
            TerminalEventCreate(
                user_id=saved.user_id,
                project_id=saved.project_id,
                run_id=saved.run_id,
                task_id=saved.task_id,
                attempt_id=command.attempt_id,
                level=TerminalLevel.SUCCESS,
                event_type=TerminalEventType.TASK_HEARTBEAT if False else TerminalEventType.STEP_COMPLETED,
                message=command.safe_message or "Task completed",
                safe_payload={"task_kind": saved.kind},
            )
        )
        return saved

    def fail(self, command: TaskFailureCommand) -> Task:
        now = utc_now()
        task = self.tasks.get_task(command.task_id)
        should_retry = command.retryable and task.attempt < task.max_attempts
        target = TaskStatus.RETRYING if should_retry else TaskStatus.FAILED
        assert_task_transition(task.status, target)
        saved = self.tasks.update_task(
            replace(
                task,
                status=target,
                available_at=iso(retry_available_at(attempt_number=task.attempt, now=now, defaults=self.defaults))
                if should_retry
                else task.available_at,
                finished_at=None if should_retry else iso(now),
                updated_at=iso(now),
                last_error_code=command.error_code,
                correlation_id=command.correlation_id,
            )
        )
        self.tasks.update_attempt(
            TaskAttempt(
                attempt_id=command.attempt_id,
                task_id=command.task_id,
                attempt_number=max(saved.attempt, 1),
                status=TaskAttemptStatus.FAILED,
                started_at=saved.started_at or iso(now),
                finished_at=iso(now),
                worker_id=command.worker_id,
                error_code=command.error_code,
                safe_error_message=command.safe_error_message,
                user_id=saved.user_id,
                project_id=saved.project_id,
                run_id=saved.run_id,
            )
        )
        self.terminal.append(
            TerminalEventCreate(
                user_id=saved.user_id,
                project_id=saved.project_id,
                run_id=saved.run_id,
                task_id=saved.task_id,
                attempt_id=command.attempt_id,
                level=TerminalLevel.WARNING if should_retry else TerminalLevel.ERROR,
                event_type=TerminalEventType.RETRY_SCHEDULED if should_retry else TerminalEventType.TASK_FAILED,
                message=command.safe_error_message,
                safe_payload={"retry_scheduled": should_retry, "error_code": command.error_code},
            )
        )
        return saved

    def terminal_page(self, *, user_id: str, project_id: str, after_sequence: int | None = None, limit: int = 100) -> TerminalPage:
        return self.terminal.list_project_events(
            user_id=user_id,
            project_id=project_id,
            after_sequence=after_sequence,
            limit=limit,
        )
