"""Worker authentication context helpers."""

from qcm_domain.auth import AppRole, WorkerContext


def build_worker_context(*, worker_id: str, correlation_id: str) -> WorkerContext:
    return WorkerContext(worker_id=worker_id, role=AppRole.WORKER, correlation_id=correlation_id)
