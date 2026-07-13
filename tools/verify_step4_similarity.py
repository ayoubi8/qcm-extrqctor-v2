"""Verify Plan 12 future Step 4 similarity match compatibility."""

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

from qcm_application.ownership import AuthorizationError
from qcm_application.reference_db_service import ReferenceDbService
from qcm_application.steps.step4_similarity_service import InMemoryStep4ArtifactSink, Step4SimilarityService
from qcm_domain.reference_db import DEFAULT_MATCH_THRESHOLD, SimilarityMatchMode, normalize_match_mode, similarity_band
from qcm_shared.contracts import ArtifactType, QualityStatus
from qcm_shared.step4_contracts import STEP4_TASK_KIND, ReferenceDbCreateCommand, Step4SimilarityConfig, Step4SimilarityRunCommand
from qcm_worker.handlers import TASK_HANDLERS
from qcm_worker.step4_similarity_handler import register_step4_similarity_handler


def main() -> int:
    assert DEFAULT_MATCH_THRESHOLD == 0.75
    assert normalize_match_mode("text_only") == SimilarityMatchMode.TEXT_ONLY
    assert normalize_match_mode("full") == SimilarityMatchMode.FULL
    assert similarity_band(0.91) == "green"

    ref_service = ReferenceDbService()
    ref_service.create(
        ReferenceDbCreateCommand(
            user_id="u",
            reference_db_id="ref-db",
            name="Private refs",
            qcms=({"Num": 1, "Text": "renal colic", "A": "stone", "Correct": "A"},),
            idempotency_key="create-ref",
        )
    )
    try:
        ref_service.get_qcms(user_id="other", reference_db_id="ref-db")
    except AuthorizationError:
        pass
    else:
        raise AssertionError("cross-user reference DB access did not fail")

    sink = InMemoryStep4ArtifactSink()
    result = Step4SimilarityService(artifact_sink=sink).run(
        Step4SimilarityRunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            source_artifact_ids=("step2-final",),
            source_qcms=({"Num": 1, "Text": "renal colic", "A": "stone", "Correct": "A"},),
            reference_qcms=ref_service.get_qcms(user_id="u", reference_db_id="ref-db"),
            config=Step4SimilarityConfig(reference_db_id="ref-db"),
        )
    )
    assert result.quality.status == QualityStatus.PASSED
    assert result.summary.matched_qcms == 1
    artifact_types = [record.request.artifact_type for record in sink.records]
    assert ArtifactType.STEP4_SIMILARITY_JSON in artifact_types
    assert ArtifactType.STEP4_SIMILARITY_XLSX in artifact_types

    TASK_HANDLERS.clear()
    register_step4_similarity_handler()
    assert STEP4_TASK_KIND in TASK_HANDLERS
    print("Plan 12 Step 4 similarity defaults, reference DB ownership, artifacts, and worker registration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
