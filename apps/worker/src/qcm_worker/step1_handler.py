"""Worker handler for Step 1 extraction tasks."""

import os
from typing import Any

from qcm_application.steps.step1_service import InMemoryStep1ArtifactSink, Step1Service
from qcm_shared.contracts import QualityStatus, TaskStatus
from qcm_shared.step1_contracts import STEP1_TASK_KIND, Step1Config, Step1RunCommand
from qcm_worker.handlers import TASK_HANDLERS, register_handler

try:
    from qcm_infrastructure.pdf import FakeOcrEngine, FakePdfTextExtractor, IdentityTextQualityFixer
    from qcm_infrastructure.pdf.pypdf_extractor import PypdfTextExtractor
    from qcm_infrastructure.pdf.openrouter_text_fixer import OpenRouterTextFixer
    from qcm_infrastructure.pdf.openrouter_vision_ocr import OpenRouterVisionOcr
    from qcm_infrastructure.storage.rest_adapter import SupabaseStorageRestAdapter
    from qcm_infrastructure.db.postgrest import PostgrestClient
    from qcm_infrastructure.llm.openrouter_adapter import build_openrouter_adapter_from_env
    _REAL_DEPS = True
except ImportError:  # pragma: no cover
    _REAL_DEPS = False


def _build_real_adapters():
    """Build real PDF extractor, OCR, text fixer, and storage downloader from env."""
    extractor = PypdfTextExtractor()
    adapter = build_openrouter_adapter_from_env()
    ocr = OpenRouterVisionOcr(adapter, model_id="openai/gpt-4o-mini") if adapter else FakeOcrEngine()
    text_fixer = OpenRouterTextFixer(adapter) if adapter else IdentityTextQualityFixer()
    storage = None
    source_file_repo = None
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        sup_url = os.getenv("SUPABASE_URL", "")
        sup_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        anon = os.getenv("SUPABASE_ANON_KEY") or sup_key
        storage = SupabaseStorageRestAdapter(sup_url, anon, service_role=sup_key)
        source_file_repo = PostgrestClient(sup_url, anon, service_role=sup_key)
    return extractor, ocr, text_fixer, storage, source_file_repo


def build_step1_service(
    payload: dict[str, Any],
    artifact_sink: InMemoryStep1ArtifactSink | None = None,
) -> Step1Service:
    direct_pages = payload.get("direct_pages") or payload.get("pages") or []
    has_inline_pages = bool(direct_pages)
    ocr_pages = payload.get("ocr_pages") or {}

    if isinstance(direct_pages, dict):
        direct_pages = {int(page): text for page, text in direct_pages.items()}
    if isinstance(ocr_pages, dict):
        ocr_pages = {int(page): text for page, text in ocr_pages.items()}

    if has_inline_pages:
        # Test/contract mode: use fake adapters with inline page data
        extractor = FakePdfTextExtractor(direct_pages)
        ocr = FakeOcrEngine(ocr_pages)
        text_fixer = IdentityTextQualityFixer()
    elif _REAL_DEPS:
        # Production mode: use real adapters
        extractor, ocr, text_fixer, _storage, _sf_repo = _build_real_adapters()
    else:
        # Fallback: no inline pages and no real deps → empty extraction
        extractor = FakePdfTextExtractor({})
        ocr = FakeOcrEngine({})
        text_fixer = IdentityTextQualityFixer()

    return Step1Service(
        extractor=extractor,
        ocr=ocr,
        text_fixer=text_fixer,
        artifact_sink=artifact_sink or InMemoryStep1ArtifactSink(),
    )


def _fetch_source_pdf(payload: dict[str, Any]) -> bytes:
    """Download the source PDF from Supabase Storage via source_file_id."""
    source_file_id = payload.get("source_file_id", "")
    if not source_file_id or not _REAL_DEPS:
        return b""

    storage_url = os.getenv("SUPABASE_URL", "")
    sr = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    anon = os.getenv("SUPABASE_ANON_KEY") or sr
    if not storage_url or not sr:
        return b""

    client = PostgrestClient(storage_url, anon, service_role=sr)
    row = client.select_one("source_files", columns="storage_key", params={"source_file_id": f"eq.{source_file_id}"})
    if not row or not row.get("storage_key"):
        return b""

    storage = SupabaseStorageRestAdapter(storage_url, anon, service_role=sr)
    return storage.get_object(row["storage_key"])


def step1_handler(payload: dict[str, Any]) -> dict[str, Any]:
    config_payload = payload.get("config") or {}
    source = payload.get("source_content", b"")

    # If no inline source_content, try fetching from Storage
    if not source and not (payload.get("direct_pages") or payload.get("pages")):
        source = _fetch_source_pdf(payload)

    if isinstance(source, str):
        source = source.encode("utf-8")

    command = Step1RunCommand(
        user_id=payload.get("user_id", ""),
        project_id=payload.get("project_id", ""),
        run_id=payload.get("run_id", ""),
        source_file_id=payload.get("source_file_id", "source-pdf"),
        source_filename=payload.get("source_filename", "source.pdf"),
        source_content=source,
        config=Step1Config(
            extraction_mode=config_payload.get("extraction_mode", "automatic"),
            override_reason=config_payload.get("override_reason"),
            page_range_start=config_payload.get("page_range_start"),
            page_range_end=config_payload.get("page_range_end"),
            text_fixer_enabled=bool(config_payload.get("text_fixer_enabled", True)),
            text_fixer_model=config_payload.get("text_fixer_model"),
        ),
        task_id=payload.get("task_id"),
        attempt_id=payload.get("attempt_id"),
        correlation_id=payload.get("correlation_id"),
    )
    sink = InMemoryStep1ArtifactSink()
    result = build_step1_service(payload, sink).run(command)
    task_status = (
        TaskStatus.COMPLETED_WITH_WARNINGS.value
        if result.quality.status in {QualityStatus.PASSED_WITH_WARNINGS, QualityStatus.MANUAL_REVIEW_REQUIRED}
        else TaskStatus.COMPLETED.value
    )
    return {
        "status": task_status,
        "message": "Step 1 extraction completed",
        "result": {
            "resolved_mode": result.detection.resolved_mode,
            "quality_status": result.quality.status.value,
            "artifact_count": len(result.artifact_ids),
        },
    }


def register_step1_handler() -> None:
    if STEP1_TASK_KIND not in TASK_HANDLERS:
        register_handler(STEP1_TASK_KIND, step1_handler)