"""API error normalization helpers."""

from qcm_domain.errors import normalize_exception


def safe_error_payload(error: Exception, *, correlation_id: str) -> dict:
    api_error = normalize_exception(error, correlation_id=correlation_id)
    return {
        "code": api_error.code,
        "message": api_error.message,
        "details": api_error.details,
        "correlation_id": api_error.correlation_id,
        "retryable": api_error.retryable,
        "safe_user_action": api_error.safe_user_action,
    }
