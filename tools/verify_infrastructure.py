"""Verify Plan 17 infrastructure, deployment, observability, and free-tier scaffolding."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/observability/src"))
sys.path.insert(0, str(ROOT / "apps/api/src"))
sys.path.insert(0, str(ROOT / "apps/worker/src"))

from qcm_observability.budget import DEFAULT_FREE_TIER_BUDGET, UsageSample, evaluate_budget
from qcm_observability.health import ComponentHealth, readiness_report
from qcm_observability.logging import StructuredLogEvent, structured_log


REQUIRED_PATHS = [
    ".github/workflows/verify.yml",
    ".env.example",
    "infra/env.schema.json",
    "infra/vercel/vercel.json",
    "infra/vercel/README.md",
    "infra/supabase/config.toml",
    "infra/supabase/storage_policies.sql",
    "infra/hf-space/Dockerfile",
    "infra/hf-space/README.md",
    "docs/runbooks/provider_limits_snapshot.md",
    "docs/runbooks/deployment.md",
    "docs/runbooks/backup_restore.md",
    "docs/runbooks/incident_response.md",
    "docs/runbooks/free_tier_operations.md",
    "packages/observability/src/qcm_observability/budget.py",
    "packages/observability/src/qcm_observability/health.py",
    "packages/observability/src/qcm_observability/logging.py",
    "apps/api/src/qcm_api/routes/health.py",
    "apps/worker/src/qcm_worker/health.py",
]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Missing Plan 17 infrastructure paths: {missing}")

    env_schema = json.loads(read("infra/env.schema.json"))
    variable_names = {item["name"] for item in env_schema["variables"]}
    for expected in [
        "QCM_APP_ENV",
        "QCM_DEPLOY_TARGET",
        "QCM_MAX_SOURCE_FILE_BYTES",
        "SUPABASE_SERVICE_ROLE_KEY",
        "OPENROUTER_API_KEY",
        "QCM_WORKER_ID",
        "SENTRY_DSN",
    ]:
        assert expected in variable_names

    vercel = json.loads(read("infra/vercel/vercel.json"))
    assert vercel["framework"] == "vite"
    assert vercel["env"]["QCM_MAX_SOURCE_FILE_BYTES"] == "52428800"
    assert "qcm-artifacts-private" in read("infra/supabase/storage_policies.sql")
    assert "qcm_api.main:app" in read("infra/hf-space/Dockerfile")
    assert "7860" in read("Dockerfile")

    warnings = evaluate_budget(
        UsageSample(source_file_bytes=60_000_000, request_body_bytes=5_000_000),
        DEFAULT_FREE_TIER_BUDGET,
    )
    assert "source_file_exceeds_50mb_cap" in warnings
    assert "vercel_request_body_limit_exceeded" in warnings
    assert readiness_report((ComponentHealth("api", True),)).status == "ready"
    redacted = structured_log(
        StructuredLogEvent("test", "info", "corr", {"service_role_key": "secret", "safe": "ok"})
    )
    assert redacted["safe_payload"]["service_role_key"] == "[redacted]"

    limits = read("docs/runbooks/provider_limits_snapshot.md")
    for expected in ["https://vercel.com/docs/functions/limitations", "https://supabase.com/pricing", "https://huggingface.co/docs/hub/spaces-gpus"]:
        assert expected in limits

    print("Plan 17 infrastructure manifests, env schema, health, logging, budgets, CI, and runbooks verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
