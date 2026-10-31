"""每个 HTTP 请求的可追踪 ID 与可信客户端身份。"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4


_MAX_REQUEST_ID_LENGTH = 128
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


@dataclass(frozen=True)
class ClientIdentity:
    """限流、审计等后续组件可安全使用的请求来源。"""

    peer_ip: str
    client_ip: str


_client_identity: ContextVar[Optional[ClientIdentity]] = ContextVar(
    "client_identity", default=None
)


def get_request_id() -> Optional[str]:
    """取得当前请求 ID；请求之外返回 ``None``。"""
    return _request_id.get()


def get_client_identity() -> Optional[ClientIdentity]:
    """取得当前请求的可信客户端身份；请求之外返回 ``None``。"""
    return _client_identity.get()


def _header_values(scope: dict[str, Any], header_name: bytes) -> list[str]:
    return [
        value.decode("latin-1")
        for name, value in scope.get("headers", [])
        if name.lower() == header_name
    ]


def _is_safe_request_id(value: str) -> bool:
    return (
        0 < len(value) <= _MAX_REQUEST_ID_LENGTH
        and all(0x21 <= ord(char) <= 0x7E for char in value)
    )


def _request_id_from_scope(scope: dict[str, Any]) -> str:
    values = _header_values(scope, b"x-request-id")
    if len(values) == 1 and _is_safe_request_id(values[0]):
        return values[0]
    return str(uuid4())


def _valid_xff_client_ip(scope: dict[str, Any], peer_ip: str, settings: Any) -> str:
    """只在可信直连代理的单一、完整 XFF 链中取最左端地址。"""
    if not getattr(settings, "trust_proxy_headers", False):
        return peer_ip
    if peer_ip not in set(getattr(settings, "trusted_proxy_ips", [])):
        return peer_ip

    values = _header_values(scope, b"x-forwarded-for")
    if len(values) != 1 or any(ord(char) < 0x20 or ord(char) == 0x7F for char in values[0]):
        return peer_ip

    candidates = [item.strip() for item in values[0].split(",")]
    if not candidates or any(not item or "%" in item for item in candidates):
        return peer_ip
    try:
        for candidate in candidates:
            ip_address(candidate)
        if ip_address(candidates[-1]) != ip_address(peer_ip):
            return peer_ip
    except ValueError:
        return peer_ip
    return candidates[0]


class RequestContextMiddleware:
    """尽早建立请求上下文，且永远将请求 ID 回写到 HTTP 响应。"""

    def __init__(self, app, *, settings: Any):
        self.app = app
        self.settings = settings

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict]],
        send: Callable[[dict], Awaitable[None]],
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id_from_scope(scope)
        client = scope.get("client") or ("unknown", 0)
        peer_ip = str(client[0] or "unknown")
        identity = ClientIdentity(
            peer_ip=peer_ip,
            client_ip=_valid_xff_client_ip(scope, peer_ip, self.settings),
        )
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        state["client_identity"] = identity
        request_token = _request_id.set(request_id)
        identity_token = _client_identity.set(identity)
        response_started = False

        async def contextual_send(message: dict) -> None:
            nonlocal response_started
            if message.get("type") == "http.response.start" and not response_started:
                response_started = True
                headers = list(message.get("headers", []))
                headers = [
                    (name, value)
                    for name, value in headers
                    if name.lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, contextual_send)
        finally:
            _client_identity.reset(identity_token)
            _request_id.reset(request_token)
