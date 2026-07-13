"""OpenRouter-compatible LLM adapter boundary."""

from dataclasses import dataclass
import json
import re
from typing import Any

from qcm_domain.errors import DomainError, ErrorCode
from qcm_shared.provider_contracts import (
    ModelCallRequest,
    ModelCallResponse,
    ProviderKey,
)


@dataclass(frozen=True, slots=True)
class OpenRouterSettings:
    api_key_ref: str
    site_url: str = "https://local.dev"
    site_name: str = "QCM Extractor"
    endpoint: str = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterAdapter:
    provider_key = ProviderKey.OPENROUTER

    def __init__(self, settings: OpenRouterSettings, http_client: Any | None = None) -> None:
        self.settings = settings
        self.http_client = http_client

    def complete_json(self, request: ModelCallRequest) -> ModelCallResponse:
        if self.http_client is None:
            raise DomainError(
                code=ErrorCode.PROVIDER_FAILURE,
                message="OpenRouter HTTP client is not configured",
                correlation_id=request.correlation_id,
                retryable=True,
                safe_user_action="try_again_later",
            )
        payload = {
            "model": request.model_id,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        response = self.http_client.post(self.settings.endpoint, json=payload)
        status_code = getattr(response, "status_code", 200)
        if status_code in {429, 500, 502, 503}:
            raise DomainError(
                code=ErrorCode.PROVIDER_LIMIT_REACHED if status_code == 429 else ErrorCode.PROVIDER_FAILURE,
                message="Provider is temporarily unavailable",
                correlation_id=request.correlation_id,
                retryable=True,
                safe_user_action="try_again_later",
            )
        if status_code >= 400:
            raise DomainError(
                code=ErrorCode.PROVIDER_FAILURE,
                message="Provider request failed",
                correlation_id=request.correlation_id,
                retryable=False,
                safe_user_action="choose_different_model",
            )
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = _extract_json(content)
        usage = data.get("usage", {})
        return ModelCallResponse(
            provider=ProviderKey.OPENROUTER,
            model_id=request.model_id,
            content=content,
            parsed_json=parsed,
            usage={
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
            },
            cost_estimate=usage.get("cost"),
        )


def _extract_json(content: str) -> dict[str, Any] | None:
    cleaned = content.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    return json.loads(match.group(0))
