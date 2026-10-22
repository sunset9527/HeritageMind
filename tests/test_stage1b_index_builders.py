"""维护任务必须生成可消费的真实索引，而不是只写任务标记。"""

import json
from types import SimpleNamespace

import pytest


class _Loader:
    def load_craft_documents(self):
        return [
            {"id": "a", "content": "景泰蓝工艺", "metadata": {"craft_id": "jingtailan"}},
            {"id": "b", "content": "苏绣针法", "metadata": {"craft_id": "suxiu"}},
        ]


class _Embedder:
    def embed_documents(self, texts):
        return [[float(len(text)), 1.0] for text in texts]


def test_knowledge_builder_writes_documents_and_embeddings(tmp_path):
    from src.services.index_builders import build_knowledge_snapshot

    stats = build_knowledge_snapshot(
        tmp_path,
        loader=_Loader(),
        embedder=_Embedder(),
        max_documents=10,
        max_total_chars=100,
    )

    payload = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert stats == {"input_count": 2, "input_chars": 9}
    assert [item["id"] for item in payload["documents"]] == ["a", "b"]
    assert payload["embeddings"]["a"] == [5.0, 1.0]
    assert payload["schema_version"] == 1


def test_knowledge_builder_rejects_resource_limit_before_publish(tmp_path):
    from src.services.index_builders import IndexResourceLimit, build_knowledge_snapshot

    with pytest.raises(IndexResourceLimit, match="文档总字符数"):
        build_knowledge_snapshot(
            tmp_path,
            loader=_Loader(),
            embedder=_Embedder(),
            max_documents=10,
            max_total_chars=3,
        )
    assert not (tmp_path / "index.json").exists()


def test_retriever_hot_loads_new_active_knowledge_snapshot(tmp_path, monkeypatch):
    from src.retrieval.index_snapshot import publish_snapshot
    from src.retrieval.retriever import MultiSourceRetriever
    import src.retrieval.retriever as module

    version = publish_snapshot(
        tmp_path,
        "knowledge_index",
        lambda directory: (directory / "index.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "documents": [{"id": "new", "content": "新知识", "metadata": {}}],
                    "embeddings": {"new": [1.0, 0.0]},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        ),
    )
    monkeypatch.setattr(module.settings, "index_versions_path", str(tmp_path))

    retriever = MultiSourceRetriever.__new__(MultiSourceRetriever)
    retriever.documents = [{"id": "old", "content": "旧知识", "metadata": {}}]
    retriever.document_embeddings = {}
    retriever.embedding_func = None
    retriever._snapshot_version = None
    retriever.refresh_active_snapshot()

    assert retriever._snapshot_version == version
    assert retriever.documents[0]["id"] == "new"
    assert retriever.document_embeddings["new"] == [1.0, 0.0]
    assert callable(retriever.embedding_func)


def test_partial_snapshot_cleanup_removes_only_part_artifacts(tmp_path):
    from src.retrieval.index_snapshot import cleanup_partial_snapshots

    kind = tmp_path / "knowledge_index"
    (kind / "dead.part").mkdir(parents=True)
    (kind / "keep").mkdir()
    (kind / "active.json.part").write_text("partial", encoding="utf-8")

    assert cleanup_partial_snapshots(tmp_path, "knowledge_index") == 2
    assert (kind / "keep").is_dir()


def test_image_builder_persists_text_and_visual_vectors(tmp_path):
    from src.services.index_builders import build_image_snapshot

    media_root = tmp_path / "media"
    (media_root / "image").mkdir(parents=True)
    (media_root / "image" / "one.png").write_bytes(b"image")
    row = SimpleNamespace(
        id=7,
        craft_id="suxiu",
        craft_name="苏绣",
        title="双面绣",
        original_name="作品.png",
        filename="one.png",
    )

    stats = build_image_snapshot(
        tmp_path / "snapshot",
        documents=[row],
        storage_root=media_root,
        text_embedder=_Embedder(),
        image_embedder=lambda _: [0.2, 0.8],
        max_documents=10,
        max_total_chars=100,
    )

    payload = json.loads(
        (tmp_path / "snapshot" / "index.json").read_text(encoding="utf-8")
    )
    assert stats["input_count"] == 1
    assert payload["items"][0]["media_id"] == 7
    assert payload["items"][0]["text_embedding"]
    assert payload["items"][0]["image_embedding"] == [0.2, 0.8]


class _AudioStore:
    def __init__(self):
        self.calls = []

    def index_transcript(self, media_id, craft_name, title, full_text):
        self.calls.append((media_id, craft_name, title, full_text))
        return 2


def test_audio_builder_replays_indexed_transcripts_into_versioned_collection(tmp_path):
    from src.services.index_builders import build_audio_snapshot

    store = _AudioStore()
    transcript = SimpleNamespace(media_id=9, craft_name="京剧", full_text="唱念做打")
    media = {9: SimpleNamespace(title="京剧音频")}
    stats = build_audio_snapshot(
        tmp_path,
        transcripts=[transcript],
        media_by_id=media,
        store=store,
        max_documents=10,
        max_total_chars=100,
    )

    assert stats == {"input_count": 1, "input_chars": 4}
    assert store.calls == [(9, "京剧", "京剧音频", "唱念做打")]
    assert json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))["chunk_count"] == 2


def test_image_search_loader_reads_only_active_snapshot(tmp_path):
    from src.retrieval.index_snapshot import publish_snapshot
    from src.retrieval.multimodal_search import load_active_image_index

    publish_snapshot(
        tmp_path,
        "image_index",
        lambda directory: (directory / "index.json").write_text(
            json.dumps({"schema_version": 1, "items": [{"media_id": 3}]}),
            encoding="utf-8",
        ),
    )

    assert load_active_image_index(tmp_path) == [{"media_id": 3}]


def test_audio_store_switches_collection_when_active_version_changes(tmp_path, monkeypatch):
    import src.retrieval.audio_store as module
    from src.retrieval.index_snapshot import publish_snapshot

    publish_snapshot(
        tmp_path,
        "audio_index",
        lambda directory: (directory / "index.json").write_text(
            json.dumps({"schema_version": 1, "collection": "audio_v2", "chunk_count": 0}),
            encoding="utf-8",
        ),
    )
    created = []

    class FakeStore:
        def __init__(self, collection_name=None):
            self.collection_name = collection_name
            created.append(collection_name)

    monkeypatch.setattr(module.settings, "index_versions_path", str(tmp_path))
    monkeypatch.setattr(module, "AudioVectorStore", FakeStore)
    module.reset_audio_store()

    assert module.get_audio_store().collection_name == "audio_v2"
    assert created == ["audio_v2"]
