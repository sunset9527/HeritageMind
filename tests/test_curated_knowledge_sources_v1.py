"""Each expanded craft must have two published, traceable curated sources."""

from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from src.services.knowledge_manifest import load_manifest


EXPANDED_CRAFTS = {
    "景泰蓝", "苏绣", "龙泉青瓷", "南京云锦", "京剧", "皮影戏",
    "宜兴紫砂", "芜湖铁画", "蜀锦", "剪纸",
}


def test_curated_knowledge_sources_v1_has_two_published_sources_per_expanded_craft():
    manifest_path = Path(__file__).parents[1] / "data" / "knowledge_sources" / "manifest.json"
    manifest = load_manifest(manifest_path)

    counts = Counter(item.craft_name for item in manifest.documents)
    source_hosts = defaultdict(set)
    for item in manifest.documents:
        source_hosts[item.craft_name].add(urlparse(item.source_url).netloc)

    assert len(manifest.documents) == 20
    assert set(counts) == EXPANDED_CRAFTS
    assert all(counts[craft] == 2 for craft in EXPANDED_CRAFTS)
    assert all(len(source_hosts[craft]) == 2 for craft in EXPANDED_CRAFTS)
    assert all(item.status == "published" for item in manifest.documents)
    assert all("摘要" in item.content for item in manifest.documents)
