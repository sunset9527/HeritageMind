"""
Cross-Encoder Reranker - 使用Cross-Encoder模型对检索结果进行重排序
"""

import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder

from config import settings

logger = logging.getLogger(__name__)

# 全局Cross-Encoder模型实例（延迟加载）
_cross_encoder: Optional[CrossEncoder] = None


def get_reranker_model(
    model_name: Optional[str] = None
) -> CrossEncoder:
    """
    获取Cross-Encoder重排序模型（工厂函数，延迟加载）
    
    Args:
        model_name: 模型名称，默认使用config中的设置
    
    Returns:
        CrossEncoder实例
    """
    global _cross_encoder
    
    if _cross_encoder is not None:
        return _cross_encoder
    
    model_name = model_name or settings.reranker_model
    
    try:
        _cross_encoder = CrossEncoder(
            model_name=model_name,
            max_length=512,
            automodel_args={"torch_dtype": "auto"},
            trust_remote_code=True
        )
        logger.info(f"Cross-Encoder模型加载成功: {model_name}")
        return _cross_encoder
    except Exception as e:
        logger.error(f"Cross-Encoder模型加载失败: {e}")
        raise


def reset_reranker_model():
    """重置Cross-Encoder模型实例"""
    global _cross_encoder
    _cross_encoder = None
    logger.info("Cross-Encoder模型实例已重置")


class CrossEncoderReranker:
    """
    Cross-Encoder重排序器
    
    使用Cross-Encoder模型对检索结果进行更精确的重排序
    documents格式: [{"doc_id": str, "content": str, "score": float, "metadata": dict}, ...]
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        max_length: int = 512
    ):
        """
        初始化重排序器
        
        Args:
            model_name: 模型名称
            max_length: 最大序列长度
        """
        self.model_name = model_name or settings.reranker_model
        self.max_length = max_length
        self._model: Optional[CrossEncoder] = None
    
    @property
    def model(self) -> CrossEncoder:
        """获取模型实例（懒加载）"""
        if self._model is None:
            self._model = CrossEncoder(
                model_name=self.model_name,
                max_length=self.max_length,
                automodel_args={"torch_dtype": "auto"},
                trust_remote_code=True
            )
            logger.info(f"Cross-Encoder模型加载: {self.model_name}")
        return self._model
    
    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        对检索结果进行重排序
        
        Args:
            query: 查询文本
            documents: 待重排序的文档列表
            top_k: 返回的Top-K结果
            
        Returns:
            重排序后的结果列表，格式: [{"doc_id": str, "content": str, "score": float, "metadata": dict}, ...]
        """
        if not documents:
            return []
        
        # 准备输入对
        doc_contents = [doc.get("content", "") for doc in documents]
        sentence_pairs = [[query, content] for content in doc_contents]
        
        try:
            # 获取相关性分数
            scores = self.model.predict(sentence_pairs)
            
            # 转换为列表并按分数排序
            scored_docs = []
            for i, doc in enumerate(documents):
                scored_docs.append({
                    "doc_id": doc.get("doc_id", ""),
                    "content": doc.get("content", ""),
                    "score": float(scores[i]),
                    "metadata": doc.get("metadata", {})
                })
            
            # 按新分数降序排序
            scored_docs.sort(key=lambda x: x["score"], reverse=True)
            
            # 返回Top-K
            return scored_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Cross-Encoder重排序失败: {e}")
            # 失败时返回原始结果
            return documents[:top_k]
    
    def compute_scores(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> List[float]:
        """
        计算查询与文档的相关性分数
        
        Args:
            query: 查询文本
            documents: 文档列表
            
        Returns:
            相关性分数列表
        """
        if not documents:
            return []
        
        doc_contents = [doc.get("content", "") for doc in documents]
        sentence_pairs = [[query, content] for content in doc_contents]
        
        try:
            scores = self.model.predict(sentence_pairs)
            return [float(s) for s in scores]
        except Exception as e:
            logger.error(f"分数计算失败: {e}")
            return [0.0] * len(documents)


class BatchCrossEncoderReranker(CrossEncoderReranker):
    """
    批量Cross-Encoder重排序器
    
    继承自CrossEncoderReranker，优化批量处理性能
    """
    
    def rerank_batch(
        self,
        queries: List[str],
        documents_list: List[List[Dict[str, Any]]],
        top_k: int = 5
    ) -> List[List[Dict[str, Any]]]:
        """
        批量重排序
        
        Args:
            queries: 查询列表
            documents_list: 每个查询对应的文档列表
            
        Returns:
            每个查询的重排序结果列表
        """
        results = []
        
        for query, docs in zip(queries, documents_list):
            reranked = self.rerank(query, docs, top_k=top_k)
            results.append(reranked)
        
        return results
