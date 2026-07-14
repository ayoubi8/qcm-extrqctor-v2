"""Manual Auto Run API route factory."""

from qcm_domain.auth import UserContext
from qcm_shared.autorun_contracts import (
    MANUAL_AUTORUN_SCHEMA_VERSION,
    ManualAutoRunControlAction,
    ManualAutoRunControlCommand,
    ManualAutoRunSnapshot,
    ManualAutoRunStartCommand,
    ManualAutoRunStepConfig,
)

try:
    from fastapi import APIRouter, Depends, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def _snapshot_from_payload(payload: dict) -> ManualAutoRunSnapshot:
    raw = payload.get("snapshot") or {}
    return ManualAutoRunSnapshot(
        schema_version=raw.get("schema_version", MANUAL_AUTORUN_SCHEMA_VERSION),
        selected_steps=tuple(
            ManualAutoRunStepConfig(
                step_key=item.get("step_key", ""),
                task_kind=item.get("task_kind", ""),
                enabled=bool(item.get("enabled", True)),
                config=dict(item.get("config") or {}),
            )
            for item in raw.get("selected_steps") or ()
        ),
        saved_defaults=dict(raw.get("saved_defaults") or {}),
        project_overrides=dict(raw.get("project_overrides") or {}),
        resource_limits=dict(raw.get("resource_limits") or {}),
    )


def create_autorun_router(autorun_service=None, current_user=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/projects/{project_id}/manual-autoruns", tags=["manual-autorun"])

    @router.post("/validate")
    def validate_manual_autorun(project_id: str, payload: dict, user: UserContext = Depends(current_user)):
        if autorun_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Manual Auto Run unavailable")
        return autorun_service.validate(_snapshot_from_payload(payload).selected_steps)

    @router.post("")
    def start_manual_autorun(project_id: str, payload: dict, user: UserContext = Depends(current_user), x_correlation_id: str = Header(default="missing-correlation-id")):
        if autorun_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Manual Auto Run unavailable")
        try:
            return autorun_service.start(
                ManualAutoRunStartCommand(
                    user_id=user.user_id,
                    project_id=project_id,
                    run_id=payload.get("run_id", ""),
                    auto_run_id=payload.get("auto_run_id", ""),
                    snapshot=_snapshot_from_payload(payload),
                    idempotency_key=payload.get("idempotency_key", ""),
                    correlation_id=x_correlation_id,
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    @router.post("/{auto_run_id}/{action}")
    def control_manual_autorun(
        project_id: str,
        auto_run_id: str,
        action: ManualAutoRunControlAction,
        payload: dict,
        user: UserContext = Depends(current_user),
        x_correlation_id: str = Header(default="missing-correlation-id"),
    ):
        if autorun_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Manual Auto Run unavailable")
        return autorun_service.control(
            ManualAutoRunControlCommand(
                user_id=user.user_id,
                project_id=project_id,
                auto_run_id=auto_run_id,
                action=action,
                correlation_id=x_correlation_id,
            )
        )

    return router