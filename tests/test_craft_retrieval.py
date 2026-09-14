"""
P2优化测试：⑤技艺名精确匹配置顶 + ①「技艺→工序→细节」层级聚合

本测试不调用真实 LLM、不依赖 embedding 模型，全部离线可复现：
- 置顶测试：用 mock 文档控制 keyword 检索排序，验证目标技艺文档被置顶 rank1
- 聚合测试：构造同技艺多工序片段（chunk 碎片）+ 跨技艺文档，验证分组与组内顺序
- 真实数据 smoke：用真实 document_loader（23 篇技艺文档）验证检索不回归

运行方式：
    python -m pytest tests/test_craft_retrieval.py -v
    或
    python tests/test_craft_retrieval.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from src.retrieval.retriever import MultiSourceRetriever
from src.retrieval.craft_name_boost import (
    apply_craft_name_boost,
    find_matched_crafts,
    is_craft_query,
    craft_id_of,
)
from src.retrieval.grouping import (
    detect_process_keywords,
    group_retrieved_docs,
    build_grouped_context,
)
from src.retrieval.document_loader import HeritageDocumentLoader

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _make_retriever(docs):
    """构造注入 mock 文档的 MultiSourceRetriever（跳过真实文档加载）"""
    r = MultiSourceRetriever.__new__(MultiSourceRetriever)
    r.documents = docs
    r.document_embeddings = {}
    r.embedding_func = None
    r.config = {"top_k": 5, "similarity_threshold": 0.0}
    return r


def _doc(doc_id, content, craft_id=None, craft_name=None, **extra_meta):
    """构造检索结果文档字典"""
    metadata = {"craft_id": craft_id or doc_id, "craft_name": craft_name or doc_id}
    metadata.update(extra_meta)
    return {"id": doc_id, "content": content, "metadata": metadata}


# ---------------------------------------------------------------------------
# ⑤ 技艺名精确匹配置顶
# ---------------------------------------------------------------------------

class TestCraftNameMatch:

    def test_find_matched_crafts_single(self):
        assert find_matched_crafts("景泰蓝的制作工艺是怎样的？") == ["景泰蓝"]

    def test_find_matched_crafts_multiple_in_order(self):
        # 多技艺 query：按在 query 中出现的顺序返回
        matched = find_matched_crafts("景泰蓝和苏绣有什么区别？")
        assert matched == ["景泰蓝", "苏绣"]

    def test_find_matched_crafts_none(self):
        assert find_matched_crafts("哪种木雕以平面浮雕见长？") == []
        assert find_matched_crafts("") == []
        assert is_craft_query("哪种木雕以平面浮雕见长？") is False

    def test_no_substring_false_positive(self):
        # "东阳木雕" 含 "木雕"，但 "木雕" 不是技艺名，不应误匹配；"玉雕" 也不应命中
        assert find_matched_crafts("东阳木雕有哪些雕刻技法？") == ["东阳木雕"]
        assert find_matched_crafts("木雕工艺") == []

    def test_craft_id_of_variants(self):
        # 整篇 id / chunk id / metadata.craft_name 反查 三种形态归一化
        assert craft_id_of(_doc("jingtailan", "内容", craft_id="jingtailan")) == "jingtailan"
        assert craft_id_of(_doc("jingtailan_c0", "内容", craft_id="jingtailan")) == "jingtailan"
        assert craft_id_of(_doc("suxiu_c2", "内容", craft_id="suxiu")) == "suxiu"
        assert craft_id_of({"id": "x", "content": "", "metadata": {"craft_name": "苏绣"}}) == "suxiu"
        assert craft_id_of({"id": "unknown_x", "content": "", "metadata": {}}) is None


class TestCraftNameBoost:

    def test_boost_pure_function(self):
        """纯函数：目标技艺文档原本排第 2，置顶后 rank1"""
        docs = [
            _doc("suxiu", "苏绣的制作工艺包括勾样、上绷、配线、刺绣、落绷等工序和步骤。",
                 craft_id="suxiu", craft_name="苏绣", similarity=0.9),
            _doc("jingtailan", "景泰蓝又称铜胎掐丝珐琅。", craft_id="jingtailan",
                 craft_name="景泰蓝", similarity=0.5),
        ]
        boosted, matched = apply_craft_name_boost(docs, "景泰蓝的制作工艺有哪些步骤？")
        assert matched == ["景泰蓝"]
        assert boosted[0]["id"] == "jingtailan"
        assert boosted[0]["craft_name_boosted"] is True
        # 其余结果保持原相对顺序
        assert [d["id"] for d in boosted[1:]] == ["suxiu"]

    def test_boost_no_craft_query_no_change(self):
        """不含技艺名 → 排序不变、无标记"""
        docs = [
            _doc("suxiu", "内容A", craft_id="suxiu", similarity=0.9),
            _doc("jingtailan", "内容B", craft_id="jingtailan", similarity=0.5),
        ]
        boosted, matched = apply_craft_name_boost(docs, "哪种木雕以平面浮雕见长？")
        assert matched == []
        assert [d["id"] for d in boosted] == ["suxiu", "jingtailan"]
        assert all("craft_name_boosted" not in d for d in boosted)

    def test_boost_multiple_crafts_keep_relative_order(self):
        """多技艺 query：命中技艺的文档全部提前，保持原相对顺序"""
        docs = [
            _doc("suxiu", "苏绣内容", craft_id="suxiu", similarity=0.9),
            _doc("jianzhi", "剪纸内容", craft_id="jianzhi", similarity=0.8),
            _doc("jingtailan", "景泰蓝内容", craft_id="jingtailan", similarity=0.7),
        ]
        boosted, matched = apply_craft_name_boost(docs, "景泰蓝和苏绣有什么区别？")
        assert set(matched) == {"景泰蓝", "苏绣"}
        ids = [d["id"] for d in boosted]
        # 两个命中技艺都提前，且原相对顺序 suxiu < jingtailan 保持
        assert ids[0] == "suxiu" and ids[1] == "jingtailan"
        assert ids[2] == "jianzhi"

    def test_boost_not_recalled_no_insertion(self):
        """目标技艺文档未被召回 → 不伪造插入，原样返回"""
        docs = [_doc("suxiu", "苏绣内容", craft_id="suxiu", similarity=0.9)]
        boosted, matched = apply_craft_name_boost(docs, "景泰蓝的制作工艺")
        assert matched == ["景泰蓝"]
        assert [d["id"] for d in boosted] == ["suxiu"]

    def test_retrieve_boost_fuzzy_question(self):
        """集成：query 含技艺名但问法模糊（目标文档 keyword 分低）→ 依然置顶"""
        docs = [
            # 苏绣文档命中"制作/工艺/步骤"3 个关键词 → keyword 分最高，boost 前 rank1
            _doc("suxiu", "苏绣的制作工艺包括勾样、上绷、配线、刺绣、落绷等基本工序和步骤。",
                 craft_id="suxiu", craft_name="苏绣"),
            _doc("dongyang_mudiao", "东阳木雕的工艺流程包括选材、打坯等。",
                 craft_id="dongyang_mudiao", craft_name="东阳木雕"),
            # 景泰蓝文档只命中"景泰蓝"与"工艺"子串 → keyword 分低，boost 前不在 rank1
            _doc("jingtailan", "景泰蓝又称铜胎掐丝珐琅，是著名的特种金属工艺品。",
                 craft_id="jingtailan", craft_name="景泰蓝"),
        ]
        retriever = _make_retriever(docs)
        results = retriever.retrieve("景泰蓝的制作工艺有哪些步骤？", top_k=3)
        ids = [r["id"] for r in results]
        print(f"\n[模糊问法置顶] boost 后排序: {ids}")
        assert ids[0] == "jingtailan", f"技艺名置顶失败：{ids}"
        assert results[0]["craft_name_boosted"] is True

    def test_retrieve_boost_disabled_no_change(self):
        """craft_boost_enabled=False → 排序与未置顶一致（零回归开关）"""
        docs = [
            _doc("suxiu", "苏绣的制作工艺包括勾样、上绷、配线、刺绣、落绷等基本工序和步骤。",
                 craft_id="suxiu", craft_name="苏绣"),
            _doc("jingtailan", "景泰蓝又称铜胎掐丝珐琅，是著名的特种金属工艺品。",
                 craft_id="jingtailan", craft_name="景泰蓝"),
        ]
        old = settings.craft_boost_enabled
        try:
            settings.craft_boost_enabled = False
            off_ids = [d["id"] for d in _make_retriever(docs).retrieve(
                "景泰蓝的制作工艺有哪些步骤？", top_k=3)]
            settings.craft_boost_enabled = True
            on_ids = [d["id"] for d in _make_retriever(docs).retrieve(
                "景泰蓝的制作工艺有哪些步骤？", top_k=3)]
        finally:
            settings.craft_boost_enabled = old
        print(f"\n[开关对比] 关闭: {off_ids} | 开启: {on_ids}")
        assert off_ids[0] == "suxiu"          # 关闭时目标技艺不在 rank1
        assert on_ids[0] == "jingtailan"      # 开启时置顶


# ---------------------------------------------------------------------------
# ① 层级聚合：技艺 → 工序 → 细节
# ---------------------------------------------------------------------------

# 苏绣 3 个工序片段（故意乱序输入，验证组内排序）
# 内容模拟真实 chunk 结构：编号步骤 + 技艺名（分块器常把标题带入每个 chunk）
SUXIU_CHUNKS = [
    _doc("suxiu_c2", "3. **配线**：苏绣的配线工序，根据图案选择合适的蚕丝线，配好颜色。配线是苏绣的关键。",
         craft_id="suxiu", craft_name="苏绣"),
    _doc("suxiu_c0", "1. **勾样**：苏绣的勾样工序，将设计的图案用笔勾画在纸上或直接勾在绷布上。",
         craft_id="suxiu", craft_name="苏绣"),
    _doc("suxiu_c1", "2. **上绷**：苏绣的上绷工序，将绣布平整地绑在绣绷上，使绣面保持平整。",
         craft_id="suxiu", craft_name="苏绣"),
]
JINGTAILAN_CHUNKS = [
    _doc("jingtailan_c0", "1. **制胎**：景泰蓝的制胎工序，用紫铜板制作各种器型的胎体，是景泰蓝的基础。",
         craft_id="jingtailan", craft_name="景泰蓝"),
    _doc("jingtailan_c1", "2. **掐丝**：景泰蓝的掐丝工序，用铜丝按照设计图案掐出轮廓，焊在铜胎上。掐丝是景泰蓝最关键的工序。",
         craft_id="jingtailan", craft_name="景泰蓝"),
]


class TestProcessKeywordExtraction:

    def test_detect_numbered_steps(self):
        kws = detect_process_keywords("1. **制胎**：用紫铜板制作胎体。\n2. **掐丝**：掐出轮廓。")
        assert kws == ["制胎", "掐丝"]

    def test_detect_section_and_chinese_step(self):
        kws = detect_process_keywords("## 制作工艺\n第一步 勾样。\n## 主要材料")
        assert "制作工艺" in kws
        assert "主要材料" in kws
        assert any("第一步" in k for k in kws)

    def test_empty_content(self):
        assert detect_process_keywords("") == []


class TestHierarchicalGrouping:

    def test_group_same_craft_sort_by_process(self):
        """同技艺 3 个工序片段（乱序输入）→ 正确聚为一组，组内按工序顺序排序"""
        groups = group_retrieved_docs(SUXIU_CHUNKS, query="苏绣的工艺流程")["groups"]
        assert set(groups.keys()) == {"suxiu"}
        group = groups["suxiu"]
        print(f"\n[分组] 组: {group['craft_name']}，工序: {group['processes']}")
        assert group["craft_name"] == "苏绣"
        ids = [d["id"] for d in group["docs"]]
        print(f"[分组] 组内顺序（乱序输入后）: {ids}")
        assert ids == ["suxiu_c0", "suxiu_c1", "suxiu_c2"], "组内应按工序 1→2→3 排序"
        # 工序关键词已提取
        assert "勾样" in group["processes"]
        assert "配线" in group["processes"]

    def test_group_cross_craft_separate(self):
        """跨技艺文档 → 正确分到不同组，不互相污染"""
        docs = SUXIU_CHUNKS + JINGTAILAN_CHUNKS
        result = group_retrieved_docs(docs, query="景泰蓝的制作工艺")
        groups = result["groups"]
        print(f"\n[跨技艺] 组数: {result['group_count']}，组: {list(groups.keys())}")
        assert result["group_count"] == 2
        assert set(groups.keys()) == {"suxiu", "jingtailan"}
        assert [d["id"] for d in groups["jingtailan"]["docs"]] == ["jingtailan_c0", "jingtailan_c1"]
        # query 命中景泰蓝 → 景泰蓝组排前面
        assert list(groups.keys())[0] == "jingtailan"

    def test_group_context_view(self):
        """拼接上下文 = 完整技艺视图：组标题 + 工序关键词 + 按顺序的细节"""
        docs = SUXIU_CHUNKS + JINGTAILAN_CHUNKS
        result = group_retrieved_docs(docs, query="苏绣")
        context = result["context"]
        print(f"\n[上下文视图]\n{context}")
        assert "【技艺：苏绣】" in context
        assert "（工序：" in context and "勾样" in context
        # 组内细节顺序：勾样 → 上绷 → 配线（用正文编号步骤定位，避开标题中的工序关键词）
        i0, i1, i2 = context.index("1. **勾样**"), context.index("2. **上绷**"), context.index("3. **配线**")
        assert i0 < i1 < i2

    def test_group_context_char_limit(self):
        """每组合并上下文有字符上限（控制生成阶段上下文体积）"""
        docs = SUXIU_CHUNKS + JINGTAILAN_CHUNKS
        result = group_retrieved_docs(docs, query="苏绣", max_chars_per_group=80)
        for group in result["groups"].values():
            # 组标题 + 组内内容应被截断到 ~80 字符
            group_text = ""
            for d in group["docs"]:
                group_text += d["content"]
            assert len(group_text) >= 80  # 原文超限
        print(f"\n[截断] max_chars_per_group=80 时 context 长度: {len(result['context'])}")
        assert len(result["context"]) < 80 * 2 + 100

    def test_retrieve_grouped_with_mock_docs(self):
        """retriever.retrieve_grouped 接口：先检索（keyword）再分组"""
        retriever = _make_retriever(SUXIU_CHUNKS + JINGTAILAN_CHUNKS)
        result = retriever.retrieve_grouped("苏绣的工艺流程", top_k=5)
        print(f"\n[retrieve_grouped] 组数: {result['group_count']}，命中技艺: {result['matched_crafts']}")
        assert result["matched_crafts"] == ["苏绣"]
        assert "suxiu" in result["groups"]
        assert result["groups"]["suxiu"]["doc_count"] == 3
        assert result["context"].startswith("【技艺：苏绣】")


# ---------------------------------------------------------------------------
# 真实数据 smoke（23 篇旧技艺文档 + 12 篇来源化资料，不依赖 LLM / embedding）
# ---------------------------------------------------------------------------

class TestRealDataSmoke:

    def test_real_docs_craft_name_full_coverage(self):
        """真实 loader：所有文档的 metadata.craft_name 全部是中文名（不再回退拼音）"""
        loader = HeritageDocumentLoader()
        docs = loader.load_craft_documents()
        assert len(docs) == 43
        missing = [d["id"] for d in docs if d["metadata"]["craft_name"] == d["id"]]
        assert missing == [], f"仍有文档 craft_name 回退为拼音 id: {missing}"
        print(f"\n[真实数据] 已加载 {len(docs)} 篇，craft_name 中文名覆盖率 100%")

    def test_real_docs_include_published_curated_evidence_metadata(self):
        """来源化资料必须带稳定文档键、来源和已发布状态，供引用链路复用。"""
        docs = HeritageDocumentLoader().load_craft_documents()
        curated = next(doc for doc in docs if doc["id"] == "curated:jingtailan-ihchina-001")

        assert curated["metadata"]["craft_id"] == "jingtailan"
        assert curated["metadata"]["craft_name"] == "景泰蓝"
        assert curated["metadata"]["document_key"] == "jingtailan-ihchina-001"
        assert curated["metadata"]["publication_status"] == "published"
        assert curated["metadata"]["source_url"].startswith("https://www.ihchina.cn/")

    def test_real_docs_boost_rank1(self):
        """真实数据：query 含技艺名 → 该技艺文档必在 rank1"""
        retriever = MultiSourceRetriever()
        for query, expect_id in [
            ("景泰蓝的制作工艺是怎样的？", "jingtailan"),
            ("苏绣有哪些艺术特色？", "suxiu"),
            ("东阳木雕有哪些主要雕刻技法？", "dongyang_mudiao"),
            ("京剧的四大行当是什么？", "jingju"),
        ]:
            results = retriever.retrieve(query, top_k=3)
            ids = [r["id"] for r in results]
            print(f"[真实置顶] {query[:18]}… → rank1={ids[0]}")
            assert ids[0] == expect_id, f"query='{query}' rank1 应为 {expect_id}，实际 {ids}"

    def test_real_docs_no_craft_query_unchanged(self):
        """真实数据：不含技艺名的难题 → 置顶开关不影响排序（零回归）"""
        retriever = MultiSourceRetriever()
        old = settings.craft_boost_enabled
        try:
            settings.craft_boost_enabled = False
            off_ids = [r["id"] for r in retriever.retrieve("哪种木雕以平面浮雕见长？", top_k=3)]
            settings.craft_boost_enabled = True
            on_ids = [r["id"] for r in retriever.retrieve("哪种木雕以平面浮雕见长？", top_k=3)]
        finally:
            settings.craft_boost_enabled = old
        print(f"\n[真实零回归] 关闭: {off_ids} | 开启: {on_ids}")
        assert off_ids == on_ids

    def test_real_docs_retrieve_grouped(self):
        """真实数据：retrieve_grouped 返回完整技艺视图（整篇文档场景每组 1 篇）"""
        retriever = MultiSourceRetriever()
        result = retriever.retrieve_grouped("景泰蓝的制作工艺", top_k=3)
        assert result["matched_crafts"] == ["景泰蓝"]
        assert "jingtailan" in result["groups"]
        assert result["context"].startswith("【技艺：景泰蓝】")
        # 整篇文档的工序关键词应从内容中提取到（如"制胎/掐丝"）
        procs = result["groups"]["jingtailan"]["processes"]
        print(f"\n[真实聚合] 景泰蓝组工序关键词: {procs}")
        assert "制胎" in procs and "掐丝" in procs


# ---------------------------------------------------------------------------
# 直接运行入口
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("P2优化验证：技艺名置顶 + 层级聚合")
    print("=" * 60)
    t = TestCraftNameMatch()
    for name in dir(t):
        if name.startswith("test_"):
            getattr(t, name)()
    t = TestCraftNameBoost()
    for name in dir(t):
        if name.startswith("test_"):
            getattr(t, name)()
    t = TestProcessKeywordExtraction()
    for name in dir(t):
        if name.startswith("test_"):
            getattr(t, name)()
    t = TestHierarchicalGrouping()
    for name in dir(t):
        if name.startswith("test_"):
            getattr(t, name)()
    t = TestRealDataSmoke()
    for name in dir(t):
        if name.startswith("test_"):
            getattr(t, name)()
    print("\n" + "=" * 60)
    print("全部测试通过 ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
