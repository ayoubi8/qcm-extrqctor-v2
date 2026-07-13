"""Worker readiness helpers for deployment smoke checks."""

from qcm_observability.health import ComponentHealth, HealthReport, readiness_report
from qcm_worker.handlers import TASK_HANDLERS


def worker_readiness() -> HealthReport:
    return readiness_report(
        (
            ComponentHealth("worker", True),
            ComponentHealth("registered_handlers", bool(TASK_HANDLERS), f"{len(TASK_HANDLERS)} handlers"),
        )
    )
