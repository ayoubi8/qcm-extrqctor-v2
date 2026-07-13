"""Auth use-case contracts built around Supabase Auth and approved profiles."""

from typing import Protocol

from qcm_domain.auth import AppRole, ProfileStatus, UserContext
from qcm_shared.auth_contracts import (
    AccountDeletionRequest,
    AuditEventDraft,
    AuthenticatedSession,
    LoginRequest,
    ModelPreference,
    Profile,
    RegisterRequest,
    UserPreference,
)

from qcm_application.ownership import ApprovalRequiredError, require_active_profile, require_admin


class AuthProvider(Protocol):
    def sign_in(self, request: LoginRequest, *, correlation_id: str) -> AuthenticatedSession:
        ...

    def sign_up(self, request: RegisterRequest, *, correlation_id: str) -> Profile:
        ...

    def verify_access_token(self, token: str, *, correlation_id: str) -> UserContext:
        ...

    def sign_out(self, token: str, *, correlation_id: str) -> None:
        ...


class ProfileRepository(Protocol):
    def get_profile(self, user_id: str) -> Profile | None:
        ...

    def update_status(
        self,
        user_id: str,
        status: ProfileStatus,
        *,
        approved_by: str | None,
        correlation_id: str,
    ) -> Profile:
        ...

    def list_preferences(self, user_id: str) -> list[UserPreference]:
        ...

    def save_preference(self, user_id: str, preference: UserPreference) -> UserPreference:
        ...

    def list_model_preferences(self, user_id: str) -> list[ModelPreference]:
        ...


class AuditSink(Protocol):
    def record(self, event: AuditEventDraft) -> None:
        ...


def ensure_session_can_access_app(user: UserContext) -> None:
    require_active_profile(user)


def approve_user(
    *,
    admin: UserContext,
    target_user_id: str,
    profiles: ProfileRepository,
    audit: AuditSink,
) -> Profile:
    require_admin(admin)
    profile = profiles.update_status(
        target_user_id,
        ProfileStatus.ACTIVE,
        approved_by=admin.user_id,
        correlation_id=admin.correlation_id,
    )
    audit.record(
        AuditEventDraft(
            actor_user_id=admin.user_id,
            actor_role=admin.role,
            event_type="profile_approved",
            target_type="profile",
            target_id=target_user_id,
            correlation_id=admin.correlation_id,
        )
    )
    return profile


def request_account_deletion(
    *,
    user: UserContext,
    request: AccountDeletionRequest,
    profiles: ProfileRepository,
    audit: AuditSink,
) -> Profile:
    if user.user_id != request.user_id and user.role != AppRole.ADMIN:
        raise ApprovalRequiredError("Only the account owner or an admin can request account deletion")
    profile = profiles.update_status(
        request.user_id,
        ProfileStatus.DELETION_REQUESTED,
        approved_by=None,
        correlation_id=request.correlation_id,
    )
    audit.record(
        AuditEventDraft(
            actor_user_id=user.user_id,
            actor_role=user.role,
            event_type="account_deletion_requested",
            target_type="profile",
            target_id=request.user_id,
            correlation_id=request.correlation_id,
            safe_payload={"reason_present": request.reason is not None},
        )
    )
    return profile
