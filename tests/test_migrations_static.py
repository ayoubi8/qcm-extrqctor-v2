import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import verify_migrations


class MigrationStaticTest(unittest.TestCase):
    def test_plan_03_migrations_pass_static_contracts(self) -> None:
        verify_migrations.verify()


if __name__ == "__main__":
    unittest.main()
