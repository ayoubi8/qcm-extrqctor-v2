"""Configuration precedence and immutable snapshot drafting."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from qcm_shared.api_contracts import ConfigResolveCommand, ConfigSnapshotDraft

PRECEDENCE = (
    "system_defaults",
    "user_defaults",
    "project_defaults",
    "run_overrides",
    "manual_auto_run_overrides",
)

AI_PRECEDENCE = (
    "system_defaults",
    "user_defaults",
    "project_defaults",
    "ai_proposal_values",
)


def _canonical_hash(values: dict[str, Any]) -> str:
    payload = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _merge_sources(command: ConfigResolveCommand, precedence: tuple[str, ...]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for source_name in precedence:
        resolved.update(getattr(command, source_name))
    return resolved


def draft_configuration_snapshot(
    command: ConfigResolveCommand,
    *,
    created_by: str,
    schema_version: str = "configuration.v1",
    include_ai_proposal: bool = False,
    secret_refs: dict[str, Any] | None = None,
) -> ConfigSnapshotDraft:
    precedence = AI_PRECEDENCE if include_ai_proposal else PRECEDENCE
    resolved = _merge_sources(command, precedence)
    if "api_key" in resolved or "OPENROUTER_API_KEY" in resolved:
        raise ValueError("Resolved configuration must not contain raw secrets")
    return ConfigSnapshotDraft(
        schema_version=schema_version,
        source_precedence=precedence,
        resolved_values=resolved,
        secret_refs=secret_refs or {},
        created_by=created_by,
        run_id=command.run_id,
        config_hash=_canonical_hash(resolved),
    )
