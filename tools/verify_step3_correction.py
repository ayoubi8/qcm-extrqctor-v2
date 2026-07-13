"""Verify Plan 11 future Step 3 correction processing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/shared/src",
    "packages/application/src",
    "apps/worker/src",
]:
    sys.path.insert(0, str(ROOT / relative))

from qcm_application.steps.step3_correction_service import InMemoryStep3ArtifactSink, Step3CorrectionService
from qcm_domain.corrections import CorrectionMode, normalize_correction_mode, score_correction_page
from qcm_shared.contracts import ArtifactType, QualityStatus
from qcm_shared.step3_contracts import STEP3_TASK_KIND, Step3CorrectionConfig, Step3CorrectionPage, Step3CorrectionRunCommand
from qcm_worker.handlers import TASK_HANDLERS
from qcm_worker.step3_correction_handler import register_step3_correction_handler


def main() -> int:
    assert normalize_correction_mode("page_text") == CorrectionMode.PAGE_DETECTION
    assert normalize_correction_mode("vision_ai") == CorrectionMode.VISION
    assert normalize_correction_mode("auto_detect") == CorrectionMode.AUTO_DETECTION
    assert score_correction_page(page_number=2, text="correction\n1. A\n2. B\n3. C\n4. D\n5. E").suggested

    sink = InMemoryStep3ArtifactSink()
    result = Step3CorrectionService(artifact_sink=sink).run(
        Step3CorrectionRunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            step2_artifact_ids=("step2-final",),
            qcms=({"Num": 1, "Text": "Q1"}, {"Num": 2, "Text": "Q2"}),
            pages=(Step3CorrectionPage(1, "CORRECTION\n1. AC\n2. B"),),
            config=Step3CorrectionConfig(mode="page_detection", selected_pages=(1,)),
        )
    )
    assert result.quality.status == QualityStatus.PASSED
    assert result.correction_map == {"1": "AC", "2": "B"}
    artifact_types = [record.request.artifact_type for record in sink.records]
    assert ArtifactType.STEP3_CORRECTION_JSON in artifact_types
    assert ArtifactType.STEP3_CORRECTION_XLSX in artifact_types

    TASK_HANDLERS.clear()
    register_step3_correction_handler()
    assert STEP3_TASK_KIND in TASK_HANDLERS
    print("Plan 11 Step 3 correction modes, suggestions, artifacts, quality, and worker registration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
