"""Future Step 3 correction API route factory."""

from qcm_domain.auth import UserContext
from qcm_shared.step3_contracts import STEP3_TASK_KIND
from qcm_shared.task_contracts import TaskCreateCommand

try:
    from fastapi import APIRouter, Depends, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def create_step3_correction_router(task_service=None, current_user=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/projects/{project_id}/steps/step3-correction", tags=["step3-correction"])

    @router.post("/run")
    def run_step3_correction(project_id: str, payload: dict, user: UserContext = Depends(current_user), x_correlation_id: str = Header(default="missing-correlation-id")):
        if task_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tasks unavailable")
        run_id = payload.get("run_id", "")
        task_payload = {
            "user_id": user.user_id,
            "project_id": project_id,
            "run_id": run_id,
            "step2_artifact_ids": payload.get("step2_artifact_ids", []),
            "qcms": payload.get("qcms", []),
            "pages": payload.get("pages", []),
            "config": payload.get("config", {}),
        }
        idempotency_key = payload.get("idempotency_key") or f"{project_id}:{run_id}:step3-correction:{payload.get('config', {}).get('mode', 'page_detection')}"
        return task_service.create_task(
            TaskCreateCommand(
                user_id=user.user_id,
                project_id=project_id,
                run_id=run_id,
                kind=STEP3_TASK_KIND,
                idempotency_key=idempotency_key,
                correlation_id=x_correlation_id,
                payload=task_payload,
                priority=int(payload.get("priority", 0)),
            )
        )

    return router