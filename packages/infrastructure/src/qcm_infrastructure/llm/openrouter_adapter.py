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
    api_key: str
    site_url: str = "https://20.5.176.133.sslip.io"
    site_name: str = "QCM Extractor"
    endpoint: str = "https://openrouter.ai/api/v1/chat/completions"
    timeout: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpenRouterSettings requires api_key")


class OpenRouterAdapter:
    provider_key = ProviderKey.OPENROUTER

    def __init__(self, settings: OpenRouterSettings, http_client: Any | None = None) -> None:
        self.settings = settings
        self.http_client = http_client or _build_default_client(settings)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.settings.site_url,
            "X-Title": self.settings.site_name,
        }

    def _handle_error_status(self, status_code: int, correlation_id: str) -> None:
        if status_code in {429, 500, 502, 503}:
            raise DomainError(
                code=ErrorCode.PROVIDER_LIMIT_REACHED if status_code == 429 else ErrorCode.PROVIDER_FAILURE,
                message="Provider is temporarily unavailable",
                correlation_id=correlation_id,
                retryable=True,
                safe_user_action="try_again_later",
            )
        if status_code >= 400:
            raise DomainError(
                code=ErrorCode.PROVIDER_FAILURE,
                message=f"Provider request failed (HTTP {status_code})",
                correlation_id=correlation_id,
                retryable=False,
                safe_user_action="choose_different_model",
            )

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
        response = self.http_client.post(self.settings.endpoint, json=payload, headers=self._headers(), timeout=self.settings.timeout)
        status_code = getattr(response, "status_code", 200)
        self._handle_error_status(status_code, request.correlation_id)
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

    def complete_vision(
        self,
        prompt: str,
        image_base64: str,
        *,
        model_id: str,
        correlation_id: str,
        max_tokens: int = 8000,
        temperature: float = 0.1,
        image_mime: str = "image/png",
    ) -> str:
        """Send a multimodal (text + image) chat request and return the text response."""
        if self.http_client is None:
            raise DomainError(
                code=ErrorCode.PROVIDER_FAILURE,
                message="OpenRouter HTTP client is not configured",
                correlation_id=correlation_id,
                retryable=True,
                safe_user_action="try_again_later",
            )
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{image_base64}"}},
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        response = self.http_client.post(self.settings.endpoint, json=payload, headers=self._headers(), timeout=self.settings.timeout)
        status_code = getattr(response, "status_code", 200)
        self._handle_error_status(status_code, correlation_id)
        data = response.json()
        return str(data["choices"][0]["message"]["content"])


def _extract_json(content: str) -> dict[str, Any] | None:
    cleaned = content.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    return json.loads(match.group(0))


def _build_default_client(settings: OpenRouterSettings):
    """Build an httpx.Client if httpx is available; return None otherwise."""
    try:
        import httpx
        return httpx.Client(timeout=settings.timeout)
    except ImportError:  # pragma: no cover
        return None


def build_openrouter_adapter_from_env() -> "OpenRouterAdapter | None":
    """Build an OpenRouterAdapter from OPENROUTER_API_KEY env var, or None if absent."""
    import os
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None
    return OpenRouterAdapter(OpenRouterSettings(api_key=key))