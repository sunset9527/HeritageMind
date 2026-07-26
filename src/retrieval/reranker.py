"""
CrossEncoder 重排序模块 — 对初检结果逐对精细打分，重排后取 top-k

使用 BAAI/bge-reranker-base（中文语义匹配专用小模型，约 1.1GB）。
首次加载需下载模型，后续调用缓存在内存中。
"""

import logging
from typing import List, Dict, Any, Optional

from config import settings

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-Encoder 重排序器 — 对 (query, doc) 逐对打分"""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.reranker_model
        self._model = None
        self._available = True

    def _load(self):
        """延迟加载模型（首次调用时触发）"""
        if self._model is not None:
            return
        if not self._available:
            return
        if not settings.reranker_enabled:
            logger.info("Reranker 已禁用（config.reranker_enabled=False）")
            self._available = False
            return
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name, max_length=512)
            logger.info(f"Reranker 模型加载完成: {self.model_name}")
        except ImportError:
            logger.warning("sentence_transformers 未安装，Reranker 不可用")
            self._available = False
        except Exception as e:
            logger.warning(f"Reranker 模型加载失败: {e}")
            self._available = False

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        对检索结果重排序。

        将 (query, doc_content) 逐对送入 CrossEncoder，
        按模型打分降序排列，取 top_k 返回。
        """
        if not documents:
            return []

        top_k = top_k or settings.top_k
        self._load()

        if not self._model:
            # 模型不可用：回退到规则排序
            logger.debug("Reranker 不可用，按已有分数排序")
            return sorted(
                documents,
                key=lambda d: d.get("score", d.get("similarity", 0)),
                reverse=True,
            )[:top_k]

        try:
            # 构造 (query, doc) 对
            pairs = [
                (query, d.get("content", "")[:1024])
                for d in documents
            ]
            scores = self._model.predict(pairs, show_progress_bar=False)

            # 附加分数并排序
            for doc, score in zip(documents, scores):
                doc["rerank_score"] = float(score)
                doc["score"] = float(score)  # 覆盖初检分数

            ranked = sorted(documents, key=lambda d: d["score"], reverse=True)
            logger.debug(f"Reranker 完成：{len(documents)}篇 → top {min(top_k, len(ranked))}")
            return ranked[:top_k]

        except Exception as e:
            logger.warning(f"Reranker 打分失败（降级到规则排序）: {e}")
            return sorted(
                documents,
                key=lambda d: d.get("score", d.get("similarity", 0)),
                reverse=True,
            )[:top_k]


class BatchCrossEncoderReranker(CrossEncoderReranker):
    """批量重排序器（接口兼容，内部复用 CrossEncoderReranker）"""

    def rerank_batch(
        self,
        queries_and_docs: List[tuple],
        top_k: Optional[int] = None,
    ) -> List[List[Dict[str, Any]]]:
        return [self.rerank(q, docs, top_k) for q, docs in queries_and_docs]


# === 全局单例 ===
_reranker: Optional[CrossEncoderReranker] = None


def get_reranker_model() -> CrossEncoderReranker:
    """获取全局 Reranker 单例"""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker


def reset_reranker_model():
    """重置全局 Reranker（释放内存）"""
    global _reranker
    _reranker = None
