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

from qcm_application.steps.step3_correction_service import InMemoryStep3ArtifactSink, Step3CorrectionService
from qcm_domain.corrections import (
    CorrectionMode,
    extract_correction_map_from_text,
    include_neighbor_pages,
    normalize_correction_mode,
    parse_page_selection,
    score_correction_page,
)
from qcm_shared.contracts import ArtifactType, QualityStatus, TaskStatus
from qcm_shared.step3_contracts import Step3CorrectionConfig, Step3CorrectionPage, Step3CorrectionRunCommand
from qcm_worker.step3_correction_handler import step3_correction_handler


class Step3CorrectionTest(unittest.TestCase):
    def command(self, config: Step3CorrectionConfig | None = None) -> Step3CorrectionRunCommand:
        return Step3CorrectionRunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            step2_artifact_ids=("step2-final",),
            qcms=(
                {"Num": 1, "Text": "Question 1"},
                {"Num": 2, "Text": "Question 2", "Correct": "A"},
                {"Num": 3, "Text": "Question 3"},
            ),
            pages=(
                Step3CorrectionPage(1, "regular page"),
                Step3CorrectionPage(2, "CORRECTION\n1. BC\n2. D\n3. AE"),
                Step3CorrectionPage(3, "extra context"),
            ),
            config=config or Step3CorrectionConfig(selected_pages=(2,)),
        )

    def test_legacy_mode_mapping_and_page_selection(self) -> None:
        self.assertEqual(normalize_correction_mode("page_text"), CorrectionMode.PAGE_DETECTION)
        self.assertEqual(normalize_correction_mode("vision_ai"), CorrectionMode.VISION)
        self.assertEqual(normalize_correction_mode("all_pages"), CorrectionMode.AUTO_DETECTION)
        self.assertEqual(parse_page_selection("1,2,5:7"), (1, 2, 5, 6, 7))
        self.assertEqual(include_neighbor_pages((2,), min_page=1, max_page=3), (1, 2, 3))

    def test_scorer_and_extractor_detect_correction_patterns(self) -> None:
        text = "corrige\n1. ABC\n2. D\n3. AE\n4. B\n5. C"
        signal = score_correction_page(page_number=4, text=text)
        self.assertTrue(signal.suggested)
        self.assertEqual(extract_correction_map_from_text(text)["1"], "ABC")

    def test_page_detection_applies_selected_pages_and_preserves_existing_by_default(self) -> None:
        sink = InMemoryStep3ArtifactSink()
        result = Step3CorrectionService(artifact_sink=sink).run(self.command())
        self.assertEqual(result.mode, "page_detection")
        self.assertEqual(result.processed_pages, (1, 2, 3))
        self.assertEqual(result.corrected_qcms[0]["Correct"], "BC")
        self.assertEqual(result.corrected_qcms[1]["Correct"], "A")
        self.assertEqual(result.quality.status, QualityStatus.PASSED)
        artifact_types = [record.request.artifact_type for record in sink.records]
        self.assertIn(ArtifactType.STEP3_CORRECTION_JSON, artifact_types)
        self.assertIn(ArtifactType.STEP3_CORRECTION_XLSX, artifact_types)
        self.assertTrue(all(record.request.source_artifact_ids == ["step2-final"] for record in sink.records))

    def test_force_overwrite_and_auto_detection_scan_all_pages(self) -> None:
        result = Step3CorrectionService().run(
            self.command(Step3CorrectionConfig(mode="auto_detection", force_overwrite=True))
        )
        self.assertEqual(result.processed_pages, (1, 2, 3))
        self.assertEqual(result.corrected_qcms[1]["Correct"], "D")

    def test_vision_mode_uses_structured_detections(self) -> None:
        result = Step3CorrectionService().run(
            self.command(
                Step3CorrectionConfig(
                    mode="vision",
                    vision_guide="highlighted answers",
                    vision_detections={"1": "a c", "3": "B"},
                )
            )
        )
        self.assertEqual(result.correction_map, {"1": "AC", "3": "B"})
        self.assertEqual(result.quality.status, QualityStatus.MANUAL_REVIEW_REQUIRED)

    def test_worker_handler_maps_manual_review_to_completed_with_warnings(self) -> None:
        result = step3_correction_handler(
            {
                "user_id": "u",
                "project_id": "p",
                "run_id": "r",
                "step2_artifact_ids": ["step2-final"],
                "qcms": [{"Num": 1, "Text": "Question"}],
                "pages": [{"page_number": 1, "text": "no corrections"}],
                "config": {"mode": "page_detection"},
            }
        )
        self.assertEqual(result["status"], TaskStatus.COMPLETED_WITH_WARNINGS.value)


if __name__ == "__main__":
    unittest.main()
