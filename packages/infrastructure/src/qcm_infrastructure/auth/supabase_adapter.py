"""Supabase Auth and profile adapter."""

from dataclasses import dataclass
from typing import Any

from qcm_domain.auth import AppRole, ProfileStatus, UserContext
from qcm_shared.auth_contracts import (
    AuthenticatedSession,
    LoginRequest,
    Profile,
    RegisterRequest,
    SessionTokens,
)

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - dependency-light verification path
    httpx = None


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
        self._require_live_auth_settings()
        response = self._post(
            "/auth/v1/token?grant_type=password",
            {"email": request.email.lower(), "password": request.password},
            use_service_role=False,
            correlation_id=correlation_id,
        )
        user = response.get("user") or {}
        profile = self._ensure_profile(
            user_id=str(user.get("id") or ""),
            email=str(user.get("email") or request.email).lower(),
            display_name=self._metadata_display_name(user),
            correlation_id=correlation_id,
        )
        return self._session_from_response(response, profile)

    def sign_up(self, request: RegisterRequest, *, correlation_id: str) -> AuthenticatedSession:
        self._require_live_auth_settings()
        response = self._post(
            "/auth/v1/signup",
            {
                "email": request.email.lower(),
                "password": request.password,
                "data": {"display_name": request.display_name},
            },
            use_service_role=False,
            correlation_id=correlation_id,
        )
        user = self._user_from_auth_response(response)
        profile = self._ensure_profile(
            user_id=str(user.get("id") or ""),
            email=str(user.get("email") or request.email).lower(),
            display_name=request.display_name or self._metadata_display_name(user),
            correlation_id=correlation_id,
        )
        if not response.get("access_token"):
            response = self._post(
                "/auth/v1/token?grant_type=password",
                {"email": request.email.lower(), "password": request.password},
                use_service_role=False,
                correlation_id=correlation_id,
            )
        return self._session_from_response(response, profile)

    def verify_access_token(self, token: str, *, correlation_id: str) -> UserContext:
        if not token:
            raise ValueError("Access token is required")
        self._require_live_auth_settings()
        user = self._get(
            "/auth/v1/user",
            use_service_role=False,
            bearer_token=token,
            correlation_id=correlation_id,
        )
        profile = self._ensure_profile(
            user_id=str(user.get("id") or ""),
            email=str(user.get("email") or "").lower(),
            display_name=self._metadata_display_name(user),
            correlation_id=correlation_id,
        )
        return UserContext(
            user_id=profile.user_id,
            email=profile.email,
            role=profile.role,
            status=profile.status,
            correlation_id=correlation_id,
        )

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
        self._require_live_auth_settings()
        self._post(
            "/auth/v1/logout",
            {},
            use_service_role=True,
            bearer_token=token,
            correlation_id=correlation_id,
        )

    @property
    def _base_url(self) -> str:
        return self.settings.supabase_url.rstrip("/")

    def _require_live_auth_settings(self) -> None:
        if httpx is None:
            raise RuntimeError("httpx is required for live Supabase authentication")
        if not self.settings.anon_key:
            raise ValueError("Supabase anon key is required for auth requests")
        if not self.settings.service_role_key:
            raise ValueError("Supabase service role key is required for profile access")

    def _headers(
        self,
        *,
        use_service_role: bool,
        bearer_token: str | None = None,
        correlation_id: str,
    ) -> dict[str, str]:
        api_key = self.settings.service_role_key if use_service_role else self.settings.anon_key
        bearer = bearer_token or api_key
        return {
            "apikey": api_key or "",
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
            "X-Correlation-Id": correlation_id,
        }

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        use_service_role: bool,
        correlation_id: str,
        bearer_token: str | None = None,
    ) -> dict[str, Any]:
        assert httpx is not None
        response = httpx.post(
            f"{self._base_url}{path}",
            headers=self._headers(
                use_service_role=use_service_role,
                bearer_token=bearer_token,
                correlation_id=correlation_id,
            ),
            json=payload,
            timeout=20,
        )
        self._raise_for_status(response, operation=path)
        if not response.content:
            return {}
        return response.json()

    def _get(
        self,
        path: str,
        *,
        use_service_role: bool,
        correlation_id: str,
        bearer_token: str | None = None,
    ) -> dict[str, Any]:
        assert httpx is not None
        response = httpx.get(
            f"{self._base_url}{path}",
            headers=self._headers(
                use_service_role=use_service_role,
                bearer_token=bearer_token,
                correlation_id=correlation_id,
            ),
            timeout=20,
        )
        self._raise_for_status(response, operation=path)
        return response.json()

    def _ensure_profile(
        self,
        *,
        user_id: str,
        email: str,
        display_name: str | None,
        correlation_id: str,
    ) -> Profile:
        if not user_id or "@" not in email:
            raise ValueError("Supabase auth response did not include a valid user")
        existing = self._fetch_profile(user_id=user_id, correlation_id=correlation_id)
        if existing is not None:
            return existing

        assert httpx is not None
        is_first_user = self._profiles_empty(correlation_id=correlation_id)
        role = AppRole.ADMIN.value if is_first_user else AppRole.USER.value
        profile_status = ProfileStatus.ACTIVE.value if is_first_user else ProfileStatus.PENDING_APPROVAL.value
        response = httpx.post(
            f"{self._base_url}/rest/v1/profiles?on_conflict=user_id",
            headers=self._headers(use_service_role=True, correlation_id=correlation_id)
            | {"Prefer": "resolution=merge-duplicates,return=representation"},
            json={
                "user_id": user_id,
                "email": email,
                "display_name": display_name,
                "role": role,
                "status": profile_status,
            },
            timeout=20,
        )
        self._raise_for_status(response, operation="profile_upsert")
        rows = response.json()
        if not rows:
            raise RuntimeError("Supabase profile upsert did not return a row")
        return self._profile_from_row(rows[0])

    def _fetch_profile(self, *, user_id: str, correlation_id: str) -> Profile | None:
        assert httpx is not None
        response = httpx.get(
            f"{self._base_url}/rest/v1/profiles",
            headers=self._headers(use_service_role=True, correlation_id=correlation_id),
            params={
                "user_id": f"eq.{user_id}",
                "select": "user_id,email,display_name,role,status,approved_by,approved_at",
                "limit": "1",
            },
            timeout=20,
        )
        self._raise_for_status(response, operation="profile_fetch")
        rows = response.json()
        return self._profile_from_row(rows[0]) if rows else None

    def _profiles_empty(self, *, correlation_id: str) -> bool:
        """Return True when no profiles exist yet (first-user bootstrap signal)."""
        assert httpx is not None
        response = httpx.get(
            f"{self._base_url}/rest/v1/profiles",
            headers=self._headers(use_service_role=True, correlation_id=correlation_id),
            params={"select": "user_id", "limit": "1"},
            timeout=20,
        )
        self._raise_for_status(response, operation="profiles_bootstrap_check")
        return not response.json()

    def _raise_for_status(self, response, *, operation: str) -> None:
        if response.status_code < 400:
            return
        detail = self._safe_error_detail(response)
        raise ValueError(f"Supabase {operation} failed: {detail}")

    def _safe_error_detail(self, response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        for key in ("msg", "message", "error_description", "error", "hint", "details"):
            value = payload.get(key)
            if value:
                return str(value)
        return f"HTTP {response.status_code}"

    def _profile_from_row(self, row: dict[str, Any]) -> Profile:
        return Profile(
            user_id=str(row["user_id"]),
            email=str(row["email"]),
            display_name=row.get("display_name"),
            role=AppRole(str(row.get("role", AppRole.USER.value))),
            status=ProfileStatus(str(row.get("status", ProfileStatus.PENDING_APPROVAL.value))),
            approved_by=row.get("approved_by"),
            approved_at=row.get("approved_at"),
        )

    def _session_from_response(self, response: dict[str, Any], profile: Profile) -> AuthenticatedSession:
        access_token = str(response.get("access_token") or "")
        if not access_token:
            raise ValueError("Registration created. Confirm the email address, then sign in.")
        return AuthenticatedSession(
            profile=profile,
            tokens=SessionTokens(
                access_token=access_token,
                refresh_token=response.get("refresh_token"),
                token_type=str(response.get("token_type") or "bearer"),
                expires_in_seconds=response.get("expires_in"),
            ),
        )

    def _metadata_display_name(self, user: dict[str, Any]) -> str | None:
        metadata = user.get("user_metadata") or {}
        display_name = metadata.get("display_name") or metadata.get("name")
        return str(display_name) if display_name else None

    def _user_from_auth_response(self, response: dict[str, Any]) -> dict[str, Any]:
        nested = response.get("user")
        if isinstance(nested, dict):
            return nested
        if response.get("id") or response.get("email"):
            return response
        return {}
