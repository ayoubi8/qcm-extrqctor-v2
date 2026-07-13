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

from qcm_application.steps.step2_finalize import Step2FinalizeService
from qcm_application.steps.step2_format import Step2FormatService
from qcm_application.steps.step2_metadata import Step2MetadataService
from qcm_domain.templates import default_qcm_template, validate_qcm_template
from qcm_shared.step2_contracts import Step2Config, Step2RunCommand, Step2SourcePage


class Step2MetadataFormatFinalizeTest(unittest.TestCase):
    def command(self, config: Step2Config | None = None) -> Step2RunCommand:
        return Step2RunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            step1_artifact_ids=("step1-text",),
            pages=(
                Step2SourcePage(
                    1,
                    "CAS CLINIQUE 1: Patient de 45 ans avec fievre.\n1. Question one\nA. Alpha\nB. Beta\nC. Gamma",
                ),
                Step2SourcePage(2, "2. Question two\nA. One\nB. Two\nC. Three"),
            ),
            config=config
            or Step2Config(
                metadata_defaults={
                    "year": "2024",
                    "source": "Alger",
                    "category": "Infectieux",
                    "subcategory": "Paludisme",
                }
            ),
        )

    def qcms(self):
        return [
            {"uid": "1_1_0", "page": 1, "number": 1, "text": "Question one", "propositions": {"A": "Alpha"}},
            {"uid": "2_2_0", "page": 2, "number": 2, "text": "Question two", "propositions": {"A": "One"}},
        ]

    def test_metadata_defaults_provenance_and_multi_page_clinical_case(self) -> None:
        result = Step2MetadataService().run(self.command(), self.qcms())
        self.assertEqual(len(result.clinical_groups), 1)
        self.assertEqual(result.clinical_groups[0].page_numbers, (1, 2))
        self.assertIn("CAS CLINIQUE 1", result.qcms[1]["cas"])
        self.assertEqual(result.qcms[0]["year"], "2024")
        self.assertEqual(result.qcms[0]["legacy_subcategory"], "Paludisme")
        self.assertNotIn("subcategory", result.qcms[0])
        self.assertTrue(any(item.field_name == "year" for item in result.provenance))

    def test_legacy_subcategory_export_policy_keeps_export_field(self) -> None:
        command = self.command(
            Step2Config(metadata_defaults={"subcategory": "Cardio"}, legacy_subcategory_policy="export")
        )
        result = Step2MetadataService().run(command, [self.qcms()[0]])
        self.assertEqual(result.qcms[0]["subcategory"], "Cardio")
        self.assertEqual(result.qcms[0]["legacy_subcategory"], "Cardio")

    def test_template_validation_rejects_missing_required_fields(self) -> None:
        template = default_qcm_template()
        template.pop("Text")
        report = validate_qcm_template(template)
        self.assertFalse(report.valid)
        with self.assertRaises(ValueError):
            Step2FormatService().run(
                self.command(Step2Config(template_overrides={"Text": None})),
                [{"uid": "1_1_0", "page": 1, "number": 1, "text": "Question"}],
            )

    def test_format_and_finalize_build_final_json_and_xlsx_payloads(self) -> None:
        metadata = Step2MetadataService().run(self.command(), self.qcms())
        formatted = Step2FormatService().run(self.command(), list(metadata.qcms))
        self.assertTrue(formatted.validation.valid)
        self.assertEqual(formatted.formatted_qcms[0]["Year"], "2024")
        self.assertIn("CAS CLINIQUE 1", formatted.formatted_qcms[0]["Cas"])
        final = Step2FinalizeService().run(self.command(), list(formatted.formatted_qcms))
        self.assertIn(b'"Year":"2024"', final.final_json_content)
        self.assertIsNotNone(final.final_xlsx_content)
        self.assertIn(b"CAS CLINIQUE", final.final_xlsx_content)


if __name__ == "__main__":
    unittest.main()
