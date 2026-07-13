"""Static and contract verification for Plan 04 storage/artifact code."""

from __future__ import annotations

import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/application/src",
    "packages/infrastructure/src",
    "packages/shared/src",
    "apps/api/src",
    "apps/worker/src",
]:
    sys.path.insert(0, str(ROOT / relative))

REQUIRED_PATHS = [
    "packages/domain/src/qcm_domain/artifacts.py",
    "packages/application/src/qcm_application/artifact_service.py",
    "packages/infrastructure/src/qcm_infrastructure/storage/base.py",
    "packages/infrastructure/src/qcm_infrastructure/storage/supabase_adapter.py",
    "packages/shared/src/qcm_shared/storage_contracts.py",
    "apps/api/src/qcm_api/routes/artifacts.py",
    "apps/worker/src/qcm_worker/cleanup.py",
]


def verify_paths() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Plan 04 paths: {missing}")


def verify_contracts() -> None:
    from qcm_application.artifact_service import initialize_upload, write_artifact_version
    from qcm_domain.artifacts import MAX_SOURCE_FILE_BYTES, StoragePathContext, build_storage_key
    from qcm_infrastructure.storage import InMemoryObjectStorage
    from qcm_shared.artifacts.registry import ARTIFACT_REGISTRY
    from qcm_shared.contracts import ArtifactType, ArtifactVersion, ProviderLimitEvent, RetentionPolicy
    from qcm_shared.storage_contracts import ArtifactWriteRequest, UploadInitRequest

    if set(ARTIFACT_REGISTRY) != set(ArtifactType):
        raise AssertionError("Artifact registry must cover every artifact type")
    too_large = initialize_upload(
        UploadInitRequest("u", "p", "source.pdf", "application/pdf", MAX_SOURCE_FILE_BYTES + 1, "idem")
    )
    assert not too_large.allowed
    assert too_large.provider_limit_event == ProviderLimitEvent.FILE_SIZE_LIMIT
    key = build_storage_key(
        StoragePathContext("u", "p", ArtifactType.STEP2_FINAL_JSON, "a", 2, "final json!.json", "r")
    )
    assert key.startswith("users/u/projects/p/runs/r/artifacts/step2_final_json/a/v0002/")
    content = b"{}"
    checksum = sha256(content).hexdigest()

    class Repo:
        def create_version(self, request, storage_key):
            return ArtifactVersion(
                artifact_version_id="v1",
                artifact_id=request.artifact_id,
                version_number=request.version_number,
                storage_key=storage_key,
                content_type=request.content_type,
                checksum=request.checksum,
                size_bytes=len(request.content),
                schema_version=request.schema_version,
                retention_policy=request.retention_policy,
                created_at="2026-07-13T00:00:00Z",
            )

    storage = InMemoryObjectStorage()
    result = write_artifact_version(
        request=ArtifactWriteRequest(
            user_id="u",
            project_id="p",
            run_id="r",
            artifact_id="a",
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
        versions=Repo(),
    )
    assert result.storage_key in storage.objects


def main() -> int:
    verify_paths()
    verify_contracts()
    print("Plan 04 storage and artifact boundaries verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
