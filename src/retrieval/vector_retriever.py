"""
ChromaDB向量检索器 - 基于Chroma向量数据库的语义检索
"""

import logging
import os
from typing import List, Dict, Any, Optional, Union
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document as LangchainDocument

from config import settings
from .embeddings import get_embedding_model

logger = logging.getLogger(__name__)


class VectorRetriever:
    """
    ChromaDB向量检索器
    
    基于Chroma向量数据库实现语义检索
    documents格式: [{"id": str, "content": str, "metadata": dict}, ...]
    """
    
    def __init__(
        self,
        collection_name: str = "heritage_documents",
        persist_directory: Optional[str] = None
    ):
        """
        初始化向量检索器
        
        Args:
            collection_name: 集合名称
            persist_directory: 持久化目录，默认从config读取
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory or settings.vector_db_path
        
        self._embedding_model = None
        self._vectorstore: Optional[Chroma] = None
        self._initialized = False
    
    @property
    def embedding_model(self):
        """获取嵌入模型（懒加载）"""
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model
    
    @property
    def vectorstore(self) -> Optional[Chroma]:
        """获取向量存储实例"""
        return self._vectorstore
    
    def _ensure_directory(self) -> None:
        """确保持久化目录存在"""
        if not os.path.exists(self.persist_directory):
            os.makedirs(self.persist_directory, exist_ok=True)
            logger.info(f"创建向量数据库目录: {self.persist_directory}")
    
    def _documents_to_langchain(self, documents: List[Dict[str, Any]]) -> tuple:
        """
        将文档格式转换为LangChain Document格式
        
        Args:
            documents: 原始文档列表
        
        Returns:
            (langchain_docs, ids) 元组
        """
        langchain_docs = []
        ids = []
        
        for doc in documents:
            doc_id = doc.get("id", "")
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            
            # 确保metadata可序列化
            serializable_metadata = {}
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool, type(None))):
                    serializable_metadata[k] = v
                else:
                    serializable_metadata[k] = str(v)
            
            langchain_docs.append(
                LangchainDocument(
                    page_content=content,
                    metadata={**serializable_metadata, "doc_id": doc_id}
                )
            )
            ids.append(doc_id)
        
        return langchain_docs, ids
    
    def build_index(
        self,
        documents: List[Dict[str, Any]],
        recreate: bool = False
    ) -> None:
        """
        构建向量索引
        
        Args:
            documents: 文档列表
            recreate: 是否重建索引（清空现有数据）
        """
        if not documents:
            logger.warning("构建向量索引时收到空文档列表")
            return
        
        self._ensure_directory()
        
        # 如果存在且不重建，尝试加载现有数据
        if os.path.exists(self.persist_directory) and not recreate:
            try:
                self._vectorstore = Chroma(
                    collection_name=self.collection_name,
                    persist_directory=self.persist_directory,
                    embedding_function=self.embedding_model
                )
                
                # 检查现有集合中的文档数
                existing_count = self._vectorstore._collection.count()
                if existing_count > 0:
                    logger.info(f"加载现有向量数据库: {existing_count} 篇文档")
                    self._initialized = True
                    return
            except Exception as e:
                logger.warning(f"加载现有向量数据库失败: {e}，将重建")
        
        # 转换文档格式
        langchain_docs, ids = self._documents_to_langchain(documents)
        
        # 创建新的向量存储
        self._vectorstore = Chroma.from_documents(
            documents=langchain_docs,
            embedding=self.embedding_model,
            ids=ids,
            collection_name=self.collection_name,
            persist_directory=self.persist_directory
        )
        
        logger.info(f"向量索引构建完成: {len(documents)} 篇文档")
        self._initialized = True
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None,
        include_scores: bool = True
    ) -> List[Dict[str, Any]]:
        """
        检索相似文档
        
        Args:
            query: 查询文本
            top_k: 返回的Top-K结果
            filter_criteria: 过滤条件，格式: {"field": "value"}
            include_scores: 是否包含相似度分数
        
        Returns:
            检索结果列表，格式: [{"doc_id": str, "content": str, "score": float, "metadata": dict}, ...]
        """
        if self._vectorstore is None:
            logger.warning("向量索引未构建，请先调用build_index()")
            return []
        
        # 执行相似度搜索
        try:
            results = self._vectorstore.similarity_search_with_score(
                query=query,
                k=top_k,
                filter=filter_criteria
            )
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
        
        # 转换结果格式
        formatted_results = []
        for doc, score in results:
            doc_id = doc.metadata.get("doc_id", "")
            
            formatted_results.append({
                "doc_id": doc_id,
                "content": doc.page_content,
                "score": float(score) if include_scores else 0.0,
                "metadata": {k: v for k, v in doc.metadata.items() if k != "doc_id"}
            })
        
        return formatted_results
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        添加文档到向量索引
        
        Args:
            documents: 要添加的文档列表
        """
        if not documents:
            return
        
        if self._vectorstore is None:
            # 如果没有现有索引，构建新索引
            self.build_index(documents)
            return
        
        # 转换格式
        langchain_docs, ids = self._documents_to_langchain(documents)
        
        # 添加到向量存储
        self._vectorstore.add_documents(documents=langchain_docs, ids=ids)
        
        # 持久化
        self._vectorstore.persist()
        
        logger.info(f"添加 {len(documents)} 篇文档到向量索引")
    
    def remove_documents(self, doc_ids: List[str]) -> None:
        """
        从向量索引中移除文档
        
        Args:
            doc_ids: 要移除的文档ID列表
        """
        if self._vectorstore is None:
            return
        
        try:
            self._vectorstore.delete(ids=doc_ids)
            self._vectorstore.persist()
            logger.info(f"从向量索引移除 {len(doc_ids)} 篇文档")
        except Exception as e:
            logger.error(f"移除文档失败: {e}")
    
    def get_count(self) -> int:
        """获取索引中的文档数量"""
        if self._vectorstore is None:
            return 0
        try:
            return self._vectorstore._collection.count()
        except Exception:
            return 0
    
    def clear(self) -> None:
        """清空向量索引"""
        if self._vectorstore is None:
            return
        
        try:
            self._vectorstore.delete_collection()
            self._vectorstore = None
            self._initialized = False
            logger.info("向量索引已清空")
        except Exception as e:
            logger.error(f"清空索引失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取检索器统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory,
            "document_count": self.get_count(),
            "initialized": self._initialized
        }
