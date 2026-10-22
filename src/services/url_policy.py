"""外部模型 Base URL 的纯本地安全策略；不执行 DNS 或网络请求。"""

from __future__ import annotations

from ipaddress import ip_address
from typing import Iterable
from urllib.parse import urlsplit


class BaseUrlPolicyError(ValueError):
    """模型 Base URL 不符合安全策略。"""


_PUBLIC_HTTPS_PORTS = {443, 8443}


def _normalise_host(host: str) -> str:
    return host.rstrip(".").lower()


def _is_non_public_ip(host: str) -> bool:
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_unspecified
        or address.is_multicast
        or address.is_reserved
    )


def validate_model_base_url(
    value: str,
    *,
    app_env: str,
    allowed_hosts: Iterable[str],
    allow_localhost_http: bool = False,
) -> str:
    """验证模型终端，返回原 URL，且绝不解析域名或发起网络请求。"""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise BaseUrlPolicyError("模型 Base URL 格式无效") from exc

    if not parsed.hostname or parsed.username or parsed.password:
        raise BaseUrlPolicyError("模型 Base URL 不允许包含凭据")

    host = _normalise_host(parsed.hostname)
    is_localhost = host == "localhost" or host.endswith(".localhost")
    if (
        app_env == "dev"
        and allow_localhost_http
        and is_localhost
        and parsed.scheme == "http"
    ):
        return value

    if parsed.scheme != "https":
        raise BaseUrlPolicyError("模型 Base URL 必须使用 HTTPS")
    if is_localhost or _is_non_public_ip(host):
        raise BaseUrlPolicyError("模型 Base URL 不允许指向本机或非公网地址")
    if port not in {None, *_PUBLIC_HTTPS_PORTS}:
        raise BaseUrlPolicyError("模型 Base URL 端口不在允许范围内")

    if app_env == "prod":
        permitted_hosts = {_normalise_host(item) for item in allowed_hosts}
        if host not in permitted_hosts:
            raise BaseUrlPolicyError("模型 Base URL 主机不在允许列表")
    return value
