"""Shared storage, signed URL, cleanup, and legacy import DTOs."""

from dataclasses import dataclass, field
from enum import StrEnum

from qcm_shared.contracts import ArtifactType, ProviderLimitEvent, RetentionPolicy


class StorageBucket(StrEnum):
    PRIVATE_ARTIFACTS = "qcm-artifacts-private"


@dataclass(frozen=True, slots=True)
class UploadInitRequest:
    user_id: str
    project_id: str
    filename: str
    content_type: str
    size_bytes: int
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class UploadInitResponse:
    allowed: bool
    storage_key: str | None
    provider_limit_event: ProviderLimitEvent
    safe_message: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactWriteRequest:
    user_id: str
    project_id: str
    artifact_id: str
    artifact_type: ArtifactType
    filename: str
    content_type: str
    content: bytes
    version_number: int
    checksum: str
    schema_version: str
    retention_policy: RetentionPolicy
    run_id: str | None = None
    source_artifact_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SignedUrlRequest:
    requester_user_id: str
    artifact_version_id: str
    expires_in_seconds: int
    correlation_id: str


@dataclass(frozen=True, slots=True)
class SignedUrlResponse:
    artifact_version_id: str
    signed_url: str
    expires_in_seconds: int
    audit_event_type: str = "signed_url_created"


@dataclass(frozen=True, slots=True)
class CleanupCandidate:
    artifact_version_id: str
    user_id: str
    project_id: str
    storage_key: str
    retention_policy: RetentionPolicy
    age_days: int
    delete_allowed: bool


@dataclass(frozen=True, slots=True)
class CleanupReport:
    scanned_count: int
    deleted_count: int
    skipped_count: int
    storage_keys_deleted: tuple[str, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LegacyArtifactManifestEntry:
    owner_user_id: str
    project_id: str
    legacy_path: str
    artifact_type: ArtifactType
    filename: str
    checksum: str | None = None
    quarantine_reason: str | None = None

    @property
    def importable(self) -> bool:
        return self.quarantine_reason is None and self.checksum is not None
