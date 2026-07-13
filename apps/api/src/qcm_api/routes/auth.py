"""Authentication route factory.

Routes are registered only when FastAPI is installed. The functions keep Plan 02 contracts
importable in dependency-light verification environments.
"""

from qcm_shared.auth_contracts import LoginRequest, RegisterRequest

try:
    from fastapi import APIRouter, Header, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover - foundation verification path
    APIRouter = None


def create_auth_router(auth_provider=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/login")
    def login(payload: dict, x_correlation_id: str = Header(default="missing-correlation-id")):
        if auth_provider is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth unavailable")
        request = LoginRequest(email=payload.get("email", ""), password=payload.get("password", ""))
        return auth_provider.sign_in(request, correlation_id=x_correlation_id)

    @router.post("/register")
    def register(payload: dict, x_correlation_id: str = Header(default="missing-correlation-id")):
        if auth_provider is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth unavailable")
        request = RegisterRequest(
            email=payload.get("email", ""),
            password=payload.get("password", ""),
            display_name=payload.get("display_name"),
        )
        return auth_provider.sign_up(request, correlation_id=x_correlation_id)

    return router
