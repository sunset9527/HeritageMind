"""Each expanded craft must have two published, traceable curated sources."""

from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from src.services.knowledge_manifest import load_manifest


EXPANDED_CRAFTS = {
    "景泰蓝", "苏绣", "龙泉青瓷", "南京云锦", "京剧", "皮影戏",
    "宜兴紫砂", "芜湖铁画", "蜀锦", "剪纸",
    "景德镇瓷器", "东阳木雕", "苗族蜡染", "木版年画",
    "缂丝", "竹编", "玉雕", "漆器", "唐三彩",
    "钧瓷", "汝瓷", "泥人张", "壮锦",
}


def test_curated_knowledge_sources_v1_has_two_published_sources_per_expanded_craft():
    manifest_path = Path(__file__).parents[1] / "data" / "knowledge_sources" / "manifest.json"
    manifest = load_manifest(manifest_path)

    deep_sources = [
        item for item in manifest.documents
        if not item.document_key.startswith("mct-first-batch-")
    ]
    counts = Counter(item.craft_name for item in deep_sources)
    source_hosts = defaultdict(set)
    for item in deep_sources:
        source_hosts[item.craft_name].add(urlparse(item.source_url).netloc)

    assert len(deep_sources) == 46
    assert set(counts) == EXPANDED_CRAFTS
    assert all(counts[craft] == 2 for craft in EXPANDED_CRAFTS)
    assert all(len(source_hosts[craft]) == 2 for craft in EXPANDED_CRAFTS)
    assert all(item.status == "published" for item in deep_sources)
    assert all("摘要" in item.content for item in deep_sources)
