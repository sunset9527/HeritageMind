"""
多源检索器 - 支持多种检索策略的检索器
"""

import logging
from typing import Dict, List, Optional, Any, Callable
import numpy as np

from config import settings, get_retriever_config
from src.retrieval.document_loader import HeritageDocumentLoader

logger = logging.getLogger(__name__)


class MultiSourceRetriever:
    """
    多源检索器
    
    支持多种检索策略：
    1. 关键词检索
    2. 语义检索（基于嵌入向量）
    3. 混合检索
    4. 过滤检索
    
    功能：
    - 从多个数据源检索
    - 排序和去重
    - 相似度阈值过滤
    """
    
    def __init__(
        self,
        document_loader: Optional[HeritageDocumentLoader] = None,
        embedding_func: Optional[Callable] = None
    ):
        """
        初始化多源检索器
        
        Args:
            document_loader: 文档加载器
            embedding_func: 嵌入函数，用于语义检索
        """
        self.document_loader = document_loader or HeritageDocumentLoader()
        self.embedding_func = embedding_func
        self.config = get_retriever_config()
        
        # 内存中的文档存储
        self.documents: List[Dict[str, Any]] = []
        self.document_embeddings: Dict[str, List[float]] = {}
        
        # 初始化文档
        self._load_documents()
    
    def _load_documents(self):
        """加载文档到内存"""
        self.documents = self.document_loader.load_craft_documents()
        logger.info(f"已加载{len(self.documents)}篇文档")
    
    def set_embedding_func(self, embedding_func: Callable):
        """
        设置嵌入函数
        
        Args:
            embedding_func: 接受文本返回向量列表的函数
        """
        self.embedding_func = embedding_func
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_type: Optional[str] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回的Top-K结果
            filter_type: 文档类型过滤
            similarity_threshold: 相似度阈值
        
        Returns:
            检索结果列表
        """
        if top_k is None:
            top_k = self.config["top_k"]
        if similarity_threshold is None:
            similarity_threshold = self.config["similarity_threshold"]
        
        # 过滤文档
        docs = self._filter_documents(filter_type)
        
        # 关键词匹配检索
        keyword_results = self._keyword_search(query, docs)
        
        # 如果有嵌入函数，执行语义检索
        if self.embedding_func is not None and self.document_embeddings:
            semantic_results = self._semantic_search(query, docs)
            # 合并结果
            results = self._merge_results(keyword_results, semantic_results)
        else:
            results = keyword_results
        
        # 过滤低相似度结果
        results = [
            r for r in results
            if r.get("similarity", 1.0) >= similarity_threshold
        ]
        
        # 返回Top-K
        return results[:top_k]
    
    def _filter_documents(
        self,
        filter_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """过滤文档"""
        if filter_type is None:
            return self.documents
        
        # 按类型过滤
        filtered = []
        for doc in self.documents:
            doc_type = doc.get("metadata", {}).get("type", "")
            if filter_type in doc_type or filter_type in doc.get("id", ""):
                filtered.append(doc)
        
        return filtered if filtered else self.documents
    
    def _keyword_search(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        关键词检索
        
        Args:
            query: 查询文本
            documents: 文档列表
        
        Returns:
            检索结果
        """
        query_keywords = self._extract_keywords(query)
        results = []
        
        for doc in documents:
            content = doc["content"].lower()
            doc_keywords = doc.get("metadata", {}).get("keywords", [])
            
            # 计算匹配分数
            match_count = 0
            matched_keywords = []
            
            for kw in query_keywords:
                if kw.lower() in content:
                    match_count += 1
                    matched_keywords.append(kw)
            
            # 检查标题和元数据关键词
            for kw in doc_keywords:
                if kw.lower() in query.lower():
                    match_count += 2  # 元数据关键词权重更高
                    matched_keywords.append(kw)
            
            if match_count > 0:
                similarity = min(match_count / max(len(query_keywords), 1) * 0.8, 1.0)
                results.append({
                    **doc,
                    "similarity": similarity,
                    "match_count": match_count,
                    "matched_keywords": list(set(matched_keywords)),
                    "retrieval_type": "keyword"
                })
        
        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results
    
    def _semantic_search(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        语义检索
        
        Args:
            query: 查询文本
            documents: 文档列表
        
        Returns:
            检索结果
        """
        if self.embedding_func is None:
            return []
        
        try:
            # 生成查询嵌入
            query_embedding = self.embedding_func(query)
            
            results = []
            for doc in documents:
                doc_id = doc.get("id", "")
                if doc_id in self.document_embeddings:
                    doc_embedding = self.document_embeddings[doc_id]
                    
                    # 计算余弦相似度
                    similarity = self._cosine_similarity(query_embedding, doc_embedding)
                    
                    results.append({
                        **doc,
                        "similarity": similarity,
                        "retrieval_type": "semantic"
                    })
            
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"语义检索失败: {e}")
            return []
    
    def _merge_results(
        self,
        keyword_results: List[Dict[str, Any]],
        semantic_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        合并关键词和语义检索结果
        
        Args:
            keyword_results: 关键词检索结果
            semantic_results: 语义检索结果
        
        Returns:
            合并后的结果
        """
        # 构建文档ID到结果的映射
        merged = {}
        
        for result in keyword_results:
            doc_id = result.get("id", "")
            merged[doc_id] = {
                **result,
                "keyword_similarity": result.get("similarity", 0),
                "semantic_similarity": 0
            }
        
        for result in semantic_results:
            doc_id = result.get("id", "")
            if doc_id in merged:
                merged[doc_id]["semantic_similarity"] = result.get("similarity", 0)
                # 重新计算综合相似度
                merged[doc_id]["similarity"] = (
                    merged[doc_id]["keyword_similarity"] * 0.4 +
                    result["similarity"] * 0.6
                )
                merged[doc_id]["retrieval_type"] = "hybrid"
            else:
                merged[doc_id] = {
                    **result,
                    "keyword_similarity": 0,
                    "semantic_similarity": result.get("similarity", 0)
                }
        
        # 转换为列表并排序
        results = list(merged.values())
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 文本
        
        Returns:
            关键词列表
        """
        # 简单实现：按空格分词，去除停用词
        stopwords = {"的", "了", "是", "在", "和", "与", "或", "什么", "如何", "怎么", "哪个"}
        
        words = text.split()
        keywords = [w for w in words if len(w) >= 2 and w not in stopwords]
        
        return keywords
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
        
        Returns:
            相似度值
        """
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = np.sqrt(sum(a * a for a in vec1))
        norm2 = np.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def build_index(self, documents: Optional[List[Dict[str, Any]]] = None):
        """
        构建检索索引
        
        Args:
            documents: 要索引的文档，None时使用加载的文档
        """
        if documents is None:
            documents = self.documents
        
        if self.embedding_func is None:
            logger.warning("未设置嵌入函数，跳过索引构建")
            return
        
        logger.info(f"开始构建{len(documents)}篇文档的索引...")
        
        for doc in documents:
            doc_id = doc.get("id", "")
            content = doc.get("content", "")
            
            try:
                embedding = self.embedding_func(content)
                self.document_embeddings[doc_id] = embedding
            except Exception as e:
                logger.error(f"文档嵌入失败 {doc_id}: {e}")
        
        logger.info(f"索引构建完成：{len(self.document_embeddings)}条嵌入")
    
    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        添加文档到检索索引
        
        Args:
            doc_id: 文档ID
            content: 文档内容
            metadata: 元数据
        """
        doc = {
            "id": doc_id,
            "content": content,
            "metadata": metadata or {}
        }
        
        self.documents.append(doc)
        
        # 如果有嵌入函数，更新索引
        if self.embedding_func is not None:
            try:
                embedding = self.embedding_func(content)
                self.document_embeddings[doc_id] = embedding
            except Exception as e:
                logger.error(f"文档嵌入失败: {e}")
    
    def remove_document(self, doc_id: str):
        """
        从索引中移除文档
        
        Args:
            doc_id: 文档ID
        """
        self.documents = [d for d in self.documents if d.get("id") != doc_id]
        
        if doc_id in self.document_embeddings:
            del self.document_embeddings[doc_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取检索器统计信息
        
        Returns:
            统计信息
        """
        return {
            "total_documents": len(self.documents),
            "indexed_documents": len(self.document_embeddings),
            "has_embedding": self.embedding_func is not None,
            "top_k": self.config["top_k"],
            "similarity_threshold": self.config["similarity_threshold"]
        }
