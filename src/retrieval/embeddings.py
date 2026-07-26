"""
Embedding 管理器 — 支持智谱 API 和本地 BGE 模型

智谱 API: embedding-2 模型，1024维，OpenAI 兼容格式
本地模式: BAAI/bge-large-zh-v1.5，via HuggingFaceEmbeddings
"""
import logging
from typing import Optional, List
from openai import OpenAI

from config import settings

logger = logging.getLogger(__name__)

_embedding_model: Optional[object] = None


def get_embedding_model() -> object:
    """获取嵌入模型实例（延迟加载，工厂函数）"""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    if settings.embedding_mode == "api" and settings.zhipu_api_key:
        _embedding_model = _create_zhipu_client()
        logger.info(f"智谱 Embedding API 就绪: {settings.embedding_model}")
    else:
        _embedding_model = _create_local_model()
        logger.info(f"本地 Embedding 模型就绪: {settings.embedding_model}")
    return _embedding_model


def _create_zhipu_client():
    """创建智谱 API 客户端"""
    return OpenAI(
        api_key=settings.zhipu_api_key,
        base_url=settings.zhipu_base_url,
    )


def _create_local_model():
    """创建本地 BGE 模型"""
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
    )


def reset_embedding_model():
    """重置嵌入模型"""
    global _embedding_model
    _embedding_model = None


def get_embedding_dimension() -> int:
    return settings.embedding_dimensions


class EmbeddingManager:
    """嵌入管理器"""

    def __init__(self, model_name: Optional[str] = None, device: str = "cpu"):
        self.model_name = model_name or settings.embedding_model
        self.device = device
        self._model: Optional[object] = None
        self._cache: dict = {}

    @property
    def model(self):
        if self._model is None:
            self._model = get_embedding_model()
        return self._model

    def embed_query(self, text: str) -> List[float]:
        if text in self._cache:
            return self._cache[text]

        if settings.embedding_mode == "api" and settings.zhipu_api_key:
            resp = self.model.embeddings.create(
                model=settings.embedding_model,
                input=text,
            )
            emb = resp.data[0].embedding
        else:
            emb = self.model.embed_query(text)

        if len(self._cache) < 1000:
            self._cache[text] = emb
        return emb

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        uncached = [(i, t) for i, t in enumerate(texts) if t not in self._cache]

        if uncached:
            if settings.embedding_mode == "api" and settings.zhipu_api_key:
                for _, t in uncached:
                    resp = self.model.embeddings.create(
                        model=settings.embedding_model,
                        input=t,
                    )
                    emb = resp.data[0].embedding
                    if len(self._cache) < 1000:
                        self._cache[t] = emb
            else:
                uncached_texts = [t for _, t in uncached]
                embeddings = self.model.embed_documents(uncached_texts)
                for (i, _), emb in zip(uncached, embeddings):
                    if len(self._cache) < 1000:
                        self._cache[texts[i]] = emb

        return [self._cache.get(t, []) for t in texts]

    def clear_cache(self):
        self._cache.clear()
