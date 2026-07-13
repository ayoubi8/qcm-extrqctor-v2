import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "domain" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "application" / "src"))

from qcm_application.correction_modes import normalize_step3_mode
from qcm_shared.config.defaults import MAX_SOURCE_FILE_BYTES
from qcm_shared.contracts import ArtifactType, Task, TaskStatus


class SharedContractsTest(unittest.TestCase):
    def test_file_size_cap_matches_phase_12(self) -> None:
        self.assertEqual(MAX_SOURCE_FILE_BYTES, 52_428_800)

    def test_task_contract_requires_positive_max_attempts(self) -> None:
        with self.assertRaises(ValueError):
            Task(
                task_id="task",
                user_id="user",
                project_id="project",
                run_id="run",
                kind="step1_extract",
                status=TaskStatus.QUEUED,
                idempotency_key="idem",
                attempt=0,
                max_attempts=0,
                payload={},
                created_at="2026-07-13T00:00:00Z",
                updated_at="2026-07-13T00:00:00Z",
                available_at="2026-07-13T00:00:00Z",
            )

    def test_artifact_type_contains_ai_autorun_contracts(self) -> None:
        self.assertEqual(ArtifactType.AI_AUTORUN_CONFIG.value, "ai_autorun_config")

    def test_step3_legacy_mode_mapping(self) -> None:
        self.assertEqual(normalize_step3_mode("page_text"), "page_detection")
        self.assertEqual(normalize_step3_mode("auto_detect"), "auto_detection")


if __name__ == "__main__":
    unittest.main()
