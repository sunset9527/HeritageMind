"""
BGE Embedding 管理器 - 提供统一的嵌入模型管理
"""

import logging
from typing import Optional, List
from langchain_huggingface import HuggingFaceEmbeddings

from config import settings

logger = logging.getLogger(__name__)

# 全局嵌入模型实例（延迟加载）
_embedding_model: Optional[HuggingFaceEmbeddings] = None


def get_embedding_model(
    model_name: Optional[str] = None,
    device: Optional[str] = None,
    encode_kwargs: Optional[dict] = None,
    model_kwargs: Optional[dict] = None
) -> HuggingFaceEmbeddings:
    """
    获取BGE嵌入模型实例（工厂函数，延迟加载）
    
    Args:
        model_name: 模型名称，默认使用config中的设置
        device: 设备，默认使用CPU
        encode_kwargs: 编码参数
        model_kwargs: 模型参数
    
    Returns:
        HuggingFaceEmbeddings实例
    """
    global _embedding_model
    
    # 如果已存在直接返回
    if _embedding_model is not None:
        return _embedding_model
    
    # 获取配置
    model_name = model_name or settings.embedding_model
    embedding_dims = settings.embedding_dimensions
    
    # 合并模型参数
    _model_kwargs = model_kwargs or {"model_name": model_name}
    if "device" not in _model_kwargs:
        _model_kwargs["device"] = device or "cpu"
    if "model_kwargs" not in _model_kwargs:
        _model_kwargs["model_kwargs"] = {}
    
    # 编码参数
    _encode_kwargs = encode_kwargs or {
        "normalize_embeddings": True,  # BGE模型推荐归一化
        "batch_size": 32
    }
    
    try:
        _embedding_model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=_model_kwargs,
            encode_kwargs=_encode_kwargs
        )
        logger.info(f"嵌入模型加载成功: {model_name}, 维度: {embedding_dims}")
        return _embedding_model
    except Exception as e:
        logger.error(f"嵌入模型加载失败: {e}")
        raise


def reset_embedding_model():
    """重置嵌入模型实例（用于重新加载或更换模型）"""
    global _embedding_model
    _embedding_model = None
    logger.info("嵌入模型实例已重置")


def get_embedding_dimension() -> int:
    """获取嵌入向量维度"""
    return settings.embedding_dimensions


class EmbeddingManager:
    """
    嵌入管理器类 - 提供更灵活的嵌入管理
    
    支持：
    - 多模型切换
    - 批量编码
    - 缓存管理
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        device: str = "cpu"
    ):
        """
        初始化嵌入管理器
        
        Args:
            model_name: 模型名称
            device: 设备
        """
        self.model_name = model_name or settings.embedding_model
        self.device = device
        self._model: Optional[HuggingFaceEmbeddings] = None
        self._cache: dict = {}  # 简单缓存
    
    @property
    def model(self) -> HuggingFaceEmbeddings:
        """获取模型实例（懒加载）"""
        if self._model is None:
            self._model = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs={"device": self.device},
                encode_kwargs={"normalize_embeddings": True}
            )
        return self._model
    
    def embed_query(self, text: str) -> List[float]:
        """
        嵌入单个查询文本
        
        Args:
            text: 文本
        
        Returns:
            嵌入向量
        """
        # 检查缓存
        if text in self._cache:
            return self._cache[text]
        
        embedding = self.model.embed_query(text)
        
        # 缓存结果
        if len(self._cache) < 1000:  # 限制缓存大小
            self._cache[text] = embedding
        
        return embedding
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量嵌入文档
        
        Args:
            texts: 文档列表
        
        Returns:
            嵌入向量列表
        """
        # 过滤已缓存的
        uncached = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            if text not in self._cache:
                uncached.append(text)
                uncached_indices.append(i)
        
        # 批量编码未缓存的
        if uncached:
            embeddings = self.model.embed_documents(uncached)
            
            # 更新缓存
            for idx, emb in zip(uncached_indices, embeddings):
                if len(self._cache) < 1000:
                    self._cache[texts[idx]] = emb
        
        # 返回结果
        return [self._cache.get(text, []) for text in texts]
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("嵌入缓存已清空")
