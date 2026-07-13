"""Future Step 4 similarity match API route factory."""

from qcm_shared.step4_contracts import STEP4_TASK_KIND
from qcm_shared.task_contracts import TaskCreateCommand

try:
    from fastapi import APIRouter, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def create_step4_similarity_router(task_service=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/projects/{project_id}/steps/step4-similarity", tags=["step4-similarity"])

    @router.post("/run")
    def run_step4_similarity(project_id: str, payload: dict, x_correlation_id: str = Header(default="missing-correlation-id")):
        if task_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tasks unavailable")
        user_id = payload.get("user_id", "")
        run_id = payload.get("run_id", "")
        config = payload.get("config", {})
        task_payload = {
            "user_id": user_id,
            "project_id": project_id,
            "run_id": run_id,
            "source_artifact_ids": payload.get("source_artifact_ids", []),
            "source_qcms": payload.get("source_qcms", []),
            "reference_qcms": payload.get("reference_qcms", []),
            "existing_matches": payload.get("existing_matches", []),
            "config": config,
        }
        idempotency_key = payload.get("idempotency_key") or (
            f"{project_id}:{run_id}:step4-similarity:{config.get('reference_db_id', 'missing-ref')}"
        )
        return task_service.create_task(
            TaskCreateCommand(
                user_id=user_id,
                project_id=project_id,
                run_id=run_id,
                kind=STEP4_TASK_KIND,
                idempotency_key=idempotency_key,
                correlation_id=x_correlation_id,
                payload=task_payload,
                priority=int(payload.get("priority", 0)),
            )
        )

    return router
