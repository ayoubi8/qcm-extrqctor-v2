"""Live integration test for the worker loop (Phase D).

Requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY. Creates a step1_extract task
(enum-valid) on the shared queue, runs one WorkerRunner iteration, and asserts the
task moves to a terminal completed status. The throwaway project is cascade-deleted.
"""

import os
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("domain", "shared", "application", "infrastructure", "observability"):
    sys.path.insert(0, str(ROOT / "packages" / sub / "src"))
sys.path.insert(0, str(ROOT / "apps" / "worker" / "src"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
LIVE = bool(SUPABASE_URL and SERVICE_KEY)


@unittest.skipUnless(LIVE, "SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY not set")
class WorkerLoopLiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from qcm_infrastructure.db.postgrest import PostgrestClient
        from qcm_infrastructure.db.repositories import (
            SupabasePipelineRunRepository,
            SupabaseProjectRepository,
            SupabaseTaskRepository,
            SupabaseTerminalRepository,
        )
        from qcm_application.task_service import TaskService
        from qcm_worker.main import build_worker_task_service, register_all_handlers
        from qcm_worker.runner import WorkerRunner

        cls.client = PostgrestClient(SUPABASE_URL, ANON_KEY or SERVICE_KEY, service_role=SERVICE_KEY)
        cls.projects = SupabaseProjectRepository(cls.client)
        cls.runs = SupabasePipelineRunRepository(cls.client)
        cls.tasks_repo = SupabaseTaskRepository(cls.client)
        cls.terminal_repo = SupabaseTerminalRepository(cls.client)
        cls.task_service = TaskService(cls.tasks_repo, cls.terminal_repo)

        register_all_handlers()
        cls.runner = WorkerRunner(worker_id="live-test-worker", task_service=cls.task_service)

        row = cls.client.select_one("profiles", columns="user_id", params={"status": "eq.active"})
        if not row:
            raise unittest.SkipTest("no active profile available for live test")
        cls.user_id = str(row["user_id"])
        cls.test_project_ids: list[str] = []

    def tearDown(self) -> None:
        for project_id in self.test_project_ids:
            try:
                self.client.delete("projects", {"project_id": f"eq.{project_id}"})
            except Exception:
                pass
        self.test_project_ids.clear()

    def test_worker_claims_and_completes_step1_task(self) -> None:
        from qcm_shared.api_contracts import ProjectCreateCommand
        from qcm_shared.task_contracts import TaskCreateCommand

        project = self.projects.create_project(
            ProjectCreateCommand(self.user_id, "Worker live test", "corr", f"worker-{uuid.uuid4()}")
        )
        self.test_project_ids.append(project.project_id)
        run = self.runs.ensure_run(user_id=self.user_id, project_id=project.project_id, triggered_by="manual")

        payload = {
            "user_id": self.user_id,
            "project_id": project.project_id,
            "run_id": run["run_id"],
            "source_file_id": "worker-test-file",
            "source_filename": "source.pdf",
            "pages": {"1": "Sample QCM page text for live worker test."},
            "config": {"extraction_mode": "automatic", "text_fixer_enabled": False},
        }
        task = self.task_service.create_task(
            TaskCreateCommand(
                user_id=self.user_id,
                project_id=project.project_id,
                run_id=run["run_id"],
                kind="step1_extract",
                idempotency_key=f"worker-task-{uuid.uuid4()}",
                correlation_id="worker-live",
                payload=payload,
            )
        )
        self.assertEqual(task.status.value, "queued")

        processed = self.runner.run_once()
        self.assertTrue(processed, "runner should have claimed the queued task")

        finished = self.tasks_repo.get_task(task.task_id)
        self.assertIn(
            finished.status.value,
            {"completed", "completed_with_warnings"},
            f"task should be terminal-completed, got {finished.status.value}",
        )


if __name__ == "__main__":
    unittest.main()