"""Health and readiness report helpers."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    name: str
    ok: bool
    detail: str = "ok"


@dataclass(frozen=True, slots=True)
class HealthReport:
    status: str
    components: tuple[ComponentHealth, ...]


def readiness_report(components: tuple[ComponentHealth, ...]) -> HealthReport:
    status = "ready" if all(component.ok for component in components) else "degraded"
    return HealthReport(status=status, components=components)
