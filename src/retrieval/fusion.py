"""
RRF (Reciprocal Rank Fusion) 融合算法
用于将多个检索结果列表融合为一个排序列表
"""

import logging
from typing import List, Dict, Any, Set, Optional

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    results_list: List[List[Dict[str, Any]]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    倒数排名融合算法 (Reciprocal Rank Fusion)
    
    将多个检索器的结果融合为一个统一的排序列表，适用于混合检索场景
    
    算法原理：
    对于每个文档，计算其在各检索结果列表中的排名，然后使用 RRF 公式计算融合分数：
    RRF_score(d) = Σ 1 / (k + rank(d))
    
    Args:
        results_list: 多个检索结果列表，每个元素是检索结果列表
                     每个结果格式: [{"doc_id": str, "content": str, "score": float, "metadata": dict}, ...]
        k: RRF算法参数，默认60。值越小，高排名结果权重越高
        
    Returns:
        融合后的排序结果列表，格式同上
        
    Example:
        >>> bm25_results = [{"doc_id": "doc1", "score": 1.5, ...}, ...]
        >>> vector_results = [{"doc_id": "doc2", "score": 0.9, ...}, ...]
        >>> fused = reciprocal_rank_fusion([bm25_results, vector_results], k=60)
    """
    if not results_list:
        return []
    
    # 记录每个文档的RRF分数和详细信息
    doc_scores: Dict[str, Dict[str, Any]] = {}
    seen_doc_ids: Set[str] = set()
    
    for results in results_list:
        if not results:
            continue
        
        # 对当前检索结果按原始分数排序（确保rank与分数一致）
        sorted_results = sorted(
            results,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        # 遍历排序后的结果，计算RRF贡献
        for rank, result in enumerate(sorted_results):
            doc_id = result.get("doc_id", "")
            
            if not doc_id:
                continue
            
            # RRF公式：1 / (k + rank)
            # rank从0开始，所以第1名贡献 1/(k+0)，第2名贡献 1/(k+1)，以此类推
            rrf_contribution = 1.0 / (k + rank)
            
            if doc_id not in doc_scores:
                # 首次出现，初始化
                doc_scores[doc_id] = {
                    "doc_id": doc_id,
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "rrf_score": 0.0,
                    "sources": []
                }
                seen_doc_ids.add(doc_id)
            
            # 累加RRF分数
            doc_scores[doc_id]["rrf_score"] += rrf_contribution
            
            # 记录来源（用于调试和分析）
            doc_scores[doc_id]["sources"].append({
                "rank": rank,
                "original_score": result.get("score", 0)
            })
    
    # 转换为列表并按RRF分数排序
    fused_results = sorted(
        doc_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True
    )
    
    # 整理输出格式，添加最终排名
    final_results = []
    for final_rank, item in enumerate(fused_results, 1):
        final_results.append({
            "doc_id": item["doc_id"],
            "content": item["content"],
            "score": item["rrf_score"],
            "metadata": item["metadata"],
            "final_rank": final_rank,
            "sources_count": len(item["sources"])
        })
    
    logger.debug(f"RRF融合完成: {len(final_results)} 个唯一文档, 来自 {len(results_list)} 个检索源")
    
    return final_results


def weighted_reciprocal_rank_fusion(
    results_list: List[List[Dict[str, Any]]],
    weights: Optional[List[float]] = None,
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    加权倒数排名融合算法
    
    与基础RRF相比，允许为不同的检索结果列表设置不同的权重
    
    Args:
        results_list: 多个检索结果列表
        weights: 每个检索结果列表的权重，长度需与results_list一致
                如果为None，则使用等权重
        k: RRF算法参数
        
    Returns:
        融合后的排序结果列表
        
    Example:
        >>> # BM25权重0.4，向量检索权重0.6
        >>> fused = weighted_reciprocal_rank_fusion(
        ...     [bm25_results, vector_results],
        ...     weights=[0.4, 0.6],
        ...     k=60
        ... )
    """
    if not results_list:
        return []
    
    # 处理权重
    n_lists = len(results_list)
    if weights is None:
        weights = [1.0] * n_lists
    else:
        if len(weights) != n_lists:
            raise ValueError(f"权重数量({len(weights)})必须与结果列表数量({n_lists})一致")
        # 归一化权重
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
    
    # 记录每个文档的加权RRF分数
    doc_scores: Dict[str, Dict[str, Any]] = {}
    
    for results, weight in zip(results_list, weights):
        if not results:
            continue
        
        # 按分数排序
        sorted_results = sorted(
            results,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        for rank, result in enumerate(sorted_results):
            doc_id = result.get("doc_id", "")
            
            if not doc_id:
                continue
            
            # 加权RRF公式：weight * 1 / (k + rank)
            weighted_rrf = weight / (k + rank)
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "doc_id": doc_id,
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "rrf_score": 0.0,
                    "sources": []
                }
            
            doc_scores[doc_id]["rrf_score"] += weighted_rrf
            doc_scores[doc_id]["sources"].append({
                "rank": rank,
                "original_score": result.get("score", 0),
                "weight": weight
            })
    
    # 排序并整理输出
    fused_results = sorted(
        doc_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True
    )
    
    final_results = []
    for final_rank, item in enumerate(fused_results, 1):
        final_results.append({
            "doc_id": item["doc_id"],
            "content": item["content"],
            "score": item["rrf_score"],
            "metadata": item["metadata"],
            "final_rank": final_rank,
            "sources_count": len(item["sources"])
        })
    
    return final_results


def score_normalize(
    results: List[Dict[str, Any]],
    method: str = "minmax"
) -> List[Dict[str, Any]]:
    """
    对检索结果进行分数归一化
    
    Args:
        results: 检索结果列表
        method: 归一化方法，"minmax"或"zscore"
        
    Returns:
        归一化后的结果列表
    """
    if not results:
        return []
    
    scores = [r.get("score", 0) for r in results]
    
    if method == "minmax":
        min_score = min(scores)
        max_score = max(scores)
        range_score = max_score - min_score
        
        if range_score == 0:
            return results
        
        normalized = []
        for r in results:
            normalized_score = (r.get("score", 0) - min_score) / range_score
            normalized.append({**r, "score": normalized_score})
        return normalized
    
    elif method == "zscore":
        import statistics
        mean_score = statistics.mean(scores)
        stdev_score = statistics.stdev(scores) if len(scores) > 1 else 1.0
        
        if stdev_score == 0:
            return results
        
        normalized = []
        for r in results:
            normalized_score = (r.get("score", 0) - mean_score) / stdev_score
            normalized.append({**r, "score": normalized_score})
        return normalized
    
    return results
