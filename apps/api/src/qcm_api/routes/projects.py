"""Project API route factory."""

from qcm_shared.api_contracts import ProjectCreateCommand

try:
    from fastapi import APIRouter, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def create_projects_router(project_service=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/projects", tags=["projects"])

    @router.post("")
    def create_project(payload: dict, x_correlation_id: str = Header(default="missing-correlation-id")):
        if project_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Projects unavailable")
        command = ProjectCreateCommand(
            user_id=payload.get("user_id", ""),
            name=payload.get("name", ""),
            idempotency_key=payload.get("idempotency_key", ""),
            correlation_id=x_correlation_id,
        )
        return project_service.create_project(command)

    @router.get("/{project_id}/snapshot")
    def project_snapshot(project_id: str, user_id: str):
        if project_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Projects unavailable")
        return project_service.snapshot(user_id=user_id, project_id=project_id)

    return router
