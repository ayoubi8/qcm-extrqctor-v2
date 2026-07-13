"""Artifact and storage-key domain rules."""

from dataclasses import dataclass
from pathlib import PurePosixPath
import re

from qcm_shared.contracts import ArtifactType, RetentionPolicy

MAX_SOURCE_FILE_BYTES = 52_428_800
DEFAULT_SIGNED_URL_SECONDS = 900
MAX_SIGNED_URL_SECONDS = 3600

_SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._=-]+")


@dataclass(frozen=True, slots=True)
class StoragePathContext:
    user_id: str
    project_id: str
    artifact_type: ArtifactType
    artifact_id: str
    version_number: int
    filename: str
    run_id: str | None = None

    def __post_init__(self) -> None:
        required = [self.user_id, self.project_id, self.artifact_id, self.filename]
        if any(not value for value in required):
            raise ValueError("StoragePathContext requires owner, project, artifact, and filename")
        if self.version_number < 1:
            raise ValueError("Artifact versions start at 1")


@dataclass(frozen=True, slots=True)
class RetentionRule:
    policy: RetentionPolicy
    cleanup_after_days: int | None
    delete_on_project_delete: bool
    user_visible: bool


def safe_storage_segment(value: str) -> str:
    cleaned = _SAFE_SEGMENT.sub("_", value.strip()).strip("._/")
    if not cleaned:
        raise ValueError("Storage path segment cannot be empty")
    return cleaned[:180]


def build_storage_key(context: StoragePathContext) -> str:
    filename = safe_storage_segment(context.filename)
    artifact_id = safe_storage_segment(context.artifact_id)
    version = f"v{context.version_number:04d}"
    base = PurePosixPath(
        "users",
        safe_storage_segment(context.user_id),
        "projects",
        safe_storage_segment(context.project_id),
    )
    if context.run_id:
        base = base / "runs" / safe_storage_segment(context.run_id)
    else:
        base = base / "project"
    return str(base / "artifacts" / context.artifact_type.value / artifact_id / version / filename)


def validate_source_file_size(size_bytes: int) -> None:
    if size_bytes < 0:
        raise ValueError("File size cannot be negative")
    if size_bytes > MAX_SOURCE_FILE_BYTES:
        raise ValueError("Source PDF exceeds the 50 MB application limit")


RETENTION_RULES: dict[RetentionPolicy, RetentionRule] = {
    RetentionPolicy.SOURCE_UNTIL_PROJECT_DELETE: RetentionRule(
        RetentionPolicy.SOURCE_UNTIL_PROJECT_DELETE, None, True, True
    ),
    RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE: RetentionRule(
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE, None, True, True
    ),
    RetentionPolicy.INTERMEDIATE_CLEANUP: RetentionRule(
        RetentionPolicy.INTERMEDIATE_CLEANUP, 30, True, False
    ),
    RetentionPolicy.DEBUG_SHORT_LIVED: RetentionRule(
        RetentionPolicy.DEBUG_SHORT_LIVED, 7, True, False
    ),
    RetentionPolicy.AUDIT_RETAINED_REDACTED: RetentionRule(
        RetentionPolicy.AUDIT_RETAINED_REDACTED, None, False, False
    ),
    RetentionPolicy.LEGACY_READ_ONLY: RetentionRule(
        RetentionPolicy.LEGACY_READ_ONLY, None, True, True
    ),
}
