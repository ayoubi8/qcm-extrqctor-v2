"""Backend API command/response contracts."""

from dataclasses import dataclass, field
from typing import Any

from qcm_domain.enums import ProductStepKey
from qcm_shared.contracts import Artifact, Task
from qcm_shared.provider_contracts import ModelSelection


@dataclass(frozen=True, slots=True)
class Pagination:
    limit: int = 50
    cursor: str | None = None

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 200:
            raise ValueError("Pagination limit must be between 1 and 200")


@dataclass(frozen=True, slots=True)
class ProjectCreateCommand:
    user_id: str
    name: str
    correlation_id: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    project_id: str
    user_id: str
    name: str
    status: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class RunStepCommand:
    user_id: str
    project_id: str
    run_id: str
    step_key: ProductStepKey
    idempotency_key: str
    correlation_id: str
    config_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConfigResolveCommand:
    user_id: str
    project_id: str
    run_id: str
    correlation_id: str
    system_defaults: dict[str, Any]
    user_defaults: dict[str, Any] = field(default_factory=dict)
    project_defaults: dict[str, Any] = field(default_factory=dict)
    run_overrides: dict[str, Any] = field(default_factory=dict)
    manual_auto_run_overrides: dict[str, Any] = field(default_factory=dict)
    ai_proposal_values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConfigSnapshotDraft:
    schema_version: str
    source_precedence: tuple[str, ...]
    resolved_values: dict[str, Any]
    secret_refs: dict[str, Any]
    created_by: str
    run_id: str
    config_hash: str


@dataclass(frozen=True, slots=True)
class ModelListResponse:
    selections: dict[str, ModelSelection]


@dataclass(frozen=True, slots=True)
class RunStepResponse:
    task: Task
    config_snapshot: ConfigSnapshotDraft
    artifacts: tuple[Artifact, ...] = ()
