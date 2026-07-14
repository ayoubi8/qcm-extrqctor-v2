"""Live integration tests for the Supabase PostgREST repositories (Phase B).

Runs only when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are in the environment.
Uses an existing active profile as the owner and a throwaway test project that is
deleted (with cascade) at the end, so no permanent data remains.
"""

import os
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("domain", "shared", "application", "infrastructure"):
    sys.path.insert(0, str(ROOT / "packages" / sub / "src"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()

LIVE = bool(SUPABASE_URL and SERVICE_KEY)


@unittest.skipUnless(LIVE, "SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY not set")
class SupabaseRepositoriesLiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from qcm_infrastructure.db.postgrest import PostgrestClient
        from qcm_infrastructure.db.repositories import (
            SupabasePipelineRunRepository,
            SupabaseProjectRepository,
            SupabaseTaskRepository,
            SupabaseTerminalRepository,
        )
        from qcm_shared.api_contracts import ProjectCreateCommand
        from qcm_shared.contracts import Task, TaskStatus
        from qcm_shared.task_contracts import TaskClaimRequest, TerminalEventCreate

        cls.TaskStatus = TaskStatus
        cls.TaskClaimRequest = TaskClaimRequest
        cls.TerminalEventCreate = TerminalEventCreate
        cls.ProjectCreateCommand = ProjectCreateCommand
        cls.Task = Task

        cls.client = PostgrestClient(SUPABASE_URL, ANON_KEY or SERVICE_KEY, service_role=SERVICE_KEY)
        cls.projects = SupabaseProjectRepository(cls.client)
        cls.runs = SupabasePipelineRunRepository(cls.client)
        cls.tasks = SupabaseTaskRepository(cls.client)
        cls.terminal = SupabaseTerminalRepository(cls.client)

        # Borrow an existing active profile as the test owner (FK requires a real user_id).
        row = cls.client.select_one("profiles", columns="user_id", params={"status": "eq.active"})
        if not row:
            raise unittest.SkipTest("no active profile available for live test")
        cls.user_id = str(row["user_id"])
        cls.test_project_ids: list[str] = []

    def _cleanup_project(self, project_id: str) -> None:
        try:
            self.client.delete("projects", {"project_id": f"eq.{project_id}"})
        except Exception:
            pass

    def tearDown(self) -> None:
        for project_id in self.test_project_ids:
            self._cleanup_project(project_id)
        self.test_project_ids.clear()

    def test_project_create_get_list(self) -> None:
        idem = f"live-test-{uuid.uuid4()}"
        command = self.ProjectCreateCommand(
            user_id=self.user_id, name="Live B test project", correlation_id="corr", idempotency_key=idem
        )
        project = self.projects.create_project(command)
        self.test_project_ids.append(project.project_id)
        self.assertEqual(project.user_id, self.user_id)
        self.assertEqual(project.name, "Live B test project")

        # projects has no idempotency_key column; a repeat create yields a new project.
        again = self.projects.create_project(command)
        self.test_project_ids.append(again.project_id)
        self.assertNotEqual(again.project_id, project.project_id)

        fetched = self.projects.get_project(user_id=self.user_id, project_id=project.project_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.project_id, project.project_id)

        listed = self.projects.list_projects(user_id=self.user_id)
        self.assertTrue(any(p.project_id == project.project_id for p in listed))

    def test_run_ensure_and_list(self) -> None:
        project = self.projects.create_project(
            self.ProjectCreateCommand(self.user_id, "Live B runs", "corr", f"live-runs-{uuid.uuid4()}")
        )
        self.test_project_ids.append(project.project_id)
        run = self.runs.ensure_run(user_id=self.user_id, project_id=project.project_id)
        self.assertEqual(run["user_id"], self.user_id)
        # idempotent upsert by run_id
        same = self.runs.ensure_run(user_id=self.user_id, project_id=project.project_id, run_id=run["run_id"])
        self.assertEqual(same["run_id"], run["run_id"])
        runs = self.runs.list_runs(user_id=self.user_id, project_id=project.project_id)
        self.assertTrue(any(r["run_id"] == run["run_id"] for r in runs))

    def test_task_create_list_claim_terminal(self) -> None:
        project = self.projects.create_project(
            self.ProjectCreateCommand(self.user_id, "Live B tasks", "corr", f"live-tasks-{uuid.uuid4()}")
        )
        self.test_project_ids.append(project.project_id)
        run = self.runs.ensure_run(user_id=self.user_id, project_id=project.project_id, triggered_by="manual")

        task = self.Task(
            task_id=str(uuid.uuid4()),
            user_id=self.user_id,
            project_id=project.project_id,
            run_id=run["run_id"],
            kind="step1_extract",
            status=self.TaskStatus.QUEUED,
            idempotency_key=f"task-{uuid.uuid4()}",
            attempt=0,
            max_attempts=3,
            payload={"source": "live-test"},
            created_at="2026-07-14T00:00:00+00:00",
            updated_at="2026-07-14T00:00:00+00:00",
            available_at="2026-07-14T00:00:00+00:00",
            correlation_id="corr",
        )
        created = self.tasks.create_task(task)
        self.assertEqual(created.kind, "step1_extract")

        listed = self.tasks.list_tasks(user_id=self.user_id, project_id=project.project_id)
        self.assertTrue(any(t.task_id == created.task_id for t in listed))

        # Claim via RPC moves to running
        from datetime import datetime, timezone

        claim = self.tasks.claim_next(self.TaskClaimRequest(worker_id="live-worker-1"), now=datetime.now(timezone.utc))
        self.assertIsNotNone(claim, "claim_next should return the queued task")
        assert claim is not None
        self.assertEqual(claim.task.status, self.TaskStatus.RUNNING)

        # terminal append + replay
        event = self.terminal.append(
            self.TerminalEventCreate(
                user_id=self.user_id,
                project_id=project.project_id,
                run_id=run["run_id"],
                level="success",
                event_type="system_message",
                message="Live terminal seed",
                safe_payload={"test": True},
            )
        )
        page = self.terminal.list_project_events(
            user_id=self.user_id, project_id=project.project_id, after_sequence=None, limit=50
        )
        self.assertTrue(any(e.message == "Live terminal seed" for e in page.events))


if __name__ == "__main__":
    unittest.main()