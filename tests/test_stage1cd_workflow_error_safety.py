from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_PUBLIC_ERROR_BOUNDARIES = (
    "src/agents/craft_expert.py",
    "src/agents/heritage_expert.py",
    "src/agents/history_expert.py",
    "src/workflow/graph.py",
    "src/workflow/nodes.py",
    "src/knowledge/granularity.py",
)


def test_public_workflow_boundaries_do_not_embed_raw_exception_text():
    offenders = [
        relative_path
        for relative_path in _PUBLIC_ERROR_BOUNDARIES
        if "str(e)" in (_ROOT / relative_path).read_text(encoding="utf-8")
    ]

    assert offenders == []
