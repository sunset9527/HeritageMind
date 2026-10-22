"""阶段 1C/1D：生产启动门禁与外部模型 URL 策略。"""

import pytest

from config import Settings
from src.services.startup_validation import StartupValidationError, validate_startup_settings
from src.services.url_policy import BaseUrlPolicyError, validate_model_base_url


def production_settings(**overrides):
    values = {
        "app_env": "prod",
        "jwt_secret_key": "nQd1F9yJ7xT3mL8pR2vK6cW4sZ9aB5eH",
        "database_url": "mysql+pymysql://app_user:strong-db-password@db.example.com:3306/heritagemind",
        "deepseek_api_key": "live-model-key-9f31c7a2",
        "cors_allowed_origins": ["https://app.example.com"],
        "allowed_model_base_url_hosts": ["api.deepseek.com", "open.bigmodel.cn"],
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def issue_codes(settings):
    with pytest.raises(StartupValidationError) as raised:
        validate_startup_settings(settings)
    return {issue.code for issue in raised.value.issues}


@pytest.mark.parametrize(
    "secret",
    ["", "example-jwt-secret", "short-secret", "heritagemind-dev-secret-change-in-production"],
)
def test_production_rejects_missing_example_or_short_jwt_secret(secret):
    assert "jwt_secret_unsafe" in issue_codes(production_settings(jwt_secret_key=secret))


def test_production_rejects_known_default_database_password_without_echoing_url():
    settings = production_settings(
        database_url="mysql+pymysql://root:123456@localhost:3306/heritagemind"
    )

    with pytest.raises(StartupValidationError) as raised:
        validate_startup_settings(settings)

    assert "database_default_password" in {issue.code for issue in raised.value.issues}
    assert "123456" not in str(raised.value)


@pytest.mark.parametrize("model_key", ["", "YOUR_API_KEY"])
def test_production_rejects_enabled_server_answers_with_empty_or_placeholder_model_key(model_key):
    assert "server_model_key_unsafe" in issue_codes(production_settings(deepseek_api_key=model_key))


def test_production_rejects_wildcard_cors_and_credentials_without_origins():
    assert "cors_wildcard_forbidden" in issue_codes(
        production_settings(cors_allowed_origins=["*"])
    )
    assert "cors_credentials_without_origins" in issue_codes(
        production_settings(cors_allowed_origins=[], cors_allow_credentials=True)
    )


def test_production_rejects_anonymous_queries_without_an_available_server_model():
    settings = production_settings(
        anonymous_query_enabled=True,
        server_answer_enabled=False,
    )

    assert "anonymous_query_requires_server_model" in issue_codes(settings)


def test_production_rejects_hsts_without_real_https():
    assert "hsts_requires_https" in issue_codes(
        production_settings(hsts_enabled=True, require_https=False)
    )


def test_production_rejects_private_model_base_url():
    settings = production_settings(deepseek_base_url="http://127.0.0.1:8000/v1")

    assert "model_base_url_forbidden" in issue_codes(settings)


def test_production_settings_that_pass_all_gates_are_accepted():
    validate_startup_settings(production_settings())


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://user:pass@api.deepseek.com/v1",
        "https://127.0.0.1/v1",
        "https://169.254.169.254/latest/meta-data",
        "https://10.1.2.3/v1",
        "https://api.deepseek.com:6379/v1",
    ],
)
def test_model_base_url_policy_rejects_dangerous_destinations(url):
    with pytest.raises(BaseUrlPolicyError):
        validate_model_base_url(
            url,
            app_env="prod",
            allowed_hosts=["api.deepseek.com"],
        )


def test_development_allows_local_http_only_with_explicit_switch():
    with pytest.raises(BaseUrlPolicyError):
        validate_model_base_url(
            "http://localhost:8000/v1",
            app_env="dev",
            allowed_hosts=[],
        )

    assert validate_model_base_url(
        "http://localhost:8000/v1",
        app_env="dev",
        allowed_hosts=[],
        allow_localhost_http=True,
    ) == "http://localhost:8000/v1"
