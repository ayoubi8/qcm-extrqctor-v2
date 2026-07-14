"""FastAPI authentication dependencies.

Wires Supabase token verification and the approved-profile guard into protected
route handlers so `user_id` is derived from the verified JWT instead of trusted
client input.
"""

from __future__ import annotations

try:
    from fastapi import Depends, Header, HTTPException, status
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
except ModuleNotFoundError:  # pragma: no cover - dependency-light verification path
    Depends = None  # type: ignore[assignment]
    Header = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    status = None  # type: ignore[assignment]
    HTTPAuthorizationCredentials = None  # type: ignore[assignment]
    HTTPBearer = None  # type: ignore[assignment]

from qcm_application.ownership import ApprovalRequiredError, AuthorizationError, require_active_profile
from qcm_domain.auth import UserContext


def _bearer_scheme() -> "HTTPBearer":
    return HTTPBearer(auto_error=False)


def build_current_user_dependency(auth_provider):
    """Return a FastAPI dependency that verifies the bearer token and returns the UserContext."""
    if HTTPBearer is None:
        return None

    bearer = _bearer_scheme()

    def get_current_user(
        creds: "HTTPAuthorizationCredentials | None" = Depends(bearer),
        x_correlation_id: str = Header(default="missing-correlation-id"),
    ) -> UserContext:
        if auth_provider is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth unavailable")
        token = creds.credentials if creds else None
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
        try:
            return auth_provider.verify_access_token(token, correlation_id=x_correlation_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc) or "Invalid token") from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token verification failed") from exc

    return get_current_user


def require_active_user(user: UserContext) -> UserContext:
    """FastAPI dependency that additionally requires an approved/active profile."""
    try:
        require_active_profile(user)
    except ApprovalRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc) or "Account pending approval") from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc) or "Forbidden") from exc
    return user


def build_active_user_dependency(auth_provider):
    """Return a FastAPI dependency that verifies the token AND requires an active profile."""
    current_user = build_current_user_dependency(auth_provider)
    if current_user is None:
        return None

    def get_active_user(user: UserContext = Depends(current_user)) -> UserContext:
        return require_active_user(user)

    return get_active_user