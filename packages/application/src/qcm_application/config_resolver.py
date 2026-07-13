"""Configuration resolution helpers for immutable run snapshots."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ConfigSource:
    name: str
    values: dict[str, Any]


def resolve_configuration(sources: list[ConfigSource]) -> dict[str, Any]:
    """Merge config sources in precedence order, with later sources overriding earlier ones."""

    resolved: dict[str, Any] = {}
    for source in sources:
        if not source.name:
            raise ValueError("ConfigSource requires a name")
        if "api_key" in source.values or "OPENROUTER_API_KEY" in source.values:
            raise ValueError("Resolved configuration sources must use secret refs, not raw secrets")
        resolved.update(source.values)
    return resolved
