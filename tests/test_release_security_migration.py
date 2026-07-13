import json
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
for relative in [
    "packages/domain/src",
    "packages/shared/src",
    "tools",
]:
    sys.path.insert(0, str(ROOT / relative))

from migration.legacy_import_validator import validate_legacy_import_manifest


class ReleaseSecurityMigrationTest(unittest.TestCase):
    def test_legacy_import_validator_quarantines_ambiguous_artifacts(self) -> None:
        manifest = json.loads((ROOT / "tests/fixtures/synthetic_legacy_manifest.json").read_text(encoding="utf-8"))
        report = validate_legacy_import_manifest(manifest)
        self.assertEqual(len(report.importable), 1)
        self.assertEqual(len(report.quarantined), 1)
        self.assertEqual(report.quarantined[0].quarantine_reason, "missing_checksum")
        self.assertTrue(any("subcategory" in warning for warning in report.warnings))

    def test_security_matrix_contains_required_two_user_and_storage_gates(self) -> None:
        matrix = json.loads((ROOT / "tests/security/security_matrix.json").read_text(encoding="utf-8"))
        self.assertIn("two_user_project_denial", matrix["required_gates"])
        self.assertIn("signed_url_owner_check", matrix["required_gates"])
        self.assertIn("supabase_storage_live_policy_check", matrix["deployed_only_gates"])

    def test_release_gate_config_includes_all_plan_verifiers(self) -> None:
        config = json.loads((ROOT / "docs/release/release_gate_config.json").read_text(encoding="utf-8"))
        required = "\n".join(config["required_commands"])
        self.assertIn("tools/verify_ai_autorun.py", required)
        self.assertIn("tools/verify_infrastructure.py", required)
        self.assertIn("tools/verify_release.py", required)
        self.assertIn("live Supabase RLS/storage tests", "\n".join(config["manual_gates"]))

    def test_private_fixture_policy_is_explicit(self) -> None:
        manifest = json.loads((ROOT / "tests/golden/synthetic_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["fixture_policy"], "synthetic_public_only")
        self.assertIn("do_not_commit", manifest["private_fixture_rule"])


if __name__ == "__main__":
    unittest.main()
