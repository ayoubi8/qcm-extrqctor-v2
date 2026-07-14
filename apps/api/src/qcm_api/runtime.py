"""Runtime service wiring for the deployed API.

When Supabase settings are present the API binds durable PostgREST repositories
(service-role; ownership still enforced by the auth dependency and user_id filtering).
Otherwise it falls back to in-memory repositories so contract/verify scripts stay green.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from qcm_application.ai_autorun_service import AiAutoRunService
from qcm_application.artifact_service import initialize_upload
from qcm_application.autorun_service import ManualAutoRunService
from qcm_application.config_resolver import ConfigSource, resolve_configuration
from qcm_application.reference_db_service import ReferenceDbService
from qcm_application.task_service import TaskService
from qcm_infrastructure.db.memory import InMemoryPipelineRunRepository, InMemoryProjectRepository
from qcm_infrastructure.tasks.memory import InMemoryTaskRepository, InMemoryTerminalRepository
from qcm_shared.api_contracts import ConfigResolveCommand, ProjectCreateCommand, ProjectSummary
from qcm_shared.contracts import Task
from qcm_shared.provider_contracts import ModelAuthorization, ModelSelection, ProviderKey
from qcm_shared.storage_contracts import SignedUrlRequest, SignedUrlResponse, UploadInitRequest
from qcm_shared.task_contracts import TerminalEventCreate
from qcm_shared.contracts import TerminalEventType, TerminalLevel


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _supabase_env_present() -> bool:
    return bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def _build_supabase_client():
    from qcm_infrastructure.db.postgrest import PostgrestClient

    return PostgrestClient(
        base_url=os.getenv("SUPABASE_URL", ""),
        api_key=os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "",
        service_role=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )


class RuntimeProjectService:
    def __init__(self, project_repo, run_repo, task_repository, terminal_repository) -> None:
        self.project_repo = project_repo
        self.run_repo = run_repo
        self.task_repository = task_repository
        self.terminal_repository = terminal_repository
        self.seeded_projects: set[str] = set()

    def create_project(self, command: ProjectCreateCommand) -> ProjectSummary:
        project = self.project_repo.create_project(command)
        self.run_repo.ensure_run(user_id=project.user_id, project_id=project.project_id)
        self._seed_terminal(project.user_id, project.project_id, None, "Project workspace created")
        return project

    def snapshot(self, *, user_id: str, project_id: str) -> dict:
        project = self.project_repo.get_project(user_id=user_id, project_id=project_id)
        if project is None:
            raise KeyError(project_id)
        runs = self.run_repo.list_runs(user_id=user_id, project_id=project_id)
        tasks = self._task_summaries(user_id=user_id, project_id=project_id)
        return {
            "project": asdict(project),
            "runs": [
                {
                    "runId": run["run_id"],
                    "projectId": run["project_id"],
                    "label": "Run",
                    "status": run["status"],
                    "createdAt": run["created_at"],
                    "updatedAt": run["updated_at"],
                }
                for run in runs
            ],
            "tasks": tasks,
            "artifacts": [],
        }

    def _task_summaries(self, *, user_id: str, project_id: str) -> list[dict]:
        tasks = self.task_repository.list_tasks(user_id=user_id, project_id=project_id) if hasattr(self.task_repository, "list_tasks") else []
        return [
            {
                "taskId": task.task_id,
                "kind": task.kind,
                "status": task.status.value,
                "runId": task.run_id,
                "updatedAt": task.updated_at,
                "safeMessage": task.last_error_code,
            }
            for task in tasks
        ]

    def _seed_terminal(self, user_id: str, project_id: str, run_id: str | None, message: str) -> None:
        key = (user_id, project_id)
        if key in self.seeded_projects:
            return
        runs = self.run_repo.list_runs(user_id=user_id, project_id=project_id)
        seed_run = run_id or (runs[0]["run_id"] if runs else None)
        self.terminal_repository.append(
            TerminalEventCreate(
                user_id=user_id,
                project_id=project_id,
                run_id=seed_run,
                level=TerminalLevel.SUCCESS,
                event_type=TerminalEventType.SYSTEM_MESSAGE,
                message=message,
                safe_payload={"runtime": "vps-api"},
            )
        )
        self.seeded_projects.add(key)


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
        task_repository: object
        terminal_repository: object
        project_repo: object
        run_repo: object
        if _supabase_env_present():
            from qcm_infrastructure.db.repositories import (
                SupabasePipelineRunRepository,
                SupabaseProjectRepository,
                SupabaseTaskRepository,
                SupabaseTerminalRepository,
            )

            client = _build_supabase_client()
            project_repo = SupabaseProjectRepository(client)
            run_repo = SupabasePipelineRunRepository(client)
            task_repository = SupabaseTaskRepository(client)
            terminal_repository = SupabaseTerminalRepository(client)
        else:
            project_repo = InMemoryProjectRepository()
            run_repo = InMemoryPipelineRunRepository()
            task_repository = InMemoryTaskRepository()
            terminal_repository = InMemoryTerminalRepository()

        self.task_service = TaskService(task_repository, terminal_repository)
        self.project_service = RuntimeProjectService(project_repo, run_repo, task_repository, terminal_repository)
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