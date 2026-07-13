"""Provider registry, model authorization, fallback, and attempt recording."""

from typing import Protocol

from qcm_domain.errors import DomainError, ErrorCode
from qcm_shared.contracts import ProviderLimitEvent
from qcm_shared.provider_contracts import (
    ModelAttemptRecord,
    ModelAuthorization,
    ModelCallRequest,
    ModelCallResponse,
    ModelFallbackResult,
    ModelSelection,
    ProviderErrorCategory,
    ProviderKey,
)


class ProviderAdapter(Protocol):
    provider_key: ProviderKey

    def complete_json(self, request: ModelCallRequest) -> ModelCallResponse:
        ...


class AttemptRecorder(Protocol):
    def record_attempt(self, attempt: ModelAttemptRecord) -> None:
        ...


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[ProviderKey, ProviderAdapter] = {}

    def register(self, provider: ProviderAdapter) -> None:
        if provider.provider_key in self._providers:
            raise ValueError(f"Provider already registered: {provider.provider_key}")
        self._providers[provider.provider_key] = provider

    def get(self, provider_key: ProviderKey) -> ProviderAdapter:
        try:
            return self._providers[provider_key]
        except KeyError as exc:
            raise DomainError(
                code=ErrorCode.PROVIDER_FAILURE,
                message="Provider is not configured",
                correlation_id="provider-registry",
                retryable=False,
                safe_user_action="contact_admin",
            ) from exc


def call_with_model_fallback(
    *,
    registry: ProviderRegistry,
    selection: ModelSelection,
    authorization: ModelAuthorization,
    prompt: str,
    purpose: str,
    schema_version: str,
    correlation_id: str,
    recorder: AttemptRecorder | None = None,
) -> ModelFallbackResult:
    provider = registry.get(selection.provider)
    attempts: list[ModelAttemptRecord] = []
    for attempt_number, model_id in enumerate(selection.ordered_models(), start=1):
        fallback_used = attempt_number > 1
        if not authorization.allows(model_id):
            attempt = ModelAttemptRecord(
                attempt_number=attempt_number,
                provider=selection.provider,
                model_id=model_id,
                status="failed",
                retryable=False,
                failure_category=ProviderErrorCategory.UNAUTHORIZED_MODEL,
                error_code=ErrorCode.MODEL_NOT_ALLOWED.value,
                safe_error_message="Model is not authorized for this user",
                fallback_used=fallback_used,
            )
            attempts.append(attempt)
            if recorder:
                recorder.record_attempt(attempt)
            continue
        try:
            response = provider.complete_json(
                ModelCallRequest(
                    provider=selection.provider,
                    model_id=model_id,
                    prompt=prompt,
                    schema_version=schema_version,
                    purpose=purpose,
                    correlation_id=correlation_id,
                )
            )
            attempt = ModelAttemptRecord(
                attempt_number=attempt_number,
                provider=selection.provider,
                model_id=model_id,
                status="completed",
                retryable=False,
                tokens_in=response.usage.get("prompt_tokens", 0),
                tokens_out=response.usage.get("completion_tokens", 0),
                cost_estimate=response.cost_estimate,
                fallback_used=fallback_used,
            )
            attempts.append(attempt)
            if recorder:
                recorder.record_attempt(attempt)
            return ModelFallbackResult(response=response, attempts=tuple(attempts), used_fallback=fallback_used)
        except DomainError as error:
            category = (
                ProviderErrorCategory.PROVIDER_LIMIT
                if error.code == ErrorCode.PROVIDER_LIMIT_REACHED
                else ProviderErrorCategory.RETRYABLE
                if error.retryable
                else ProviderErrorCategory.FATAL
            )
            attempt = ModelAttemptRecord(
                attempt_number=attempt_number,
                provider=selection.provider,
                model_id=model_id,
                status="failed",
                retryable=error.retryable,
                failure_category=category,
                error_code=error.code.value,
                safe_error_message=error.message,
                fallback_used=fallback_used,
                provider_limit_event=ProviderLimitEvent.PROVIDER_UNAVAILABLE
                if category == ProviderErrorCategory.RETRYABLE
                else ProviderLimitEvent.UNKNOWN,
            )
            attempts.append(attempt)
            if recorder:
                recorder.record_attempt(attempt)
            if not error.retryable:
                break
    return ModelFallbackResult(response=None, attempts=tuple(attempts), used_fallback=len(attempts) > 1)
