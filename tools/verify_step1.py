"""Verify Plan 07 Step 1 extraction contracts without live PDF/OCR/provider dependencies."""

from __future__ import annotations

import sys
from pathlib import Path

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
from qcm_domain.documents import DIRECT_TEXT_THRESHOLD, ExtractionMode, classify_page_text, resolve_extraction_plan
from qcm_infrastructure.pdf import FakeOcrEngine, FakePdfTextExtractor, IdentityTextQualityFixer
from qcm_shared.contracts import ArtifactType, QualityStatus
from qcm_shared.step1_contracts import STEP1_TASK_KIND, Step1RunCommand
from qcm_worker.step1_handler import register_step1_handler
from qcm_worker.handlers import TASK_HANDLERS


def main() -> int:
    weak = classify_page_text(1, "   ...")
    strong = classify_page_text(2, "A" * (DIRECT_TEXT_THRESHOLD + 1))
    report = resolve_extraction_plan((weak, strong), ExtractionMode.AUTOMATIC)
    assert report.resolved_mode == ExtractionMode.MIXED

    sink = InMemoryStep1ArtifactSink()
    ocr = FakeOcrEngine({1: "OCR recovered text"})
    service = Step1Service(
        extractor=FakePdfTextExtractor({1: "", 2: "Direct text " + ("A" * 220)}),
        ocr=ocr,
        text_fixer=IdentityTextQualityFixer(),
        artifact_sink=sink,
    )
    result = service.run(
        Step1RunCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            source_file_id="source",
            source_filename="fixture.pdf",
            source_content=b"%PDF fixture",
        )
    )
    assert result.detection.resolved_mode == "mixed"
    assert result.quality.status == QualityStatus.PASSED_WITH_WARNINGS
    assert ocr.calls == [1]
    assert len(sink.records) == 5
    assert any(record.request.artifact_type == ArtifactType.STEP1_TEXT for record in sink.records)

    TASK_HANDLERS.clear()
    register_step1_handler()
    assert STEP1_TASK_KIND in TASK_HANDLERS
    print("Plan 07 Step 1 ingestion, extraction, OCR routing, artifacts, and quality verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
