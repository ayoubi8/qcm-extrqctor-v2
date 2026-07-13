"""Verify Plan 10 combined Step 2 metadata, template, and finalization internals."""

from __future__ import annotations

import sys
from pathlib import Path

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
from qcm_shared.step2_contracts import STEP2_METADATA_PROMPT_ID, Step2Config, Step2RunCommand, Step2SourcePage


def main() -> int:
    template_report = validate_qcm_template(default_qcm_template())
    assert template_report.valid

    command = Step2RunCommand(
        user_id="u",
        project_id="p",
        run_id="r",
        step1_artifact_ids=("step1-text",),
        pages=(
            Step2SourcePage(1, "CAS CLINIQUE 1: Patient stable.\n1. Question\nA. Alpha\nB. Beta\nC. Gamma"),
            Step2SourcePage(2, "2. Follow-up question\nA. One\nB. Two\nC. Three"),
        ),
        config=Step2Config(metadata_defaults={"year": "2024", "source": "Alger", "subcategory": "Legacy"}),
    )
    qcms = [
        {"uid": "1_1_0", "page": 1, "number": 1, "text": "Question", "propositions": {"A": "Alpha"}},
        {"uid": "2_2_0", "page": 2, "number": 2, "text": "Follow-up", "propositions": {"A": "One"}},
    ]
    metadata = Step2MetadataService().run(command, qcms)
    assert metadata.clinical_groups
    assert metadata.clinical_groups[0].page_numbers == (1, 2)
    assert any(item.source == STEP2_METADATA_PROMPT_ID for item in metadata.provenance)

    formatted = Step2FormatService().run(command, list(metadata.qcms))
    assert formatted.validation.valid
    assert formatted.formatted_qcms[0]["Year"] == "2024"

    final = Step2FinalizeService().run(command, list(formatted.formatted_qcms))
    assert b'"Year":"2024"' in final.final_json_content
    assert final.final_xlsx_content is not None
    print("Plan 10 Step 2 metadata, Cas Clinique, template validation, and finalization verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
