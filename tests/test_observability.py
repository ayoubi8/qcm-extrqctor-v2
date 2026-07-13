import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/observability/src"))

from qcm_observability.budget import FreeTierBudget, UsageSample, evaluate_budget
from qcm_observability.health import ComponentHealth, readiness_report
from qcm_observability.logging import StructuredLogEvent, structured_log


class ObservabilityTest(unittest.TestCase):
    def test_budget_warns_for_file_and_vercel_body_limits(self) -> None:
        warnings = evaluate_budget(
            UsageSample(source_file_bytes=60_000_000, request_body_bytes=5_000_000),
            FreeTierBudget(max_source_file_bytes=52_428_800, vercel_request_body_bytes=4_500_000),
        )
        self.assertIn("source_file_exceeds_50mb_cap", warnings)
        self.assertIn("vercel_request_body_limit_exceeded", warnings)

    def test_readiness_reports_degraded_component(self) -> None:
        report = readiness_report((ComponentHealth("api", True), ComponentHealth("db", False, "missing")))
        self.assertEqual(report.status, "degraded")

    def test_structured_log_redacts_secret_fields(self) -> None:
        event = structured_log(
            StructuredLogEvent(
                event="provider_call",
                level="info",
                correlation_id="corr",
                safe_payload={"api_key": "secret", "nested": {"token": "secret"}, "model": "m"},
            )
        )
        self.assertEqual(event["safe_payload"]["api_key"], "[redacted]")
        self.assertEqual(event["safe_payload"]["nested"]["token"], "[redacted]")
        self.assertEqual(event["safe_payload"]["model"], "m")


if __name__ == "__main__":
    unittest.main()
