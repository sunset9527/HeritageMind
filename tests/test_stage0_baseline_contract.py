"""阶段 0 的版本、接口、前端与文档口径契约。"""

import asyncio
from pathlib import Path

from api import app, root


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_root_version_matches_fastapi_metadata():
    payload = asyncio.run(root())

    assert payload["version"] == app.version


def test_openapi_description_uses_dynamic_statistics_endpoints():
    description = app.description or ""

    assert "23 种" not in description
    assert "55,000" not in description
    assert "65 节点" not in description
    assert "/dashboard/summary" in description
    assert "/documents/summary" in description
    assert "/graph/stats" in description


def test_legacy_query_and_upload_routes_are_removed():
    paths = app.openapi()["paths"]

    assert "/query/simple" not in paths
    assert "/upload" not in paths
    assert "/query" in paths
    assert "/documents/upload" in paths


def test_frontend_client_does_not_expose_legacy_simple_query():
    query_client = (REPO_ROOT / "frontend" / "src" / "api" / "query.ts").read_text(
        encoding="utf-8"
    )

    assert "sendQuerySimple" not in query_client
    assert "/query/simple" not in query_client


def test_streamlit_runtime_is_removed_from_current_project_files():
    current_files = [
        REPO_ROOT / "Dockerfile",
        REPO_ROOT / "docker-compose.yml",
        REPO_ROOT / "config.py",
        REPO_ROOT / "README.md",
        REPO_ROOT / "deploy" / "README.md",
    ]

    for path in current_files:
        assert "streamlit" not in path.read_text(encoding="utf-8").lower(), path


def test_default_compose_frontend_is_vue_development_service():
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "  frontend:\n    build:\n      context: ./frontend\n      target: development" in compose
    assert '      - "5173:5173"' in compose
    assert "  vue-frontend:" not in compose


def test_readme_distinguishes_delivery_states_and_statistics_scopes():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    for status_label in ("已实现", "占位或降级", "依赖外部配置", "尚未上线"):
        assert status_label in readme
    for scope_label in (
        "官方名录覆盖",
        "深度资料覆盖",
        "图片覆盖",
        "活动图书片段",
        "图谱规模",
        "检索指标",
    ):
        assert scope_label in readme
