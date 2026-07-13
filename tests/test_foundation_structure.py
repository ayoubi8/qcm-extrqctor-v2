from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FoundationStructureTest(unittest.TestCase):
    def test_required_top_level_directories_exist(self) -> None:
        for relative in ["apps", "packages", "prompts", "artifact-schemas", "migrations", "tests"]:
            self.assertTrue((ROOT / relative).exists(), relative)

    def test_plan_03_adds_ordered_sql_migrations(self) -> None:
        self.assertEqual(
            [path.name for path in sorted((ROOT / "migrations").glob("*.sql"))],
            [
                "0001_profiles_projects.sql",
                "0002_runs_tasks_artifacts.sql",
                "0003_step_specific.sql",
                "0004_legacy_import_validation.sql",
            ],
        )


if __name__ == "__main__":
    unittest.main()
