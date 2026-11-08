"""Small in-process registry for safe dependency health summaries."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from typing import Iterable


class DependencyStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DependencyHealth:
    status: DependencyStatus
    reason_code: str | None
    last_checked_at: datetime
    last_success_at: datetime | None
    last_failure_at: datetime | None
    consecutive_failures: int


@dataclass(frozen=True)
class Readiness:
    status: DependencyStatus
    http_status: int
    dependencies: dict[str, DependencyHealth]


class DependencyHealthRegistry:
    """Track only stable reason codes; raw exceptions stay out of health APIs."""

    def __init__(self) -> None:
        self._entries: dict[str, DependencyHealth] = {}

    def mark(
        self,
        name: str,
        status: DependencyStatus | str,
        *,
        reason_code: str | None = None,
        detail: str | None = None,
    ) -> DependencyHealth:
        del detail  # Intentionally not persisted in this public registry.
        value = DependencyStatus(status)
        now = datetime.now(timezone.utc)
        previous = self._entries.get(name)
        was_failure = value in {DependencyStatus.DEGRADED, DependencyStatus.UNAVAILABLE}
        failures = (previous.consecutive_failures if previous else 0) + 1 if was_failure else 0
        entry = DependencyHealth(
            status=value,
            reason_code=reason_code,
            last_checked_at=now,
            last_success_at=now if value == DependencyStatus.HEALTHY else (previous.last_success_at if previous else None),
            last_failure_at=now if was_failure else (previous.last_failure_at if previous else None),
            consecutive_failures=failures,
        )
        self._entries[name] = entry
        return entry

    def snapshot(self) -> dict[str, DependencyHealth]:
        return {name: replace(entry) for name, entry in self._entries.items()}

    def readiness(self, *, required: Iterable[str]) -> Readiness:
        required_names = set(required)
        dependencies = self.snapshot()
        required_failed = any(
            dependencies.get(name, DependencyHealth(
                DependencyStatus.UNKNOWN, None, datetime.now(timezone.utc), None, None, 0
            )).status not in {DependencyStatus.HEALTHY, DependencyStatus.DISABLED}
            for name in required_names
        )
        if required_failed:
            return Readiness(DependencyStatus.UNAVAILABLE, 503, dependencies)
        if any(
            entry.status in {DependencyStatus.DEGRADED, DependencyStatus.UNAVAILABLE}
            for entry in dependencies.values()
        ):
            return Readiness(DependencyStatus.DEGRADED, 200, dependencies)
        return Readiness(DependencyStatus.HEALTHY, 200, dependencies)


dependency_health = DependencyHealthRegistry()


def required_api_dependencies(app_env: str) -> set[str]:
    """Return API readiness dependencies for the configured environment."""
    required = {"mysql", "retriever"}
    if app_env == "prod":
        required.add("redis")
    return required
