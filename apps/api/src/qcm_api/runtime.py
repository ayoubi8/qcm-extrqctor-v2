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
    def __init__(self, project_repo, run_repo, task_repository, terminal_repository, artifact_service=None) -> None:
        self.project_repo = project_repo
        self.run_repo = run_repo
        self.task_repository = task_repository
        self.terminal_repository = terminal_repository
        self.artifact_service = artifact_service
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
            "artifacts": self.artifact_service.list_artifacts(user_id=user_id, project_id=project_id) if self.artifact_service else [],
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
    def __init__(self, storage=None, artifact_repo=None, source_file_repo=None) -> None:
        self.storage = storage
        self.artifact_repo = artifact_repo
        self.source_file_repo = source_file_repo

    def initialize_upload(self, request: UploadInitRequest):
        return initialize_upload(request)

    def create_signed_url(self, request: SignedUrlRequest) -> SignedUrlResponse:
        expires = request.expires_in_seconds or 900
        if self.storage is None:
            return SignedUrlResponse(
                artifact_version_id=request.artifact_version_id,
                signed_url="",
                expires_in_seconds=expires,
            )
        version = self.artifact_repo.get_version_for_signed_url(request.artifact_version_id)
        if version is None:
            raise KeyError(request.artifact_version_id)
        owner = str(version.get("user_id") or "")
        if owner and owner != request.requester_user_id:
            from qcm_application.ownership import AuthorizationError
            raise AuthorizationError("Artifact version does not belong to requester")
        signed = self.storage.create_signed_url(str(version["storage_key"]), expires)
        return SignedUrlResponse(
            artifact_version_id=request.artifact_version_id,
            signed_url=signed,
            expires_in_seconds=expires,
        )

    def upload_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> dict:
        from hashlib import sha256
        from qcm_domain.artifacts import StoragePathContext, build_storage_key, validate_source_file_size
        from qcm_shared.contracts import ArtifactType, RetentionPolicy

        validate_source_file_size(len(content))
        checksum = sha256(content).hexdigest()
        artifact_id = str(uuid4())
        context = StoragePathContext(
            user_id=user_id,
            project_id=project_id,
            run_id=None,
            artifact_type=ArtifactType.SOURCE_PDF,
            artifact_id=artifact_id,
            version_number=1,
            filename=filename,
        )
        storage_key = build_storage_key(context)
        self.storage.put(storage_key, content, content_type)
        sf = self.source_file_repo.create_source_file(
            user_id=user_id,
            project_id=project_id,
            original_filename=filename,
            storage_key=storage_key,
            content_type=content_type,
            size_bytes=len(content),
            checksum=checksum,
        )
        art = self.artifact_repo.create_artifact(
            user_id=user_id,
            project_id=project_id,
            artifact_type=ArtifactType.SOURCE_PDF.value,
            name=filename,
            run_id=None,
        )
        ver = self.artifact_repo.create_version(
            artifact_id=art["artifact_id"],
            user_id=user_id,
            project_id=project_id,
            version_number=1,
            storage_key=storage_key,
            content_type=content_type,
            checksum=checksum,
            size_bytes=len(content),
            schema_version="source_pdf.v1",
            retention_policy=RetentionPolicy.SOURCE_UNTIL_PROJECT_DELETE.value,
            run_id=None,
        )
        return {
            "source_file_id": sf["source_file_id"],
            "artifact_id": art["artifact_id"],
            "artifact_version_id": ver["artifact_version_id"],
            "storage_key": storage_key,
            "checksum": checksum,
            "allowed": True,
        }

    def list_artifacts(self, *, user_id: str, project_id: str) -> list[dict]:
        if self.artifact_repo is None:
            return []
        rows = self.artifact_repo.list_versions_for_project(user_id=user_id, project_id=project_id)
        return [
            {
                "artifactVersionId": r.get("artifact_version_id"),
                "artifactId": r.get("artifact_id"),
                "artifactType": "source_pdf",
                "filename": "",
                "contentType": r.get("content_type", ""),
                "versionNumber": int(r.get("version_number") or 1),
                "createdAt": r.get("created_at") or "",
                "sizeBytes": int(r.get("size_bytes") or 0),
                "checksum": r.get("checksum"),
                "runId": r.get("run_id"),
            }
            for r in rows
        ]


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
        artifact_service: RuntimeArtifactService
        if _supabase_env_present():
            from qcm_infrastructure.db.repositories import (
                SupabaseArtifactRepository,
                SupabasePipelineRunRepository,
                SupabaseProjectRepository,
                SupabaseSourceFileRepository,
                SupabaseTaskRepository,
                SupabaseTerminalRepository,
            )
            from qcm_infrastructure.storage.rest_adapter import SupabaseStorageRestAdapter

            client = _build_supabase_client()
            project_repo = SupabaseProjectRepository(client)
            run_repo = SupabasePipelineRunRepository(client)
            task_repository = SupabaseTaskRepository(client)
            terminal_repository = SupabaseTerminalRepository(client)
            storage = SupabaseStorageRestAdapter(
                os.getenv("SUPABASE_URL", ""),
                os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "",
                service_role=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            )
            artifact_repo = SupabaseArtifactRepository(client)
            source_file_repo = SupabaseSourceFileRepository(client)
            artifact_service = RuntimeArtifactService(
                storage=storage, artifact_repo=artifact_repo, source_file_repo=source_file_repo
            )
        else:
            project_repo = InMemoryProjectRepository()
            run_repo = InMemoryPipelineRunRepository()
            task_repository = InMemoryTaskRepository()
            terminal_repository = InMemoryTerminalRepository()
            artifact_service = RuntimeArtifactService()

        self.task_service = TaskService(task_repository, terminal_repository)
        self.project_service = RuntimeProjectService(project_repo, run_repo, task_repository, terminal_repository, artifact_service)
        self.artifact_service = artifact_service
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