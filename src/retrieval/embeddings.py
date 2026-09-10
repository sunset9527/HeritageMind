"""
Embedding 管理器 — 本地 BGE-M3 优先，智谱 API 兜底

策略（按 embedding_mode）:
  - "local_first"（默认）: 先尝试加载本地 BGE-M3，加载失败则降级到智谱 API
  - "local": 仅使用本地模型，不降级
  - "api": 仅使用智谱 API，不尝试本地
"""
import os
import logging
from typing import Optional, List
from openai import OpenAI

from config import settings

logger = logging.getLogger(__name__)

_embedding_model: Optional[object] = None
_embedding_backend: Optional[str] = None  # "local" 或 "api"


def get_embedding_model() -> object:
    """获取嵌入模型实例（延迟加载，本地优先、API 兜底）"""
    global _embedding_model, _embedding_backend
    if _embedding_model is not None:
        return _embedding_model

    mode = settings.embedding_mode

    # ── 仅 API 模式 ──
    if mode == "api":
        if not settings.zhipu_api_key:
            raise ValueError("embedding_mode=api 但 zhipu_api_key 未配置")
        _embedding_model = _create_zhipu_client()
        _embedding_backend = "api"
        logger.info(f"Embedding 后端: 智谱 API ({settings.embedding_model})")
        return _embedding_model

    # ── only local 模式 ──
    if mode == "local":
        _embedding_model = _create_local_model()
        _embedding_backend = "local"
        logger.info(f"Embedding 后端: 本地模型 ({settings.local_embedding_model_path})")
        return _embedding_model

    # ── local_first 模式（默认）: 本地优先，失败降级 API ──
    _embedding_model = _try_create_local()
    if _embedding_model is not None:
        _embedding_backend = "local"
        logger.info(f"Embedding 后端: 本地 BGE-M3 ({settings.local_embedding_model_path})")
        return _embedding_model

    if settings.zhipu_api_key:
        _embedding_model = _create_zhipu_client()
        _embedding_backend = "api"
        logger.warning("本地 BGE-M3 不可用，降级为智谱 Embedding API")
        return _embedding_model

    raise RuntimeError(
        "Embedding 初始化失败：本地 BGE-M3 不可用，且 zhipu_api_key 未配置。"
        f"请检查模型路径: {settings.local_embedding_model_path}"
    )


def _try_create_local():
    """尝试加载本地 BGE-M3 模型，失败返回 None"""
    model_path = settings.local_embedding_model_path
    if not os.path.isdir(model_path):
        logger.warning(f"本地模型路径不存在: {model_path}")
        return None

    required_files = ["config.json", "pytorch_model.bin", "tokenizer.json"]
    for f in required_files:
        if not os.path.isfile(os.path.join(model_path, f)):
            logger.warning(f"本地模型文件缺失: {model_path}/{f}")
            return None

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        model = HuggingFaceEmbeddings(
            model_name=model_path,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
        )
        # 触发一次实际加载，确认模型可用
        model.embed_query("测试")
        return model
    except Exception as e:
        logger.warning(f"本地 BGE-M3 加载失败: {e}")
        return None


def _create_zhipu_client():
    """创建智谱 API 客户端"""
    return OpenAI(
        api_key=settings.zhipu_api_key,
        base_url=settings.zhipu_base_url,
    )


def _create_local_model():
    """强制创建本地模型（不检查存在性，供 local 模式使用）"""
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=settings.local_embedding_model_path,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
    )


def reset_embedding_model():
    """重置嵌入模型"""
    global _embedding_model, _embedding_backend
    _embedding_model = None
    _embedding_backend = None


def get_embedding_backend() -> Optional[str]:
    """返回当前使用的 embedding 后端: 'local' 或 'api'"""
    return _embedding_backend


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

    def _is_api_backend(self) -> bool:
        """判断当前是否使用 API 后端"""
        return _embedding_backend == "api"

    def embed_query(self, text: str) -> List[float]:
        if text in self._cache:
            return self._cache[text]

        if self._is_api_backend():
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
        uncached = [(i, t) for i, t in enumerate(texts) if t not in self._cache]

        if uncached:
            if self._is_api_backend():
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
