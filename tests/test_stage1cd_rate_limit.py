"""阶段 1C/1D：Redis 限流与进程内保守降级。"""

import asyncio
import threading
from types import SimpleNamespace

import httpx
import pytest
from fastapi import Depends, FastAPI

from src.deps import get_current_user, require_admin
from src.deps_rate_limit import enforce_account_and_ip_rate_limits, rate_limit
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

    async def eval(self, script, key_count, *args):
        keys = tuple(args[:key_count])
        window = args[key_count]
        self.calls.append((script, key_count, keys, window))
        if self.failed:
            raise TimeoutError("redis unavailable")
        for key in keys:
            self.counts[key] = self.counts.get(key, 0) + 1
        return [max(self.counts[key] for key in keys), self.ttl]


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
        script, key_count, keys, window = redis.calls[0]
        key = keys[0]
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


@pytest.mark.parametrize(
    ("failure_kind", "secret"),
    [
        ("provider", "connect-secret"),
        ("timeout", "timeout-secret"),
        ("exception", "script-secret"),
    ],
)
def test_production_redis_failures_return_503_from_real_public_api_route(
    monkeypatch, failure_kind, secret
):
    async def scenario():
        class EvalFailureRedis:
            async def eval(self, *args):
                if failure_kind == "timeout":
                    raise TimeoutError(secret)
                raise RuntimeError(secret)

        def provider():
            if failure_kind == "provider":
                raise ConnectionError(secret)
            return EvalFailureRedis()

        limiter = RateLimiter(
            redis_provider=provider,
            policies=_policies(limit=1),
            app_env="prod",
        )
        monkeypatch.setattr("src.deps_rate_limit.get_rate_limiter", lambda: limiter)
        import api

        transport = httpx.ASGITransport(app=api.app, client=("198.51.100.7", 1))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/crafts", headers={"X-Request-ID": "redis-down"})

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "rate_limit_unavailable"
        assert "redis" not in response.text.lower()
        assert secret not in response.text
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


@pytest.mark.parametrize("category", [RateLimitCategory.LOGIN, RateLimitCategory.REGISTRATION])
def test_credential_account_and_trusted_client_ip_buckets_both_reject(monkeypatch, category):
    async def scenario():
        limiter = RateLimiter(redis_client=FakeRedis(), policies=_policies(limit=1))
        monkeypatch.setattr("src.deps_rate_limit.get_rate_limiter", lambda: limiter)
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware, settings=SimpleNamespace(
            trust_proxy_headers=True, trusted_proxy_ips=["203.0.113.9"]
        ))

        @app.get("/login/{account}")
        async def login(account: str):
            await enforce_account_and_ip_rate_limits(category, account)
            return {"ok": True}

        async def request(client_ip, account, forwarded_ip):
            transport = httpx.ASGITransport(app=app, client=(client_ip, 1))
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get(
                    f"/login/{account}",
                    headers={"X-Forwarded-For": f"{forwarded_ip}, {client_ip}"},
                )

        # Same trusted client IP cycling accounts is limited by its IP bucket.
        assert (await request("203.0.113.9", "alice", "198.51.100.10")).status_code == 200
        assert (await request("203.0.113.9", "bob", "198.51.100.10")).status_code == 429

        # New limiter: a single account is still limited when the trusted client IP changes.
        limiter = RateLimiter(redis_client=FakeRedis(), policies=_policies(limit=1))
        assert (await request("203.0.113.9", "carol", "198.51.100.11")).status_code == 200
        assert (await request("203.0.113.9", "carol", "198.51.100.12")).status_code == 429

        # The proxy's peer IP is shared, but distinct validated XFF clients remain isolated.
        limiter = RateLimiter(redis_client=FakeRedis(), policies=_policies(limit=1))
        assert (await request("203.0.113.9", "dave", "198.51.100.13")).status_code == 200
        assert (await request("203.0.113.9", "erin", "198.51.100.14")).status_code == 200

    asyncio.run(scenario())


def test_memory_fallback_has_a_lock_for_sweep_capacity_and_increment():
    limiter = RateLimiter(redis_client=FakeRedis(), policies=_policies())

    assert isinstance(limiter._memory_lock, type(threading.Lock()))


def test_rate_limit_key_uses_stable_rotatable_hmac_without_subject_text():
    async def scenario():
        redis = FakeRedis()
        first = RateLimiter(redis_client=FakeRedis(), policies=_policies(), hmac_key="current-secret")
        second = RateLimiter(redis_client=FakeRedis(), policies=_policies(), hmac_key="next-secret")
        rotating = RateLimiter(
            redis_client=redis,
            policies=_policies(limit=2),
            hmac_key="next-secret",
            hmac_previous_keys=["current-secret"],
        )

        one = first.key_for(RateLimitCategory.LOGIN, account_identifier="Alice@Example.com")
        two = first.key_for(RateLimitCategory.LOGIN, account_identifier="alice@example.com")
        changed = second.key_for(RateLimitCategory.LOGIN, account_identifier="alice@example.com")
        rotation_keys = rotating._keys_for(RateLimitCategory.LOGIN, account_identifier="alice@example.com")
        first_window = await rotating.check(RateLimitCategory.LOGIN, account_identifier="alice@example.com")
        second_window = await rotating.check(RateLimitCategory.LOGIN, account_identifier="alice@example.com")
        exceeded = await rotating.check(RateLimitCategory.LOGIN, account_identifier="alice@example.com")

        script, key_count, sent_keys, window = redis.calls[0]
        assert one == two
        assert changed != one
        assert changed == rotation_keys[0] and one in rotation_keys
        assert "Alice" not in one and "example.com" not in one
        assert key_count == 2 and sent_keys == rotation_keys and window == 60
        assert "INCR" in script and "EXPIRE" in script and "TTL" in script
        assert first_window.allowed and second_window.allowed and not exceeded.allowed
        assert {redis.counts[key] for key in rotation_keys} == {3}

    asyncio.run(scenario())


def test_memory_lock_prevents_concurrent_fallback_counter_loss():
    limiter = RateLimiter(redis_client=FakeRedis(), policies=_policies(limit=1000))
    policy = RateLimitPolicy(1000, 60)
    keys = limiter._keys_for(RateLimitCategory.LOGIN, account_identifier="threaded@example.com")
    workers = 16
    barrier = threading.Barrier(workers)
    errors = []

    def increment():
        try:
            barrier.wait()
            limiter._check_memory(keys, policy)
        except BaseException as exc:  # pragma: no cover - assertion below reports it
            errors.append(exc)

    threads = [threading.Thread(target=increment) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert limiter.memory_key_count == 1
    assert limiter._memory[keys[0]].count == workers


def test_all_public_business_get_routes_use_read_only_rate_limit():
    import api

    exempt_paths = {"/health", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    authenticated_dependencies = {get_current_user, require_admin}
    routes = []
    for route in api.app.routes:
        if "GET" not in getattr(route, "methods", set()) or route.path in exempt_paths:
            continue
        dependant = getattr(route, "dependant", None)
        calls = [dependency.call for dependency in dependant.dependencies] if dependant else []
        if not any(call in authenticated_dependencies for call in calls):
            routes.append((route.path, calls))

    assert routes
    for path, calls in routes:
        assert any(
            getattr(call, "rate_limit_category", None) == RateLimitCategory.READ_ONLY
            for call in calls
        ), f"missing READ_ONLY limiter: {path}"


def test_health_and_openapi_are_not_business_rate_limited():
    import api

    for path in ("/health", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"):
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
