"""Provider, model fallback, usage, and prompt contracts."""

from dataclasses import dataclass, field
from qcm_shared.compat import StrEnum
from typing import Any

from qcm_shared.contracts import ProviderLimitEvent


class ProviderKey(StrEnum):
    OPENROUTER = "openrouter"


class ProviderErrorCategory(StrEnum):
    RETRYABLE = "retryable"
    PROVIDER_LIMIT = "provider_limit"
    INVALID_SCHEMA = "invalid_schema"
    UNAUTHORIZED_MODEL = "unauthorized_model"
    FATAL = "fatal"


@dataclass(frozen=True, slots=True)
class ModelSelection:
    provider: ProviderKey
    primary_model_id: str
    fallback_model_ids: tuple[str, ...] = ()

    def ordered_models(self) -> tuple[str, ...]:
        return (self.primary_model_id, *self.fallback_model_ids)

    def __post_init__(self) -> None:
        if self.provider != ProviderKey.OPENROUTER:
            raise ValueError("OpenRouter is the only initial provider")
        if not self.primary_model_id:
            raise ValueError("ModelSelection requires primary_model_id")


@dataclass(frozen=True, slots=True)
class PromptSpec:
    prompt_id: str
    schema_version: str
    purpose: str
    template: str


@dataclass(frozen=True, slots=True)
class ModelCallRequest:
    provider: ProviderKey
    model_id: str
    prompt: str
    schema_version: str
    purpose: str
    correlation_id: str
    max_tokens: int = 4000
    temperature: float = 0.1
    json_schema: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ModelCallResponse:
    provider: ProviderKey
    model_id: str
    content: str
    parsed_json: dict[str, Any] | None
    usage: dict[str, int]
    cost_estimate: float | None = None
    raw_response_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ModelAttemptRecord:
    attempt_number: int
    provider: ProviderKey
    model_id: str
    status: str
    retryable: bool
    failure_category: ProviderErrorCategory | None = None
    error_code: str | None = None
    safe_error_message: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_estimate: float | None = None
    fallback_used: bool = False
    provider_limit_event: ProviderLimitEvent = ProviderLimitEvent.NONE


@dataclass(frozen=True, slots=True)
class ModelFallbackResult:
    response: ModelCallResponse | None
    attempts: tuple[ModelAttemptRecord, ...]
    used_fallback: bool


@dataclass(frozen=True, slots=True)
class ModelAuthorization:
    allowed_model_ids: set[str] = field(default_factory=set)

    def allows(self, model_id: str) -> bool:
        return not self.allowed_model_ids or model_id in self.allowed_model_ids
