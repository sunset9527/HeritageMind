"""The official first-batch registry is a traceable breadth layer, not a research summary."""

from pathlib import Path

from src.services.knowledge_manifest import load_manifest


FIRST_BATCH_URL = "https://zwgk.mct.gov.cn/zfxxgkml/fwzwhyc/202012/t20201206_916788.html"


def test_official_first_batch_registry_has_all_518_traceable_records():
    manifest_path = Path(__file__).parents[1] / "data" / "knowledge_sources" / "manifest.json"
    manifest = load_manifest(manifest_path)
    records = [
        item
        for item in manifest.documents
        if item.document_key.startswith("mct-first-batch-")
    ]

    assert len(manifest.documents) >= 500
    assert len(records) == 518
    assert len({item.craft_name for item in records}) >= 500
    assert all(item.source_url == FIRST_BATCH_URL for item in records)
    assert all(item.status == "published" for item in records)
    assert all("名录记录" in item.content for item in records)
    assert all("不替代工艺、历史或传承的深度研究" in item.content for item in records)
