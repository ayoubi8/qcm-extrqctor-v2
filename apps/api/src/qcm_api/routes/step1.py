"""Step 1 API route factory."""

from qcm_shared.step1_contracts import STEP1_TASK_KIND
from qcm_shared.task_contracts import TaskCreateCommand

try:
    from fastapi import APIRouter, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def create_step1_router(task_service=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/projects/{project_id}/step1", tags=["step1"])

    @router.post("/run")
    def run_step1(project_id: str, payload: dict, x_correlation_id: str = Header(default="missing-correlation-id")):
        if task_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tasks unavailable")
        user_id = payload.get("user_id", "")
        run_id = payload.get("run_id", "")
        idempotency_key = payload.get("idempotency_key") or f"{project_id}:{run_id}:step1:{payload.get('source_file_id', '')}"
        task_payload = {
            "user_id": user_id,
            "project_id": project_id,
            "run_id": run_id,
            "source_file_id": payload.get("source_file_id", ""),
            "source_filename": payload.get("source_filename", "source.pdf"),
            "config": payload.get("config", {}),
        }
        return task_service.create_task(
            TaskCreateCommand(
                user_id=user_id,
                project_id=project_id,
                run_id=run_id,
                kind=STEP1_TASK_KIND,
                idempotency_key=idempotency_key,
                correlation_id=x_correlation_id,
                payload=task_payload,
                priority=int(payload.get("priority", 0)),
            )
        )

    return router
