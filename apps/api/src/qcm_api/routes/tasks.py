"""Task control API route factory."""

from qcm_domain.auth import UserContext
from qcm_shared.task_contracts import TaskCancelCommand, TaskCreateCommand

try:
    from fastapi import APIRouter, Depends, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def create_tasks_router(task_service=None, current_user=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/tasks", tags=["tasks"])

    @router.post("")
    def create_task(payload: dict, user: UserContext = Depends(current_user), x_correlation_id: str = Header(default="missing-correlation-id")):
        if task_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tasks unavailable")
        command = TaskCreateCommand(
            user_id=user.user_id,
            project_id=payload.get("project_id", ""),
            run_id=payload.get("run_id", ""),
            kind=payload.get("kind", ""),
            idempotency_key=payload.get("idempotency_key", ""),
            correlation_id=x_correlation_id,
            payload=payload.get("payload", {}),
            priority=int(payload.get("priority", 0)),
        )
        return task_service.create_task(command)

    @router.post("/{task_id}/cancel")
    def cancel_task(task_id: str, payload: dict, user: UserContext = Depends(current_user), x_correlation_id: str = Header(default="missing-correlation-id")):
        if task_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tasks unavailable")
        return task_service.cancel(
            TaskCancelCommand(
                task_id=task_id,
                actor_user_id=user.user_id,
                correlation_id=x_correlation_id,
            )
        )

    return router