"""AI Auto Run contracts."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from qcm_shared.provider_contracts import ModelSelection

AI_AUTORUN_TASK_KIND = "ai_autorun"
AI_AUTORUN_SCHEMA_VERSION = "ai-autorun.v1"


class AiAutoRunStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    MANUAL_INTERVENTION_REQUIRED = "manual_intervention_required"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AiAutoRunAction(StrEnum):
    RETRY = "retry"
    CANCEL = "cancel"
    CONTINUE = "continue"


@dataclass(frozen=True, slots=True)
class AiAutoRunPageInput:
    page_number: int
    text: str
    source_artifact_id: str | None = None


@dataclass(frozen=True, slots=True)
class AiAutoRunStartCommand:
    user_id: str
    project_id: str
    run_id: str
    ai_run_id: str
    pages: tuple[AiAutoRunPageInput, ...]
    model_selection: ModelSelection
    idempotency_key: str
    correlation_id: str
    user_constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AiGeneratedConfigs:
    step2_config: dict[str, Any]
    step3_correction_config: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AiAutoRunResult:
    ai_run_id: str
    status: AiAutoRunStatus
    document_map: dict[str, Any]
    generated_configs: AiGeneratedConfigs
    evidence_summaries: tuple[dict[str, Any], ...]
    artifact_ids: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    safe_stop_reason: str | None = None


@dataclass(frozen=True, slots=True)
class AiAutoRunRecord:
    ai_run_id: str
    user_id: str
    project_id: str
    run_id: str
    status: AiAutoRunStatus
    model_selection: ModelSelection
    artifact_ids: tuple[str, ...] = ()
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True, slots=True)
class AiAutoRunActionCommand:
    user_id: str
    project_id: str
    ai_run_id: str
    action: AiAutoRunAction | str
    correlation_id: str
