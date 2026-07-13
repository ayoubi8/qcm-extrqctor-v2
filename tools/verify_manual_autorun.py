"""Verify Plan 15 Manual Auto Run contracts, service, worker, and frontend hooks."""

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

from qcm_application.autorun_service import ManualAutoRunService
from qcm_shared.autorun_contracts import (
    MANUAL_AUTORUN_TASK_KIND,
    MANUAL_AUTORUN_SCHEMA_VERSION,
    ManualAutoRunSnapshot,
    ManualAutoRunStepConfig,
)
from qcm_worker.autorun_handler import register_manual_autorun_handler
from qcm_worker.handlers import TASK_HANDLERS


REQUIRED_PATHS = [
    "apps/api/src/qcm_api/routes/autorun.py",
    "apps/worker/src/qcm_worker/autorun_handler.py",
    "apps/web/src/autorun/AutoRunPanel.tsx",
    "apps/web/src/autorun/AutoRunNotification.tsx",
    "apps/web/src/autorun/api.ts",
    "apps/web/src/autorun/autorunStore.ts",
    "apps/web/src/autorun/types.ts",
    "packages/application/src/qcm_application/autorun_service.py",
    "packages/shared/src/qcm_shared/autorun_contracts.py",
]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Plan 15 Manual Auto Run paths: {missing}")

    snapshot = ManualAutoRunSnapshot(
        schema_version=MANUAL_AUTORUN_SCHEMA_VERSION,
        selected_steps=(
            ManualAutoRunStepConfig("step2", "step2_orchestrate", True),
            ManualAutoRunStepConfig("step1", "step1_extract", True),
        ),
    )
    validation = ManualAutoRunService().validate(snapshot.selected_steps)
    assert validation.valid
    assert tuple(step.step_key for step in validation.normalized_steps) == ("step1", "step2")
    assert validation.warnings

    invalid = ManualAutoRunService().validate((ManualAutoRunStepConfig("step3-correction", "legacy_step6", True),))
    assert not invalid.valid

    TASK_HANDLERS.clear()
    register_manual_autorun_handler()
    assert MANUAL_AUTORUN_TASK_KIND in TASK_HANDLERS

    panel = read("apps/web/src/autorun/AutoRunPanel.tsx")
    for expected in ["Manual Auto Run", "Validate", "Start", "Pause", "Retry", "Cancel"]:
        assert expected in panel
    assert "setNotice({ tone: \"success\", message: \"Manual Auto Run started\" })" in panel

    client = read("apps/web/src/api/client.ts")
    for expected in ["validateManualAutoRun", "startManualAutoRun", "controlManualAutoRun"]:
        assert expected in client

    print("Plan 15 Manual Auto Run validation, control, worker registration, and UI hooks verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
