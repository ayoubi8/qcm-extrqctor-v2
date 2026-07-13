"""Task state machine, retry, lease, and terminal safety rules."""

from datetime import datetime, timedelta, timezone

from qcm_shared.config.defaults import TaskRuntimeDefaults
from qcm_shared.contracts import TaskStatus, TerminalLevel

TERMINAL_TASK_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.COMPLETED_WITH_WARNINGS,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
    TaskStatus.EXPIRED,
    TaskStatus.SKIPPED,
}

QUEUE_TASK_STATUSES = {TaskStatus.QUEUED, TaskStatus.RETRYING}

VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.CANCELLED, TaskStatus.SKIPPED},
    TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.EXPIRED},
    TaskStatus.RETRYING: {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.EXPIRED},
    TaskStatus.RUNNING: {
        TaskStatus.COMPLETED,
        TaskStatus.COMPLETED_WITH_WARNINGS,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.RETRYING,
        TaskStatus.EXPIRED,
    },
    TaskStatus.COMPLETED: set(),
    TaskStatus.COMPLETED_WITH_WARNINGS: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
    TaskStatus.EXPIRED: set(),
    TaskStatus.SKIPPED: set(),
}


class InvalidTaskTransition(ValueError):
    pass


def assert_task_transition(current: TaskStatus, target: TaskStatus) -> None:
    if target not in VALID_TRANSITIONS[current]:
        raise InvalidTaskTransition(f"Invalid task transition: {current} -> {target}")


def retry_available_at(
    *,
    attempt_number: int,
    now: datetime,
    defaults: TaskRuntimeDefaults | None = None,
) -> datetime:
    config = defaults or TaskRuntimeDefaults()
    backoffs = config.retry_backoff_seconds
    delay = backoffs[min(max(attempt_number - 1, 0), len(backoffs) - 1)]
    return now + timedelta(seconds=delay)


def lease_expires_at(
    *,
    now: datetime,
    defaults: TaskRuntimeDefaults | None = None,
) -> datetime:
    config = defaults or TaskRuntimeDefaults()
    return now + timedelta(seconds=config.lease_ttl_seconds)


def is_lease_expired(lease_expires_at_value: str | None, *, now: datetime | None = None) -> bool:
    if lease_expires_at_value is None:
        return False
    current = now or datetime.now(timezone.utc)
    lease = datetime.fromisoformat(lease_expires_at_value.replace("Z", "+00:00"))
    return lease <= current


def terminal_level_for_text(text: str) -> TerminalLevel:
    lowered = text.lower()
    if "error" in lowered or "[error]" in lowered:
        return TerminalLevel.ERROR
    if "warn" in lowered or "warning" in lowered:
        return TerminalLevel.WARNING
    if "success" in lowered or "[ok]" in lowered:
        return TerminalLevel.SUCCESS
    return TerminalLevel.INFO
