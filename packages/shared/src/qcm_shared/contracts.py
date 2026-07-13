"""Shared DTO contracts aligned with Phase 12 implementation plans.

These dataclasses are intentionally dependency-light for Plan 01 verification. Later plans can
wrap or replace the validation layer with Pydantic v2 models without changing field names.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TaskStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SKIPPED = "skipped"


class TaskAttemptStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TerminalLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class TerminalEventType(StrEnum):
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    TASK_CLAIMED = "task_claimed"
    TASK_HEARTBEAT = "task_heartbeat"
    ARTIFACT_WRITTEN = "artifact_written"
    QUALITY_WARNING = "quality_warning"
    RETRY_SCHEDULED = "retry_scheduled"
    CANCEL_REQUESTED = "cancel_requested"
    TASK_FAILED = "task_failed"
    SYSTEM_MESSAGE = "system_message"


class ArtifactType(StrEnum):
    SOURCE_PDF = "source_pdf"
    PAGE_TEXT = "page_text"
    PAGE_IMAGE = "page_image"
    STEP1_TEXT = "step1_text"
    STEP2_PAGE_QCM_JSON = "step2_page_qcm_json"
    STEP2_FINAL_JSON = "step2_final_json"
    STEP2_FINAL_XLSX = "step2_final_xlsx"
    STEP3_CORRECTION_JSON = "step3_correction_json"
    STEP3_CORRECTION_XLSX = "step3_correction_xlsx"
    STEP4_SIMILARITY_JSON = "step4_similarity_json"
    STEP4_SIMILARITY_XLSX = "step4_similarity_xlsx"
    REFERENCE_DB = "reference_db"
    AI_AUTORUN_DOCUMENT_MAP = "ai_autorun_document_map"
    AI_AUTORUN_CONFIG = "ai_autorun_config"
    AI_AUTORUN_EVIDENCE = "ai_autorun_evidence"
    DEBUG_INTERNAL = "debug_internal"
    LEGACY_IMPORT = "legacy_import"


class RetentionPolicy(StrEnum):
    SOURCE_UNTIL_PROJECT_DELETE = "source_until_project_delete"
    FINAL_UNTIL_PROJECT_DELETE = "final_until_project_delete"
    INTERMEDIATE_CLEANUP = "intermediate_cleanup"
    DEBUG_SHORT_LIVED = "debug_short_lived"
    AUDIT_RETAINED_REDACTED = "audit_retained_redacted"
    LEGACY_READ_ONLY = "legacy_read_only"


class QualityStatus(StrEnum):
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    SKIPPED = "skipped"


class ProviderLimitEvent(StrEnum):
    NONE = "none"
    RATE_LIMITED = "rate_limited"
    CONTEXT_LIMIT = "context_limit"
    TOKEN_LIMIT = "token_limit"
    FILE_SIZE_LIMIT = "file_size_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ApiError:
    code: str
    message: str
    correlation_id: str
    retryable: bool
    details: dict[str, Any] | None = None
    safe_user_action: str | None = None


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    user_id: str
    project_id: str
    run_id: str
    kind: str
    status: TaskStatus
    idempotency_key: str
    attempt: int
    max_attempts: int
    payload: dict[str, Any]
    created_at: str
    updated_at: str
    available_at: str
    lease_expires_at: str | None = None
    heartbeat_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    priority: int = 0
    correlation_id: str | None = None
    last_error_code: str | None = None

    def __post_init__(self) -> None:
        required = [self.task_id, self.user_id, self.project_id, self.run_id, self.idempotency_key]
        if any(not value for value in required):
            raise ValueError("Task requires task, owner, project, run, and idempotency identifiers")
        if self.max_attempts < 1:
            raise ValueError("Task max_attempts must be at least 1")
        if self.attempt < 0:
            raise ValueError("Task attempt cannot be negative")


@dataclass(frozen=True, slots=True)
class TaskAttempt:
    attempt_id: str
    task_id: str
    attempt_number: int
    status: TaskAttemptStatus
    started_at: str
    worker_id: str
    finished_at: str | None = None
    error_code: str | None = None
    safe_error_message: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        if not self.attempt_id or not self.task_id or not self.worker_id:
            raise ValueError("TaskAttempt requires attempt, task, and worker identifiers")
        if self.attempt_number < 1:
            raise ValueError("TaskAttempt attempt_number starts at 1")


@dataclass(frozen=True, slots=True)
class TerminalEvent:
    event_id: str
    user_id: str
    project_id: str
    level: TerminalLevel
    event_type: TerminalEventType
    message: str
    safe_payload: dict[str, Any]
    created_at: str
    run_id: str | None = None
    task_id: str | None = None
    attempt_id: str | None = None
    sequence: int | None = None


@dataclass(frozen=True, slots=True)
class Artifact:
    artifact_id: str
    user_id: str
    project_id: str
    artifact_type: ArtifactType
    created_at: str
    updated_at: str
    run_id: str | None = None
    latest_version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactVersion:
    artifact_version_id: str
    artifact_id: str
    version_number: int
    storage_key: str
    content_type: str
    checksum: str
    size_bytes: int
    schema_version: str
    retention_policy: RetentionPolicy
    created_at: str
    source_artifact_ids: list[str] = field(default_factory=list)
    user_id: str | None = None
    project_id: str | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        if self.version_number < 1:
            raise ValueError("ArtifactVersion version_number starts at 1")
        if self.size_bytes < 0:
            raise ValueError("ArtifactVersion size_bytes cannot be negative")
        if not self.storage_key:
            raise ValueError("ArtifactVersion requires storage_key")


@dataclass(frozen=True, slots=True)
class ConfigurationSnapshot:
    snapshot_id: str
    schema_version: str
    source_precedence: list[str]
    resolved_values: dict[str, Any]
    secret_refs: dict[str, Any]
    created_by: str
    run_id: str
    created_at: str


@dataclass(frozen=True, slots=True)
class QualityEvaluation:
    evaluation_id: str
    run_id: str
    status: QualityStatus
    metrics: dict[str, Any]
    warnings: list[str]
    failures: list[str]
    manual_review_required: bool
    evidence_artifact_ids: list[str]
    artifact_id: str | None = None


@dataclass(frozen=True, slots=True)
class UsageRecord:
    usage_id: str
    user_id: str
    provider: str
    operation: str
    tokens_in: int
    tokens_out: int
    provider_limit_event: ProviderLimitEvent
    created_at: str
    project_id: str | None = None
    run_id: str | None = None
    task_id: str | None = None
    model_id: str | None = None
    cost_estimate: float | None = None

    def __post_init__(self) -> None:
        if not self.usage_id or not self.user_id or not self.provider or not self.operation:
            raise ValueError("UsageRecord requires usage, owner, provider, and operation")
        if self.tokens_in < 0 or self.tokens_out < 0:
            raise ValueError("UsageRecord token counts cannot be negative")
