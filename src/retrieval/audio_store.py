"""音频转写文本向量索引（v1.4）— 裸 chromadb 1.x + 本地 BGE-M3 显式向量

- 不沿用旧 `vector_retriever.py`（langchain Chroma wrapper，面向 chromadb 0.4.x）。
- 显式传 BGE-M3 embeddings 数组：离线、collection 维度可控、embedding 异常可降级。
- collection metadata `hnsw:space=cosine` → 距离 = 1-cos，score = max(0, 1-dist)。
- 检索降级：embedding 失败时 `where_document $contains` 子串兜底。
- 转写文本按 chunk 持久于 chroma `documents`（metadata 带 media_id/craft_name/title/chunk_idx）；
  `full_text` 在 DB sidecar，重建用 split_transcript 精确重放。
"""
import logging
from typing import Dict, List, Optional

from config import settings
from src.retrieval.embeddings import EmbeddingManager

logger = logging.getLogger(__name__)

# 分句边界字符（含英文标点），切块时优先在此处断，避免硬切在词中
_BOUNDARIES = set("。！？；…\n，、,.!?;:：")


def split_transcript(text: str, max_chars: int = 500, overlap: int = 50) -> List[str]:
    """把转写全文切成入库分块（纯函数）。

    规则：尽量在句边界断开；每块 ≤ max_chars；相邻块在上一块结尾处保留 overlap 重叠，
    不跳内容、不死循环。
    """
    text = (text or "").strip()
    if not text:
        return []
    if max_chars < 1:
        max_chars = 1
    if overlap >= max_chars:
        overlap = max_chars - 1

    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            cut = _last_boundary(text, start, end)
            if cut is not None and cut > start:
                end = cut
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        # 下一段从上一段结尾往前 overlap 处起（保留重叠）；至少前进 1 保证终止
        start = max(start + 1, end - overlap)
    return chunks


def _last_boundary(text: str, lo: int, hi: int) -> Optional[int]:
    """返回 [lo, hi) 内最后一个边界字符的下一位置；无则 None。"""
    for i in range(hi - 1, lo - 1, -1):
        if text[i] in _BOUNDARIES:
            return i + 1
    return None


class AudioVectorStore:
    """音频转写文本的持久向量读写（chromadb 1.x raw API）。"""

    def __init__(
        self,
        path: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedder: Optional[object] = None,
        persistent: bool = True,
    ):
        self._path = path or settings.audio_index_path
        self._collection_name = collection_name or settings.audio_index_collection
        self._embedder = embedder if embedder is not None else EmbeddingManager()
        self._persistent = persistent
        self._client = None
        self._collection = None

    # ---------- 懒加载 ----------
    def _ensure_client(self):
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            cs = ChromaSettings(anonymized_telemetry=False)
            if self._persistent:
                logger.info(f"打开音频向量库: {self._path}")
                self._client = chromadb.PersistentClient(path=self._path, settings=cs)
            else:
                self._client = chromadb.EphemeralClient(settings=cs)

    def _ensure_collection(self):
        self._ensure_client()
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    # ---------- 写入 ----------
    def index_transcript(
        self, media_id: int, craft_name: str, title: str, full_text: str
    ) -> int:
        """为一条音频建/重建转写索引。幂等：先按 media_id 清旧再 add。返回分块数。"""
        self._ensure_collection()
        self._collection.delete(where={"media_id": media_id})  # 幂等重入

        chunks = split_transcript(full_text, settings.audio_chunk_max_chars, settings.audio_chunk_overlap)
        if not chunks:
            logger.warning(f"media_id={media_id} 转写文本为空，跳过入库")
            return 0

        embeddings = self._embedder.embed_documents(chunks)
        ids = [f"{media_id}:c{i}" for i in range(len(chunks))]
        metas = [
            {
                "media_id": media_id,
                "craft_name": craft_name,
                "title": title,
                "chunk_idx": i,
            }
            for i in range(len(chunks))
        ]
        # chroma 要求 ids/embeddings/metadatas/documents 等长
        if len(embeddings) != len(chunks):
            raise ValueError(f"embed_documents 返回 {len(embeddings)} 条，期望 {len(chunks)} 条")
        self._collection.add(ids=ids, embeddings=embeddings, metadatas=metas, documents=chunks)
        logger.info(f"media_id={media_id} 入库 {len(chunks)} 个分块")
        return len(chunks)

    def delete_media(self, media_id: int) -> None:
        """删除一条音频的全部向量。"""
        self._ensure_collection()
        self._collection.delete(where={"media_id": media_id})

    # ---------- 检索 ----------
    def search(
        self,
        query: str,
        top_k: int = 10,
        craft_name: Optional[str] = None,
    ) -> List[Dict]:
        """向量检索转写分块；embedding 异常自动降级子串匹配。

        返回每条 chunk：{chunk_id, media_id, craft_name, title, chunk_idx, snippet, score}
        """
        q = (query or "").strip()
        if not q:
            return []
        where = {"craft_name": craft_name} if craft_name else None

        self._ensure_collection()
        try:
            qe = self._embedder.embed_query(q)
        except Exception as e:
            logger.warning(f"audio embed_query 失败，降级子串检索: {e}")
            return self._search_substring(q, where, top_k)

        try:
            res = self._collection.query(
                query_embeddings=[qe],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning(f"audio chroma query 失败，降级子串检索: {e}")
            return self._search_substring(q, where, top_k)

        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        out: List[Dict] = []
        for i in range(len(ids or [])):
            meta = metas[i] or {}
            score = max(0.0, 1.0 - float(dists[i])) if i < len(dists) else 0.0
            out.append(self._hit(ids[i], meta, docs[i] if i < len(docs) else "", score))
        return out

    def _search_substring(self, q: str, where: Optional[dict], top_k: int) -> List[Dict]:
        """降级：chroma where_document $contains 子串匹配（score 恒 0）。"""
        res = self._collection.get(
            where=where,
            where_document={"$contains": q},
            limit=top_k,
        )
        ids = res.get("ids") or []
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        return [
            self._hit(ids[i], metas[i] or {}, docs[i] if i < len(docs) else "", 0.0)
            for i in range(len(ids))
        ]

    @staticmethod
    def _hit(chunk_id: str, meta: dict, snippet: str, score: float) -> Dict:
        return {
            "chunk_id": chunk_id,
            "media_id": int(meta.get("media_id", 0)),
            "craft_name": meta.get("craft_name", ""),
            "title": meta.get("title", ""),
            "chunk_idx": int(meta.get("chunk_idx", 0)),
            "snippet": snippet,
            "score": score,
        }


# 进程级单例（worker / API 共用）
_audio_store: Optional[AudioVectorStore] = None


def get_audio_store() -> AudioVectorStore:
    global _audio_store
    if _audio_store is None:
        _audio_store = AudioVectorStore()
    return _audio_store


def reset_audio_store() -> None:
    global _audio_store
    _audio_store = None
