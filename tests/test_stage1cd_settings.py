"""阶段 1C/1D：生产安全配置的纯 Settings 校验。"""

import pytest
from pydantic import ValidationError

from config import Settings


def test_security_defaults_are_explicit_and_safe_for_future_middleware():
    settings = Settings(_env_file=None)

    assert settings.app_env == "dev"
    assert settings.cors_allowed_origins == []
    assert settings.cors_allow_credentials is False
    assert settings.anonymous_query_enabled is False
    assert settings.allowed_model_base_url_hosts == [
        "api.deepseek.com",
        "open.bigmodel.cn",
    ]


def test_list_settings_accept_comma_separated_environment_style_values():
    settings = Settings(
        _env_file=None,
        cors_allowed_origins="https://app.example.com, https://admin.example.com",
        trusted_proxy_ips="203.0.113.5, 2001:db8::5",
        allowed_model_base_url_hosts="models.example.com,api.example.com",
    )

    assert settings.cors_allowed_origins == [
        "https://app.example.com",
        "https://admin.example.com",
    ]
    assert settings.trusted_proxy_ips == ["203.0.113.5", "2001:db8::5"]
    assert settings.allowed_model_base_url_hosts == [
        "models.example.com",
        "api.example.com",
    ]


def test_list_settings_accept_json_arrays():
    settings = Settings(
        _env_file=None,
        cors_allowed_origins='["https://app.example.com"]',
        allowed_model_base_url_hosts='["models.example.com"]',
    )

    assert settings.cors_allowed_origins == ["https://app.example.com"]
    assert settings.allowed_model_base_url_hosts == ["models.example.com"]


@pytest.mark.parametrize("app_env", ["dev", "test", "prod"])
def test_environment_contract_accepts_only_short_environment_names(app_env):
    assert Settings(_env_file=None, app_env=app_env).app_env == app_env


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("app_env", "development"),
        ("app_env", "production"),
        ("app_env", "staging"),
        ("anonymous_query_window_seconds", 0),
        ("authenticated_query_quota", 0),
        ("server_model_timeout_seconds", 0),
        ("request_concurrency_limit", 0),
        ("cors_allowed_origins", "https://app.example.com,,https://admin.example.com"),
        ("allowed_model_base_url_hosts", "https://models.example.com"),
        ("deepseek_base_url", "file:///tmp/model"),
        ("zhipu_base_url", "https://user:pass@models.example.com/v1"),
    ],
)
def test_invalid_security_settings_fail_during_initialization(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})
