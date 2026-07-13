"""Verify Plan 08 combined Step 2 orchestration without live provider dependencies."""

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

from qcm_application.steps.step2_orchestrator import InMemoryStep2ArtifactSink, Step2Orchestrator
from qcm_domain.enums import InternalCycleKey
from qcm_domain.steps.step2_contracts import COMBINED_STEP2_CYCLE_ORDER, cycles_from
from qcm_shared.contracts import ArtifactType, QualityStatus
from qcm_shared.step2_contracts import STEP2_TASK_KIND, Step2Config, Step2RunCommand, Step2SourcePage
from qcm_worker.handlers import TASK_HANDLERS
from qcm_worker.step2_orchestrator_handler import register_step2_orchestrator_handler


def main() -> int:
    assert cycles_from(InternalCycleKey.STEP2_METADATA) == (
        InternalCycleKey.STEP2_METADATA,
        InternalCycleKey.STEP2_FORMAT,
        InternalCycleKey.STEP2_FINALIZE,
    )
    assert len(COMBINED_STEP2_CYCLE_ORDER) == 4

    sink = InMemoryStep2ArtifactSink()
    result = Step2Orchestrator(artifact_sink=sink).run(
        Step2RunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            step1_artifact_ids=("step1-text",),
            pages=(
                Step2SourcePage(1, "1. Question one\nA. Alpha\nB. Beta\nC. Gamma\nD. Delta"),
                Step2SourcePage(2, "2. Question two\nA. Alpha\nB. Beta\nC. Gamma\nD. Delta"),
            ),
            config=Step2Config(metadata_defaults={"year": "2024", "source": "Alger"}),
        )
    )
    assert result.quality.status == QualityStatus.PASSED
    assert result.quality.total_qcms == 2
    assert result.final_json_artifact_id is not None
    assert result.final_xlsx_artifact_id is not None
    artifact_types = [record.request.artifact_type for record in sink.records]
    assert artifact_types.count(ArtifactType.STEP2_PAGE_QCM_JSON) == 2
    assert ArtifactType.STEP2_FINAL_JSON in artifact_types
    assert ArtifactType.STEP2_FINAL_XLSX in artifact_types

    TASK_HANDLERS.clear()
    register_step2_orchestrator_handler()
    assert STEP2_TASK_KIND in TASK_HANDLERS
    print("Plan 08 combined Step 2 orchestrator, cycles, artifacts, resume hooks, and worker registration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
