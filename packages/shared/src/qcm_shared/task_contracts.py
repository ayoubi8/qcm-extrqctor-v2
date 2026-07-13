"""Task queue, worker, and terminal API DTOs."""

from dataclasses import dataclass, field
from typing import Any

from qcm_shared.contracts import Task, TaskAttempt, TerminalEvent, TerminalLevel, TerminalEventType


@dataclass(frozen=True, slots=True)
class TaskCreateCommand:
    user_id: str
    project_id: str
    run_id: str
    kind: str
    idempotency_key: str
    correlation_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    max_attempts: int = 3


@dataclass(frozen=True, slots=True)
class TaskClaimRequest:
    worker_id: str
    supported_kinds: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TaskClaim:
    task: Task
    attempt: TaskAttempt


@dataclass(frozen=True, slots=True)
class TaskHeartbeatCommand:
    task_id: str
    worker_id: str
    correlation_id: str


@dataclass(frozen=True, slots=True)
class TaskCancelCommand:
    task_id: str
    actor_user_id: str
    correlation_id: str


@dataclass(frozen=True, slots=True)
class TaskCompletionCommand:
    task_id: str
    attempt_id: str
    worker_id: str
    status: str
    correlation_id: str
    safe_message: str | None = None


@dataclass(frozen=True, slots=True)
class TaskFailureCommand:
    task_id: str
    attempt_id: str
    worker_id: str
    error_code: str
    safe_error_message: str
    retryable: bool
    correlation_id: str


@dataclass(frozen=True, slots=True)
class TerminalEventCreate:
    user_id: str
    project_id: str
    level: TerminalLevel
    event_type: TerminalEventType
    message: str
    safe_payload: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None
    task_id: str | None = None
    attempt_id: str | None = None


@dataclass(frozen=True, slots=True)
class TerminalPage:
    events: tuple[TerminalEvent, ...]
    next_cursor: int | None
