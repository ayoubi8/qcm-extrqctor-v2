"""Artifact metadata and private object workflow services."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from qcm_application.ownership import AuthorizationError
from qcm_domain.artifacts import (
    DEFAULT_SIGNED_URL_SECONDS,
    MAX_SIGNED_URL_SECONDS,
    StoragePathContext,
    build_storage_key,
    validate_source_file_size,
)
from qcm_shared.auth_contracts import AuditEventDraft
from qcm_shared.contracts import ArtifactType, ArtifactVersion, ProviderLimitEvent
from qcm_shared.storage_contracts import (
    ArtifactWriteRequest,
    CleanupCandidate,
    CleanupReport,
    SignedUrlRequest,
    SignedUrlResponse,
    UploadInitRequest,
    UploadInitResponse,
)


class ObjectStorage(Protocol):
    def put(self, storage_key: str, content: bytes, content_type: str) -> None:
        ...

    def create_signed_url(self, storage_key: str, expires_in_seconds: int) -> str:
        ...

    def delete_many(self, storage_keys: list[str]) -> int:
        ...


class ArtifactVersionRepository(Protocol):
    def create_version(self, request: ArtifactWriteRequest, storage_key: str) -> ArtifactVersion:
        ...

    def get_version_for_signed_url(self, artifact_version_id: str) -> ArtifactVersion:
        ...


class AuditSink(Protocol):
    def record(self, event: AuditEventDraft) -> None:
        ...


@dataclass(frozen=True, slots=True)
class ArtifactWriteResult:
    version: ArtifactVersion
    storage_key: str
    checksum: str


def checksum_bytes(content: bytes) -> str:
    return sha256(content).hexdigest()


def initialize_upload(request: UploadInitRequest) -> UploadInitResponse:
    try:
        validate_source_file_size(request.size_bytes)
    except ValueError as error:
        return UploadInitResponse(
            allowed=False,
            storage_key=None,
            provider_limit_event=ProviderLimitEvent.FILE_SIZE_LIMIT,
            safe_message=str(error),
        )
    context = StoragePathContext(
        user_id=request.user_id,
        project_id=request.project_id,
        run_id=None,
        artifact_type=ArtifactType.SOURCE_PDF,
        artifact_id=request.idempotency_key,
        version_number=1,
        filename=request.filename,
    )
    return UploadInitResponse(
        allowed=True,
        storage_key=build_storage_key(context),
        provider_limit_event=ProviderLimitEvent.NONE,
    )


def write_artifact_version(
    *,
    request: ArtifactWriteRequest,
    storage: ObjectStorage,
    versions: ArtifactVersionRepository,
) -> ArtifactWriteResult:
    digest = checksum_bytes(request.content)
    if digest != request.checksum:
        raise ValueError("Artifact checksum mismatch")
    if request.artifact_type == ArtifactType.SOURCE_PDF:
        validate_source_file_size(len(request.content))
    context = StoragePathContext(
        user_id=request.user_id,
        project_id=request.project_id,
        run_id=request.run_id,
        artifact_type=request.artifact_type,
        artifact_id=request.artifact_id,
        version_number=request.version_number,
        filename=request.filename,
    )
    storage_key = build_storage_key(context)
    storage.put(storage_key, request.content, request.content_type)
    version = versions.create_version(request, storage_key)
    return ArtifactWriteResult(version=version, storage_key=storage_key, checksum=digest)


def create_signed_url(
    *,
    request: SignedUrlRequest,
    requester_is_admin: bool,
    storage: ObjectStorage,
    versions: ArtifactVersionRepository,
    audit: AuditSink,
) -> SignedUrlResponse:
    expires = request.expires_in_seconds or DEFAULT_SIGNED_URL_SECONDS
    if expires < 1 or expires > MAX_SIGNED_URL_SECONDS:
        raise ValueError("Signed URL expiry must be between 1 and 3600 seconds")
    version = versions.get_version_for_signed_url(request.artifact_version_id)
    owner_user_id = getattr(version, "user_id", None)
    if owner_user_id and owner_user_id != request.requester_user_id and not requester_is_admin:
        raise AuthorizationError("Artifact version does not belong to requester")
    signed_url = storage.create_signed_url(version.storage_key, expires)
    audit.record(
        AuditEventDraft(
            actor_user_id=request.requester_user_id,
            actor_role="admin" if requester_is_admin else "user",
            event_type="signed_url_created",
            target_type="artifact_version",
            target_id=request.artifact_version_id,
            project_id=getattr(version, "project_id", None),
            correlation_id=request.correlation_id,
            safe_payload={"expires_in_seconds": expires},
        )
    )
    return SignedUrlResponse(
        artifact_version_id=request.artifact_version_id,
        signed_url=signed_url,
        expires_in_seconds=expires,
    )


def cleanup_storage_versions(
    *,
    candidates: list[CleanupCandidate],
    storage: ObjectStorage,
) -> CleanupReport:
    allowed = [candidate.storage_key for candidate in candidates if candidate.delete_allowed]
    deleted = storage.delete_many(allowed) if allowed else 0
    return CleanupReport(
        scanned_count=len(candidates),
        deleted_count=deleted,
        skipped_count=len(candidates) - len(allowed),
        storage_keys_deleted=tuple(allowed),
    )
