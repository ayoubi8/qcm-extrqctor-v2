"""Worker process entry point reserved for durable execution."""

from qcm_worker.handlers import TASK_HANDLERS
from qcm_worker.health import worker_readiness


def main() -> int:
    readiness = worker_readiness()
    print(f"qcm-worker {readiness.status}; registered handlers={len(TASK_HANDLERS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
