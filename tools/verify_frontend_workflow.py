"""Verify Plan 14 frontend projects, pipeline, history, results, and terminal workflow."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "apps/web/src/api/client.ts",
    "apps/web/src/projects/ProjectLauncher.tsx",
    "apps/web/src/projects/HistoryRestorePanel.tsx",
    "apps/web/src/projects/types.ts",
    "apps/web/src/pipeline/PipelinePage.tsx",
    "apps/web/src/pipeline/StepList.tsx",
    "apps/web/src/pipeline/ConfigPanel.tsx",
    "apps/web/src/pipeline/pipelineStore.ts",
    "apps/web/src/pipeline/stepRegistry.ts",
    "apps/web/src/pipeline/types.ts",
    "apps/web/src/results/ResultHub.tsx",
    "apps/web/src/results/ArtifactViewer.tsx",
    "apps/web/src/results/RunSelector.tsx",
    "apps/web/src/results/types.ts",
    "apps/web/src/terminal/TerminalPanel.tsx",
    "apps/web/src/terminal/useTerminalReplay.ts",
    "tests/visual/plan14_workflow_matrix.json",
]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Plan 14 frontend workflow paths: {missing}")

    client = read("apps/web/src/api/client.ts")
    for expected in ["createProject", "initializeUpload", "fetchProjectSnapshot", "fetchTerminalPage", "fetchSignedUrl", "cancelTask"]:
        assert expected in client

    pipeline = read("apps/web/src/pipeline/PipelinePage.tsx")
    for expected in ["useQuery", "fetchProjectSnapshot", "ProjectLauncher", "HistoryRestorePanel", "ResultHub", "ArtifactViewer", "RunSelector"]:
        assert expected in pipeline

    store = read("apps/web/src/pipeline/pipelineStore.ts")
    assert "activeStepId" in store
    assert "selectedArtifactVersionId" in store
    assert "status" not in store.lower(), "server-owned status must not live in the UI store"

    registry = read("apps/web/src/pipeline/stepRegistry.ts")
    for expected in ["step1_extract", "step2_orchestrate", "step3_correction", "step4_similarity_match"]:
        assert expected in registry

    terminal = read("apps/web/src/terminal/useTerminalReplay.ts")
    assert "useQuery" in terminal
    assert "afterSequence" in terminal
    assert "refetchInterval" in terminal

    app = read("apps/web/src/App.tsx")
    assert "PipelinePage" in app
    assert "TerminalPanel" in app

    manifest = json.loads(read("tests/visual/plan14_workflow_matrix.json"))
    assert manifest["plan"] == 14
    assert "history-restore" in manifest["states"]
    assert "Terminal replay uses cursor polling fallback" in manifest["serverStateRules"]

    print("Plan 14 frontend project restore, pipeline, results, terminal replay, and server-state boundaries verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
