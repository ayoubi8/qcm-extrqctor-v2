"""Repository and recording ports for backend use cases."""

from typing import Protocol

from qcm_domain.auth import UserContext
from qcm_shared.api_contracts import ProjectCreateCommand, ProjectSummary
from qcm_shared.auth_contracts import AuditEventDraft
from qcm_shared.contracts import Task, UsageRecord  # type: ignore[attr-defined]
from qcm_shared.provider_contracts import ModelAttemptRecord, ModelSelection


class ProjectRepository(Protocol):
    def create_project(self, command: ProjectCreateCommand) -> ProjectSummary:
        ...

    def list_projects(self, user: UserContext) -> list[ProjectSummary]:
        ...

    def get_project_owner(self, project_id: str) -> str:
        ...


class TaskRepository(Protocol):
    def create_task(self, task: Task) -> Task:
        ...


class ConfigurationSnapshotRepository(Protocol):
    def save_snapshot(self, snapshot) -> object:
        ...


class ModelPreferenceRepository(Protocol):
    def get_selection(self, user_id: str, scope: str) -> ModelSelection:
        ...

    def allowed_models(self, user_id: str) -> set[str]:
        ...


class ProviderAttemptRepository(Protocol):
    def record_attempt(self, attempt: ModelAttemptRecord) -> None:
        ...


class UsageRepository(Protocol):
    def record_usage(self, usage: UsageRecord) -> None:
        ...


class AuditRepository(Protocol):
    def record(self, event: AuditEventDraft) -> None:
        ...
