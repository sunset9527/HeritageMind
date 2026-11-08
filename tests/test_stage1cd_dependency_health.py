from datetime import datetime, timezone

from src.services.dependency_health import (
    DependencyHealthRegistry,
    DependencyStatus,
    required_api_dependencies,
)


def test_required_dependency_failure_makes_readiness_unavailable():
    registry = DependencyHealthRegistry()
    registry.mark("mysql", DependencyStatus.HEALTHY)
    registry.mark("retriever", DependencyStatus.UNAVAILABLE, reason_code="index_missing")
    registry.mark("reranker", DependencyStatus.DEGRADED, reason_code="model_unavailable")

    readiness = registry.readiness(required={"mysql", "retriever"})

    assert readiness.status == DependencyStatus.UNAVAILABLE
    assert readiness.http_status == 503
    assert readiness.dependencies["retriever"].reason_code == "index_missing"
    assert readiness.dependencies["reranker"].status == DependencyStatus.DEGRADED


def test_optional_degradation_keeps_readiness_available():
    registry = DependencyHealthRegistry()
    registry.mark("mysql", DependencyStatus.HEALTHY)
    registry.mark("retriever", DependencyStatus.HEALTHY)
    registry.mark("mcp", DependencyStatus.DEGRADED, reason_code="tool_timeout")

    readiness = registry.readiness(required={"mysql", "retriever"})

    assert readiness.status == DependencyStatus.DEGRADED
    assert readiness.http_status == 200


def test_optional_unavailable_dependency_is_reported_as_degraded_not_healthy():
    registry = DependencyHealthRegistry()
    registry.mark("mysql", DependencyStatus.HEALTHY)
    registry.mark("retriever", DependencyStatus.HEALTHY)
    registry.mark("mcp", DependencyStatus.UNAVAILABLE, reason_code="retry_exhausted")

    readiness = registry.readiness(required={"mysql", "retriever"})

    assert readiness.status == DependencyStatus.DEGRADED
    assert readiness.http_status == 200


def test_disabled_dependency_is_not_reported_as_unavailable_and_snapshots_are_safe():
    registry = DependencyHealthRegistry()
    registry.mark("mysql", DependencyStatus.HEALTHY)
    registry.mark(
        "whisper",
        DependencyStatus.DISABLED,
        reason_code="feature_disabled",
        detail=r"C:\\models\\whisper and sk-stage1-secret must not leak",
    )

    snapshot = registry.snapshot()

    assert snapshot["whisper"].status == DependencyStatus.DISABLED
    assert snapshot["whisper"].reason_code == "feature_disabled"
    assert not hasattr(snapshot["whisper"], "detail")
    assert snapshot["whisper"].last_checked_at <= datetime.now(timezone.utc)


def test_recovery_resets_consecutive_failure_count():
    registry = DependencyHealthRegistry()
    registry.mark("redis", DependencyStatus.UNAVAILABLE, reason_code="connection_failed")
    registry.mark("redis", DependencyStatus.UNAVAILABLE, reason_code="connection_failed")
    registry.mark("redis", DependencyStatus.HEALTHY)

    entry = registry.snapshot()["redis"]

    assert entry.status == DependencyStatus.HEALTHY
    assert entry.consecutive_failures == 0
    assert entry.last_success_at is not None


def test_redis_is_required_for_production_api_readiness_only():
    assert required_api_dependencies("dev") == {"mysql", "retriever"}
    assert required_api_dependencies("test") == {"mysql", "retriever"}
    assert required_api_dependencies("prod") == {"mysql", "retriever", "redis"}
