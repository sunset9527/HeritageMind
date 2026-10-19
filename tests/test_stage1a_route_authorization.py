"""阶段 1A 敏感路由的后端权限契约。"""

import pytest

from api import app
from fastapi import HTTPException

from src.deps import get_current_user, require_admin
from src.models.user import User


def _route(path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method.upper() in getattr(route, "methods", set()):
            return route
    return None


def _direct_dependencies(route) -> set:
    return {dependency.call for dependency in route.dependant.dependencies}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/prompts"),
        ("POST", "/prompts"),
        ("GET", "/prompts/{prompt_id}"),
        ("PUT", "/prompts/{prompt_id}"),
        ("DELETE", "/prompts/{prompt_id}"),
        ("POST", "/media/upload"),
        ("DELETE", "/media/{media_id}"),
        ("PUT", "/media/{media_id}/status"),
        ("GET", "/media/{media_id}/transcript"),
        ("POST", "/media/{media_id}/transcribe"),
        ("POST", "/knowledge/rebuild-embeddings"),
        ("POST", "/search/index-images"),
        ("POST", "/search/audio/index"),
        ("POST", "/documents/upload"),
    ],
)
def test_sensitive_route_requires_admin(method: str, path: str):
    route = _route(path, method)

    assert route is not None, f"missing route: {method} {path}"
    assert require_admin in _direct_dependencies(route), f"missing admin dependency: {method} {path}"


def test_admin_media_list_exists_and_requires_admin():
    route = _route("/admin/media", "GET")

    assert route is not None
    assert require_admin in _direct_dependencies(route)


def test_public_media_list_remains_anonymous_read_only():
    route = _route("/media/list", "GET")

    assert route is not None
    assert require_admin not in _direct_dependencies(route)


def test_admin_dependency_preserves_401_and_403_semantics():
    with pytest.raises(HTTPException) as anonymous_error:
        get_current_user(token=None, db=None)
    assert anonymous_error.value.status_code == 401
    assert anonymous_error.value.headers == {"WWW-Authenticate": "Bearer"}

    regular_user = User(
        id=1,
        username="regular",
        email="regular@example.com",
        password_hash="hash",
        role="user",
    )
    with pytest.raises(HTTPException) as forbidden_error:
        require_admin(regular_user)
    assert forbidden_error.value.status_code == 403

    admin = User(
        id=2,
        username="admin",
        email="admin@example.com",
        password_hash="hash",
        role="admin",
    )
    assert require_admin(admin) is admin
