"""Verify Plan 16 AI Auto Run contracts, safety gates, worker, prompts, and UI hooks."""

from __future__ import annotations

import json
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

from qcm_application.ai_autorun_service import AiAutoRunService
from qcm_domain.ai_autorun import AiAutoRunGate, AiDocumentMap, AiDocumentMapPage, evaluate_ai_quality
from qcm_shared.ai_autorun_contracts import AI_AUTORUN_TASK_KIND, AiAutoRunPageInput, AiAutoRunStartCommand
from qcm_shared.provider_contracts import ModelAuthorization, ModelSelection, ProviderKey
from qcm_worker.ai_autorun_handler import register_ai_autorun_handler
from qcm_worker.handlers import TASK_HANDLERS


REQUIRED_PATHS = [
    "apps/api/src/qcm_api/routes/ai_autorun.py",
    "apps/worker/src/qcm_worker/ai_autorun_handler.py",
    "apps/web/src/ai_autorun/AiAutoRunWindow.tsx",
    "apps/web/src/ai_autorun/aiAutoRunStore.ts",
    "apps/web/src/ai_autorun/api.ts",
    "packages/application/src/qcm_application/ai_autorun_service.py",
    "packages/domain/src/qcm_domain/ai_autorun.py",
    "packages/shared/src/qcm_shared/ai_autorun_contracts.py",
    "prompts/ai_autorun/planner.v1.md",
    "prompts/ai_autorun/evaluator.v1.md",
]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Plan 16 AI Auto Run paths: {missing}")

    command = AiAutoRunStartCommand(
        user_id="u",
        project_id="p",
        run_id="r",
        ai_run_id="ai",
        pages=(AiAutoRunPageInput(1, "question qcm"), AiAutoRunPageInput(2, "correction answers")),
        model_selection=ModelSelection(ProviderKey.OPENROUTER, "allowed-model"),
        idempotency_key="idem",
        correlation_id="corr",
    )
    result = AiAutoRunService(model_authorization=ModelAuthorization({"allowed-model"})).plan(command)
    assert result.artifact_ids == ("ai-document-map", "ai-generated-config", "ai-evidence")
    assert "reasoning" not in json.dumps(result.evidence_summaries).lower()

    gate, warnings = evaluate_ai_quality(
        document_map=AiDocumentMap((AiDocumentMapPage(1, "context", 0.4, "Page 1 classified as context"),)),
        config_errors=(),
    )
    assert gate == AiAutoRunGate.MANUAL_INTERVENTION
    assert warnings

    TASK_HANDLERS.clear()
    register_ai_autorun_handler()
    assert AI_AUTORUN_TASK_KIND in TASK_HANDLERS

    registry = read("prompts/v1/registry.json")
    assert "ai_autorun.planner.v1" in registry
    assert "ai_autorun.evaluator.v1" in registry
    window = read("apps/web/src/ai_autorun/AiAutoRunWindow.tsx")
    for expected in ["AI Auto Run", "Raw private reasoning is never displayed", "Launch", "Cancel"]:
        assert expected in window

    print("Plan 16 AI Auto Run safety gates, artifacts, worker, prompts, and floating UI verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
