"""Supabase Auth adapter boundary.

The real Supabase SDK calls are wired in a later plan after database migrations exist. This
adapter validates configuration and documents the interface expected by application services.
"""

from dataclasses import dataclass

from qcm_domain.auth import AppRole, ProfileStatus, UserContext
from qcm_shared.auth_contracts import AuthenticatedSession, LoginRequest, Profile, RegisterRequest


@dataclass(frozen=True, slots=True)
class SupabaseAuthSettings:
    supabase_url: str
    anon_key: str | None = None
    service_role_key: str | None = None

    def __post_init__(self) -> None:
        if not self.supabase_url:
            raise ValueError("SupabaseAuthSettings requires supabase_url")


class SupabaseAuthAdapter:
    provider_key = "supabase"

    def __init__(self, settings: SupabaseAuthSettings) -> None:
        self.settings = settings

    def sign_in(self, request: LoginRequest, *, correlation_id: str) -> AuthenticatedSession:
        raise NotImplementedError("Supabase sign-in is implemented after live auth wiring")

    def sign_up(self, request: RegisterRequest, *, correlation_id: str) -> Profile:
        raise NotImplementedError("Supabase sign-up is implemented after live auth wiring")

    def verify_access_token(self, token: str, *, correlation_id: str) -> UserContext:
        if not token:
            raise ValueError("Access token is required")
        raise NotImplementedError("Supabase token verification is implemented after live auth wiring")

    def service_context(self, *, correlation_id: str) -> UserContext:
        if not self.settings.service_role_key:
            raise ValueError("Service role key is required for service context")
        return UserContext(
            user_id="service",
            email="",
            role=AppRole.SERVICE,
            status=ProfileStatus.ACTIVE,
            correlation_id=correlation_id,
        )

    def sign_out(self, token: str, *, correlation_id: str) -> None:
        if not token:
            raise ValueError("Access token is required")
        raise NotImplementedError("Supabase sign-out is implemented after live auth wiring")
