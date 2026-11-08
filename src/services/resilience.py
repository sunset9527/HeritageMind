"""Small async resilience boundary for optional external dependencies."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from src.services.dependency_health import (
    DependencyHealthRegistry,
    DependencyStatus,
    dependency_health,
)


Result = TypeVar("Result")


class CircuitOpenError(RuntimeError):
    """Raised before calling a dependency whose circuit is temporarily open."""


class CircuitBreaker:
    """A process-local closed/open/half-open circuit breaker."""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if recovery_timeout_seconds <= 0:
            raise ValueError("recovery_timeout_seconds must be positive")
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._clock = clock
        self._failure_count = 0
        self._opened_at: float | None = None
        self._probe_in_progress = False
        self.state = "closed"

    def allow_call(self) -> None:
        if self.state == "closed":
            return
        if self.state == "open":
            assert self._opened_at is not None
            if self._clock() - self._opened_at < self.recovery_timeout_seconds:
                raise CircuitOpenError("dependency circuit is open")
            self.state = "half_open"
        if self._probe_in_progress:
            raise CircuitOpenError("dependency recovery probe is in progress")
        self._probe_in_progress = True

    def record_success(self) -> None:
        self._failure_count = 0
        self._opened_at = None
        self._probe_in_progress = False
        self.state = "closed"

    def record_failure(self) -> None:
        self._probe_in_progress = False
        if self.state == "half_open":
            self._opened_at = self._clock()
            self.state = "open"
            return
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self._opened_at = self._clock()
            self.state = "open"


async def call_with_resilience(
    dependency: str,
    operation: Callable[[], Awaitable[Result]],
    *,
    timeout_seconds: float,
    max_retries: int = 0,
    retryable_exceptions: tuple[type[BaseException], ...] = (TimeoutError,),
    retry_delay_seconds: float = 0.1,
    breaker: CircuitBreaker | None = None,
    registry: DependencyHealthRegistry = dependency_health,
) -> Result:
    """Run an idempotent async operation with bounded retry and health reporting.

    The caller explicitly opts into retries by naming exception types. Raw exception
    details intentionally never enter the dependency health registry.
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if max_retries < 0:
        raise ValueError("max_retries must not be negative")
    if retry_delay_seconds < 0:
        raise ValueError("retry_delay_seconds must not be negative")

    if breaker is not None:
        try:
            breaker.allow_call()
        except CircuitOpenError:
            registry.mark(dependency, DependencyStatus.UNAVAILABLE, reason_code="circuit_open")
            raise

    for attempt in range(max_retries + 1):
        try:
            result = await asyncio.wait_for(operation(), timeout=timeout_seconds)
        except asyncio.CancelledError:
            raise
        except retryable_exceptions:
            if attempt < max_retries:
                await asyncio.sleep(retry_delay_seconds * (2 ** attempt))
                continue
            if breaker is not None:
                breaker.record_failure()
            registry.mark(dependency, DependencyStatus.UNAVAILABLE, reason_code="retry_exhausted")
            raise
        except Exception:
            if breaker is not None:
                breaker.record_failure()
            registry.mark(dependency, DependencyStatus.UNAVAILABLE, reason_code="non_retryable_failure")
            raise
        else:
            if breaker is not None:
                breaker.record_success()
            registry.mark(dependency, DependencyStatus.HEALTHY)
            return result

    raise RuntimeError("unreachable resilience retry state")
