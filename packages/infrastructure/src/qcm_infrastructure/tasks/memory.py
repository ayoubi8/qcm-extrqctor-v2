"""In-memory task repositories for local verification.

The production queue is the Plan 03 Postgres schema/functions. This adapter mirrors the same
semantics for unit tests: idempotency, priority/available ordering, attempts, leases, and cursor
terminal replay.
"""

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from qcm_domain.tasks import QUEUE_TASK_STATUSES, assert_task_transition, lease_expires_at
from qcm_shared.config.defaults import TaskRuntimeDefaults
from qcm_shared.contracts import Task, TaskAttempt, TaskAttemptStatus, TaskStatus, TerminalEvent
from qcm_shared.task_contracts import TaskClaim, TaskClaimRequest, TerminalEventCreate, TerminalPage


class InMemoryTaskRepository:
    def __init__(self, defaults: TaskRuntimeDefaults | None = None) -> None:
        self.defaults = defaults or TaskRuntimeDefaults()
        self.tasks: dict[str, Task] = {}
        self.idempotency: dict[tuple[str, str, str], str] = {}
        self.attempts: dict[str, TaskAttempt] = {}

    def create_task(self, task: Task) -> Task:
        key = (task.user_id, task.project_id, task.idempotency_key)
        if key in self.idempotency:
            return self.tasks[self.idempotency[key]]
        self.tasks[task.task_id] = task
        self.idempotency[key] = task.task_id
        return task

    def get_task(self, task_id: str) -> Task:
        return self.tasks[task_id]

    def list_tasks(self, *, user_id: str, project_id: str) -> list[Task]:
        return [
            task for task in self.tasks.values()
            if task.user_id == user_id and task.project_id == project_id
        ]

    def update_task(self, task: Task) -> Task:
        self.tasks[task.task_id] = task
        return task

    def update_attempt(self, attempt: TaskAttempt) -> TaskAttempt:
        self.attempts[attempt.attempt_id] = attempt
        return attempt

    def claim_next(self, request: TaskClaimRequest, *, now: datetime) -> TaskClaim | None:
        candidates = []
        for task in self.tasks.values():
            available = datetime.fromisoformat(task.available_at.replace("Z", "+00:00"))
            supported = not request.supported_kinds or task.kind in request.supported_kinds
            if task.status in QUEUE_TASK_STATUSES and available <= now and supported:
                candidates.append(task)
        if not candidates:
            return None
        task = sorted(candidates, key=lambda item: (-item.priority, item.available_at, item.created_at))[0]
        assert_task_transition(task.status, TaskStatus.RUNNING)
        attempt_number = task.attempt + 1
        updated = replace(
            task,
            status=TaskStatus.RUNNING,
            attempt=attempt_number,
            heartbeat_at=now.isoformat(),
            lease_expires_at=lease_expires_at(now=now, defaults=self.defaults).isoformat(),
            started_at=task.started_at or now.isoformat(),
            updated_at=now.isoformat(),
        )
        self.tasks[task.task_id] = updated
        attempt = TaskAttempt(
            attempt_id=str(uuid4()),
            task_id=task.task_id,
            attempt_number=attempt_number,
            status=TaskAttemptStatus.RUNNING,
            started_at=now.isoformat(),
            worker_id=request.worker_id,
            user_id=task.user_id,
            project_id=task.project_id,
            run_id=task.run_id,
        )
        self.attempts[attempt.attempt_id] = attempt
        return TaskClaim(task=updated, attempt=attempt)


class InMemoryTerminalRepository:
    def __init__(self) -> None:
        self.events: list[TerminalEvent] = []
        self.sequence = 0

    def append(self, event: TerminalEventCreate) -> TerminalEvent:
        self.sequence += 1
        created = TerminalEvent(
            event_id=str(uuid4()),
            user_id=event.user_id,
            project_id=event.project_id,
            run_id=event.run_id,
            task_id=event.task_id,
            attempt_id=event.attempt_id,
            level=event.level,
            event_type=event.event_type,
            message=event.message,
            safe_payload=event.safe_payload,
            created_at=datetime.now(timezone.utc).isoformat(),
            sequence=self.sequence,
        )
        self.events.append(created)
        return created

    def list_project_events(
        self,
        *,
        user_id: str,
        project_id: str,
        after_sequence: int | None,
        limit: int,
    ) -> TerminalPage:
        selected = [
            event
            for event in self.events
            if event.user_id == user_id
            and event.project_id == project_id
            and (after_sequence is None or (event.sequence or 0) > after_sequence)
        ][:limit]
        next_cursor = selected[-1].sequence if selected else after_sequence
        return TerminalPage(events=tuple(selected), next_cursor=next_cursor)
