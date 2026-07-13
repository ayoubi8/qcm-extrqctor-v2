"""Shared contracts and registries for API, worker, and frontend boundaries."""

from qcm_shared.auth_contracts import AuthenticatedSession, ModelPreference, Profile, SessionTokens
from qcm_shared.contracts import (
    ApiError,
    Artifact,
    ArtifactType,
    ArtifactVersion,
    ConfigurationSnapshot,
    QualityEvaluation,
    Task,
    TaskAttempt,
    TaskStatus,
    TerminalEvent,
    UsageRecord,
)
from qcm_shared.task_contracts import TaskClaim, TaskCreateCommand, TerminalPage
from qcm_shared.storage_contracts import SignedUrlRequest, SignedUrlResponse, UploadInitRequest
from qcm_shared.api_contracts import ConfigSnapshotDraft, ProjectCreateCommand, RunStepCommand
from qcm_shared.ai_autorun_contracts import AiAutoRunResult, AiAutoRunStartCommand
from qcm_shared.provider_contracts import ModelSelection, ProviderKey
from qcm_shared.autorun_contracts import ManualAutoRunSnapshot, ManualAutoRunStartCommand
from qcm_shared.step4_contracts import Step4SimilarityConfig, Step4SimilarityResult

__all__ = [
    "ApiError",
    "AiAutoRunResult",
    "AiAutoRunStartCommand",
    "ManualAutoRunSnapshot",
    "ManualAutoRunStartCommand",
    "AuthenticatedSession",
    "Artifact",
    "ArtifactType",
    "ArtifactVersion",
    "ConfigurationSnapshot",
    "ModelPreference",
    "Profile",
    "ConfigSnapshotDraft",
    "ModelSelection",
    "ProjectCreateCommand",
    "ProviderKey",
    "QualityEvaluation",
    "SessionTokens",
    "SignedUrlRequest",
    "SignedUrlResponse",
    "Task",
    "TaskAttempt",
    "TaskClaim",
    "TaskCreateCommand",
    "TaskStatus",
    "TerminalEvent",
    "TerminalPage",
    "UploadInitRequest",
    "RunStepCommand",
    "Step4SimilarityConfig",
    "Step4SimilarityResult",
    "UsageRecord",
]
