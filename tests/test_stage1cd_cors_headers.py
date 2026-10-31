"""阶段 1C/1D：受控 CORS 与通用安全响应头。"""

import asyncio
from types import SimpleNamespace

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.middleware.request_context import RequestContextMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware


def _settings(**overrides):
    values = {
        "cors_allowed_origins": ["https://app.example.com"],
        "cors_allow_credentials": True,
        "app_env": "dev",
        "hsts_enabled": False,
        "require_https": False,
        "trust_proxy_headers": False,
        "trusted_proxy_ips": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _app(settings):
    app = FastAPI()

    @app.get("/ok")
    async def ok():
        return {"ok": True}

    # CORS is innermost so the security wrapper also covers OPTIONS preflights.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type", "x-request-id"],
    )
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(RequestContextMiddleware, settings=settings)
    return app


async def _request(app, method, path, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_allowed_origin_and_credentials_are_explicitly_reflected():
    response = asyncio.run(_request(
        _app(_settings()), "GET", "/ok", headers={"Origin": "https://app.example.com"}
    ))

    assert response.headers["access-control-allow-origin"] == "https://app.example.com"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_disallowed_origin_is_not_granted_cors_access():
    response = asyncio.run(_request(
        _app(_settings()), "GET", "/ok", headers={"Origin": "https://evil.example"}
    ))

    assert "access-control-allow-origin" not in response.headers


def test_allowed_preflight_includes_security_headers_and_disallowed_preflight_is_denied():
    app = _app(_settings())
    headers = {
        "Origin": "https://app.example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    allowed = asyncio.run(_request(app, "OPTIONS", "/ok", headers=headers))
    denied = asyncio.run(_request(
        app,
        "OPTIONS",
        "/ok",
        headers={**headers, "Origin": "https://evil.example"},
    ))

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://app.example.com"
    assert allowed.headers["x-content-type-options"] == "nosniff"
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
    assert denied.headers["x-content-type-options"] == "nosniff"


def test_requests_without_origin_are_not_treated_as_cors_requests():
    response = asyncio.run(_request(_app(_settings()), "GET", "/ok"))

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_security_headers_are_present_and_hsts_requires_all_production_switches():
    dev = asyncio.run(_request(_app(_settings()), "GET", "/ok"))
    hsts = asyncio.run(_request(_app(_settings(app_env="prod", hsts_enabled=True, require_https=True)), "GET", "/ok"))
    not_hsts = asyncio.run(_request(_app(_settings(app_env="prod", hsts_enabled=True, require_https=False)), "GET", "/ok"))

    assert dev.headers["x-content-type-options"] == "nosniff"
    assert dev.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert dev.headers["x-frame-options"] == "DENY"
    assert dev.headers["permissions-policy"] == "geolocation=(), camera=(), microphone=()"
    assert "frame-ancestors 'none'" in dev.headers["content-security-policy"]
    assert "strict-transport-security" not in dev.headers
    assert hsts.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert "strict-transport-security" not in not_hsts.headers
