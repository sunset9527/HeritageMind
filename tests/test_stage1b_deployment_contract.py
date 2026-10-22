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
    ):
        assert phrase in source
