"""Artifact API route factory."""

from qcm_domain.auth import UserContext
from qcm_shared.storage_contracts import SignedUrlRequest, UploadInitRequest

try:
    from fastapi import APIRouter, Depends, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover - dependency-light verification path
    APIRouter = None


def create_artifacts_router(artifact_service=None, current_user=None):
    if APIRouter is None:
        return None

    router = APIRouter(tags=["artifacts"])

    @router.post("/uploads/init")
    def initialize_upload(payload: dict, user: UserContext = Depends(current_user)):
        if artifact_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Artifacts unavailable")
        request = UploadInitRequest(
            user_id=user.user_id,
            project_id=payload.get("project_id", ""),
            filename=payload.get("filename", ""),
            content_type=payload.get("content_type", "application/octet-stream"),
            size_bytes=int(payload.get("size_bytes", 0)),
            idempotency_key=payload.get("idempotency_key", ""),
        )
        return artifact_service.initialize_upload(request)

    @router.get("/artifact-versions/{artifact_version_id}/signed-url")
    def signed_url(
        artifact_version_id: str,
        user: UserContext = Depends(current_user),
        expires_in_seconds: int = 900,
        x_correlation_id: str = Header(default="missing-correlation-id"),
    ):
        if artifact_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Artifacts unavailable")
        request = SignedUrlRequest(
            requester_user_id=user.user_id,
            artifact_version_id=artifact_version_id,
            expires_in_seconds=expires_in_seconds,
            correlation_id=x_correlation_id,
        )
        return artifact_service.create_signed_url(request)

    return router