"""
文档检索模块 - 非遗文档加载与多源检索

包含完整的RAG检索管线：
- embeddings: BGE嵌入模型管理
- bm25_retriever: BM25关键词检索
- vector_retriever: ChromaDB向量检索
- fusion: RRF结果融合
- reranker: Cross-Encoder重排序
- query_rewriter: 查询重写
"""

from .document_loader import HeritageDocumentLoader
from .retriever import MultiSourceRetriever

# RAG检索管线组件（容错加载，避免单个依赖缺失导致整个包崩溃）

try:
    from .embeddings import (
        get_embedding_model,
        reset_embedding_model,
        get_embedding_dimension,
        EmbeddingManager
    )
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"embeddings模块加载失败: {e}")
    get_embedding_model = None
    reset_embedding_model = None
    get_embedding_dimension = None
    EmbeddingManager = None

try:
    from .bm25_retriever import BM25Retriever
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"BM25Retriever加载失败（可能缺少jieba）: {e}")
    BM25Retriever = None

try:
    from .vector_retriever import VectorRetriever
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"VectorRetriever加载失败: {e}")
    VectorRetriever = None

try:
    from .fusion import (
        reciprocal_rank_fusion,
        weighted_reciprocal_rank_fusion,
        score_normalize
    )
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"fusion模块加载失败: {e}")
    reciprocal_rank_fusion = None
    weighted_reciprocal_rank_fusion = None
    score_normalize = None

try:
    from .reranker import (
        CrossEncoderReranker,
        BatchCrossEncoderReranker,
        get_reranker_model,
        reset_reranker_model
    )
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"reranker模块加载失败: {e}")
    CrossEncoderReranker = None
    BatchCrossEncoderReranker = None
    get_reranker_model = None
    reset_reranker_model = None

try:
    from .query_rewriter import (
        QueryRewriter,
        SimpleQueryRewriter,
        RewrittenQuery
    )
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"query_rewriter模块加载失败: {e}")
    QueryRewriter = None
    SimpleQueryRewriter = None
    RewrittenQuery = None

__all__ = [
    # 原有模块
    "HeritageDocumentLoader",
    "MultiSourceRetriever",
    
    # 嵌入管理
    "get_embedding_model",
    "reset_embedding_model",
    "get_embedding_dimension",
    "EmbeddingManager",
    
    # BM25检索
    "BM25Retriever",
    
    # 向量检索
    "VectorRetriever",
    
    # RRF融合
    "reciprocal_rank_fusion",
    "weighted_reciprocal_rank_fusion",
    "score_normalize",
    
    # 重排序
    "CrossEncoderReranker",
    "BatchCrossEncoderReranker",
    "get_reranker_model",
    "reset_reranker_model",
    
    # 查询重写
    "QueryRewriter",
    "SimpleQueryRewriter",
    "RewrittenQuery",
]
