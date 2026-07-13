"""Provider-free authentication and tenancy domain objects."""

from dataclasses import dataclass
from qcm_domain.compat import StrEnum


class AppRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    SERVICE = "service"
    WORKER = "worker"


class ProfileStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETION_REQUESTED = "deletion_requested"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class UserContext:
    user_id: str
    email: str
    role: AppRole
    status: ProfileStatus
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("UserContext requires user_id")
        if not self.email and self.role not in {AppRole.SERVICE, AppRole.WORKER}:
            raise ValueError("UserContext requires email for user/admin actors")
        if not self.correlation_id:
            raise ValueError("UserContext requires correlation_id")

    @property
    def is_admin(self) -> bool:
        return self.role == AppRole.ADMIN

    @property
    def is_active(self) -> bool:
        return self.status == ProfileStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class WorkerContext:
    worker_id: str
    role: AppRole
    correlation_id: str

    def __post_init__(self) -> None:
        if self.role != AppRole.WORKER:
            raise ValueError("WorkerContext role must be worker")
        if not self.worker_id or not self.correlation_id:
            raise ValueError("WorkerContext requires worker_id and correlation_id")
