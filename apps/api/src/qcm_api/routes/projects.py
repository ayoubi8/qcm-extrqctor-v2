"""Project API route factory."""

from qcm_domain.auth import UserContext
from qcm_shared.api_contracts import ProjectCreateCommand

try:
    from fastapi import APIRouter, Depends, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def create_projects_router(project_service=None, current_user=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/projects", tags=["projects"])

    @router.post("")
    def create_project(payload: dict, user: UserContext = Depends(current_user), x_correlation_id: str = Header(default="missing-correlation-id")):
        if project_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Projects unavailable")
        command = ProjectCreateCommand(
            user_id=user.user_id,
            name=payload.get("name", ""),
            idempotency_key=payload.get("idempotency_key", ""),
            correlation_id=x_correlation_id,
        )
        return project_service.create_project(command)

    @router.get("/{project_id}/snapshot")
    def project_snapshot(project_id: str, user: UserContext = Depends(current_user)):
        if project_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Projects unavailable")
        try:
            return project_service.snapshot(user_id=user.user_id, project_id=project_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc

    return router