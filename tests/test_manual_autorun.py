import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/shared/src",
    "packages/application/src",
    "apps/worker/src",
]:
    sys.path.insert(0, str(ROOT / relative))

from qcm_application.autorun_service import InMemoryManualAutoRunRepository, ManualAutoRunService
from qcm_application.ownership import AuthorizationError
from qcm_shared.autorun_contracts import (
    MANUAL_AUTORUN_TASK_KIND,
    MANUAL_AUTORUN_SCHEMA_VERSION,
    ManualAutoRunControlAction,
    ManualAutoRunControlCommand,
    ManualAutoRunSnapshot,
    ManualAutoRunStartCommand,
    ManualAutoRunStatus,
    ManualAutoRunStepConfig,
)
from qcm_shared.contracts import Task, TaskStatus
from qcm_shared.task_contracts import TaskCreateCommand
from qcm_worker.autorun_handler import manual_autorun_handler


class FakeTaskCreator:
    def __init__(self) -> None:
        self.commands: list[TaskCreateCommand] = []

    def create_task(self, command: TaskCreateCommand) -> Task:
        self.commands.append(command)
        return Task(
            task_id=f"task-{len(self.commands)}",
            user_id=command.user_id,
            project_id=command.project_id,
            run_id=command.run_id,
            kind=command.kind,
            status=TaskStatus.QUEUED,
            idempotency_key=command.idempotency_key,
            attempt=0,
            max_attempts=command.max_attempts,
            payload=command.payload,
            created_at="now",
            updated_at="now",
            available_at="now",
        )


class ManualAutoRunTest(unittest.TestCase):
    def snapshot(self, steps: tuple[ManualAutoRunStepConfig, ...] | None = None) -> ManualAutoRunSnapshot:
        return ManualAutoRunSnapshot(
            schema_version=MANUAL_AUTORUN_SCHEMA_VERSION,
            selected_steps=steps
            or (
                ManualAutoRunStepConfig("step2", "step2_orchestrate", True, {"template": "default"}),
                ManualAutoRunStepConfig("step1", "step1_extract", True, {"mode": "automatic"}),
            ),
        )

    def command(self) -> ManualAutoRunStartCommand:
        return ManualAutoRunStartCommand(
            user_id="u",
            project_id="p",
            run_id="r",
            auto_run_id="ar",
            snapshot=self.snapshot(),
            idempotency_key="idem",
            correlation_id="corr",
        )

    def test_validation_normalizes_canonical_step_order(self) -> None:
        result = ManualAutoRunService().validate(self.snapshot().selected_steps)
        self.assertTrue(result.valid)
        self.assertEqual(tuple(step.step_key for step in result.normalized_steps), ("step1", "step2"))
        self.assertIn("canonical visible pipeline order", result.warnings[0])

    def test_validation_blocks_unknown_or_wrong_step_mapping(self) -> None:
        result = ManualAutoRunService().validate((ManualAutoRunStepConfig("step3-correction", "legacy_step6", True),))
        self.assertFalse(result.valid)
        self.assertIn("step3_correction", result.errors[0])

    def test_start_is_idempotent_and_queues_workflow_task(self) -> None:
        task_creator = FakeTaskCreator()
        service = ManualAutoRunService(task_creator=task_creator)
        first = service.start(self.command())
        second = service.start(self.command())
        self.assertEqual(first.auto_run_id, second.auto_run_id)
        self.assertEqual(first.status, ManualAutoRunStatus.QUEUED)
        self.assertEqual(first.child_task_ids, ("task-1",))
        self.assertEqual(len(task_creator.commands), 1)
        self.assertEqual(task_creator.commands[0].kind, MANUAL_AUTORUN_TASK_KIND)

    def test_control_is_owner_scoped(self) -> None:
        repository = InMemoryManualAutoRunRepository()
        service = ManualAutoRunService(repository=repository)
        service.start(self.command())
        paused = service.control(
            ManualAutoRunControlCommand("u", "p", "ar", ManualAutoRunControlAction.PAUSE, "corr")
        )
        self.assertEqual(paused.status, ManualAutoRunStatus.PAUSED)
        with self.assertRaises(AuthorizationError):
            service.control(ManualAutoRunControlCommand("other", "p", "ar", "cancel", "corr"))

    def test_worker_handler_plans_sequential_child_tasks(self) -> None:
        result = manual_autorun_handler(
            {
                "auto_run_id": "ar",
                "user_id": "u",
                "project_id": "p",
                "run_id": "r",
                "snapshot": {
                    "schema_version": MANUAL_AUTORUN_SCHEMA_VERSION,
                    "selected_steps": [
                        {"step_key": "step2", "task_kind": "step2_orchestrate", "enabled": True, "config": {}},
                        {"step_key": "step1", "task_kind": "step1_extract", "enabled": True, "config": {}},
                    ],
                },
            }
        )
        self.assertEqual(result["status"], TaskStatus.COMPLETED_WITH_WARNINGS.value)
        child_tasks = result["result"]["child_tasks"]
        self.assertEqual([item["step_key"] for item in child_tasks], ["step1", "step2"])


if __name__ == "__main__":
    unittest.main()
