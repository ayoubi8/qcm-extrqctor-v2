import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/shared/src",
    "packages/application/src",
    "packages/infrastructure/src",
    "apps/api/src",
]:
    sys.path.insert(0, str(ROOT / relative))

from qcm_application.config_snapshot import draft_configuration_snapshot
from qcm_application.provider_service import ProviderRegistry, call_with_model_fallback
from qcm_domain.errors import DomainError, ErrorCode, normalize_exception
from qcm_infrastructure.llm.openrouter_adapter import OpenRouterAdapter, OpenRouterSettings
from qcm_shared.api_contracts import ConfigResolveCommand
from qcm_shared.provider_contracts import (
    ModelAuthorization,
    ModelCallResponse,
    ModelSelection,
    ProviderKey,
)
from qcm_shared.contracts import ProviderLimitEvent, UsageRecord


class RecordingProvider:
    provider_key = ProviderKey.OPENROUTER

    def __init__(self, failing_models: set[str] | None = None) -> None:
        self.failing_models = failing_models or set()

    def complete_json(self, request):
        if request.model_id in self.failing_models:
            raise DomainError(
                ErrorCode.PROVIDER_FAILURE,
                "Provider failed",
                request.correlation_id,
                retryable=True,
            )
        return ModelCallResponse(
            provider=request.provider,
            model_id=request.model_id,
            content='{"model": "%s"}' % request.model_id,
            parsed_json={"model": request.model_id},
            usage={"prompt_tokens": 10, "completion_tokens": 4},
            cost_estimate=0.01,
        )


class BackendFoundationTest(unittest.TestCase):
    def test_domain_error_normalizes_to_api_error(self) -> None:
        api_error = normalize_exception(
            DomainError(ErrorCode.MODEL_NOT_ALLOWED, "Nope", "corr", safe_user_action="choose_different_model"),
            correlation_id="corr",
        )
        self.assertEqual(api_error.code, "model_not_allowed")
        self.assertEqual(api_error.safe_user_action, "choose_different_model")

    def test_config_snapshot_precedence_and_secret_rejection(self) -> None:
        snapshot = draft_configuration_snapshot(
            ConfigResolveCommand(
                user_id="user-1",
                project_id="project-1",
                run_id="run-1",
                correlation_id="corr",
                system_defaults={"model": "base", "temperature": 0.1},
                user_defaults={"model": "user"},
                project_defaults={"page_range": "all"},
                run_overrides={"model": "run"},
                manual_auto_run_overrides={"page_range": "1-3"},
            ),
            created_by="user-1",
        )
        self.assertEqual(snapshot.resolved_values["model"], "run")
        self.assertEqual(snapshot.resolved_values["page_range"], "1-3")
        with self.assertRaises(ValueError):
            draft_configuration_snapshot(
                ConfigResolveCommand(
                    user_id="u",
                    project_id="p",
                    run_id="r",
                    correlation_id="corr",
                    system_defaults={"api_key": "raw"},
                ),
                created_by="u",
            )

    def test_provider_fallback_records_failed_primary_and_successful_fallback(self) -> None:
        registry = ProviderRegistry()
        registry.register(RecordingProvider({"primary"}))
        result = call_with_model_fallback(
            registry=registry,
            selection=ModelSelection(ProviderKey.OPENROUTER, "primary", ("fallback",)),
            authorization=ModelAuthorization({"primary", "fallback"}),
            prompt="Return JSON",
            purpose="test",
            schema_version="test.v1",
            correlation_id="corr",
        )
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.response.model_id, "fallback")
        self.assertEqual([attempt.status for attempt in result.attempts], ["failed", "completed"])

    def test_unauthorized_model_is_skipped_before_provider_call(self) -> None:
        registry = ProviderRegistry()
        registry.register(RecordingProvider())
        result = call_with_model_fallback(
            registry=registry,
            selection=ModelSelection(ProviderKey.OPENROUTER, "blocked", ("allowed",)),
            authorization=ModelAuthorization({"allowed"}),
            prompt="Return JSON",
            purpose="test",
            schema_version="test.v1",
            correlation_id="corr",
        )
        self.assertEqual(result.response.model_id, "allowed")
        self.assertEqual(result.attempts[0].error_code, "model_not_allowed")

    def test_openrouter_adapter_parses_json_and_usage_from_http_client(self) -> None:
        class Response:
            status_code = 200

            def json(self):
                return {
                    "choices": [{"message": {"content": "```json\n{\"ok\": true}\n```"}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 5, "cost": 0.2},
                }

        class Client:
            def post(self, endpoint, json=None, headers=None, timeout=None):
                return Response()

        adapter = OpenRouterAdapter(OpenRouterSettings(api_key="secret:openrouter"), Client())
        response = adapter.complete_json(
            request=__import__("qcm_shared.provider_contracts", fromlist=["ModelCallRequest"]).ModelCallRequest(
                provider=ProviderKey.OPENROUTER,
                model_id="model",
                prompt="prompt",
                schema_version="schema.v1",
                purpose="test",
                correlation_id="corr",
            )
        )
        self.assertEqual(response.parsed_json, {"ok": True})
        self.assertEqual(response.usage["completion_tokens"], 5)

    def test_usage_record_contract_validates_tokens(self) -> None:
        with self.assertRaises(ValueError):
            UsageRecord(
                usage_id="usage-1",
                user_id="user-1",
                provider="openrouter",
                operation="llm_call",
                tokens_in=-1,
                tokens_out=0,
                provider_limit_event=ProviderLimitEvent.NONE,
                created_at="2026-07-13T00:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
