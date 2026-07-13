"""Verify Plan 18 testing, security, migration, and release gates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/domain/src"))
sys.path.insert(0, str(ROOT / "packages/shared/src"))
sys.path.insert(0, str(ROOT / "tools"))

from migration.legacy_import_validator import validate_legacy_import_manifest

REQUIRED_PATHS = [
    "docs/release/release_gate_config.json",
    "docs/release/security_acceptance.md",
    "docs/release/migration_acceptance.md",
    "docs/release/rollout_plan.md",
    "docs/release/rollback_plan.md",
    "docs/release/final_acceptance_report.md",
    "tests/fixtures/synthetic_legacy_manifest.json",
    "tests/golden/synthetic_manifest.json",
    "tests/security/security_matrix.json",
    "tests/e2e/playwright_plan.json",
    "tests/visual/release_visual_matrix.json",
    "tools/migration/legacy_import_validator.py",
]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def load_json(relative: str):
    return json.loads(read(relative))


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Plan 18 release paths: {missing}")

    release_gate = load_json("docs/release/release_gate_config.json")
    commands = "\n".join(release_gate["required_commands"])
    for expected in [
        "tools/verify_foundation.py",
        "tools/verify_step4_similarity.py",
        "tools/verify_manual_autorun.py",
        "tools/verify_ai_autorun.py",
        "tools/verify_infrastructure.py",
        "tools/verify_release.py",
        "-m unittest discover tests",
    ]:
        assert expected in commands

    manual_gates = "\n".join(release_gate["manual_gates"])
    for expected in [
        "provider limits",
        "private fixture",
        "browser e2e",
        "Supabase RLS/storage",
        "backup/restore",
    ]:
        assert expected in manual_gates

    legacy_report = validate_legacy_import_manifest(load_json("tests/fixtures/synthetic_legacy_manifest.json"))
    assert len(legacy_report.importable) == 1
    assert len(legacy_report.quarantined) == 1
    assert legacy_report.quarantined[0].quarantine_reason == "missing_checksum"

    security = load_json("tests/security/security_matrix.json")
    for expected in [
        "two_user_project_denial",
        "signed_url_owner_check",
        "reference_db_owner_check",
        "ai_no_raw_reasoning_check",
        "secret_redaction_check",
    ]:
        assert expected in security["required_gates"]

    golden = load_json("tests/golden/synthetic_manifest.json")
    assert golden["fixture_policy"] == "synthetic_public_only"
    assert "private" in golden["private_fixture_rule"]

    e2e = load_json("tests/e2e/playwright_plan.json")
    assert e2e["status"] == "planned_until_node_dependencies_installed"
    visual = load_json("tests/visual/release_visual_matrix.json")
    assert "ai_autorun_window" in visual["screens"]

    release_docs = "\n".join(
        read(path)
        for path in [
            "docs/release/security_acceptance.md",
            "docs/release/migration_acceptance.md",
            "docs/release/rollout_plan.md",
            "docs/release/rollback_plan.md",
            "docs/release/final_acceptance_report.md",
        ]
    )
    for expected in ["read-only", "rollback", "cross-user", "backup", "private fixture"]:
        assert expected in release_docs.lower()

    print("Plan 18 release gates, security matrix, migration validator, rollout, rollback, and acceptance docs verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
