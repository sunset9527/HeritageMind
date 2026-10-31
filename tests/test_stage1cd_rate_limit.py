"""阶段 1C/1D：Redis 限流与进程内保守降级。"""

import asyncio
from types import SimpleNamespace

import httpx
from fastapi import Depends, FastAPI

from src.deps_rate_limit import rate_limit
from src.middleware.request_context import ClientIdentity, RequestContextMiddleware
from src.services.rate_limit import (
    RateLimitCategory,
    RateLimitPolicy,
    RateLimiter,
    policies_from_settings,
)


class FakeRedis:
    """只实现 Lua 调用的确定性 Redis 替身。"""

    def __init__(self, *, ttl=60):
        self.ttl = ttl
        self.counts = {}
        self.calls = []
        self.failed = False

    async def eval(self, script, key_count, key, window):
        self.calls.append((script, key_count, key, window))
        if self.failed:
            raise TimeoutError("redis unavailable")
        self.counts[key] = self.counts.get(key, 0) + 1
        return [self.counts[key], self.ttl]


def _policies(limit=2, window=60):
    return {category: RateLimitPolicy(limit, window) for category in RateLimitCategory}


def _identity(ip="198.51.100.7"):
    return ClientIdentity(peer_ip=ip, client_ip=ip)


def test_redis_fixed_window_first_boundary_limit_and_retry_ttl():
    async def scenario():
        redis = FakeRedis(ttl=47)
        limiter = RateLimiter(redis_client=redis, policies=_policies())
        first = await limiter.check(RateLimitCategory.LOGIN, account_identifier="Alice@Example.COM")
        second = await limiter.check(RateLimitCategory.LOGIN, account_identifier="alice@example.com")
        blocked = await limiter.check(RateLimitCategory.LOGIN, account_identifier="alice@example.com")

        assert first.allowed and first.count == 1 and first.remaining == 1
        assert second.allowed and second.count == 2 and second.remaining == 0
        assert not blocked.allowed and blocked.retry_after == 47
        script, key_count, key, window = redis.calls[0]
        assert "INCR" in script and "EXPIRE" in script and "TTL" in script
        assert key_count == 1 and window == 60
        assert "Alice" not in key and "example.com" not in key

    asyncio.run(scenario())


def test_identity_isolation_uses_user_then_trusted_client_ip_and_never_plaintext():
    async def scenario():
        redis = FakeRedis()
        limiter = RateLimiter(redis_client=redis, policies=_policies(limit=1))
        user = await limiter.check(RateLimitCategory.AUTHENTICATED_QUERY, user_id=42)
        same_user = await limiter.check(RateLimitCategory.AUTHENTICATED_QUERY, user_id=42)
        other_user = await limiter.check(RateLimitCategory.AUTHENTICATED_QUERY, user_id=43)
        anonymous = await limiter.check(RateLimitCategory.ANONYMOUS_QUERY, identity=_identity("203.0.113.8"))
        other_ip = await limiter.check(RateLimitCategory.ANONYMOUS_QUERY, identity=_identity("203.0.113.9"))

        assert user.allowed and not same_user.allowed and other_user.allowed
        assert anonymous.allowed and other_ip.allowed
        keys = list(redis.counts)
        assert all("user:42" not in key and "ip:203.0.113." not in key for key in keys)

    asyncio.run(scenario())


def test_dev_local_fallback_is_bounded_and_uses_injected_clock():
    async def scenario():
        now = [100.0]
        redis = FakeRedis()
        redis.failed = True
        limiter = RateLimiter(
            redis_client=redis,
            policies=_policies(limit=2, window=10),
            clock=lambda: now[0],
            memory_max_keys=2,
        )
        one = await limiter.check(RateLimitCategory.LOGIN, account_identifier="a")
        two = await limiter.check(RateLimitCategory.LOGIN, account_identifier="a")
        three = await limiter.check(RateLimitCategory.LOGIN, account_identifier="a")
        assert one.allowed and two.allowed and not three.allowed
        assert three.retry_after == 10
        await limiter.check(RateLimitCategory.LOGIN, account_identifier="b")
        await limiter.check(RateLimitCategory.LOGIN, account_identifier="c")
        assert limiter.memory_key_count <= 2
        now[0] += 10
        fresh_window = await limiter.check(RateLimitCategory.LOGIN, account_identifier="a")
        assert fresh_window.allowed and fresh_window.count == 1

    asyncio.run(scenario())


def test_memory_fallback_rejects_new_key_at_capacity_without_resetting_active_identity():
    async def scenario():
        redis = FakeRedis()
        redis.failed = True
        limiter = RateLimiter(
            redis_client=redis,
            policies=_policies(limit=1, window=60),
            memory_max_keys=1,
        )

        first_identity = await limiter.check(RateLimitCategory.LOGIN, account_identifier="first")
        new_identity = await limiter.check(RateLimitCategory.LOGIN, account_identifier="second")
        first_identity_again = await limiter.check(RateLimitCategory.LOGIN, account_identifier="first")

        assert first_identity.allowed
        assert not new_identity.allowed
        assert not first_identity_again.allowed
        assert limiter.memory_key_count == 1

    asyncio.run(scenario())


def test_production_redis_failure_returns_stable_503_with_request_id(monkeypatch):
    async def scenario():
        redis = FakeRedis()
        redis.failed = True
        limiter = RateLimiter(
            redis_client=redis,
            policies=_policies(limit=1),
            app_env="prod",
        )
        monkeypatch.setattr("src.deps_rate_limit.get_rate_limiter", lambda: limiter)
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware, settings=SimpleNamespace(
            trust_proxy_headers=False, trusted_proxy_ips=[]
        ))

        @app.get("/protected")
        async def protected(_: None = Depends(rate_limit(RateLimitCategory.READ_ONLY))):
            return {"ok": True}

        transport = httpx.ASGITransport(app=app, client=("198.51.100.7", 1))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/protected", headers={"X-Request-ID": "redis-down"})

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "rate_limit_unavailable"
        assert "redis" not in response.text.lower()
        assert response.headers["x-request-id"] == "redis-down"

    asyncio.run(scenario())


def test_settings_define_every_business_category_and_keep_anonymous_policy_when_disabled():
    settings = SimpleNamespace(
        registration_quota=5, registration_window_seconds=3600,
        login_quota=10, login_window_seconds=900,
        anonymous_query_quota=20, anonymous_query_window_seconds=60,
        authenticated_query_quota=120, authenticated_query_window_seconds=60,
        ai_search_quota=30, ai_search_window_seconds=60,
        upload_quota=20, upload_window_seconds=60,
        index_rebuild_quota=6, index_rebuild_window_seconds=3600,
        readonly_quota=300, readonly_window_seconds=60,
    )
    policies = policies_from_settings(settings)

    assert set(policies) == set(RateLimitCategory)
    assert policies[RateLimitCategory.ANONYMOUS_QUERY] == RateLimitPolicy(20, 60)
    assert policies[RateLimitCategory.INDEX_REBUILD] == RateLimitPolicy(6, 3600)


def test_all_public_read_routes_use_read_only_rate_limit():
    import api

    public_paths = {
        "/", "/graph/stats", "/graph/visualize", "/graph/subgraph/{craft_name}",
        "/gap-report", "/crafts", "/profiles", "/config", "/dashboard/summary",
        "/documents/summary", "/media/list", "/media/{media_id}",
        "/media/file/{media_type}/{filename}", "/search/image", "/search/audio",
        "/knowledge/categories", "/encyclopedia", "/local-books/images/{craft_id}",
        "/encyclopedia/{slug}", "/inheritors", "/inheritors/{slug}",
    }
    routes = {
        route.path: route
        for route in api.app.routes
        if getattr(route, "path", None) in public_paths and "GET" in getattr(route, "methods", set())
    }

    assert set(routes) == public_paths
    for path, route in routes.items():
        calls = [dependency.call for dependency in route.dependant.dependencies]
        assert any(
            getattr(call, "rate_limit_category", None) == RateLimitCategory.READ_ONLY
            for call in calls
        ), f"missing READ_ONLY limiter: {path}"


def test_health_and_openapi_are_not_business_rate_limited():
    import api

    for path in ("/health", "/openapi.json", "/docs", "/redoc"):
        route = next(
            route for route in api.app.routes
            if getattr(route, "path", None) == path and "GET" in getattr(route, "methods", set())
        )
        dependant = getattr(route, "dependant", None)
        calls = [dependency.call for dependency in dependant.dependencies] if dependant else []
        assert not any(hasattr(call, "rate_limit_category") for call in calls)


def test_dependency_returns_stable_429_retry_after_and_request_id(monkeypatch):
    async def scenario():
        limiter = RateLimiter(redis_client=FakeRedis(), policies=_policies(limit=1))
        monkeypatch.setattr("src.deps_rate_limit.get_rate_limiter", lambda: limiter)
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware, settings=SimpleNamespace(
            trust_proxy_headers=False, trusted_proxy_ips=[]
        ))

        @app.get("/limited")
        async def limited(_: None = Depends(rate_limit(RateLimitCategory.READ_ONLY))):
            return {"ok": True}

        transport = httpx.ASGITransport(app=app, client=("198.51.100.7", 1))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/limited", headers={"X-Request-ID": "rl-test"})).status_code == 200
            blocked = await client.get("/limited", headers={"X-Request-ID": "rl-test"})
            assert blocked.status_code == 429
            assert blocked.json()["detail"]["code"] == "rate_limit_exceeded"
            assert blocked.headers["retry-after"] == "60"
            assert blocked.headers["x-request-id"] == "rl-test"

    asyncio.run(scenario())
