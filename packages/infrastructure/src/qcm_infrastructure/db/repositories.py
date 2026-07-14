"""Supabase (PostgREST) repository adapters.

Concrete adapters over the Plan 03 schema via the lightweight PostgrestClient. Service-role
calls bypass RLS; ownership is still enforced by the auth dependency and explicit user_id
filtering in queries. Reference DB / artifact-version adapters are deferred to Phase C
(they require the artifacts parent + storage); only the core project/run/task/terminal
adapters needed for durable data and the worker queue are implemented here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from qcm_domain.tasks import QUEUE_TASK_STATUSES
from qcm_shared.api_contracts import ProjectCreateCommand, ProjectSummary
from qcm_shared.contracts import Task, TaskAttempt, TaskAttemptStatus, TaskStatus, TerminalEvent
from qcm_shared.task_contracts import TaskClaim, TaskClaimRequest, TerminalEventCreate, TerminalPage

from qcm_infrastructure.db.postgrest import PostgrestClient, PostgrestError


_TASK_COLUMNS = (
    "task_id,user_id,project_id,run_id,kind,status,idempotency_key,attempt,max_attempts,"
    "payload,priority,correlation_id,last_error_code,created_at,updated_at,available_at,"
    "lease_expires_at,heartbeat_at,started_at,finished_at"
)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def _task_from_row(row: dict[str, Any]) -> Task:
    return Task(
        task_id=str(row["task_id"]),
        user_id=str(row["user_id"]),
        project_id=str(row["project_id"]),
        run_id=str(row["run_id"]),
        kind=str(row["kind"]),
        status=TaskStatus(str(row["status"])),
        idempotency_key=str(row["idempotency_key"]),
        attempt=int(row.get("attempt") or 0),
        max_attempts=int(row.get("max_attempts") or 3),
        payload=row.get("payload") or {},
        created_at=_iso(row.get("created_at")) or "",
        updated_at=_iso(row.get("updated_at")) or "",
        available_at=_iso(row.get("available_at")) or "",
        lease_expires_at=_iso(row.get("lease_expires_at")),
        heartbeat_at=_iso(row.get("heartbeat_at")),
        started_at=_iso(row.get("started_at")),
        finished_at=_iso(row.get("finished_at")),
        priority=int(row.get("priority") or 0),
        correlation_id=row.get("correlation_id"),
        last_error_code=row.get("last_error_code"),
    )


def _attempt_from_row(row: dict[str, Any]) -> TaskAttempt:
    return TaskAttempt(
        attempt_id=str(row["attempt_id"]),
        task_id=str(row["task_id"]),
        attempt_number=int(row["attempt_number"]),
        status=TaskAttemptStatus(str(row["status"])),
        started_at=_iso(row.get("started_at")) or "",
        worker_id=str(row.get("worker_id") or ""),
        finished_at=_iso(row.get("finished_at")),
        error_code=row.get("error_code"),
        safe_error_message=row.get("safe_error_message"),
        user_id=str(row["user_id"]) if row.get("user_id") else None,
        project_id=str(row["project_id"]) if row.get("project_id") else None,
        run_id=str(row["run_id"]) if row.get("run_id") else None,
    )


def _event_from_row(row: dict[str, Any]) -> TerminalEvent:
    return TerminalEvent(
        event_id=str(row["event_id"]),
        user_id=str(row["user_id"]),
        project_id=str(row["project_id"]),
        level=row.get("level"),
        event_type=row.get("event_type"),
        message=str(row.get("message") or ""),
        safe_payload=row.get("safe_payload") or {},
        created_at=_iso(row.get("created_at")) or "",
        run_id=str(row["run_id"]) if row.get("run_id") else None,
        task_id=str(row["task_id"]) if row.get("task_id") else None,
        attempt_id=str(row["attempt_id"]) if row.get("attempt_id") else None,
        sequence=row.get("sequence"),
    )


class SupabaseProjectRepository:
    def __init__(self, client: PostgrestClient) -> None:
        self.client = client

    def create_project(self, command: ProjectCreateCommand) -> ProjectSummary:
        # projects has no idempotency_key column; idempotency is app-level only.
        row = self.client.insert(
            "projects",
            {
                "project_id": str(__import__("uuid").uuid4()),
                "user_id": command.user_id,
                "name": command.name or "Untitled project",
                "status": "active",
            },
        )
        return ProjectSummary(
            project_id=str(row["project_id"]),
            user_id=str(row["user_id"]),
            name=str(row["name"]),
            status=str(row["status"]),
            updated_at=_iso(row["updated_at"]) or "",
        )

    def get_project(self, *, user_id: str, project_id: str) -> ProjectSummary | None:
        row = self.client.select_one(
            "projects",
            columns="project_id,user_id,name,status,updated_at",
            params={"project_id": f"eq.{project_id}", "user_id": f"eq.{user_id}"},
        )
        if not row:
            return None
        return ProjectSummary(
            project_id=str(row["project_id"]),
            user_id=str(row["user_id"]),
            name=str(row["name"]),
            status=str(row["status"]),
            updated_at=_iso(row["updated_at"]) or "",
        )

    def list_projects(self, *, user_id: str) -> list[ProjectSummary]:
        rows = self.client.select(
            "projects",
            columns="project_id,user_id,name,status,updated_at",
            params={"user_id": f"eq.{user_id}"},
            order="updated_at.desc",
        )
        return [
            ProjectSummary(
                project_id=str(r["project_id"]),
                user_id=str(r["user_id"]),
                name=str(r["name"]),
                status=str(r["status"]),
                updated_at=_iso(r["updated_at"]) or "",
            )
            for r in rows
        ]


class SupabasePipelineRunRepository:
    def __init__(self, client: PostgrestClient) -> None:
        self.client = client

    def ensure_run(self, *, user_id: str, project_id: str, run_id: str | None = None, triggered_by: str = "manual") -> dict:
        from uuid import uuid4
        run_id = run_id or str(uuid4())
        row = self.client.insert(
            "pipeline_runs",
            {
                "pipeline_run_id": run_id,
                "user_id": user_id,
                "project_id": project_id,
                "triggered_by": triggered_by,
            },
            on_conflict="pipeline_run_id",
        )
        row = row or {}
        return {
            "run_id": str(row.get("pipeline_run_id") or run_id),
            "user_id": str(row.get("user_id") or user_id),
            "project_id": str(row.get("project_id") or project_id),
            "status": str(row.get("status") or "pending"),
            "triggered_by": str(row.get("triggered_by") or triggered_by),
            "created_at": _iso(row.get("created_at")) or "",
            "updated_at": _iso(row.get("updated_at")) or "",
        }

    def list_runs(self, *, user_id: str, project_id: str) -> list[dict]:
        rows = self.client.select(
            "pipeline_runs",
            columns="pipeline_run_id,user_id,project_id,status,triggered_by,created_at,updated_at",
            params={"user_id": f"eq.{user_id}", "project_id": f"eq.{project_id}"},
            order="created_at.desc",
        )
        return [
            {
                "run_id": str(r["pipeline_run_id"]),
                "user_id": str(r["user_id"]),
                "project_id": str(r["project_id"]),
                "status": str(r["status"]),
                "triggered_by": str(r.get("triggered_by") or "manual"),
                "created_at": _iso(r["created_at"]) or "",
                "updated_at": _iso(r["updated_at"]) or "",
            }
            for r in rows
        ]


class SupabaseTaskRepository:
    def __init__(self, client: PostgrestClient) -> None:
        self.client = client

    def create_task(self, task: Task) -> Task:
        body = {
            "task_id": task.task_id,
            "user_id": task.user_id,
            "project_id": task.project_id,
            "run_id": task.run_id,
            "kind": task.kind,
            "status": task.status.value,
            "idempotency_key": task.idempotency_key,
            "attempt": task.attempt,
            "max_attempts": task.max_attempts,
            "payload": task.payload,
            "priority": task.priority,
            "correlation_id": task.correlation_id or "",
            "available_at": task.available_at.replace("Z", "+00:00") if task.available_at else None,
        }
        try:
            row = self.client.insert("tasks", body)
        except PostgrestError as exc:
            if exc.status == 409:
                existing = self.client.select_one(
                    "tasks",
                    columns=_TASK_COLUMNS,
                    params={
                        "user_id": f"eq.{task.user_id}",
                        "project_id": f"eq.{task.project_id}",
                        "idempotency_key": f"eq.{task.idempotency_key}",
                    },
                )
                if existing:
                    return _task_from_row(existing)
            raise
        return _task_from_row(row or body)

    def get_task(self, task_id: str) -> Task:
        row = self.client.select_one("tasks", columns=_TASK_COLUMNS, params={"task_id": f"eq.{task_id}"})
        if not row:
            raise KeyError(task_id)
        return _task_from_row(row)

    def update_task(self, task: Task) -> Task:
        body: dict[str, Any] = {
            "status": task.status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if task.lease_expires_at:
            body["lease_expires_at"] = task.lease_expires_at.replace("Z", "+00:00")
        if task.heartbeat_at:
            body["heartbeat_at"] = task.heartbeat_at.replace("Z", "+00:00")
        if task.started_at:
            body["started_at"] = task.started_at.replace("Z", "+00:00")
        if task.finished_at:
            body["finished_at"] = task.finished_at.replace("Z", "+00:00")
        if task.available_at:
            body["available_at"] = task.available_at.replace("Z", "+00:00")
        if task.last_error_code is not None:
            body["last_error_code"] = task.last_error_code
        if task.correlation_id:
            body["correlation_id"] = task.correlation_id
        row = self.client.patch("tasks", {"task_id": f"eq.{task.task_id}"}, body)
        return _task_from_row(row) if row else task

    def update_attempt(self, attempt: TaskAttempt) -> TaskAttempt:
        # task_attempts is append-only (prevent_update trigger); the authoritative status
        # lives on the tasks row. No-op here so TaskService.complete/fail stay compatible.
        return attempt

    def list_tasks(self, *, user_id: str, project_id: str) -> list[Task]:
        rows = self.client.select(
            "tasks",
            columns=_TASK_COLUMNS,
            params={"user_id": f"eq.{user_id}", "project_id": f"eq.{project_id}"},
            order="created_at.desc",
        )
        return [_task_from_row(r) for r in rows]

    def claim_next(self, request: TaskClaimRequest, *, now: datetime) -> TaskClaim | None:
        row = self.client.rpc("claim_next_task", {"p_worker_id": request.worker_id})
        # PostgREST returns an all-NULL row (not empty) when the RPC finds no task.
        if not row or row.get("task_id") is None:
            return None
        task = _task_from_row(row)
        if request.supported_kinds and task.kind not in request.supported_kinds:
            # The RPC claims any queued task; put it back if unsupported.
            self.client.patch(
                "tasks",
                {"task_id": f"eq.{task.task_id}"},
                {"status": "queued", "attempt": task.attempt - 1, "updated_at": now.isoformat()},
            )
            return None
        attempt_row = self.client.select_one(
            "task_attempts",
            columns="attempt_id,task_id,attempt_number,status,started_at,worker_id,finished_at,error_code,safe_error_message,user_id,project_id,run_id",
            params={"task_id": f"eq.{task.task_id}", "order": "attempt_number.desc"},
        )
        attempt = _attempt_from_row(attempt_row) if attempt_row else TaskAttempt(
            attempt_id="",
            task_id=task.task_id,
            attempt_number=task.attempt,
            status=TaskAttemptStatus.RUNNING,
            started_at=now.isoformat(),
            worker_id=request.worker_id,
            user_id=task.user_id,
            project_id=task.project_id,
            run_id=task.run_id,
        )
        return TaskClaim(task=task, attempt=attempt)


class SupabaseTerminalRepository:
    def __init__(self, client: PostgrestClient) -> None:
        self.client = client

    def append(self, event: TerminalEventCreate) -> TerminalEvent:
        level_value = event.level.value if hasattr(event.level, "value") else str(event.level)
        type_value = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
        body = {
            "user_id": event.user_id,
            "project_id": event.project_id,
            "level": level_value,
            "event_type": type_value,
            "message": event.message,
            "safe_payload": event.safe_payload,
        }
        if event.run_id:
            body["run_id"] = event.run_id
        if event.task_id:
            body["task_id"] = event.task_id
        if event.attempt_id:
            body["attempt_id"] = event.attempt_id
        row = self.client.insert("terminal_events", body)
        row = row or {}
        return TerminalEvent(
            event_id=str(row.get("event_id") or ""),
            user_id=event.user_id,
            project_id=event.project_id,
            level=event.level,
            event_type=event.event_type,
            message=event.message,
            safe_payload=event.safe_payload,
            created_at=_iso(row.get("created_at")) or "",
            run_id=event.run_id,
            task_id=event.task_id,
            attempt_id=event.attempt_id,
            sequence=row.get("sequence"),
        )

    def list_project_events(self, *, user_id: str, project_id: str, after_sequence: int | None, limit: int) -> TerminalPage:
        params = {"user_id": f"eq.{user_id}", "project_id": f"eq.{project_id}"}
        if after_sequence is not None:
            params["sequence"] = f"gt.{after_sequence}"
        rows = self.client.select(
            "terminal_events",
            columns="event_id,sequence,user_id,project_id,run_id,task_id,attempt_id,level,event_type,message,safe_payload,created_at",
            params=params,
            limit=limit,
            order="sequence.asc",
        )
        events = [_event_from_row(r) for r in rows]
        next_cursor = events[-1].sequence if events and events[-1].sequence is not None else after_sequence
        return TerminalPage(events=tuple(events), next_cursor=next_cursor)