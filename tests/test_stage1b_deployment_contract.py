"""独立 worker、共享运行时卷和代理上传边界的静态部署契约。"""

from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def _compose(name: str):
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


def test_dockerfile_has_separate_worker_dependencies_and_entrypoint():
    source = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements.worker.txt" in source
    assert "AS worker" in source
    assert 'python", "-m", "src.workers.upload_worker"' in source


def test_container_healthchecks_use_liveness_not_readiness():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    development = _compose("docker-compose.yml")

    assert "/health/live" in dockerfile
    assert "/health/live" in development["services"]["api"]["healthcheck"]["test"][-1]


def test_development_and_production_compose_have_worker_redis_and_scoped_volumes():
    for filename in ("docker-compose.yml", "docker-compose.production.yml"):
        compose = _compose(filename)
        assert {"api", "worker", "redis"}.issubset(compose["services"])
        worker = compose["services"]["worker"]
        assert "redis" in worker["depends_on"]
        mounts = [str(item) for item in worker["volumes"]]
        assert any("/app/data/uploads" in item for item in mounts)
        assert any("/app/data/media" in item for item in mounts)
        assert any("/app/data/index_versions" in item for item in mounts)
        assert all(not item.endswith(":/app/data") for item in mounts)


def test_both_nginx_configs_enforce_52m_and_upload_timeout():
    for filename in ("frontend/nginx.conf", "deploy/nginx/heritagemind.conf.template"):
        source = (ROOT / filename).read_text(encoding="utf-8").lower()
        assert "client_max_body_size 52m" in source
        assert "proxy_send_timeout 300s" in source


def test_production_nginx_template_is_mounted_for_envsubst():
    compose = _compose("docker-compose.production.yml")
    nginx = compose["services"]["nginx"]
    mounts = [str(item) for item in nginx["volumes"]]
    assert any("/etc/nginx/templates/default.conf.template" in item for item in mounts)
    assert {"DOMAIN", "SSL_CERTIFICATE", "SSL_CERTIFICATE_KEY"}.issubset(
        nginx["environment"]
    )


def test_production_compose_requires_database_jwt_and_server_model_secrets():
    source = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")

    for required_expression in (
        "${MYSQL_PASSWORD:?MYSQL_PASSWORD must be set}",
        "${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD must be set}",
        "${JWT_SECRET_KEY:?JWT_SECRET_KEY must be set}",
        "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY must be set}",
        "${RATE_LIMIT_HMAC_KEY:?RATE_LIMIT_HMAC_KEY must be set}",
    ):
        assert required_expression in source
    assert "${MYSQL_PASSWORD}" not in source
    assert "${MYSQL_ROOT_PASSWORD}" not in source
    assert "${JWT_SECRET_KEY}" not in source
    assert "${DEEPSEEK_API_KEY}" not in source


def test_production_compose_pins_api_and_worker_to_production_mode():
    compose = _compose("docker-compose.production.yml")

    for service_name in ("api", "worker"):
        assert compose["services"][service_name]["environment"]["APP_ENV"] == "prod"


def test_frontend_build_context_excludes_test_cache_and_dependency_artifacts():
    source = (ROOT / "frontend" / ".dockerignore").read_text(encoding="utf-8")

    assert ".pytest_cache/" in source
    assert "node_modules/" in source
    assert "dist/" in source


def test_api_build_context_excludes_pytest_temporary_artifacts():
    source = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    for artifact in (
        ".pytest-tmp*/",
        "frontend/.pytest_cache/",
        "frontend/node_modules/",
        "frontend/dist/",
    ):
        assert artifact in source


def test_deployment_docs_cover_migration_worker_health_failure_and_rollback():
    source = (
        (ROOT / "README.md").read_text(encoding="utf-8")
        + (ROOT / "deploy/README.md").read_text(encoding="utf-8")
    ).lower()
    for phrase in (
        "python -m alembic upgrade head",
        "python -m src.workers.upload_worker",
        "/health",
        "failed",
        "rollback",
        "rate_limit_hmac_key",
    ):
        assert phrase in source
