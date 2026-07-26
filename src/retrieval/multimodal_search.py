"""多模态检索 — 文搜图、以图搜图、音频转写检索

图片检索基于标题 + 技艺名 + 描述文本的 BGE 向量匹配。
完整 CLIP 视觉模型在 HuggingFace 可访问时自动启用。
"""
import logging
from typing import List, Dict, Any, Optional

from src.services.media import STORAGE_ROOT, get_media_url
from src.models.media import MediaDocument

logger = logging.getLogger(__name__)


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
    docs = list(db.scalars(select(MediaDocument).where(MediaDocument.media_type == "image")))

    if not docs:
        return []

    # 构建每张图片的检索文本
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
    docs = list(db.scalars(select(MediaDocument).where(MediaDocument.media_type == "image")))
    results = []

    if emb:
        from src.retrieval.image_embeddings import cosine_similarity
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
