import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/shared/src",
    "packages/application/src",
    "packages/infrastructure/src",
    "apps/worker/src",
]:
    sys.path.insert(0, str(ROOT / relative))

from qcm_application.steps.step2_orchestrator import InMemoryStep2ArtifactSink, Step2Orchestrator
from qcm_domain.enums import InternalCycleKey
from qcm_domain.steps.step2_contracts import COMBINED_STEP2_CYCLE_ORDER, cycles_from
from qcm_shared.contracts import ArtifactType, QualityStatus, TaskStatus
from qcm_shared.step2_contracts import Step2Config, Step2RunCommand, Step2SourcePage
from qcm_worker.step2_orchestrator_handler import step2_orchestrator_handler


class Step2OrchestratorTest(unittest.TestCase):
    def command(self, config: Step2Config | None = None, previous=None) -> Step2RunCommand:
        return Step2RunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            step1_artifact_ids=("step1-text",),
            pages=(
                Step2SourcePage(1, "1. Question one stem\nA. alpha\nB. beta\nC. gamma\nD. delta"),
                Step2SourcePage(2, "2. Question two stem\nA. alpha\nB. beta\nC. gamma\nD. delta"),
            ),
            config=config or Step2Config(metadata_defaults={"year": "2024", "source": "Alger"}),
            previous_cycle_data=previous or {},
        )

    def test_cycle_order_matches_combined_step2_contract(self) -> None:
        self.assertEqual(
            COMBINED_STEP2_CYCLE_ORDER,
            (
                InternalCycleKey.STEP2_QCM_PAGES,
                InternalCycleKey.STEP2_METADATA,
                InternalCycleKey.STEP2_FORMAT,
                InternalCycleKey.STEP2_FINALIZE,
            ),
        )
        self.assertEqual(cycles_from(InternalCycleKey.STEP2_FORMAT), (InternalCycleKey.STEP2_FORMAT, InternalCycleKey.STEP2_FINALIZE))

    def test_full_combined_run_writes_internal_and_final_artifacts(self) -> None:
        sink = InMemoryStep2ArtifactSink()
        result = Step2Orchestrator(artifact_sink=sink).run(self.command())
        self.assertEqual(result.quality.status, QualityStatus.PASSED)
        self.assertEqual(result.quality.total_qcms, 2)
        self.assertEqual([cycle.cycle_key for cycle in result.cycles], [cycle.value for cycle in COMBINED_STEP2_CYCLE_ORDER])
        self.assertIsNotNone(result.final_json_artifact_id)
        self.assertIsNotNone(result.final_xlsx_artifact_id)
        artifact_types = [record.request.artifact_type for record in sink.records]
        self.assertEqual(artifact_types.count(ArtifactType.STEP2_PAGE_QCM_JSON), 2)
        self.assertIn(ArtifactType.STEP2_FINAL_JSON, artifact_types)
        self.assertIn(ArtifactType.STEP2_FINAL_XLSX, artifact_types)
        self.assertTrue(all(record.request.source_artifact_ids == ["step1-text"] for record in sink.records))
        self.assertEqual(result.qcms[0]["Year"], "2024")

    def test_entry_validation_requires_step1_artifacts(self) -> None:
        command = Step2RunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            step1_artifact_ids=(),
            pages=(Step2SourcePage(1, "text"),),
        )
        with self.assertRaises(ValueError):
            Step2Orchestrator().run(command)

    def test_resume_from_metadata_preserves_prior_qcm_cycle(self) -> None:
        previous = {
            "qcms": [{"uid": "p1-q1", "page": 1, "number": 1, "text": "Prior QCM", "propositions": {}}],
            "artifact_ids": ["prior-page-qcm"],
        }
        result = Step2Orchestrator(artifact_sink=InMemoryStep2ArtifactSink()).run(
            self.command(
                Step2Config(metadata_defaults={"year": "2025"}, resume_from_cycle=InternalCycleKey.STEP2_METADATA.value),
                previous=previous,
            )
        )
        self.assertEqual(result.cycles[0].cycle_key, InternalCycleKey.STEP2_QCM_PAGES.value)
        self.assertEqual(result.cycles[0].status, "preserved")
        self.assertEqual(result.quality.total_qcms, 1)
        self.assertEqual(result.qcms[0]["Year"], "2025")

    def test_worker_handler_reports_completed_with_warnings_when_metadata_defaults_absent(self) -> None:
        result = step2_orchestrator_handler(
            {
                "user_id": "u",
                "project_id": "p",
                "run_id": "r",
                "step1_artifact_ids": ["step1-text"],
                "pages": [{"page_number": 1, "text": "Question one"}],
                "config": {"template_name": "default"},
            }
        )
        self.assertEqual(result["status"], TaskStatus.COMPLETED_WITH_WARNINGS.value)
        self.assertEqual(result["result"]["total_qcms"], 1)


if __name__ == "__main__":
    unittest.main()
