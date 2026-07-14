"""Runtime service wiring for the deployed API.

These services provide a live, lightweight backend foundation while durable repository
adapters are brought online.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from qcm_application.ai_autorun_service import AiAutoRunService
from qcm_application.artifact_service import initialize_upload
from qcm_application.autorun_service import ManualAutoRunService
from qcm_application.config_resolver import ConfigSource, resolve_configuration
from qcm_application.reference_db_service import ReferenceDbService
from qcm_application.task_service import TaskService
from qcm_infrastructure.tasks.memory import InMemoryTaskRepository, InMemoryTerminalRepository
from qcm_shared.api_contracts import ConfigResolveCommand, ProjectCreateCommand, ProjectSummary
from qcm_shared.contracts import Task
from qcm_shared.provider_contracts import ModelAuthorization, ModelSelection, ProviderKey
from qcm_shared.storage_contracts import SignedUrlRequest, SignedUrlResponse, UploadInitRequest


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeProjectService:
    def __init__(self, task_repository: InMemoryTaskRepository) -> None:
        self.task_repository = task_repository
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
            updated_at=utc_now(),
        )
        self.projects[project.project_id] = project
        self.idempotency[key] = project.project_id
        return project

    def snapshot(self, *, user_id: str, project_id: str) -> dict:
        project = self.projects.get(project_id) or ProjectSummary(
            project_id=project_id,
            user_id=user_id,
            name="Demo QCM workspace",
            status="active",
            updated_at=utc_now(),
        )
        tasks = [
            self._task_summary(task)
            for task in self.task_repository.tasks.values()
            if task.user_id == user_id and task.project_id == project_id
        ]
        return {
            "project": asdict(project),
            "runs": [
                {
                    "runId": "demo-run",
                    "projectId": project_id,
                    "label": "Latest run",
                    "status": "draft",
                    "createdAt": project.updated_at,
                    "updatedAt": project.updated_at,
                }
            ],
            "tasks": tasks,
            "artifacts": [],
        }

    def _task_summary(self, task: Task) -> dict:
        return {
            "taskId": task.task_id,
            "kind": task.kind,
            "status": task.status.value,
            "runId": task.run_id,
            "updatedAt": task.updated_at,
            "safeMessage": task.last_error_code,
        }


class RuntimeArtifactService:
    def initialize_upload(self, request: UploadInitRequest):
        return initialize_upload(request)

    def create_signed_url(self, request: SignedUrlRequest) -> SignedUrlResponse:
        return SignedUrlResponse(
            artifact_version_id=request.artifact_version_id,
            signed_url="",
            expires_in_seconds=request.expires_in_seconds or 900,
        )


class RuntimeConfigService:
    def resolve(self, command: ConfigResolveCommand) -> dict:
        return {
            "schema_version": "config-resolve.v1",
            "resolved_values": resolve_configuration(
                [
                    ConfigSource("system_defaults", command.system_defaults),
                    ConfigSource("user_defaults", command.user_defaults),
                    ConfigSource("project_defaults", command.project_defaults),
                    ConfigSource("run_overrides", command.run_overrides),
                    ConfigSource("manual_auto_run_overrides", command.manual_auto_run_overrides),
                    ConfigSource("ai_proposal_values", command.ai_proposal_values),
                ]
            ),
            "correlation_id": command.correlation_id,
        }


class RuntimeModelService:
    def list_models(self) -> dict:
        selection = ModelSelection(
            provider=ProviderKey.OPENROUTER,
            primary_model_id="openai/gpt-4o-mini",
            fallback_model_ids=("meta-llama/llama-3.1-8b-instruct:free",),
        )
        return {"selections": {"default": asdict(selection)}}


class RuntimeServices:
    def __init__(self) -> None:
        task_repository = InMemoryTaskRepository()
        terminal_repository = InMemoryTerminalRepository()
        self.task_service = TaskService(task_repository, terminal_repository)
        self.project_service = RuntimeProjectService(task_repository)
        self.artifact_service = RuntimeArtifactService()
        self.config_service = RuntimeConfigService()
        self.model_service = RuntimeModelService()
        self.reference_db_service = ReferenceDbService()
        self.autorun_service = ManualAutoRunService(task_creator=self.task_service)
        self.ai_autorun_service = AiAutoRunService(
            task_creator=self.task_service,
            model_authorization=ModelAuthorization(
                allowed_model_ids={
                    "openai/gpt-4o-mini",
                    "meta-llama/llama-3.1-8b-instruct:free",
                }
            ),
        )


runtime_services = RuntimeServices()
