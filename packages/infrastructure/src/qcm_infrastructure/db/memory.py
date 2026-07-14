"""In-memory project and pipeline-run repositories for local/contract verification."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from qcm_shared.api_contracts import ProjectCreateCommand, ProjectSummary


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[str, ProjectSummary] = {}
        self.idempotency: dict[tuple[str, str], str] = {}

    def create_project(self, command: ProjectCreateCommand) -> ProjectSummary:
        key = (command.user_id, command.idempotency_key)
        if key in self.idempotency:
            return self.projects[self.idempotency[key]]
        project = ProjectSummary(
            project_id=str(uuid4()),
            user_id=command.user_id,
            name=command.name or "Untitled project",
            status="active",
            updated_at=_utc_now(),
        )
        self.projects[project.project_id] = project
        self.idempotency[key] = project.project_id
        return project

    def get_project(self, *, user_id: str, project_id: str) -> ProjectSummary | None:
        project = self.projects.get(project_id)
        if project is None or project.user_id != user_id:
            return None
        return project

    def list_projects(self, *, user_id: str) -> list[ProjectSummary]:
        return [p for p in self.projects.values() if p.user_id == user_id]


class InMemoryPipelineRunRepository:
    def __init__(self) -> None:
        self.runs: dict[tuple[str, str], dict] = {}

    def ensure_run(self, *, user_id: str, project_id: str, run_id: str | None = None, triggered_by: str = "manual") -> dict:
        run_id = run_id or str(uuid4())
        key = (project_id, run_id)
        if key in self.runs:
            return self.runs[key]
        now = _utc_now()
        run = {
            "run_id": run_id,
            "user_id": user_id,
            "project_id": project_id,
            "status": "pending",
            "triggered_by": triggered_by,
            "created_at": now,
            "updated_at": now,
        }
        self.runs[key] = run
        return run

    def list_runs(self, *, user_id: str, project_id: str) -> list[dict]:
        return [
            run for run in self.runs.values()
            if run["user_id"] == user_id and run["project_id"] == project_id
        ]