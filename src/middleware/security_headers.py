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
_HSTS_HEADER = (b"strict-transport-security", b"max-age=31536000; includeSubDomains")


class SecurityHeadersMiddleware:
    """在响应开始时覆写安全头，覆盖路由错误及 CORS 预检响应。"""

    def __init__(self, app, *, settings: Any):
        self.app = app
        self.settings = settings

    def _headers(self) -> tuple[tuple[bytes, bytes], ...]:
        headers = _BASE_HEADERS
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

        header_names = {name for name, _ in self._headers()}

        async def secure_send(message: dict) -> None:
            if message.get("type") == "http.response.start":
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() not in header_names
                ]
                headers.extend(self._headers())
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, secure_send)
