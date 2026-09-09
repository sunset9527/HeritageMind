"""
v1.4 AudioVectorStore 测试（chromadb 1.5.1 EphemeralClient + 注入 FakeEmbedder，零网络/零 BGE 加载）。

覆盖：index→search 命中排序、二次 index 去重、delete_media、craft_name 过滤、embedding 异常降级子串。
"""
import uuid

import pytest

from src.retrieval.audio_store import AudioVectorStore

_TOKENS = ["景泰蓝", "苏绣", "掐丝", "传承", "历史", "工艺"]


class FakeEmbedder:
    """基于词表命中构造固定维稀疏向量（词袋），cosine 可预期；可选 fail_query。"""

    def __init__(self, fail_query=False):
        self.fail_query = fail_query

    def _vec(self, text):
        return [1.0 if tok in text else 0.0 for tok in _TOKENS]

    def embed_query(self, text):
        if self.fail_query:
            raise RuntimeError("embedding unavailable")
        return self._vec(text)

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]


@pytest.fixture()
def store():
    # 每个测试用唯一 collection 名，避免同进程 chroma 内存库跨测试残留串扰
    return AudioVectorStore(
        path=None,
        collection_name=f"audio_test_{uuid.uuid4().hex}",
        embedder=FakeEmbedder(),
        persistent=False,
    )


def test_index_then_search_hits(store):
    n = store.index_transcript(1, "景泰蓝", "大师访谈", "景泰蓝的掐丝工艺历史悠久")
    assert n >= 1
    hits = store.search("掐丝", top_k=5)
    assert hits and hits[0]["media_id"] == 1
    assert "掐丝" in hits[0]["snippet"]


def test_search_ranks_relevant_higher(store):
    store.index_transcript(1, "景泰蓝", "t1", "景泰蓝的掐丝工艺与烧蓝技术")
    store.index_transcript(2, "苏绣", "t2", "苏绣的针法与图案设计")
    hits = store.search("掐丝", top_k=5)
    assert hits[0]["media_id"] == 1


def test_reindex_replaces_old(store):
    store.index_transcript(1, "景泰蓝", "t1", "旧文本只谈历史与起源")
    n2 = store.index_transcript(1, "景泰蓝", "t1", "新文本专注掐丝工艺")
    assert store._collection.count() == n2  # delete+add 去重（若未删旧 count 会是 2）
    hits = store.search("掐丝", top_k=5)
    assert hits and hits[0]["media_id"] == 1
    # 旧文本独有词被真实移除：库中 documents 不含"起源"（全 0 向量查询 chroma 会兜底返回，故直接查内容）
    stored = "".join(store._collection.get()["documents"])
    assert "起源" not in stored
    assert "掐丝" in stored


def test_delete_media(store):
    store.index_transcript(1, "景泰蓝", "t1", "掐丝工艺")
    store.delete_media(1)
    assert store._collection.count() == 0
    assert store.search("掐丝", top_k=5) == []


def test_craft_name_filter(store):
    store.index_transcript(1, "景泰蓝", "t1", "景泰蓝与苏绣都是非遗")
    store.index_transcript(2, "苏绣", "t2", "苏绣的传承人很多")
    hits = store.search("苏绣", top_k=5, craft_name="苏绣")
    assert hits
    assert {h["media_id"] for h in hits} == {2}


def test_embedding_failure_falls_back_to_substring(store):
    store._embedder = FakeEmbedder(fail_query=True)
    store.index_transcript(1, "景泰蓝", "t1", "这段讲掐丝工艺与点蓝")
    hits = store.search("掐丝", top_k=5)
    assert hits and hits[0]["media_id"] == 1
    assert "掐丝" in hits[0]["snippet"]
    assert hits[0]["score"] == 0.0


def test_empty_query_returns_empty(store):
    store.index_transcript(1, "景泰蓝", "t1", "掐丝工艺")
    assert store.search("   ") == []
