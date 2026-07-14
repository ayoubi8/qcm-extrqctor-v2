"""Artifact API route factory."""

from qcm_domain.auth import UserContext
from qcm_shared.storage_contracts import SignedUrlRequest, UploadInitRequest

try:
    from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
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

    @router.post("/uploads/{project_id}/source-file")
    async def upload_source_file(
        project_id: str,
        file: UploadFile = File(...),
        user: UserContext = Depends(current_user),
        x_correlation_id: str = Header(default="missing-correlation-id"),
    ):
        if artifact_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Artifacts unavailable")
        if not hasattr(artifact_service, "upload_source_file"):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Storage not configured")
        content = await file.read()
        filename = file.filename or "source.pdf"
        content_type = file.content_type or "application/pdf"
        try:
            return artifact_service.upload_source_file(
                user_id=user.user_id,
                project_id=project_id,
                filename=filename,
                content=content,
                content_type=content_type,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc) or "Upload failed") from exc

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
        try:
            return artifact_service.create_signed_url(request)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact version not found") from exc
        except Exception as exc:
            from qcm_application.ownership import AuthorizationError
            if isinstance(exc, AuthorizationError):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Signed URL failed") from exc

    return router