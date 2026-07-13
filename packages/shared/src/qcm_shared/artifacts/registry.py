"""Artifact registry used by API, worker, storage, and UI layers."""

from dataclasses import dataclass

from qcm_shared.contracts import ArtifactType, RetentionPolicy


@dataclass(frozen=True, slots=True)
class ArtifactRegistryEntry:
    artifact_type: ArtifactType
    schema_version: str
    default_content_type: str
    retention_policy: RetentionPolicy
    user_visible: bool


ARTIFACT_REGISTRY: dict[ArtifactType, ArtifactRegistryEntry] = {
    ArtifactType.SOURCE_PDF: ArtifactRegistryEntry(
        ArtifactType.SOURCE_PDF,
        "source-pdf.v1",
        "application/pdf",
        RetentionPolicy.SOURCE_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.STEP1_TEXT: ArtifactRegistryEntry(
        ArtifactType.STEP1_TEXT,
        "step1-text.v1",
        "text/plain",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.PAGE_TEXT: ArtifactRegistryEntry(
        ArtifactType.PAGE_TEXT,
        "page-text.v1",
        "text/plain",
        RetentionPolicy.INTERMEDIATE_CLEANUP,
        False,
    ),
    ArtifactType.PAGE_IMAGE: ArtifactRegistryEntry(
        ArtifactType.PAGE_IMAGE,
        "page-image.v1",
        "image/png",
        RetentionPolicy.INTERMEDIATE_CLEANUP,
        False,
    ),
    ArtifactType.STEP2_PAGE_QCM_JSON: ArtifactRegistryEntry(
        ArtifactType.STEP2_PAGE_QCM_JSON,
        "step2-page-qcm-json.v1",
        "application/json",
        RetentionPolicy.INTERMEDIATE_CLEANUP,
        False,
    ),
    ArtifactType.STEP2_FINAL_JSON: ArtifactRegistryEntry(
        ArtifactType.STEP2_FINAL_JSON,
        "step2-final-json.v1",
        "application/json",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.STEP2_FINAL_XLSX: ArtifactRegistryEntry(
        ArtifactType.STEP2_FINAL_XLSX,
        "step2-final-xlsx.v1",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.STEP3_CORRECTION_JSON: ArtifactRegistryEntry(
        ArtifactType.STEP3_CORRECTION_JSON,
        "step3-correction-json.v1",
        "application/json",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.STEP3_CORRECTION_XLSX: ArtifactRegistryEntry(
        ArtifactType.STEP3_CORRECTION_XLSX,
        "step3-correction-xlsx.v1",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.STEP4_SIMILARITY_JSON: ArtifactRegistryEntry(
        ArtifactType.STEP4_SIMILARITY_JSON,
        "step4-similarity-json.v1",
        "application/json",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.STEP4_SIMILARITY_XLSX: ArtifactRegistryEntry(
        ArtifactType.STEP4_SIMILARITY_XLSX,
        "step4-similarity-xlsx.v1",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.REFERENCE_DB: ArtifactRegistryEntry(
        ArtifactType.REFERENCE_DB,
        "reference-db.v1",
        "application/json",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.AI_AUTORUN_DOCUMENT_MAP: ArtifactRegistryEntry(
        ArtifactType.AI_AUTORUN_DOCUMENT_MAP,
        "ai-autorun-document-map.v1",
        "application/json",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.AI_AUTORUN_CONFIG: ArtifactRegistryEntry(
        ArtifactType.AI_AUTORUN_CONFIG,
        "ai-autorun-config.v1",
        "application/json",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.AI_AUTORUN_EVIDENCE: ArtifactRegistryEntry(
        ArtifactType.AI_AUTORUN_EVIDENCE,
        "ai-autorun-evidence.v1",
        "application/json",
        RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        True,
    ),
    ArtifactType.DEBUG_INTERNAL: ArtifactRegistryEntry(
        ArtifactType.DEBUG_INTERNAL,
        "debug-internal.v1",
        "application/json",
        RetentionPolicy.DEBUG_SHORT_LIVED,
        False,
    ),
    ArtifactType.LEGACY_IMPORT: ArtifactRegistryEntry(
        ArtifactType.LEGACY_IMPORT,
        "legacy-import.v1",
        "application/octet-stream",
        RetentionPolicy.LEGACY_READ_ONLY,
        True,
    ),
}
