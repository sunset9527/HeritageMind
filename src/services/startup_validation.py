"""生产启动前的纯配置门禁；调用方决定何时把异常转为进程退出。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List
from urllib.parse import urlsplit

from config import Settings
from src.services.url_policy import BaseUrlPolicyError, validate_model_base_url


@dataclass(frozen=True)
class StartupValidationIssue:
    """不会携带密钥、URL 或密码原文的可安全记录问题。"""

    code: str
    field: str
    message: str


class StartupValidationError(RuntimeError):
    """生产配置不能安全启动时抛出。"""

    def __init__(self, issues: List[StartupValidationIssue]):
        self.issues = tuple(issues)
        super().__init__(
            "启动配置校验失败："
            + "; ".join(f"{issue.code} ({issue.field})" for issue in self.issues)
        )


def _is_placeholder(value: str) -> bool:
    candidate = value.strip().lower()
    return not candidate or any(
        marker in candidate
        for marker in ("placeholder", "your_api", "your-api", "changeme", "example", "dummy")
    )


def _unsafe_jwt_secret(value: str) -> bool:
    candidate = value.strip().lower()
    return (
        len(value.strip()) < 32
        or candidate == "heritagemind-dev-secret-change-in-production"
        or _is_placeholder(value)
    )


def _unsafe_rate_limit_hmac_key(value: str) -> bool:
    candidate = value.strip().lower()
    return (
        len(value.strip()) < 32
        or candidate == "heritagemind-dev-rate-limit-hmac-change-in-production"
        or _is_placeholder(value)
    )


def _has_known_default_database_password(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return parsed.password in {"123456", "password", "root"}


def collect_startup_issues(settings: Settings) -> List[StartupValidationIssue]:
    """收集生产环境门禁问题，开发和测试配置保持可用。"""
    if settings.app_env != "prod":
        return []

    issues: List[StartupValidationIssue] = []

    def add(code: str, field: str, message: str) -> None:
        issues.append(StartupValidationIssue(code=code, field=field, message=message))

    if _unsafe_jwt_secret(settings.jwt_secret_key):
        add("jwt_secret_unsafe", "jwt_secret_key", "JWT 密钥缺失、示例或长度不足")
    if _unsafe_rate_limit_hmac_key(settings.rate_limit_hmac_key):
        add(
            "rate_limit_hmac_key_unsafe",
            "rate_limit_hmac_key",
            "限流摘要密钥缺失、示例或长度不足",
        )
    for previous_key in settings.rate_limit_hmac_previous_keys:
        if _unsafe_rate_limit_hmac_key(previous_key):
            add(
                "rate_limit_hmac_previous_key_unsafe",
                "rate_limit_hmac_previous_keys",
                "限流轮换密钥缺失、示例或长度不足",
            )
    if _has_known_default_database_password(settings.database_url):
        add("database_default_password", "database_url", "数据库使用了已知默认密码")
    if settings.server_answer_enabled and _is_placeholder(settings.deepseek_api_key):
        add("server_model_key_unsafe", "deepseek_api_key", "服务器问答已启用但模型密钥不可用")
    if "*" in settings.cors_allowed_origins:
        add("cors_wildcard_forbidden", "cors_allowed_origins", "生产环境不允许 CORS 通配符")
    if settings.cors_allow_credentials and not settings.cors_allowed_origins:
        add(
            "cors_credentials_without_origins",
            "cors_allowed_origins",
            "启用 CORS 凭据时必须配置来源",
        )
    if settings.hsts_enabled and not settings.require_https:
        add("hsts_requires_https", "require_https", "启用 HSTS 时必须启用真实 HTTPS")

    for field, value in (
        ("deepseek_base_url", settings.deepseek_base_url),
        ("zhipu_base_url", settings.zhipu_base_url),
    ):
        try:
            validate_model_base_url(
                value,
                app_env=settings.app_env,
                allowed_hosts=settings.allowed_model_base_url_hosts,
                allow_localhost_http=settings.allow_localhost_model_base_url,
            )
        except BaseUrlPolicyError:
            add("model_base_url_forbidden", field, "模型 Base URL 不符合生产安全策略")

    server_model_available = settings.server_answer_enabled and not _is_placeholder(
        settings.deepseek_api_key
    )
    if settings.anonymous_query_enabled and (
        not server_model_available or settings.anonymous_query_quota <= 0
    ):
        add(
            "anonymous_query_requires_server_model",
            "anonymous_query_enabled",
            "匿名问答需要可用服务器模型和正数匿名配额",
        )
    return issues


def validate_startup_settings(settings: Settings) -> None:
    """生产不安全配置抛出专用异常；开发/测试保持无侵入。"""
    issues = collect_startup_issues(settings)
    if issues:
        raise StartupValidationError(issues)
