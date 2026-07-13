"""Dependency-light verification for Plan 06 durable task and terminal boundaries."""

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
    "apps/api/src",
]:
    sys.path.insert(0, str(ROOT / relative))

REQUIRED_PATHS = [
    "packages/domain/src/qcm_domain/tasks.py",
    "packages/shared/src/qcm_shared/task_contracts.py",
    "packages/application/src/qcm_application/task_service.py",
    "packages/infrastructure/src/qcm_infrastructure/tasks/memory.py",
    "apps/worker/src/qcm_worker/runner.py",
    "apps/api/src/qcm_api/routes/tasks.py",
    "apps/api/src/qcm_api/routes/terminal.py",
    "apps/web/src/terminal/api.ts",
    "apps/web/src/terminal/TerminalEventList.tsx",
]


def verify_paths() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Plan 06 paths: {missing}")


def verify_contracts() -> None:
    from qcm_application.task_service import TaskService
    from qcm_infrastructure.tasks import InMemoryTaskRepository, InMemoryTerminalRepository
    from qcm_shared.contracts import TaskStatus
    from qcm_shared.task_contracts import TaskCreateCommand, TaskClaimRequest, TaskFailureCommand

    tasks = InMemoryTaskRepository()
    terminal = InMemoryTerminalRepository()
    service = TaskService(tasks, terminal)
    task = service.create_task(
        TaskCreateCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            kind="step1_extract",
            idempotency_key="idem",
            correlation_id="corr",
        )
    )
    duplicate = service.create_task(
        TaskCreateCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            kind="step1_extract",
            idempotency_key="idem",
            correlation_id="corr",
        )
    )
    assert task.task_id == duplicate.task_id
    claim = service.claim_next(TaskClaimRequest(worker_id="worker"))
    assert claim is not None
    failed = service.fail(
        TaskFailureCommand(
            task_id=claim.task.task_id,
            attempt_id=claim.attempt.attempt_id,
            worker_id="worker",
            error_code="provider_failure",
            safe_error_message="Retry later",
            retryable=True,
            correlation_id="corr",
        )
    )
    assert failed.status == TaskStatus.RETRYING
    page = service.terminal_page(user_id="u", project_id="p")
    assert len(page.events) >= 2


def main() -> int:
    verify_paths()
    verify_contracts()
    print("Plan 06 durable tasks and terminal boundaries verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
