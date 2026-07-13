"""Legacy import validation for release gates."""

from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from qcm_shared.contracts import ArtifactType
from qcm_shared.storage_contracts import LegacyArtifactManifestEntry


@dataclass(frozen=True, slots=True)
class LegacyImportCandidate:
    owner_user_id: str
    project_id: str
    legacy_path: str
    artifact_type: str
    filename: str
    checksum: str | None = None
    created_at: str | None = None
    subcategory: str | None = None


@dataclass(frozen=True, slots=True)
class LegacyImportValidationReport:
    importable: tuple[LegacyArtifactManifestEntry, ...]
    quarantined: tuple[LegacyArtifactManifestEntry, ...]
    warnings: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.quarantined


def validate_legacy_import_manifest(raw_items: list[dict[str, Any]]) -> LegacyImportValidationReport:
    importable: list[LegacyArtifactManifestEntry] = []
    quarantined: list[LegacyArtifactManifestEntry] = []
    warnings: list[str] = []
    for raw in raw_items:
        candidate = LegacyImportCandidate(
            owner_user_id=str(raw.get("owner_user_id", "")),
            project_id=str(raw.get("project_id", "")),
            legacy_path=str(raw.get("legacy_path", "")),
            artifact_type=str(raw.get("artifact_type", "")),
            filename=str(raw.get("filename", "")),
            checksum=raw.get("checksum"),
            created_at=raw.get("created_at"),
            subcategory=raw.get("subcategory"),
        )
        quarantine_reason = _quarantine_reason(candidate)
        artifact_type = _artifact_type(candidate.artifact_type)
        entry = LegacyArtifactManifestEntry(
            owner_user_id=candidate.owner_user_id,
            project_id=candidate.project_id,
            legacy_path=candidate.legacy_path,
            artifact_type=artifact_type,
            filename=candidate.filename,
            checksum=candidate.checksum,
            quarantine_reason=quarantine_reason,
        )
        if quarantine_reason:
            quarantined.append(entry)
        else:
            importable.append(entry)
        if candidate.subcategory:
            warnings.append(f"Preserve legacy subcategory metadata for {candidate.filename}")
        if candidate.created_at:
            warnings.append(f"Preserve legacy timestamp metadata for {candidate.filename}")
    return LegacyImportValidationReport(tuple(importable), tuple(quarantined), tuple(warnings))


def _artifact_type(value: str) -> ArtifactType:
    try:
        return ArtifactType(value)
    except ValueError:
        return ArtifactType.LEGACY_IMPORT


def _quarantine_reason(candidate: LegacyImportCandidate) -> str | None:
    if not candidate.owner_user_id or not candidate.project_id:
        return "missing_owner_or_project"
    if not candidate.filename:
        return "missing_filename"
    if not candidate.checksum:
        return "missing_checksum"
    if PureWindowsPath(candidate.legacy_path).is_absolute() or PurePosixPath(candidate.legacy_path).is_absolute():
        return "absolute_private_path_requires_manual_approval"
    if _artifact_type(candidate.artifact_type) == ArtifactType.LEGACY_IMPORT and candidate.artifact_type != ArtifactType.LEGACY_IMPORT.value:
        return "unsupported_artifact_type"
    return None
