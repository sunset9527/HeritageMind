from pathlib import Path


API_SOURCE = (Path(__file__).parents[1] / "api.py").read_text(encoding="utf-8")


def test_health_routes_expose_liveness_readiness_and_admin_dependency_details():
    assert '@app.get("/health/live")' in API_SOURCE
    assert '@app.get("/health/ready")' in API_SOURCE
    assert '@app.get("/health/dependencies")' in API_SOURCE
    assert "Depends(require_admin)" in API_SOURCE


def test_legacy_health_route_delegates_to_readiness_instead_of_fixed_success():
    health_block = API_SOURCE.split('@app.get("/health")', 1)[1].split("# ============================================================================", 1)[0]

    assert "health_readiness" in health_block
    assert 'return {"status": "healthy"}' not in health_block


def test_readiness_uses_a_short_redis_probe_and_environment_dependency_policy():
    assert "asyncio.wait_for(get_redis().ping(), timeout=1)" in API_SOURCE
    assert "required_api_dependencies(settings.app_env)" in API_SOURCE
