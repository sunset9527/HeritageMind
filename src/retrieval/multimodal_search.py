"""多模态检索 — 文搜图、以图搜图、音频转写检索

图片检索基于标题 + 技艺名 + 描述文本的 BGE 向量匹配。
完整 CLIP 视觉模型在 HuggingFace 可访问时自动启用。
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.services.media import STORAGE_ROOT, get_media_url
from src.models.media import MediaDocument

logger = logging.getLogger(__name__)


def load_active_image_index(root: Path | str | None = None) -> List[Dict[str, Any]]:
    """读取已原子发布的图片索引；损坏或尚未构建时安全降级。"""
    from config import settings
    from src.retrieval.index_snapshot import active_version

    base = Path(root or settings.index_versions_path)
    version = active_version(base, "image_index")
    if version is None:
        return []
    try:
        payload = json.loads(
            (base / "image_index" / version / "index.json").read_text(encoding="utf-8")
        )
        if payload.get("schema_version") != 1 or not isinstance(payload.get("items"), list):
            raise ValueError("不支持的图片索引格式")
        return payload["items"]
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        logger.error("活动图片索引读取失败，降级实时检索: %s", exc)
        return []


def _get_embedding(text: str) -> Optional[List[float]]:
    """获取文本的 BGE 嵌入"""
    try:
        from src.retrieval.embeddings import get_embedding_model
        model = get_embedding_model()
        if model is None:
            return None
        return model.encode(text).tolist()
    except Exception:
        return None


def _cosine(a: List[float], b: List[float]) -> float:
    import numpy as np
    aa, bb = np.array(a), np.array(b)
    return float(np.dot(aa, bb) / (np.linalg.norm(aa) * np.linalg.norm(bb) + 1e-8))


def search_images_by_text(db, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
    """文搜图：用文本描述搜索已上传图片（基于标题+描述向量匹配）"""
    from sqlalchemy import select
    docs = list(db.scalars(select(MediaDocument).where(
        MediaDocument.media_type == "image",
        MediaDocument.status == "published",
    )))

    if not docs:
        return []

    active_items = load_active_image_index()
    if active_items:
        query_emb = _get_embedding(query)
        doc_map = {item.id: item for item in docs}
        if query_emb is not None:
            results = []
            for item in active_items:
                doc = doc_map.get(item.get("media_id"))
                vector = item.get("text_embedding")
                if doc is None or not vector:
                    continue
                results.append(
                    {
                        "id": doc.id,
                        "craft_name": doc.craft_name,
                        "title": doc.title,
                        "url": get_media_url(doc),
                        "score": _cosine(query_emb, vector),
                    }
                )
            results.sort(key=lambda result: result["score"], reverse=True)
            return results[:top_k]

    # 尚无可用快照时保留兼容降级路径。
    doc_texts = []
    for d in docs:
        text = f"{d.craft_name} {d.title} {d.original_name}"
        doc_texts.append(text)

    # 查询向量化
    query_emb = _get_embedding(query)

    if query_emb is None:
        # 降级：关键词匹配
        results = []
        for i, d in enumerate(docs):
            text = doc_texts[i]
            score = sum(1 for ch in query if ch in text) / max(len(query), 1)
            if score > 0:
                results.append({"id": d.id, "craft_name": d.craft_name,
                                "title": d.title, "url": get_media_url(d), "score": score})
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    # 向量匹配
    results = []
    for i, d in enumerate(docs):
        doc_emb = _get_embedding(doc_texts[i])
        if doc_emb is None:
            continue
        score = _cosine(query_emb, doc_emb)
        results.append({"id": d.id, "craft_name": d.craft_name,
                        "title": d.title, "url": get_media_url(d), "score": float(score)})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def search_similar_images(db, image_bytes: bytes, top_k: int = 6) -> List[Dict[str, Any]]:
    """以图搜图：尝试 CLIP，不可用时返回最近上传的图片"""
    # 尝试 CLIP
    emb = None
    try:
        from src.retrieval.image_embeddings import image_to_embedding
        emb = image_to_embedding(image_bytes)
    except Exception:
        pass

    from sqlalchemy import select
    docs = list(db.scalars(select(MediaDocument).where(
        MediaDocument.media_type == "image",
        MediaDocument.status == "published",
    )))
    results = []

    if emb:
        from src.retrieval.image_embeddings import cosine_similarity
        active_items = load_active_image_index()
        doc_map = {item.id: item for item in docs}
        if active_items:
            for item in active_items:
                d = doc_map.get(item.get("media_id"))
                demb = item.get("image_embedding")
                if d is not None and demb:
                    results.append({"id": d.id, "craft_name": d.craft_name,
                                    "title": d.title, "url": get_media_url(d),
                                    "score": float(cosine_similarity(emb, demb))})
        else:
            for d in docs:
                path = STORAGE_ROOT / "image" / d.filename
                if not path.exists():
                    continue
                try:
                    from src.retrieval.image_embeddings import image_file_to_embedding
                    demb = image_file_to_embedding(path)
                    if demb:
                        results.append({"id": d.id, "craft_name": d.craft_name,
                                        "title": d.title, "url": get_media_url(d),
                                        "score": float(cosine_similarity(emb, demb))})
                except Exception:
                    continue
        results.sort(key=lambda r: r["score"], reverse=True)

    if not results:
        # 降级：返回最近上传的图片
        for d in reversed(docs[-top_k:]):
            results.append({"id": d.id, "craft_name": d.craft_name,
                            "title": d.title, "url": get_media_url(d), "score": 0.5})

    return results[:top_k]


def index_all_images(db) -> int:
    """图片索引计数（向量在首次查询时构建）"""
    from sqlalchemy import select
    count = db.scalar(select(MediaDocument).where(MediaDocument.media_type == "image"))
    return count or 0
