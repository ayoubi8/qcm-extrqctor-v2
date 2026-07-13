"""Ownership and approval guards used before project-scoped operations."""

from dataclasses import dataclass

from qcm_domain.auth import AppRole, ProfileStatus, UserContext


class AuthorizationError(PermissionError):
    code = "unauthorized"


class ApprovalRequiredError(PermissionError):
    code = "approval_required"


@dataclass(frozen=True, slots=True)
class OwnedResource:
    user_id: str
    project_id: str | None = None


def require_active_profile(user: UserContext) -> None:
    if user.status != ProfileStatus.ACTIVE:
        raise ApprovalRequiredError("User profile is not active")


def require_admin(user: UserContext) -> None:
    require_active_profile(user)
    if user.role != AppRole.ADMIN:
        raise AuthorizationError("Admin privileges required")


def require_owner(user: UserContext, resource: OwnedResource) -> None:
    require_active_profile(user)
    if user.role == AppRole.ADMIN:
        return
    if resource.user_id != user.user_id:
        raise AuthorizationError("Resource does not belong to authenticated user")


def require_project_owner(user: UserContext, *, resource_user_id: str, project_id: str) -> OwnedResource:
    resource = OwnedResource(user_id=resource_user_id, project_id=project_id)
    require_owner(user, resource)
    return resource
