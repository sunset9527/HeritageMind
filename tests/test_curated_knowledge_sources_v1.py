"""The first curated package deepens six existing core crafts with two sources each."""

from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from src.services.knowledge_manifest import load_manifest


FOCUS_CRAFTS = {"景泰蓝", "苏绣", "龙泉青瓷", "南京云锦", "京剧", "皮影戏"}


def test_curated_knowledge_sources_v1_has_two_published_sources_per_focus_craft():
    manifest_path = Path(__file__).parents[1] / "data" / "knowledge_sources" / "manifest.json"
    manifest = load_manifest(manifest_path)

    counts = Counter(item.craft_name for item in manifest.documents)
    source_hosts = defaultdict(set)
    for item in manifest.documents:
        source_hosts[item.craft_name].add(urlparse(item.source_url).netloc)

    assert len(manifest.documents) == 12
    assert set(counts) == FOCUS_CRAFTS
    assert all(counts[craft] == 2 for craft in FOCUS_CRAFTS)
    assert all(len(source_hosts[craft]) == 2 for craft in FOCUS_CRAFTS)
    assert all(item.status == "published" for item in manifest.documents)
    assert all("摘要" in item.content for item in manifest.documents)
