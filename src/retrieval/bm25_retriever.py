"""
BM25关键词检索器 - 基于BM25算法的关键词检索
"""

import logging
from typing import List, Dict, Any, Optional
import jieba
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class BM25Retriever:
    """
    BM25关键词检索器
    
    使用BM25算法进行关键词检索，支持中英文分词
    documents格式: [{"id": str, "content": str, "metadata": dict}, ...]
    """
    
    def __init__(self, tokenize_fn: Optional[callable] = None):
        """
        初始化BM25检索器
        
        Args:
            tokenize_fn: 自定义分词函数，默认使用jieba
        """
        self.tokenize_fn = tokenize_fn or self._default_tokenize
        self.bm25: Optional[BM25Okapi] = None
        self.documents: List[Dict[str, Any]] = []
        self.doc_id_to_idx: Dict[str, int] = {}
    
    @staticmethod
    def _default_tokenize(text: str) -> List[str]:
        """
        默认分词函数（使用jieba）
        
        Args:
            text: 文本
        
        Returns:
            分词列表
        """
        return list(jieba.cut(text))
    
    def build_index(self, documents: List[Dict[str, Any]]) -> None:
        """
        构建BM25索引
        
        Args:
            documents: 文档列表，每项包含id, content, metadata
        """
        if not documents:
            logger.warning("构建BM25索引时收到空文档列表")
            return
        
        self.documents = documents
        
        # 建立doc_id到索引的映射
        self.doc_id_to_idx = {
            doc.get("id", f"doc_{i}"): i 
            for i, doc in enumerate(documents)
        }
        
        # 提取内容并分词
        tokenized_corpus = [
            self.tokenize_fn(doc.get("content", ""))
            for doc in documents
        ]
        
        # 构建BM25索引
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        logger.info(f"BM25索引构建完成: {len(documents)}篇文档")
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_fn: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回的Top-K结果
            filter_fn: 可选的过滤函数，接收(doc_id, doc)返回bool
        
        Returns:
            检索结果列表，格式: [{"doc_id": str, "content": str, "score": float, "metadata": dict}, ...]
        """
        if self.bm25 is None:
            logger.warning("BM25索引未构建，请先调用build_index()")
            return []
        
        # 分词查询
        tokenized_query = self.tokenize_fn(query)
        
        # 获取所有文档的BM25分数
        scores = self.bm25.get_scores(tokenized_query)
        
        # 按分数排序获取Top-K
        top_indices = sorted(
            range(len(scores)), 
            key=lambda i: scores[i], 
            reverse=True
        )[:top_k]
        
        results = []
        for idx in top_indices:
            doc = self.documents[idx]
            doc_id = doc.get("id", f"doc_{idx}")
            
            # 过滤检查
            if filter_fn and not filter_fn(doc_id, doc):
                continue
            
            results.append({
                "doc_id": doc_id,
                "content": doc.get("content", ""),
                "score": float(scores[idx]),
                "metadata": doc.get("metadata", {})
            })
        
        return results
    
    def get_scores(self, query: str) -> Dict[str, float]:
        """
        获取查询对所有文档的BM25分数
        
        Args:
            query: 查询文本
        
        Returns:
            doc_id到分数的映射
        """
        if self.bm25 is None:
            return {}
        
        tokenized_query = self.tokenize_fn(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        return {
            self.documents[i].get("id", f"doc_{i}"): float(scores[i])
            for i in range(len(scores))
        }
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        添加文档到现有索引（重新构建索引）
        
        Args:
            documents: 要添加的文档列表
        """
        # 合并文档
        existing_ids = set(self.doc_id_to_idx.keys())
        new_docs = [d for d in documents if d.get("id") not in existing_ids]
        
        if new_docs:
            self.documents.extend(new_docs)
            # 重建索引
            self.build_index(self.documents)
            logger.info(f"添加 {len(new_docs)} 篇文档并重建索引")
    
    def remove_document(self, doc_id: str) -> bool:
        """
        从索引中移除文档
        
        Args:
            doc_id: 文档ID
        
        Returns:
            是否成功移除
        """
        if doc_id not in self.doc_id_to_idx:
            return False
        
        # 过滤掉目标文档
        self.documents = [
            d for d in self.documents 
            if d.get("id") != doc_id
        ]
        
        # 重建索引
        if self.documents:
            self.build_index(self.documents)
        else:
            self.bm25 = None
            self.doc_id_to_idx = {}
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取检索器统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "total_documents": len(self.documents),
            "indexed": self.bm25 is not None,
            "corpus_size": len(self.documents)
        }
