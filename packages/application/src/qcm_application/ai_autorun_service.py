"""AI Auto Run deterministic orchestration foundation."""

from dataclasses import replace
from datetime import datetime, timezone
import json
from typing import Any, Protocol

from qcm_application.artifact_service import checksum_bytes
from qcm_application.ownership import AuthorizationError
from qcm_domain.ai_autorun import (
    AiAutoRunGate,
    AiDocumentMap,
    AiDocumentMapPage,
    assert_safe_summary,
    evaluate_ai_quality,
    validate_ai_generated_config,
)
from qcm_shared.ai_autorun_contracts import (
    AI_AUTORUN_SCHEMA_VERSION,
    AI_AUTORUN_TASK_KIND,
    AiAutoRunAction,
    AiAutoRunActionCommand,
    AiAutoRunRecord,
    AiAutoRunResult,
    AiAutoRunStartCommand,
    AiAutoRunStatus,
    AiGeneratedConfigs,
)
from qcm_shared.contracts import ArtifactType, RetentionPolicy
from qcm_shared.provider_contracts import ModelAuthorization
from qcm_shared.storage_contracts import ArtifactWriteRequest
from qcm_shared.task_contracts import TaskCreateCommand


class AiAutoRunTaskCreator(Protocol):
    def create_task(self, command: TaskCreateCommand):
        ...


class AiAutoRunArtifactSink(Protocol):
    def write(self, request: ArtifactWriteRequest) -> str:
        ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryAiAutoRunRepository:
    def __init__(self) -> None:
        self.records: dict[str, AiAutoRunRecord] = {}
        self.idempotency: dict[tuple[str, str], str] = {}

    def save(self, record: AiAutoRunRecord, *, idempotency_key: str | None = None) -> AiAutoRunRecord:
        self.records[record.ai_run_id] = record
        if idempotency_key:
            self.idempotency[(record.user_id, idempotency_key)] = record.ai_run_id
        return record

    def get_idempotent(self, *, user_id: str, idempotency_key: str) -> AiAutoRunRecord | None:
        ai_run_id = self.idempotency.get((user_id, idempotency_key))
        return self.records.get(ai_run_id) if ai_run_id else None

    def get_owned(self, *, user_id: str, project_id: str, ai_run_id: str) -> AiAutoRunRecord:
        record = self.records[ai_run_id]
        if record.user_id != user_id or record.project_id != project_id:
            raise AuthorizationError("AI Auto Run does not belong to requester")
        return record


class AiAutoRunService:
    def __init__(
        self,
        *,
        repository: InMemoryAiAutoRunRepository | None = None,
        task_creator: AiAutoRunTaskCreator | None = None,
        artifact_sink: AiAutoRunArtifactSink | None = None,
        model_authorization: ModelAuthorization | None = None,
    ) -> None:
        self.repository = repository or InMemoryAiAutoRunRepository()
        self.task_creator = task_creator
        self.artifact_sink = artifact_sink
        self.model_authorization = model_authorization or ModelAuthorization()

    def start(self, command: AiAutoRunStartCommand) -> AiAutoRunRecord:
        existing = self.repository.get_idempotent(user_id=command.user_id, idempotency_key=command.idempotency_key)
        if existing is not None:
            return existing
        self._validate_start(command)
        record = AiAutoRunRecord(
            ai_run_id=command.ai_run_id,
            user_id=command.user_id,
            project_id=command.project_id,
            run_id=command.run_id,
            status=AiAutoRunStatus.QUEUED,
            model_selection=command.model_selection,
            created_at=_now(),
            updated_at=_now(),
        )
        if self.task_creator is not None:
            task = self.task_creator.create_task(
                TaskCreateCommand(
                    user_id=command.user_id,
                    project_id=command.project_id,
                    run_id=command.run_id,
                    kind=AI_AUTORUN_TASK_KIND,
                    idempotency_key=command.idempotency_key,
                    correlation_id=command.correlation_id,
                    payload=_command_payload(command),
                )
            )
            record = replace(record, artifact_ids=(task.task_id,))
        return self.repository.save(record, idempotency_key=command.idempotency_key)

    def plan(self, command: AiAutoRunStartCommand) -> AiAutoRunResult:
        self._validate_start(command)
        document_map = build_document_map(command.pages)
        generated = AiGeneratedConfigs(
            step2_config={
                "template_name": command.user_constraints.get("template_name", "default"),
                "output_format": "json+xlsx",
                "metadata_source": "ai_autorun",
            },
            step3_correction_config={
                "mode": command.user_constraints.get("correction_mode", "page_detection"),
                "selected_pages": [
                    page.page_number for page in document_map.pages if page.role in {"correction", "answer_key"}
                ],
                "include_neighbors": True,
            },
        )
        config_errors = validate_ai_generated_config(generated.step2_config, required_keys=("template_name", "output_format"))
        gate, warnings = evaluate_ai_quality(document_map=document_map, config_errors=config_errors)
        status = {
            AiAutoRunGate.PASSED: AiAutoRunStatus.COMPLETED,
            AiAutoRunGate.MANUAL_INTERVENTION: AiAutoRunStatus.MANUAL_INTERVENTION_REQUIRED,
            AiAutoRunGate.SAFE_STOP: AiAutoRunStatus.FAILED,
        }[gate]
        evidence = tuple(
            {
                "page_number": page.page_number,
                "role": page.role,
                "confidence": page.confidence,
                "summary": page.evidence_summary,
            }
            for page in document_map.pages
        )
        artifact_ids = self._write_plan_artifacts(command, document_map=document_map, generated=generated, evidence=evidence)
        return AiAutoRunResult(
            ai_run_id=command.ai_run_id,
            status=status,
            document_map=_document_map_payload(document_map),
            generated_configs=generated,
            evidence_summaries=evidence,
            artifact_ids=artifact_ids,
            warnings=warnings,
            safe_stop_reason="; ".join(config_errors) if config_errors else None,
        )

    def action(self, command: AiAutoRunActionCommand) -> AiAutoRunRecord:
        record = self.repository.get_owned(
            user_id=command.user_id,
            project_id=command.project_id,
            ai_run_id=command.ai_run_id,
        )
        action = command.action if isinstance(command.action, AiAutoRunAction) else AiAutoRunAction(command.action)
        target = {
            AiAutoRunAction.RETRY: AiAutoRunStatus.QUEUED,
            AiAutoRunAction.CANCEL: AiAutoRunStatus.CANCELLED,
            AiAutoRunAction.CONTINUE: AiAutoRunStatus.RUNNING,
        }[action]
        return self.repository.save(replace(record, status=target, updated_at=_now()))

    def _validate_start(self, command: AiAutoRunStartCommand) -> None:
        if not command.user_id or not command.project_id or not command.run_id or not command.ai_run_id:
            raise ValueError("AI Auto Run requires owner, project, run, and AI run identifiers")
        if not command.pages:
            raise ValueError("AI Auto Run requires page inputs")
        unauthorized = [model_id for model_id in command.model_selection.ordered_models() if not self.model_authorization.allows(model_id)]
        if unauthorized:
            raise ValueError(f"Unauthorized AI Auto Run model: {unauthorized[0]}")
        for value in command.user_constraints.values():
            if isinstance(value, str):
                assert_safe_summary(value)

    def _write_plan_artifacts(
        self,
        command: AiAutoRunStartCommand,
        *,
        document_map: AiDocumentMap,
        generated: AiGeneratedConfigs,
        evidence: tuple[dict[str, Any], ...],
    ) -> tuple[str, ...]:
        artifact_ids: list[str] = []
        artifacts = (
            (
                f"{command.ai_run_id}-document-map",
                ArtifactType.AI_AUTORUN_DOCUMENT_MAP,
                "ai-autorun-document-map.json",
                _json_bytes(_document_map_payload(document_map)),
            ),
            (
                f"{command.ai_run_id}-generated-config",
                ArtifactType.AI_AUTORUN_CONFIG,
                "ai-autorun-generated-config.json",
                _json_bytes(
                    {
                        "step2_config": generated.step2_config,
                        "step3_correction_config": generated.step3_correction_config,
                    }
                ),
            ),
            (
                f"{command.ai_run_id}-evidence",
                ArtifactType.AI_AUTORUN_EVIDENCE,
                "ai-autorun-evidence.json",
                _json_bytes({"evidence": list(evidence)}),
            ),
        )
        for artifact_id, artifact_type, filename, content in artifacts:
            request = ArtifactWriteRequest(
                user_id=command.user_id,
                project_id=command.project_id,
                run_id=command.run_id,
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                filename=filename,
                content_type="application/json",
                content=content,
                version_number=1,
                checksum=checksum_bytes(content),
                schema_version=AI_AUTORUN_SCHEMA_VERSION,
                retention_policy=RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
            )
            artifact_ids.append(self.artifact_sink.write(request) if self.artifact_sink else artifact_id)
        return tuple(artifact_ids)


def build_document_map(pages) -> AiDocumentMap:
    mapped: list[AiDocumentMapPage] = []
    for page in pages:
        text = page.text.lower()
        if "correction" in text or "answer" in text:
            role = "correction"
            confidence = 0.82
        elif "qcm" in text or "question" in text:
            role = "question"
            confidence = 0.76
        else:
            role = "context"
            confidence = 0.5
        mapped.append(
            AiDocumentMapPage(
                page_number=page.page_number,
                role=role,
                confidence=confidence,
                evidence_summary=f"Page {page.page_number} classified as {role}",
            )
        )
    return AiDocumentMap(tuple(mapped))


def _document_map_payload(document_map: AiDocumentMap) -> dict[str, Any]:
    return {
        "pages": [
            {
                "page_number": page.page_number,
                "role": page.role,
                "confidence": page.confidence,
                "evidence_summary": page.evidence_summary,
            }
            for page in document_map.pages
        ]
    }


def _command_payload(command: AiAutoRunStartCommand) -> dict[str, Any]:
    return {
        "user_id": command.user_id,
        "project_id": command.project_id,
        "run_id": command.run_id,
        "ai_run_id": command.ai_run_id,
        "pages": [
            {"page_number": page.page_number, "text": page.text, "source_artifact_id": page.source_artifact_id}
            for page in command.pages
        ],
        "model_selection": {
            "provider": command.model_selection.provider.value,
            "primary_model_id": command.model_selection.primary_model_id,
            "fallback_model_ids": list(command.model_selection.fallback_model_ids),
        },
        "user_constraints": command.user_constraints,
    }


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
