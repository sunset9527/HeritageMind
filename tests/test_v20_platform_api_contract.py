"""Public platform routes are explicit and keep admin writes behind the API layer."""


def test_platform_routes_are_registered():
    from api import app

    paths = {route.path for route in app.routes}

    assert {"/encyclopedia", "/encyclopedia/{slug}", "/inheritors", "/inheritors/{slug}", "/admin/graph-candidates", "/admin/inheritors", "/search/ai"} <= paths
