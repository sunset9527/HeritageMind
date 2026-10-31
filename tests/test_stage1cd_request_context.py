"""阶段 1C/1D：请求追踪、可信代理边界及 API 启动门禁。"""

import asyncio
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, HTTPException

from config import Settings
from src.middleware.request_context import (
    RequestContextMiddleware,
    get_client_identity,
    get_request_id,
)
from src.middleware.request_size import RequestBodyLimitMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware
from src.services.startup_validation import StartupValidationError


def _settings(**overrides):
    values = {
        "trust_proxy_headers": False,
        "trusted_proxy_ips": [],
        "app_env": "dev",
        "hsts_enabled": False,
        "require_https": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _app(settings=None):
    app = FastAPI()
    settings = settings or _settings()

    @app.get("/context")
    async def context():
        identity = get_client_identity()
        return {
            "request_id": get_request_id(),
            "client_ip": identity.client_ip if identity else None,
            "peer_ip": identity.peer_ip if identity else None,
        }

    @app.get("/error")
    async def error():
        raise HTTPException(status_code=418, detail="expected")

    @app.get("/boom")
    async def boom():
        raise RuntimeError("unexpected")

    # add_middleware is LIFO.  The transparent context/security wrappers must
    # sit outside the request-body guard so 413 responses also carry headers.
    app.add_middleware(RequestBodyLimitMiddleware, max_bytes=3)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(RequestContextMiddleware, settings=settings)
    return app


async def _request(app, method, path, *, raise_app_exceptions=True, **kwargs):
    transport = httpx.ASGITransport(
        app=app,
        client=("198.51.100.7", 4321),
        raise_app_exceptions=raise_app_exceptions,
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_missing_request_id_is_uuid_and_context_is_exposed():
    response = asyncio.run(_request(_app(), "GET", "/context"))

    assert response.status_code == 200
    assert response.headers["x-request-id"] == response.json()["request_id"]
    assert uuid.UUID(response.headers["x-request-id"])
    assert response.json()["client_ip"] == "198.51.100.7"
    assert response.json()["peer_ip"] == "198.51.100.7"


def test_valid_external_request_id_is_preserved_but_unsafe_values_are_replaced():
    app = _app()
    accepted = asyncio.run(_request(app, "GET", "/context", headers={"X-Request-ID": "trace-42"}))
    rejected = asyncio.run(_request(app, "GET", "/context", headers={"X-Request-ID": "bad\x7fid"}))
    too_long = asyncio.run(_request(app, "GET", "/context", headers={"X-Request-ID": "a" * 129}))

    assert accepted.headers["x-request-id"] == "trace-42"
    assert accepted.json()["request_id"] == "trace-42"
    assert rejected.headers["x-request-id"] != "bad\x7fid"
    assert uuid.UUID(rejected.headers["x-request-id"])
    assert uuid.UUID(too_long.headers["x-request-id"])


def test_untrusted_peer_cannot_spoof_client_ip_through_xff():
    response = asyncio.run(_request(
        _app(_settings(trust_proxy_headers=True, trusted_proxy_ips=["203.0.113.9"])),
        "GET",
        "/context",
        headers={"X-Forwarded-For": "203.0.113.42"},
    ))

    assert response.json()["client_ip"] == "198.51.100.7"


def test_only_configured_direct_proxy_can_supply_valid_leftmost_xff_ip():
    app = _app(_settings(trust_proxy_headers=True, trusted_proxy_ips=["203.0.113.9"]))

    async def request_from_trusted_proxy():
        transport = httpx.ASGITransport(app=app, client=("203.0.113.9", 4321))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/context", headers={"X-Forwarded-For": "198.51.100.42, 203.0.113.9"})

    response = asyncio.run(request_from_trusted_proxy())

    assert response.json()["client_ip"] == "198.51.100.42"
    assert response.json()["peer_ip"] == "203.0.113.9"


def test_invalid_xff_from_trusted_proxy_falls_back_to_peer():
    app = _app(_settings(trust_proxy_headers=True, trusted_proxy_ips=["203.0.113.9"]))

    async def request_from_trusted_proxy():
        transport = httpx.ASGITransport(app=app, client=("203.0.113.9", 4321))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/context", headers={"X-Forwarded-For": "not-an-ip, 203.0.113.9"})

    response = asyncio.run(request_from_trusted_proxy())

    assert response.json()["client_ip"] == "203.0.113.9"


def test_request_context_and_security_headers_cover_body_limit_and_http_errors():
    app = _app()
    oversized = asyncio.run(_request(app, "POST", "/context", content=b"1234"))
    error = asyncio.run(_request(app, "GET", "/error"))
    unhandled = asyncio.run(_request(app, "GET", "/boom", raise_app_exceptions=False))

    assert oversized.status_code == 413
    assert oversized.headers["x-request-id"]
    assert oversized.headers["x-content-type-options"] == "nosniff"
    assert error.status_code == 418
    assert error.headers["x-request-id"]
    assert error.headers["x-content-type-options"] == "nosniff"
    assert unhandled.status_code == 500
    assert unhandled.headers["x-request-id"]
    assert unhandled.headers["x-content-type-options"] == "nosniff"


def test_api_stack_keeps_body_limit_as_first_body_reader_and_covers_its_413(monkeypatch):
    """验证真实 api.py 的 LIFO 接线，而非只验证小型测试应用。"""
    import api

    classes = [middleware.cls.__name__ for middleware in api.app.user_middleware]
    assert classes[:4] == [
        "RequestContextMiddleware",
        "SecurityHeadersMiddleware",
        "RequestBodyLimitMiddleware",
        "CORSMiddleware",
    ]

    body_limit = next(
        middleware
        for middleware in api.app.user_middleware
        if middleware.cls.__name__ == "RequestBodyLimitMiddleware"
    )
    old_limit = body_limit.kwargs["max_bytes"]
    old_stack = api.app.middleware_stack
    try:
        monkeypatch.setitem(body_limit.kwargs, "max_bytes", 3)
        api.app.middleware_stack = None
        response = asyncio.run(_request(api.app, "POST", "/health", content=b"1234"))
    finally:
        body_limit.kwargs["max_bytes"] = old_limit
        api.app.middleware_stack = old_stack

    assert response.status_code == 413
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_api_lifespan_rejects_invalid_production_settings_before_expensive_initialization(monkeypatch):
    import api

    invalid = Settings(_env_file=None, app_env="prod")
    monkeypatch.setattr(api, "settings", invalid)
    monkeypatch.setattr(api, "init_db", lambda: pytest.fail("init_db must not run"))

    async def start():
        async with api.lifespan(api.app):
            pytest.fail("invalid production settings must not start")

    with pytest.raises(StartupValidationError):
        asyncio.run(start())
