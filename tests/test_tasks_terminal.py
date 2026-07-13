import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/shared/src",
    "packages/application/src",
    "packages/infrastructure/src",
    "apps/worker/src",
]:
    sys.path.insert(0, str(ROOT / relative))

from qcm_application.task_service import TaskService
from qcm_domain.tasks import InvalidTaskTransition, assert_task_transition
from qcm_infrastructure.tasks import InMemoryTaskRepository, InMemoryTerminalRepository
from qcm_shared.contracts import TaskStatus
from qcm_shared.task_contracts import (
    TaskCancelCommand,
    TaskClaimRequest,
    TaskCompletionCommand,
    TaskCreateCommand,
    TaskFailureCommand,
)
from qcm_worker.handlers import TASK_HANDLERS, register_handler
from qcm_worker.runner import WorkerRunner


class TaskTerminalTest(unittest.TestCase):
    def setUp(self) -> None:
        TASK_HANDLERS.clear()
        self.tasks = InMemoryTaskRepository()
        self.terminal = InMemoryTerminalRepository()
        self.service = TaskService(self.tasks, self.terminal)

    def test_invalid_terminal_transition_is_rejected(self) -> None:
        with self.assertRaises(InvalidTaskTransition):
            assert_task_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING)

    def test_idempotent_create_and_priority_claim(self) -> None:
        low = self.service.create_task(
            TaskCreateCommand("u", "p", "r", "step1_extract", "idem-low", "corr", priority=0)
        )
        high = self.service.create_task(
            TaskCreateCommand("u", "p", "r", "step2_page_qcm", "idem-high", "corr", priority=10)
        )
        duplicate = self.service.create_task(
            TaskCreateCommand("u", "p", "r", "step1_extract", "idem-low", "corr", priority=0)
        )
        self.assertEqual(low.task_id, duplicate.task_id)
        claim = self.service.claim_next(TaskClaimRequest(worker_id="worker"))
        self.assertEqual(claim.task.task_id, high.task_id)

    def test_heartbeat_cancel_retry_and_terminal_replay(self) -> None:
        task = self.service.create_task(
            TaskCreateCommand("u", "p", "r", "step1_extract", "idem", "corr")
        )
        claim = self.service.claim_next(TaskClaimRequest(worker_id="worker"))
        self.assertIsNotNone(claim.task.lease_expires_at)
        retried = self.service.fail(
            TaskFailureCommand(
                claim.task.task_id,
                claim.attempt.attempt_id,
                "worker",
                "provider_failure",
                "Retry later",
                True,
                "corr",
            )
        )
        self.assertEqual(retried.status, TaskStatus.RETRYING)
        page = self.service.terminal_page(user_id="u", project_id="p")
        self.assertGreaterEqual(len(page.events), 2)
        cancelled = self.service.cancel(TaskCancelCommand(retried.task_id, "u", "corr"))
        self.assertEqual(cancelled.status, TaskStatus.CANCELLED)
        replay = self.service.terminal_page(user_id="u", project_id="p", after_sequence=page.next_cursor)
        self.assertGreaterEqual(len(replay.events), 1)

    def test_worker_runner_executes_registered_handler(self) -> None:
        register_handler("step1_extract", lambda payload: {"status": "completed", "message": "done"})
        task = self.service.create_task(
            TaskCreateCommand("u", "p", "r", "step1_extract", "idem", "corr")
        )
        runner = WorkerRunner(worker_id="worker", task_service=self.service)
        self.assertTrue(runner.run_once())
        self.assertEqual(self.tasks.get_task(task.task_id).status, TaskStatus.COMPLETED)

    def test_non_retryable_failure_finalizes_task(self) -> None:
        task = self.service.create_task(
            TaskCreateCommand("u", "p", "r", "step1_extract", "idem", "corr", max_attempts=1)
        )
        claim = self.service.claim_next(TaskClaimRequest(worker_id="worker"))
        failed = self.service.fail(
            TaskFailureCommand(
                task.task_id,
                claim.attempt.attempt_id,
                "worker",
                "invalid_schema",
                "Invalid schema",
                False,
                "corr",
            )
        )
        self.assertEqual(failed.status, TaskStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
