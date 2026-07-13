"""Manual Auto Run contracts."""

from dataclasses import dataclass, field
from qcm_shared.compat import StrEnum
from typing import Any

MANUAL_AUTORUN_TASK_KIND = "manual_autorun"
MANUAL_AUTORUN_SCHEMA_VERSION = "manual-autorun.v1"


class ManualAutoRunStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ManualAutoRunControlAction(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    RETRY = "retry"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class ManualAutoRunStepConfig:
    step_key: str
    task_kind: str
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ManualAutoRunSnapshot:
    schema_version: str
    selected_steps: tuple[ManualAutoRunStepConfig, ...]
    saved_defaults: dict[str, Any] = field(default_factory=dict)
    project_overrides: dict[str, Any] = field(default_factory=dict)
    resource_limits: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ManualAutoRunStartCommand:
    user_id: str
    project_id: str
    run_id: str
    auto_run_id: str
    snapshot: ManualAutoRunSnapshot
    idempotency_key: str
    correlation_id: str


@dataclass(frozen=True, slots=True)
class ManualAutoRunValidation:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    normalized_steps: tuple[ManualAutoRunStepConfig, ...] = ()


@dataclass(frozen=True, slots=True)
class ManualAutoRunRecord:
    auto_run_id: str
    user_id: str
    project_id: str
    run_id: str
    status: ManualAutoRunStatus
    snapshot: ManualAutoRunSnapshot
    child_task_ids: tuple[str, ...] = ()
    current_step_key: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True, slots=True)
class ManualAutoRunControlCommand:
    user_id: str
    project_id: str
    auto_run_id: str
    action: ManualAutoRunControlAction | str
    correlation_id: str


@dataclass(frozen=True, slots=True)
class ManualAutoRunReport:
    auto_run_id: str
    status: ManualAutoRunStatus
    child_task_ids: tuple[str, ...]
    completed_steps: tuple[str, ...]
    warnings: tuple[str, ...] = ()
