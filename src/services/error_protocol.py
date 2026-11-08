"""Install a safe, stable HTTP error contract on a FastAPI application."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.middleware.request_context import get_request_id
from src.services.error_sanitizer import redact_sensitive_text


logger = logging.getLogger(__name__)


_STATUS_ERRORS: dict[int, tuple[str, str]] = {
    400: ("bad_request", "请求参数不符合要求"),
    401: ("unauthenticated", "请先登录后再试"),
    403: ("forbidden", "无权执行此操作"),
    404: ("not_found", "请求的资源不存在"),
    409: ("conflict", "当前资源状态不允许此操作"),
    422: ("validation_error", "请求参数不符合要求"),
    429: ("rate_limit_exceeded", "请求过于频繁，请稍后再试"),
    503: ("dependency_unavailable", "当前服务暂不可用，请稍后重试"),
}

_PUBLIC_DETAIL_ERRORS: dict[str, tuple[str, str]] = {
    "busy": ("busy", "服务繁忙，请稍后重试"),
    "rate_limit_unavailable": ("rate_limit_unavailable", "服务繁忙，请稍后再试"),
    "rate_limit_exceeded": ("rate_limit_exceeded", "请求过于频繁，请稍后再试"),
}


def error_envelope(code: str, message: str, *, request_id: str | None = None) -> dict[str, dict[str, str]]:
    """Build the only public shape used for HTTP errors."""
    error: dict[str, str] = {"code": code, "message": message}
    if request_id:
        error["request_id"] = request_id
    return {"error": error}


def sse_error_event(
    code: str,
    message: str,
    *,
    request_id: str | None = None,
) -> dict[str, str]:
    """Build the error event shape used by streaming endpoints."""
    event = {"event": "error", "step": "error", "msg": message, "code": code}
    if request_id:
        event["request_id"] = request_id
    return event


def _request_id(request: Request) -> str | None:
    return get_request_id() or getattr(request.state, "request_id", None)


def _http_error(exc: StarletteHTTPException) -> tuple[str, str]:
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code")
        if isinstance(code, str) and code in _PUBLIC_DETAIL_ERRORS:
            return _PUBLIC_DETAIL_ERRORS[code]
    return _STATUS_ERRORS.get(exc.status_code, ("request_error", "请求未能完成，请稍后重试"))


def _response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_envelope(code, message, request_id=_request_id(request)),
        headers=headers,
    )


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = _http_error(exc)
    return _response(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
        headers=exc.headers,
    )


async def _validation_exception_handler(request: Request, _exc: RequestValidationError) -> JSONResponse:
    return _response(
        request,
        status_code=422,
        code="validation_error",
        message="请求参数不符合要求",
    )


async def _unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled request error request_id=%s error=%s",
        _request_id(request),
        redact_sensitive_text(exc),
    )
    return _response(
        request,
        status_code=500,
        code="internal_error",
        message="服务暂时无法处理该请求，请稍后重试",
    )


def install_error_handlers(app: FastAPI) -> None:
    """Register global handlers without exposing raw exception details."""
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unexpected_exception_handler)
