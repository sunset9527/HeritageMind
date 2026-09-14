"""Public platform routes are explicit and keep admin writes behind the API layer."""


def test_platform_routes_are_registered():
    from api import app

    paths = {route.path for route in app.routes}

    assert {
        "/encyclopedia", "/encyclopedia/{slug}", "/inheritors", "/inheritors/{slug}",
        "/admin/crafts", "/admin/crafts/{craft_id}", "/admin/crafts/{craft_id}/publish",
        "/admin/inheritors", "/admin/inheritors/{profile_id}", "/admin/inheritors/{profile_id}/publish",
        "/admin/graph-candidates", "/admin/graph-candidates/scan",
        "/admin/graph-candidates/{candidate_id}/approve", "/admin/graph-candidates/{candidate_id}/reject",
        "/admin/audit-logs", "/search/ai",
    } <= paths
