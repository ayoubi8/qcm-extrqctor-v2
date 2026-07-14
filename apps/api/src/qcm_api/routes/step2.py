"""Combined Step 2 API route factory."""

from qcm_domain.auth import UserContext
from qcm_shared.step2_contracts import STEP2_TASK_KIND
from qcm_shared.task_contracts import TaskCreateCommand

try:
    from fastapi import APIRouter, Depends, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def create_step2_router(task_service=None, current_user=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/projects/{project_id}/steps/step2", tags=["step2"])

    @router.post("/run")
    def run_step2(project_id: str, payload: dict, user: UserContext = Depends(current_user), x_correlation_id: str = Header(default="missing-correlation-id")):
        if task_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tasks unavailable")
        run_id = payload.get("run_id", "")
        task_payload = {
            "user_id": user.user_id,
            "project_id": project_id,
            "run_id": run_id,
            "step1_artifact_ids": payload.get("step1_artifact_ids", []),
            "pages": payload.get("pages", []),
            "config": payload.get("config", {}),
            "previous_cycle_data": payload.get("previous_cycle_data", {}),
        }
        idempotency_key = payload.get("idempotency_key") or f"{project_id}:{run_id}:step2:{len(task_payload['pages'])}"
        return task_service.create_task(
            TaskCreateCommand(
                user_id=user.user_id,
                project_id=project_id,
                run_id=run_id,
                kind=STEP2_TASK_KIND,
                idempotency_key=idempotency_key,
                correlation_id=x_correlation_id,
                payload=task_payload,
                priority=int(payload.get("priority", 0)),
            )
        )

    return router