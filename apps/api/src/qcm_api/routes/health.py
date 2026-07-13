"""Deployment health, readiness, and lightweight metrics routes."""

try:
    from fastapi import APIRouter
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None

from qcm_observability.health import ComponentHealth, readiness_report


def create_health_router():
    if APIRouter is None:
        return None

    router = APIRouter(tags=["health"])

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/ready")
    def ready() -> dict:
        report = readiness_report(
            (
                ComponentHealth("api", True),
                ComponentHealth("database", False, "adapter-not-bound-in-local-foundation"),
                ComponentHealth("storage", False, "adapter-not-bound-in-local-foundation"),
            )
        )
        return {
            "status": report.status,
            "components": [component.__dict__ for component in report.components],
        }

    @router.get("/metrics")
    def metrics() -> dict:
        return {
            "format": "json",
            "counters": {
                "qcm_api_health_checks": 1,
            },
        }

    return router
