"""Worker process entry point for durable task execution.

Registers all task handlers and runs a claim/dispatch/complete loop against the same
Supabase task queue as the API (service-role). Falls back to in-memory repositories
when Supabase env is absent so the readiness check stays importable for verification.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYTHONPATHS = [
    ROOT / "packages" / "domain" / "src",
    ROOT / "packages" / "shared" / "src",
    ROOT / "packages" / "application" / "src",
    ROOT / "packages" / "infrastructure" / "src",
    ROOT / "packages" / "observability" / "src",
    ROOT / "apps" / "worker" / "src",
]
for path in reversed(PYTHONPATHS):
    sys.path.insert(0, str(path))

from qcm_application.task_service import TaskService  # noqa: E402
from qcm_infrastructure.tasks.memory import InMemoryTaskRepository  # noqa: E402
from qcm_infrastructure.tasks.memory import InMemoryTerminalRepository  # noqa: E402
from qcm_shared.config.defaults import TaskRuntimeDefaults  # noqa: E402
from qcm_worker.handlers import TASK_HANDLERS  # noqa: E402
from qcm_worker.health import worker_readiness  # noqa: E402
from qcm_worker.runner import WorkerRunner  # noqa: E402


def register_all_handlers() -> None:
    from qcm_worker.step1_handler import register_step1_handler
    from qcm_worker.step2_orchestrator_handler import register_step2_orchestrator_handler
    from qcm_worker.step3_correction_handler import register_step3_correction_handler
    from qcm_worker.step4_similarity_handler import register_step4_similarity_handler
    from qcm_worker.autorun_handler import register_manual_autorun_handler
    from qcm_worker.ai_autorun_handler import register_ai_autorun_handler

    register_step1_handler()
    register_step2_orchestrator_handler()
    register_step3_correction_handler()
    register_step4_similarity_handler()
    register_manual_autorun_handler()
    register_ai_autorun_handler()


def build_worker_task_service() -> TaskService:
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        from qcm_infrastructure.db.postgrest import PostgrestClient
        from qcm_infrastructure.db.repositories import SupabaseTaskRepository, SupabaseTerminalRepository

        client = PostgrestClient(
            base_url=os.getenv("SUPABASE_URL", ""),
            api_key=os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "",
            service_role=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        )
        return TaskService(SupabaseTaskRepository(client), SupabaseTerminalRepository(client))
    return TaskService(InMemoryTaskRepository(), InMemoryTerminalRepository())


def run_once(worker_id: str | None = None) -> bool:
    worker_id = worker_id or os.getenv("QCM_WORKER_ID", "local-worker-1")
    register_all_handlers()
    runner = WorkerRunner(worker_id=worker_id, task_service=build_worker_task_service())
    return runner.run_once()


def run_forever(worker_id: str | None = None) -> None:
    worker_id = worker_id or os.getenv("QCM_WORKER_ID", "local-worker-1")
    register_all_handlers()
    defaults = TaskRuntimeDefaults()
    runner = WorkerRunner(worker_id=worker_id, task_service=build_worker_task_service())
    print(f"qcm-worker {worker_id} ready with {len(TASK_HANDLERS)} handlers", flush=True)
    while True:
        try:
            processed = runner.run_once()
            if not processed:
                time.sleep(defaults.worker_poll_seconds)
        except KeyboardInterrupt:
            print("qcm-worker stopping", flush=True)
            break
        except Exception as exc:  # pragma: no cover - resilience guard
            print(f"qcm-worker loop error: {exc}", flush=True)
            time.sleep(defaults.worker_poll_seconds)


def main() -> int:
    readiness = worker_readiness()
    print(f"qcm-worker {readiness.status}; registered handlers={len(TASK_HANDLERS)}")
    return 0


if __name__ == "__main__":
    run_forever()