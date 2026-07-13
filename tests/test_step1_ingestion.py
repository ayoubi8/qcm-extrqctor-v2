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

from qcm_application.steps.step1_service import InMemoryStep1ArtifactSink, Step1Service
from qcm_domain.artifacts import MAX_SOURCE_FILE_BYTES
from qcm_domain.documents import (
    DIRECT_TEXT_THRESHOLD,
    ExtractionMode,
    PageExtractionMethod,
    classify_page_text,
    resolve_extraction_plan,
)
from qcm_infrastructure.pdf import FakeOcrEngine, FakePdfTextExtractor, ReplacementTextQualityFixer
from qcm_shared.contracts import ArtifactType, QualityStatus, TaskStatus
from qcm_shared.step1_contracts import Step1Config, Step1RunCommand
from qcm_worker.step1_handler import step1_handler


class Step1IngestionTest(unittest.TestCase):
    def command(self, config: Step1Config | None = None) -> Step1RunCommand:
        return Step1RunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            source_file_id="source-artifact",
            source_filename="source.pdf",
            source_content=b"%PDF fixture",
            config=config or Step1Config(),
        )

    def test_meaningful_character_threshold_routes_pages(self) -> None:
        weak = classify_page_text(1, "   ... \n")
        strong = classify_page_text(2, "A" * (DIRECT_TEXT_THRESHOLD + 1))
        report = resolve_extraction_plan((weak, strong), ExtractionMode.AUTOMATIC)
        methods = [decision.method for decision in report.page_decisions]
        self.assertEqual(report.resolved_mode, ExtractionMode.MIXED)
        self.assertEqual(methods, [PageExtractionMethod.OCR, PageExtractionMethod.DIRECT])

    def test_manual_override_requires_reason(self) -> None:
        signal = classify_page_text(1, "A" * (DIRECT_TEXT_THRESHOLD + 1))
        with self.assertRaises(ValueError):
            resolve_extraction_plan((signal,), ExtractionMode.OCR)

    def test_step1_mixed_pdf_writes_page_final_and_report_artifacts(self) -> None:
        sink = InMemoryStep1ArtifactSink()
        ocr = FakeOcrEngine({1: "Corrected OCR page one"})
        service = Step1Service(
            extractor=FakePdfTextExtractor({1: "", 2: "Direct page " + ("A" * 220)}),
            ocr=ocr,
            text_fixer=ReplacementTextQualityFixer({"0": "O"}),
            artifact_sink=sink,
        )
        result = service.run(self.command())
        self.assertEqual(result.detection.resolved_mode, "mixed")
        self.assertEqual([page.extraction_method for page in result.pages], ["ocr", "direct"])
        self.assertEqual(ocr.calls, [1])
        self.assertEqual(result.quality.status, QualityStatus.PASSED_WITH_WARNINGS)
        self.assertEqual(len(sink.records), 5)
        artifact_types = [record.request.artifact_type for record in sink.records]
        self.assertEqual(artifact_types.count(ArtifactType.PAGE_TEXT), 2)
        self.assertIn(ArtifactType.STEP1_TEXT, artifact_types)
        self.assertTrue(all(record.request.source_artifact_ids == ["source-artifact"] for record in sink.records))

    def test_direct_override_uses_direct_text_for_all_pages(self) -> None:
        sink = InMemoryStep1ArtifactSink()
        ocr = FakeOcrEngine({1: "should not be used"})
        service = Step1Service(
            extractor=FakePdfTextExtractor({1: "", 2: "Direct page " + ("A" * 220)}),
            ocr=ocr,
            text_fixer=ReplacementTextQualityFixer({}),
            artifact_sink=sink,
        )
        result = service.run(
            self.command(Step1Config(extraction_mode="direct", override_reason="User inspected PDF text layer"))
        )
        self.assertEqual(result.detection.resolved_mode, "direct")
        self.assertEqual(ocr.calls, [])
        self.assertTrue(result.quality.warnings)

    def test_source_file_size_cap_is_enforced_before_extraction(self) -> None:
        service = Step1Service(
            extractor=FakePdfTextExtractor(["unused"]),
            ocr=FakeOcrEngine(),
            text_fixer=ReplacementTextQualityFixer({}),
        )
        oversized = Step1RunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            source_file_id="source",
            source_filename="source.pdf",
            source_content=b"x" * (MAX_SOURCE_FILE_BYTES + 1),
        )
        with self.assertRaises(ValueError):
            service.run(oversized)

    def test_worker_handler_returns_completed_with_warnings_for_mixed_pdf(self) -> None:
        result = step1_handler(
            {
                "user_id": "u",
                "project_id": "p",
                "run_id": "r",
                "source_file_id": "source",
                "source_content": "%PDF",
                "direct_pages": {1: "", 2: "A" * 220},
                "ocr_pages": {1: "OCR recovered text"},
                "config": {"extraction_mode": "automatic"},
            }
        )
        self.assertEqual(result["status"], TaskStatus.COMPLETED_WITH_WARNINGS.value)
        self.assertEqual(result["result"]["resolved_mode"], "mixed")


if __name__ == "__main__":
    unittest.main()
