import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/shared/src",
    "packages/application/src",
    "apps/worker/src",
]:
    sys.path.insert(0, str(ROOT / relative))

from qcm_application.ai_autorun_service import AiAutoRunService
from qcm_domain.ai_autorun import AiAutoRunGate, AiDocumentMap, AiDocumentMapPage, assert_safe_summary, evaluate_ai_quality
from qcm_shared.ai_autorun_contracts import (
    AI_AUTORUN_TASK_KIND,
    AiAutoRunAction,
    AiAutoRunActionCommand,
    AiAutoRunPageInput,
    AiAutoRunStartCommand,
    AiAutoRunStatus,
)
from qcm_shared.contracts import ArtifactType, TaskStatus
from qcm_shared.provider_contracts import ModelAuthorization, ModelSelection, ProviderKey
from qcm_worker.ai_autorun_handler import ai_autorun_handler


class ArtifactSink:
    def __init__(self) -> None:
        self.requests = []

    def write(self, request):
        self.requests.append(request)
        return request.artifact_id


class AiAutoRunTest(unittest.TestCase):
    def command(self) -> AiAutoRunStartCommand:
        return AiAutoRunStartCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            ai_run_id="ai",
            pages=(
                AiAutoRunPageInput(1, "question page with qcm"),
                AiAutoRunPageInput(2, "correction answers"),
            ),
            model_selection=ModelSelection(ProviderKey.OPENROUTER, "allowed-model", ("fallback-model",)),
            idempotency_key="idem",
            correlation_id="corr",
        )

    def test_safe_summary_blocks_raw_reasoning(self) -> None:
        with self.assertRaises(ValueError):
            assert_safe_summary("hidden reasoning: private scratchpad")

    def test_document_map_quality_requests_manual_intervention_for_low_confidence(self) -> None:
        document_map = AiDocumentMap((AiDocumentMapPage(1, "context", 0.4, "Page 1 classified as context"),))
        gate, warnings = evaluate_ai_quality(document_map=document_map, config_errors=())
        self.assertEqual(gate, AiAutoRunGate.MANUAL_INTERVENTION)
        self.assertTrue(warnings)

    def test_plan_writes_ai_artifacts_and_evidence_only(self) -> None:
        sink = ArtifactSink()
        result = AiAutoRunService(
            artifact_sink=sink,
            model_authorization=ModelAuthorization({"allowed-model", "fallback-model"}),
        ).plan(self.command())
        self.assertIn(result.status, {AiAutoRunStatus.COMPLETED, AiAutoRunStatus.MANUAL_INTERVENTION_REQUIRED})
        artifact_types = [request.artifact_type for request in sink.requests]
        self.assertIn(ArtifactType.AI_AUTORUN_DOCUMENT_MAP, artifact_types)
        self.assertIn(ArtifactType.AI_AUTORUN_CONFIG, artifact_types)
        self.assertIn(ArtifactType.AI_AUTORUN_EVIDENCE, artifact_types)
        self.assertNotIn("reasoning", str(result.evidence_summaries).lower())

    def test_unauthorized_model_is_blocked(self) -> None:
        with self.assertRaises(ValueError):
            AiAutoRunService(model_authorization=ModelAuthorization({"other-model"})).start(self.command())

    def test_action_is_owner_scoped_status_update(self) -> None:
        service = AiAutoRunService(model_authorization=ModelAuthorization({"allowed-model", "fallback-model"}))
        service.start(self.command())
        record = service.action(AiAutoRunActionCommand("u", "p", "ai", AiAutoRunAction.CANCEL, "corr"))
        self.assertEqual(record.status, AiAutoRunStatus.CANCELLED)

    def test_worker_handler_returns_warning_for_low_confidence_context(self) -> None:
        result = ai_autorun_handler(
            {
                "user_id": "u",
                "project_id": "p",
                "run_id": "r",
                "ai_run_id": "ai",
                "pages": [{"page_number": 1, "text": "plain cover page"}],
                "model_selection": {"provider": "openrouter", "primary_model_id": "configured-by-admin"},
            }
        )
        self.assertEqual(result["status"], TaskStatus.COMPLETED_WITH_WARNINGS.value)
        self.assertEqual(result["result"]["ai_run_id"], "ai")

    def test_task_kind_is_distinct_from_manual_autorun(self) -> None:
        self.assertEqual(AI_AUTORUN_TASK_KIND, "ai_autorun")


if __name__ == "__main__":
    unittest.main()
