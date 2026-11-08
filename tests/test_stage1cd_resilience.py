import asyncio

import httpx
import pytest

from src.services.dependency_health import DependencyHealthRegistry, DependencyStatus
from src.services.resilience import CircuitBreaker, CircuitOpenError, call_with_resilience


def test_transient_failure_is_retried_once_and_recovery_is_recorded():
    registry = DependencyHealthRegistry()
    attempts = 0

    async def operation():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("upstream timed out")
        return "answer"

    result = asyncio.run(
        call_with_resilience(
            "mcp",
            operation,
            timeout_seconds=1,
            max_retries=1,
            retryable_exceptions=(TimeoutError,),
            retry_delay_seconds=0,
            registry=registry,
        )
    )

    assert result == "answer"
    assert attempts == 2
    assert registry.snapshot()["mcp"].status == DependencyStatus.HEALTHY


def test_non_transient_failure_is_not_retried_and_exposes_only_a_reason_code():
    registry = DependencyHealthRegistry()
    attempts = 0

    async def operation():
        nonlocal attempts
        attempts += 1
        raise ValueError("api_key=stage1-secret must not escape")

    with pytest.raises(ValueError):
        asyncio.run(
            call_with_resilience(
                "embedding",
                operation,
                timeout_seconds=1,
                max_retries=1,
                retryable_exceptions=(TimeoutError,),
                retry_delay_seconds=0,
                registry=registry,
            )
        )

    health = registry.snapshot()["embedding"]
    assert attempts == 1
    assert health.status == DependencyStatus.UNAVAILABLE
    assert health.reason_code == "non_retryable_failure"
    assert not hasattr(health, "detail")


def test_open_circuit_fails_fast_then_successful_probe_closes_it():
    now = [0.0]
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout_seconds=10,
        clock=lambda: now[0],
    )
    registry = DependencyHealthRegistry()
    failures = 0

    async def failing_operation():
        nonlocal failures
        failures += 1
        raise TimeoutError("temporary outage")

    for _ in range(2):
        with pytest.raises(TimeoutError):
            asyncio.run(
                call_with_resilience(
                    "reranker",
                    failing_operation,
                    timeout_seconds=1,
                    retryable_exceptions=(TimeoutError,),
                    breaker=breaker,
                    registry=registry,
                )
            )

    with pytest.raises(CircuitOpenError):
        asyncio.run(
            call_with_resilience(
                "reranker",
                failing_operation,
                timeout_seconds=1,
                retryable_exceptions=(TimeoutError,),
                breaker=breaker,
                registry=registry,
            )
        )
    assert failures == 2
    assert registry.snapshot()["reranker"].reason_code == "circuit_open"

    now[0] = 10.0

    async def successful_probe():
        return "recovered"

    assert asyncio.run(
        call_with_resilience(
            "reranker",
            successful_probe,
            timeout_seconds=1,
            retryable_exceptions=(TimeoutError,),
            breaker=breaker,
            registry=registry,
        )
    ) == "recovered"
    assert breaker.state == "closed"
    assert registry.snapshot()["reranker"].status == DependencyStatus.HEALTHY


def test_mcp_timeout_is_retried_and_recorded_without_exposing_upstream_secret():
    from src.services.mcp_tools import search_wikipedia

    registry = DependencyHealthRegistry()
    attempts = 0

    class TimeoutClient:
        async def get(self, url, params):
            nonlocal attempts
            attempts += 1
            raise httpx.ReadTimeout("api_key=stage1-secret upstream timeout")

    result = asyncio.run(
        search_wikipedia("cloisonne", client=TimeoutClient(), registry=registry)
    )

    assert result.status == "unavailable"
    assert result.message == "Wikipedia temporarily unavailable"
    assert "stage1-secret" not in result.message
    assert attempts == 2
    health = registry.snapshot()["mcp_wikipedia"]
    assert health.status == DependencyStatus.UNAVAILABLE
    assert health.reason_code == "retry_exhausted"
