"""Structured logging with secret redaction."""

from dataclasses import asdict, dataclass, field
from typing import Any

SECRET_KEYS = ("key", "secret", "token", "password", "dsn")


@dataclass(frozen=True, slots=True)
class StructuredLogEvent:
    event: str
    level: str
    correlation_id: str
    safe_payload: dict[str, Any] = field(default_factory=dict)


def redact_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if any(marker in key.lower() for marker in SECRET_KEYS):
            redacted[key] = "[redacted]"
        elif isinstance(value, dict):
            redacted[key] = redact_secrets(value)
        else:
            redacted[key] = value
    return redacted


def structured_log(event: StructuredLogEvent) -> dict[str, Any]:
    payload = asdict(event)
    payload["safe_payload"] = redact_secrets(event.safe_payload)
    return payload
