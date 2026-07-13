"""AI Auto Run API route factory."""

from qcm_shared.ai_autorun_contracts import AiAutoRunAction, AiAutoRunActionCommand, AiAutoRunPageInput, AiAutoRunStartCommand
from qcm_shared.provider_contracts import ModelSelection, ProviderKey

try:
    from fastapi import APIRouter, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def _command(project_id: str, payload: dict, correlation_id: str) -> AiAutoRunStartCommand:
    model = payload.get("model_selection") or {}
    return AiAutoRunStartCommand(
        user_id=payload.get("user_id", ""),
        project_id=project_id,
        run_id=payload.get("run_id", ""),
        ai_run_id=payload.get("ai_run_id", ""),
        pages=tuple(
            AiAutoRunPageInput(
                page_number=int(item.get("page_number", 0)),
                text=item.get("text", ""),
                source_artifact_id=item.get("source_artifact_id"),
            )
            for item in payload.get("pages") or ()
        ),
        model_selection=ModelSelection(
            provider=ProviderKey(model.get("provider", "openrouter")),
            primary_model_id=model.get("primary_model_id", "configured-by-admin"),
            fallback_model_ids=tuple(model.get("fallback_model_ids") or ()),
        ),
        idempotency_key=payload.get("idempotency_key", ""),
        correlation_id=correlation_id,
        user_constraints=dict(payload.get("user_constraints") or {}),
    )


def create_ai_autorun_router(ai_autorun_service=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/projects/{project_id}/ai-autoruns", tags=["ai-autorun"])

    @router.post("")
    def start_ai_autorun(project_id: str, payload: dict, x_correlation_id: str = Header(default="missing-correlation-id")):
        if ai_autorun_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI Auto Run unavailable")
        try:
            return ai_autorun_service.start(_command(project_id, payload, x_correlation_id))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    @router.post("/{ai_run_id}/{action}")
    def action_ai_autorun(
        project_id: str,
        ai_run_id: str,
        action: AiAutoRunAction,
        payload: dict,
        x_correlation_id: str = Header(default="missing-correlation-id"),
    ):
        if ai_autorun_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI Auto Run unavailable")
        return ai_autorun_service.action(
            AiAutoRunActionCommand(
                user_id=payload.get("user_id", ""),
                project_id=project_id,
                ai_run_id=ai_run_id,
                action=action,
                correlation_id=x_correlation_id,
            )
        )

    return router
