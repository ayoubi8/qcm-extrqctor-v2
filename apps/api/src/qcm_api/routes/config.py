"""Configuration and model API route factory."""

from qcm_domain.auth import UserContext
from qcm_shared.api_contracts import ConfigResolveCommand

try:
    from fastapi import APIRouter, Depends, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def create_config_router(config_service=None, model_service=None, current_user=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/config", tags=["config"])

    @router.post("/resolve")
    def resolve_config(payload: dict, user: UserContext = Depends(current_user), x_correlation_id: str = Header(default="missing-correlation-id")):
        if config_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Config unavailable")
        command = ConfigResolveCommand(
            user_id=user.user_id,
            project_id=payload.get("project_id", ""),
            run_id=payload.get("run_id", ""),
            correlation_id=x_correlation_id,
            system_defaults=payload.get("system_defaults", {}),
            user_defaults=payload.get("user_defaults", {}),
            project_defaults=payload.get("project_defaults", {}),
            run_overrides=payload.get("run_overrides", {}),
            manual_auto_run_overrides=payload.get("manual_auto_run_overrides", {}),
            ai_proposal_values=payload.get("ai_proposal_values", {}),
        )
        return config_service.resolve(command)

    @router.get("/models")
    def list_models(user: UserContext = Depends(current_user)):
        if model_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Models unavailable")
        return model_service.list_models()

    return router