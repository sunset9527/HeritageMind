"""所有 HTTP 响应共享的浏览器安全响应头。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable


_BASE_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"x-frame-options", b"DENY"),
    (b"permissions-policy", b"geolocation=(), camera=(), microphone=()"),
    (
        b"content-security-policy",
        b"default-src 'self'; base-uri 'self'; frame-ancestors 'none'; "
        b"object-src 'none'; form-action 'self'; "
        b"script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        b"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        b"img-src 'self' data: https://fastapi.tiangolo.com",
    ),
)
_DOCUMENT_HEADERS = _BASE_HEADERS[:-1] + (
    (
        b"content-security-policy",
        b"default-src 'self'; base-uri 'self'; frame-ancestors 'none'; "
        b"object-src 'none'; form-action 'self'; "
        b"script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        b"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        b"font-src 'self' https://fonts.gstatic.com; "
        b"img-src 'self' data: https://fastapi.tiangolo.com",
    ),
)
_DOCUMENT_PATHS = frozenset({"/docs", "/redoc"})
_HSTS_HEADER = (b"strict-transport-security", b"max-age=31536000; includeSubDomains")


class SecurityHeadersMiddleware:
    """在响应开始时覆写安全头，覆盖路由错误及 CORS 预检响应。"""

    def __init__(self, app, *, settings: Any):
        self.app = app
        self.settings = settings

    def _headers(self, path: str) -> tuple[tuple[bytes, bytes], ...]:
        headers = _DOCUMENT_HEADERS if path in _DOCUMENT_PATHS else _BASE_HEADERS
        if (
            getattr(self.settings, "app_env", None) == "prod"
            and getattr(self.settings, "hsts_enabled", False)
            and getattr(self.settings, "require_https", False)
        ):
            headers += (_HSTS_HEADER,)
        return headers

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict]],
        send: Callable[[dict], Awaitable[None]],
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers_to_apply = self._headers(scope.get("path", ""))
        header_names = {name for name, _ in headers_to_apply}

        async def secure_send(message: dict) -> None:
            if message.get("type") == "http.response.start":
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() not in header_names
                ]
                headers.extend(headers_to_apply)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, secure_send)
