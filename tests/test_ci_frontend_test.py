"""CI 应在前端生产构建前运行 Vitest。"""

from pathlib import Path


def test_ci_runs_frontend_unit_tests_before_build():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "- run: npm run test" in workflow
    assert workflow.index("- run: npm run test") < workflow.index("- run: npm run build")
