"""
Cross-Encoder 重排序模块

对初检结果进行精细排序，提升检索精度。
当前为占位实现——完整版等待 v1.0.2 迭代。
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-Encoder 重排序器"""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._model = None
        logger.info(f"Reranker 初始化（延迟加载）: {model_name}")

    def _load_model(self):
        """延迟加载模型"""
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name, max_length=512)
            logger.info(f"Reranker 模型加载完成: {self.model_name}")
        except ImportError:
            logger.warning("sentence_transformers 未安装，使用规则评分降级")
        except Exception as e:
            logger.warning(f"Reranker 模型加载失败（使用规则评分降级）: {e}")

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        对检索结果重排序

        当前实现：按已有相似度分数降序排列（规则降级）。
        完整版将在 v1.0.2 中接入 Cross-Encoder 模型。
        """
        if not documents:
            return []

        # 规则降级：按已有分数排序
        scored = sorted(
            documents,
            key=lambda d: d.get("score", d.get("relevance", 0)),
            reverse=True,
        )
        return scored[:top_k]


class BatchCrossEncoderReranker(CrossEncoderReranker):
    """批量重排序器"""

    def rerank_batch(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        return self.rerank(query, documents, top_k)


# 全局实例缓存
_reranker_model: Optional[CrossEncoderReranker] = None


def get_reranker_model() -> CrossEncoderReranker:
    global _reranker_model
    if _reranker_model is None:
        _reranker_model = CrossEncoderReranker()
    return _reranker_model


def reset_reranker_model():
    global _reranker_model
    _reranker_model = None
