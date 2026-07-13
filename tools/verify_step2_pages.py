"""Verify Plan 09 page-by-page QCM extraction inside combined Step 2."""

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

from qcm_application.steps.step2_pages import Step2PageCycleService
from qcm_domain.qcm import stable_qcm_uid
from qcm_shared.step2_contracts import STEP2_PAGE_PROMPT_ID, Step2Config, Step2RunCommand, Step2SourcePage


def main() -> int:
    command = Step2RunCommand(
        user_id="u",
        project_id="p",
        run_id="r",
        step1_artifact_ids=("step1-text",),
        pages=(
            Step2SourcePage(1, "1. Split stem\nA. Alpha"),
            Step2SourcePage(2, "B. Beta\nC. Gamma\nD. Delta\n2. Complete stem\nA. One\nB. Two\nC. Three"),
        ),
        config=Step2Config(metadata_defaults={"year": "2024"}),
    )
    service = Step2PageCycleService()
    inputs = service.build_page_inputs(command)
    assert inputs[0].previous_page_text is None
    assert inputs[0].next_page_text is not None
    assert inputs[0].prompt_id == STEP2_PAGE_PROMPT_ID

    result = service.run(command)
    first = next(qcm for qcm in result.qcms if qcm["number"] == 1)
    assert first["uid"] == stable_qcm_uid(1, 1, 0)
    assert first["propositions"]["D"] == "Delta"
    assert result.split_report.merged_count == 1
    assert len(result.page_outputs) == 2
    print("Plan 09 Step 2 page QCM extraction, context windows, split repair, and checkpoints verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
