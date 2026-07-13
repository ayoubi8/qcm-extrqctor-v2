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

from qcm_application.ownership import AuthorizationError
from qcm_application.reference_db_service import ReferenceDbService
from qcm_application.steps.step4_similarity_service import InMemoryStep4ArtifactSink, Step4SimilarityService
from qcm_domain.reference_db import (
    DEFAULT_CORRECTION_WEIGHT,
    DEFAULT_GREEN_BAND,
    DEFAULT_MATCH_THRESHOLD,
    DEFAULT_TEXT_WEIGHT,
    DEFAULT_YELLOW_BAND,
    SimilarityMatchMode,
    normalize_match_mode,
    similarity_band,
    validate_match_threshold,
    validate_match_weights,
)
from qcm_shared.contracts import ArtifactType, QualityStatus, TaskStatus
from qcm_shared.step4_contracts import ReferenceDbCreateCommand, Step4SimilarityConfig, Step4SimilarityRunCommand
from qcm_worker.step4_similarity_handler import step4_similarity_handler


class Step4SimilarityTest(unittest.TestCase):
    def command(self, config: Step4SimilarityConfig | None = None) -> Step4SimilarityRunCommand:
        return Step4SimilarityRunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            source_artifact_ids=("step2-final",),
            source_qcms=(
                {"Num": 1, "Text": "renal colic pain", "A": "stone", "B": "fever", "Correct": "A"},
                {"Num": 2, "Text": "viral rash", "A": "antibiotic", "B": "supportive", "Correct": "B"},
            ),
            reference_qcms=(
                {"Num": "ref-1", "Text": "renal colic pain", "A": "stone", "B": "fever", "Correct": "A"},
                {"Num": "ref-2", "Text": "unrelated cardiology", "A": "beta blocker", "Correct": "A"},
            ),
            config=config or Step4SimilarityConfig(reference_db_id="ref-db"),
        )

    def test_defaults_and_domain_validation(self) -> None:
        self.assertEqual(DEFAULT_MATCH_THRESHOLD, 0.75)
        self.assertEqual(DEFAULT_TEXT_WEIGHT, 0.7)
        self.assertEqual(DEFAULT_CORRECTION_WEIGHT, 0.3)
        self.assertEqual(DEFAULT_GREEN_BAND, 0.90)
        self.assertEqual(DEFAULT_YELLOW_BAND, 0.75)
        self.assertEqual(normalize_match_mode("weighted"), SimilarityMatchMode.WEIGHTED)
        self.assertEqual(validate_match_threshold(0.75), 0.75)
        self.assertEqual(validate_match_weights(7, 3), (0.7, 0.3))
        self.assertEqual(similarity_band(0.92), "green")
        self.assertEqual(similarity_band(0.8), "yellow")
        self.assertEqual(similarity_band(0.2), "red")

    def test_reference_db_is_user_private_and_idempotent(self) -> None:
        service = ReferenceDbService()
        command = ReferenceDbCreateCommand(
            user_id="u1",
            reference_db_id="ref-1",
            name="Private refs",
            qcms=({"Num": 1, "Text": "Q"},),
            idempotency_key="idem-1",
        )
        first = service.create(command)
        second = service.create(command)
        self.assertEqual(first.metadata.reference_db_id, second.metadata.reference_db_id)
        self.assertEqual(len(service.list_owned(user_id="u1")), 1)
        with self.assertRaises(AuthorizationError):
            service.get_qcms(user_id="u2", reference_db_id="ref-1")

    def test_text_only_run_writes_match_artifacts(self) -> None:
        sink = InMemoryStep4ArtifactSink()
        result = Step4SimilarityService(artifact_sink=sink).run(self.command())
        self.assertEqual(result.quality.status, QualityStatus.PASSED)
        self.assertEqual(result.summary.matched_qcms, 1)
        self.assertEqual(result.matches[0]["best_match"]["ref_id"], "ref-1")
        artifact_types = [record.request.artifact_type for record in sink.records]
        self.assertIn(ArtifactType.STEP4_SIMILARITY_JSON, artifact_types)
        self.assertIn(ArtifactType.STEP4_SIMILARITY_XLSX, artifact_types)
        self.assertTrue(all(record.request.source_artifact_ids == ["step2-final"] for record in sink.records))

    def test_weighted_mode_uses_correction_similarity(self) -> None:
        result = Step4SimilarityService().run(
            self.command(
                Step4SimilarityConfig(
                    reference_db_id="ref-db",
                    mode="weighted",
                    threshold=0.65,
                    text_weight=0.7,
                    correction_weight=0.3,
                )
            )
        )
        self.assertEqual(result.summary.mode, "weighted")
        self.assertIsNotNone(result.matches[0]["best_match"]["corr_similarity"])

    def test_export_existing_filters_and_writes_export_artifact(self) -> None:
        config = Step4SimilarityConfig(
            reference_db_id="ref-db",
            export_existing=True,
            export_min_similarity=0.8,
            export_qcm_ids=("1",),
        )
        result = Step4SimilarityService().run(
            Step4SimilarityRunCommand(
                user_id="u",
                project_id="p",
                run_id="r",
                source_artifact_ids=("step4-old",),
                source_qcms=(),
                reference_qcms=(),
                existing_matches=(
                    {"source_id": "1", "best_match": {"similarity": 0.91, "band": "green", "mode": "text_only", "ref_qcm": {"Num": 9}}},
                    {"source_id": "2", "best_match": {"similarity": 0.5, "band": "red", "mode": "text_only", "ref_qcm": {}}},
                ),
                config=config,
            )
        )
        self.assertEqual(len(result.exported_matches), 1)
        self.assertIsNotNone(result.export_artifact_id)
        self.assertEqual(result.quality.status, QualityStatus.PASSED_WITH_WARNINGS)

    def test_worker_handler_maps_no_matches_to_completed_with_warnings(self) -> None:
        result = step4_similarity_handler(
            {
                "user_id": "u",
                "project_id": "p",
                "run_id": "r",
                "source_artifact_ids": ["step2-final"],
                "source_qcms": [{"Num": 1, "Text": "dermatology"}],
                "reference_qcms": [{"Num": "ref", "Text": "cardiology"}],
                "config": {"reference_db_id": "ref-db", "threshold": 0.95},
            }
        )
        self.assertEqual(result["status"], TaskStatus.COMPLETED_WITH_WARNINGS.value)


if __name__ == "__main__":
    unittest.main()
