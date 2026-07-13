"""Persistent terminal replay API route factory."""

try:
    from fastapi import APIRouter, HTTPException, Query, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def create_terminal_router(task_service=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/projects/{project_id}/terminal", tags=["terminal"])

    @router.get("")
    def terminal_events(project_id: str, user_id: str, after_sequence: int | None = None, limit: int = Query(default=100, ge=1, le=500)):
        if task_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Terminal unavailable")
        return task_service.terminal_page(
            user_id=user_id,
            project_id=project_id,
            after_sequence=after_sequence,
            limit=limit,
        )

    return router
