"""A first real project must meet the deep-source standard before scaling collection."""

from pathlib import Path

import pytest

from src.services.knowledge_manifest import load_manifest


@pytest.mark.parametrize(
    ("registry_document_key", "required_dimensions"),
    [
        ("mct-first-batch-351", {"craft", "history_region", "contemporary_practice"}),
        ("mct-first-batch-352", {"craft", "history_region", "contemporary_practice"}),
        ("mct-first-batch-359", {"craft", "history_region", "safeguarding"}),
        ("mct-first-batch-360", {"craft", "history_region", "safeguarding"}),
        ("mct-first-batch-358", {"craft", "history_region", "safeguarding"}),
    ],
)
def test_selected_first_batch_projects_have_three_linked_official_deep_sources(
    registry_document_key: str,
    required_dimensions: set[str],
):
    manifest = load_manifest(Path(__file__).parents[1] / "data" / "knowledge_sources" / "manifest.json")
    sources = [
        item
        for item in manifest.documents
        if item.registry_document_key == registry_document_key
    ]

    assert len(sources) >= 3
    assert {item.evidence_layer for item in sources} == {"deep_summary"}
    assert len({item.source_url for item in sources}) >= 3
    assert len({item.source_name for item in sources}) >= 2
    assert {dimension for item in sources for dimension in item.evidence_dimensions} >= required_dimensions
