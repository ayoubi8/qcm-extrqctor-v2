import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/shared/src",
    "packages/application/src",
]:
    sys.path.insert(0, str(ROOT / relative))

from qcm_application.steps.step2_pages import RuleBasedPageQcmExtractor, Step2PageCycleService
from qcm_domain.qcm import stable_qcm_uid
from qcm_shared.step2_contracts import Step2Config, Step2RunCommand, Step2SourcePage


class Step2PagesTest(unittest.TestCase):
    def command(self, pages: tuple[Step2SourcePage, ...]) -> Step2RunCommand:
        return Step2RunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            step1_artifact_ids=("step1-text",),
            pages=pages,
            config=Step2Config(metadata_defaults={"year": "2024"}),
        )

    def test_page_inputs_freeze_previous_current_next_context(self) -> None:
        service = Step2PageCycleService()
        inputs = service.build_page_inputs(
            self.command(
                (
                    Step2SourcePage(1, "1. First\nA. a\nB. b\nC. c"),
                    Step2SourcePage(2, "2. Second\nA. a\nB. b\nC. c"),
                    Step2SourcePage(3, "3. Third\nA. a\nB. b\nC. c"),
                )
            )
        )
        self.assertIsNone(inputs[0].previous_page_text)
        self.assertIn("First", inputs[1].previous_page_text)
        self.assertIn("Third", inputs[1].next_page_text)
        self.assertIsNone(inputs[-1].next_page_text)

    def test_rule_based_extractor_parses_numbered_qcm_and_propositions(self) -> None:
        service = Step2PageCycleService(RuleBasedPageQcmExtractor())
        result = service.run(
            self.command((Step2SourcePage(4, "10. Stem text\nA. Alpha\nB. Beta\nC. Gamma\nD. Delta"),))
        )
        self.assertEqual(result.qcms[0]["uid"], stable_qcm_uid(4, 10, 0))
        self.assertEqual(result.qcms[0]["propositions"]["A"], "Alpha")
        self.assertEqual(result.page_outputs[0].quality_metrics.incomplete_qcm_count, 0)

    def test_split_qcm_is_reconstructed_from_next_page_orphan_propositions(self) -> None:
        service = Step2PageCycleService()
        result = service.run(
            self.command(
                (
                    Step2SourcePage(1, "1. Split stem\nA. Alpha"),
                    Step2SourcePage(2, "B. Beta\nC. Gamma\nD. Delta\n2. Next stem\nA. One\nB. Two\nC. Three"),
                )
            )
        )
        first = next(qcm for qcm in result.qcms if qcm["number"] == 1)
        self.assertEqual(first["propositions"]["D"], "Delta")
        self.assertEqual(result.split_report.merged_count, 1)
        self.assertIn(2, result.split_report.orphan_proposition_pages)

    def test_duplicate_qcms_are_merged_by_page_and_number(self) -> None:
        service = Step2PageCycleService()
        result = service.run(
            self.command(
                (
                    Step2SourcePage(
                        1,
                        "1. Stem\nA. Alpha\nB. Beta\nC. Gamma\n1. Stem with longer wording\nD. Delta\nE. Epsilon",
                    ),
                )
            )
        )
        self.assertEqual(len(result.qcms), 1)
        self.assertEqual(result.split_report.duplicate_count, 1)
        self.assertEqual(result.qcms[0]["propositions"]["E"], "Epsilon")


if __name__ == "__main__":
    unittest.main()
