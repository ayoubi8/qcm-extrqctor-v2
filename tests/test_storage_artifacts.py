import sys
from hashlib import sha256
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/shared/src",
    "packages/application/src",
    "packages/infrastructure/src",
    "apps/worker/src",
]:
    sys.path.insert(0, str(ROOT / relative))

from qcm_application.artifact_service import (
    cleanup_storage_versions,
    create_signed_url,
    initialize_upload,
    write_artifact_version,
)
from qcm_application.ownership import AuthorizationError
from qcm_domain.artifacts import MAX_SOURCE_FILE_BYTES, StoragePathContext, build_storage_key
from qcm_infrastructure.storage import InMemoryObjectStorage
from qcm_shared.artifacts.registry import ARTIFACT_REGISTRY
from qcm_shared.auth_contracts import AuditEventDraft
from qcm_shared.contracts import ArtifactType, ArtifactVersion, ProviderLimitEvent, RetentionPolicy
from qcm_shared.storage_contracts import (
    ArtifactWriteRequest,
    CleanupCandidate,
    SignedUrlRequest,
    UploadInitRequest,
)
from qcm_worker.cleanup import select_cleanup_keys


class FakeVersionRepository:
    def __init__(self, version: ArtifactVersion | None = None, owner: str = "user-1") -> None:
        self.version = version
        self.owner = owner

    def create_version(self, request: ArtifactWriteRequest, storage_key: str) -> ArtifactVersion:
        version = ArtifactVersion(
            artifact_version_id="version-1",
            artifact_id=request.artifact_id,
            version_number=request.version_number,
            storage_key=storage_key,
            content_type=request.content_type,
            checksum=request.checksum,
            size_bytes=len(request.content),
            schema_version=request.schema_version,
            retention_policy=request.retention_policy,
            created_at="2026-07-13T00:00:00Z",
            source_artifact_ids=request.source_artifact_ids,
            user_id=request.user_id,
            project_id=request.project_id,
            run_id=request.run_id,
        )
        self.version = version
        self.owner = request.user_id
        return version

    def get_version_for_signed_url(self, artifact_version_id: str) -> ArtifactVersion:
        if self.version is None:
            raise FileNotFoundError(artifact_version_id)
        object.__setattr__(self.version, "user_id", self.owner)
        object.__setattr__(self.version, "project_id", self.version.project_id or "project-1")
        return self.version


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[AuditEventDraft] = []

    def record(self, event: AuditEventDraft) -> None:
        self.events.append(event)


class StorageArtifactTest(unittest.TestCase):
    def test_registry_covers_all_artifact_types(self) -> None:
        self.assertEqual(set(ARTIFACT_REGISTRY), set(ArtifactType))

    def test_source_upload_rejects_over_50mb(self) -> None:
        response = initialize_upload(
            UploadInitRequest(
                user_id="user-1",
                project_id="project-1",
                filename="source.pdf",
                content_type="application/pdf",
                size_bytes=MAX_SOURCE_FILE_BYTES + 1,
                idempotency_key="upload-1",
            )
        )
        self.assertFalse(response.allowed)
        self.assertEqual(response.provider_limit_event, ProviderLimitEvent.FILE_SIZE_LIMIT)

    def test_storage_key_is_private_and_owner_scoped(self) -> None:
        key = build_storage_key(
            StoragePathContext(
                user_id="user-1",
                project_id="project-1",
                run_id="run-1",
                artifact_type=ArtifactType.AI_AUTORUN_CONFIG,
                artifact_id="artifact-1",
                version_number=3,
                filename="config proposal.json",
            )
        )
        self.assertEqual(
            key,
            "users/user-1/projects/project-1/runs/run-1/artifacts/"
            "ai_autorun_config/artifact-1/v0003/config_proposal.json",
        )

    def test_write_artifact_checks_checksum_and_writes_storage(self) -> None:
        content = b'{"ok": true}'
        checksum = sha256(content).hexdigest()
        storage = InMemoryObjectStorage()
        result = write_artifact_version(
            request=ArtifactWriteRequest(
                user_id="user-1",
                project_id="project-1",
                run_id="run-1",
                artifact_id="artifact-1",
                artifact_type=ArtifactType.STEP2_FINAL_JSON,
                filename="final.json",
                content_type="application/json",
                content=content,
                version_number=1,
                checksum=checksum,
                schema_version="step2-final-json.v1",
                retention_policy=RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
            ),
            storage=storage,
            versions=FakeVersionRepository(),
        )
        self.assertIn(result.storage_key, storage.objects)

    def test_signed_url_requires_owner_before_url(self) -> None:
        version = ArtifactVersion(
            artifact_version_id="version-1",
            artifact_id="artifact-1",
            version_number=1,
            storage_key="users/user-1/projects/project-1/project/artifacts/source_pdf/a/v0001/source.pdf",
            content_type="application/pdf",
            checksum="abc",
            size_bytes=3,
            schema_version="source-pdf.v1",
            retention_policy=RetentionPolicy.SOURCE_UNTIL_PROJECT_DELETE,
            created_at="2026-07-13T00:00:00Z",
            user_id="user-1",
            project_id="project-1",
        )
        storage = InMemoryObjectStorage()
        storage.put(version.storage_key, b"pdf", "application/pdf")
        audit = FakeAudit()
        response = create_signed_url(
            request=SignedUrlRequest("user-1", "version-1", 900, "corr"),
            requester_is_admin=False,
            storage=storage,
            versions=FakeVersionRepository(version, "user-1"),
            audit=audit,
        )
        self.assertIn("expires_in=900", response.signed_url)
        self.assertEqual(audit.events[0].event_type, "signed_url_created")
        with self.assertRaises(AuthorizationError):
            create_signed_url(
                request=SignedUrlRequest("user-2", "version-1", 900, "corr"),
                requester_is_admin=False,
                storage=storage,
                versions=FakeVersionRepository(version, "user-1"),
                audit=audit,
            )

    def test_cleanup_respects_retention_policy(self) -> None:
        candidates = [
            CleanupCandidate(
                "debug-1",
                "user-1",
                "project-1",
                "debug/key",
                RetentionPolicy.DEBUG_SHORT_LIVED,
                age_days=8,
                delete_allowed=True,
            ),
            CleanupCandidate(
                "final-1",
                "user-1",
                "project-1",
                "final/key",
                RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
                age_days=400,
                delete_allowed=True,
            ),
        ]
        self.assertEqual(select_cleanup_keys(candidates), ["debug/key"])
        storage = InMemoryObjectStorage()
        storage.put("debug/key", b"debug", "application/json")
        storage.put("final/key", b"final", "application/json")
        report = cleanup_storage_versions(candidates=[candidates[0]], storage=storage)
        self.assertEqual(report.deleted_count, 1)
        self.assertNotIn("debug/key", storage.objects)


if __name__ == "__main__":
    unittest.main()
