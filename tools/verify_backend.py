"""Dependency-light verification for Plan 05 backend/provider foundations."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/shared/src",
    "packages/application/src",
    "packages/infrastructure/src",
    "apps/api/src",
]:
    sys.path.insert(0, str(ROOT / relative))

REQUIRED_PATHS = [
    "packages/domain/src/qcm_domain/errors.py",
    "packages/shared/src/qcm_shared/api_contracts.py",
    "packages/shared/src/qcm_shared/provider_contracts.py",
    "packages/application/src/qcm_application/config_snapshot.py",
    "packages/application/src/qcm_application/provider_service.py",
    "packages/application/src/qcm_application/repositories.py",
    "packages/application/src/qcm_application/use_cases/projects.py",
    "packages/application/src/qcm_application/use_cases/runs.py",
    "packages/infrastructure/src/qcm_infrastructure/llm/openrouter_adapter.py",
    "packages/infrastructure/src/qcm_infrastructure/db/repositories.py",
    "apps/api/src/qcm_api/error_handlers.py",
    "apps/api/src/qcm_api/routes/projects.py",
    "apps/api/src/qcm_api/routes/config.py",
]


def verify_paths() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Plan 05 paths: {missing}")


def verify_contracts() -> None:
    from qcm_application.config_snapshot import draft_configuration_snapshot
    from qcm_application.provider_service import ProviderRegistry, call_with_model_fallback
    from qcm_domain.errors import DomainError, ErrorCode, normalize_exception
    from qcm_shared.api_contracts import ConfigResolveCommand
    from qcm_shared.provider_contracts import (
        ModelAuthorization,
        ModelCallResponse,
        ModelSelection,
        ProviderKey,
    )
    from qcm_application import repositories

    error = normalize_exception(
        DomainError(ErrorCode.INVALID_CONFIGURATION, "Bad config", "corr"),
        correlation_id="ignored",
    )
    assert error.code == "invalid_configuration"

    snapshot = draft_configuration_snapshot(
        ConfigResolveCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            correlation_id="corr",
            system_defaults={"model": "base", "a": 1},
            user_defaults={"a": 2},
            run_overrides={"b": 3},
        ),
        created_by="u",
    )
    assert snapshot.resolved_values == {"model": "base", "a": 2, "b": 3}
    assert snapshot.config_hash

    class Provider:
        provider_key = ProviderKey.OPENROUTER

        def complete_json(self, request):
            return ModelCallResponse(
                provider=request.provider,
                model_id=request.model_id,
                content='{"ok": true}',
                parsed_json={"ok": True},
                usage={"prompt_tokens": 1, "completion_tokens": 2},
            )

    registry = ProviderRegistry()
    registry.register(Provider())
    result = call_with_model_fallback(
        registry=registry,
        selection=ModelSelection(ProviderKey.OPENROUTER, "model-a", ("model-b",)),
        authorization=ModelAuthorization({"model-a"}),
        prompt="Return JSON",
        purpose="verify",
        schema_version="verify.v1",
        correlation_id="corr",
    )
    assert result.response is not None
    assert result.response.parsed_json == {"ok": True}
    assert repositories.UsageRecord is not None


def main() -> int:
    verify_paths()
    verify_contracts()
    print("Plan 05 backend and provider foundation verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
