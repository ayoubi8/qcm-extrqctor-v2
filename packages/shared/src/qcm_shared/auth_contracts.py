"""Shared auth, profile, preference, usage, and audit DTOs."""

from dataclasses import dataclass, field
from qcm_shared.compat import StrEnum
from typing import Any

from qcm_domain.auth import AppRole, ProfileStatus
from qcm_shared.contracts import ProviderLimitEvent


class AccountDeletionStatus(StrEnum):
    NONE = "none"
    REQUESTED = "requested"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class LoginRequest:
    email: str
    password: str

    def __post_init__(self) -> None:
        if "@" not in self.email:
            raise ValueError("LoginRequest requires an email address")
        if not self.password:
            raise ValueError("LoginRequest requires a password")


@dataclass(frozen=True, slots=True)
class RegisterRequest:
    email: str
    password: str
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class SessionTokens:
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in_seconds: int | None = None

    def __post_init__(self) -> None:
        if not self.access_token:
            raise ValueError("SessionTokens requires access_token")


@dataclass(frozen=True, slots=True)
class Profile:
    user_id: str
    email: str
    role: AppRole
    status: ProfileStatus
    display_name: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None

    def __post_init__(self) -> None:
        if not self.user_id or "@" not in self.email:
            raise ValueError("Profile requires user_id and email")


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    profile: Profile
    tokens: SessionTokens

    @property
    def approved(self) -> bool:
        return self.profile.status == ProfileStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UserPreference:
    preference_key: str
    value: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.preference_key:
            raise ValueError("UserPreference requires preference_key")


@dataclass(frozen=True, slots=True)
class ModelPreference:
    provider: str
    primary_model_id: str
    fallback_model_ids: tuple[str, ...] = field(default_factory=tuple)
    scope: str = "default"

    def __post_init__(self) -> None:
        if self.provider != "openrouter":
            raise ValueError("OpenRouter is the only initial model provider")
        if not self.primary_model_id:
            raise ValueError("ModelPreference requires primary_model_id")


@dataclass(frozen=True, slots=True)
class UsageLimitState:
    user_id: str
    provider: str
    provider_limit_event: ProviderLimitEvent
    operation: str
    safe_message: str | None = None


@dataclass(frozen=True, slots=True)
class AuditEventDraft:
    actor_user_id: str | None
    actor_role: AppRole
    event_type: str
    target_type: str
    target_id: str
    correlation_id: str
    project_id: str | None = None
    safe_payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = [self.event_type, self.target_type, self.target_id, self.correlation_id]
        if any(not value for value in required):
            raise ValueError("AuditEventDraft requires event, target, and correlation identifiers")


@dataclass(frozen=True, slots=True)
class AccountDeletionRequest:
    user_id: str
    requested_by: str
    reason: str | None
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.user_id or not self.requested_by or not self.correlation_id:
            raise ValueError("AccountDeletionRequest requires user, requester, and correlation id")
