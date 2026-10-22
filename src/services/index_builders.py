"""三类维护任务的有界索引构建器。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class IndexResourceLimit(ValueError):
    """索引输入超过配置上限。"""


def _validate_limits(
    documents: list[dict[str, Any]], *, max_documents: int, max_total_chars: int
) -> int:
    if len(documents) > max_documents:
        raise IndexResourceLimit(f"文档数量超过上限 {max_documents}")
    total_chars = sum(len(str(item.get("content", ""))) for item in documents)
    if total_chars > max_total_chars:
        raise IndexResourceLimit(f"文档总字符数超过上限 {max_total_chars}")
    return total_chars


def build_knowledge_snapshot(
    directory: Path,
    *,
    loader=None,
    embedder=None,
    max_documents: int,
    max_total_chars: int,
) -> dict[str, int]:
    """构建可由 ``MultiSourceRetriever`` 热加载的知识索引。"""
    if loader is None:
        from src.retrieval.document_loader import HeritageDocumentLoader

        loader = HeritageDocumentLoader()
    if embedder is None:
        from src.retrieval.embeddings import EmbeddingManager

        embedder = EmbeddingManager()

    documents = list(loader.load_craft_documents())
    total_chars = _validate_limits(
        documents,
        max_documents=max_documents,
        max_total_chars=max_total_chars,
    )
    texts = [str(item.get("content", "")) for item in documents]
    vectors = embedder.embed_documents(texts)
    if len(vectors) != len(documents) or any(not vector for vector in vectors):
        raise ValueError("知识索引向量数量不匹配或包含空向量")
    embeddings = {
        str(document.get("id", "")): vector
        for document, vector in zip(documents, vectors)
        if str(document.get("id", ""))
    }
    if len(embeddings) != len(documents):
        raise ValueError("知识文档 ID 为空或重复")

    directory.mkdir(parents=True, exist_ok=True)
    (directory / "index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "documents": documents,
                "embeddings": embeddings,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    return {"input_count": len(documents), "input_chars": total_chars}


def build_image_snapshot(
    directory: Path,
    *,
    documents,
    storage_root: Path | str,
    text_embedder=None,
    image_embedder=None,
    max_documents: int,
    max_total_chars: int,
) -> dict[str, int]:
    """构建文搜图与以图搜图共用的版本化向量文件。"""
    rows = list(documents)
    texts = [f"{row.craft_name} {row.title or ''} {row.original_name}".strip() for row in rows]
    total_chars = _validate_limits(
        [{"content": text} for text in texts],
        max_documents=max_documents,
        max_total_chars=max_total_chars,
    )
    if text_embedder is None:
        from src.retrieval.embeddings import EmbeddingManager

        text_embedder = EmbeddingManager()
    if image_embedder is None:
        from src.retrieval.image_embeddings import image_file_to_embedding

        image_embedder = image_file_to_embedding
    text_vectors = text_embedder.embed_documents(texts)
    if len(text_vectors) != len(rows) or any(not vector for vector in text_vectors):
        raise ValueError("图片文本向量数量不匹配或包含空向量")

    root = Path(storage_root).resolve()
    items = []
    for row, text, text_vector in zip(rows, texts, text_vectors):
        path = (root / "image" / row.filename).resolve()
        try:
            path.relative_to(root / "image")
        except ValueError as exc:
            raise ValueError("图片索引路径越界") from exc
        if not path.is_file():
            raise FileNotFoundError(f"图片文件不存在: media_id={row.id}")
        visual_vector = image_embedder(path)
        if not visual_vector:
            raise ValueError(f"图片视觉向量生成失败: media_id={row.id}")
        items.append(
            {
                "media_id": row.id,
                "craft_id": row.craft_id,
                "craft_name": row.craft_name,
                "title": row.title or "",
                "text": text,
                "text_embedding": text_vector,
                "image_embedding": visual_vector,
            }
        )

    directory.mkdir(parents=True, exist_ok=True)
    (directory / "index.json").write_text(
        json.dumps(
            {"schema_version": 1, "items": items},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    return {"input_count": len(rows), "input_chars": total_chars}

def build_audio_snapshot(
    directory: Path,
    *,
    transcripts,
    media_by_id: dict[int, Any],
    store,
    max_documents: int,
    max_total_chars: int,
) -> dict[str, int]:
    """把数据库中的完整转写重放到一个全新的版本化 Chroma collection。"""
    rows = list(transcripts)
    texts = [str(row.full_text or "") for row in rows]
    total_chars = _validate_limits(
        [{"content": text} for text in texts],
        max_documents=max_documents,
        max_total_chars=max_total_chars,
    )
    chunk_count = 0
    for row, text in zip(rows, texts):
        media = media_by_id.get(row.media_id)
        if media is None:
            raise ValueError(f"音频媒体记录不存在: media_id={row.media_id}")
        chunk_count += store.index_transcript(
            row.media_id,
            row.craft_name,
            media.title or "",
            text,
        )
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "collection": getattr(store, "_collection_name", None),
                "chunk_count": chunk_count,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    return {"input_count": len(rows), "input_chars": total_chars}
