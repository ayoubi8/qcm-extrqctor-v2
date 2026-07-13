"""Stable domain errors normalized into API-safe responses."""

from dataclasses import dataclass, field
from qcm_domain.compat import StrEnum
from typing import Any

from qcm_shared.contracts import ApiError


class ErrorCode(StrEnum):
    UNAUTHORIZED = "unauthorized"
    APPROVAL_REQUIRED = "approval_required"
    INVALID_SCHEMA = "invalid_schema"
    INVALID_CONFIGURATION = "invalid_configuration"
    MODEL_NOT_ALLOWED = "model_not_allowed"
    PROVIDER_LIMIT_REACHED = "provider_limit_reached"
    PROVIDER_FAILURE = "provider_failure"
    FILE_SIZE_LIMIT_EXCEEDED = "file_size_limit_exceeded"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INTERNAL_ERROR = "internal_error"


@dataclass(slots=True)
class DomainError(Exception):
    code: ErrorCode
    message: str
    correlation_id: str
    retryable: bool = False
    safe_user_action: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_api_error(self) -> ApiError:
        return ApiError(
            code=self.code.value,
            message=self.message,
            details=self.details or None,
            correlation_id=self.correlation_id,
            retryable=self.retryable,
            safe_user_action=self.safe_user_action,
        )


def normalize_exception(error: Exception, *, correlation_id: str) -> ApiError:
    if isinstance(error, DomainError):
        return error.to_api_error()
    return ApiError(
        code=ErrorCode.INTERNAL_ERROR.value,
        message="Unexpected server error",
        details=None,
        correlation_id=correlation_id,
        retryable=False,
        safe_user_action="try_again_later",
    )
