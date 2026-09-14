from pathlib import Path


def test_prerender_build_script_and_manifest_cover_public_detail_routes():
    project = Path(__file__).resolve().parents[1]
    script = (project / "frontend" / "prerender.mjs").read_text(encoding="utf-8")
    manifest = (project / "frontend" / "prerender-manifest.json").read_text(encoding="utf-8")
    package = (project / "frontend" / "package.json").read_text(encoding="utf-8")

    assert '"build:ssg"' in package
    assert "encyclopedia" in script and "inheritors" in script
    assert "canonical" in script
    assert "景泰蓝" in manifest
