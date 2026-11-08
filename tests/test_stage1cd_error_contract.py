import asyncio
import inspect
from types import SimpleNamespace

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from src.middleware.request_context import RequestContextMiddleware
from src.services.error_protocol import (
    _unexpected_exception_handler,
    _validation_exception_handler,
    install_error_handlers,
    sse_error_event,
)


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(
        RequestContextMiddleware,
        settings=SimpleNamespace(trust_proxy_headers=False, trusted_proxy_ips=[]),
    )

    @app.get("/forbidden")
    async def forbidden():
        raise HTTPException(status_code=403, detail="internal policy says no")

    @app.get("/validation")
    async def validation(limit: int):
        return {"limit": limit}

    @app.get("/boom")
    async def boom():
        raise RuntimeError(
            "api_key=stage1-secret at C:\\Users\\operator\\private.txt"
        )

    return app


async def _request(path: str):
    transport = httpx.ASGITransport(app=_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, headers={"X-Request-ID": "trace-error-42"})


def test_http_exception_uses_stable_forbidden_error_envelope():
    response = asyncio.run(_request("/forbidden"))

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "forbidden",
            "message": "无权执行此操作",
            "request_id": "trace-error-42",
        }
    }


def test_validation_error_does_not_reflect_user_input():
    response = asyncio.run(_request("/validation?limit=api_key%3Dstage1-secret"))

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "请求参数不符合要求",
            "request_id": "trace-error-42",
        }
    }
    assert "stage1-secret" not in response.text


def test_unknown_error_is_redacted_and_uses_internal_error_envelope():
    response = asyncio.run(_request("/boom"))

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "服务暂时无法处理该请求，请稍后重试",
            "request_id": "trace-error-42",
        }
    }
    assert "stage1-secret" not in response.text
    assert "private.txt" not in response.text


def test_api_app_installs_the_global_error_handlers():
    import api

    assert api.app.exception_handlers[RequestValidationError] is _validation_exception_handler
    assert api.app.exception_handlers[Exception] is _unexpected_exception_handler


def test_sse_error_uses_the_same_code_message_and_request_id_fields():
    assert sse_error_event(
        "dependency_unavailable",
        "当前服务暂不可用，请稍后重试",
        request_id="trace-error-42",
    ) == {
        "event": "error",
        "step": "error",
        "msg": "当前服务暂不可用，请稍后重试",
        "code": "dependency_unavailable",
        "request_id": "trace-error-42",
    }


def test_stream_route_uses_the_shared_sse_error_contract():
    import api

    assert "sse_error_event(" in inspect.getsource(api.query_stream)
