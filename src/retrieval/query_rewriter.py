"""
查询重写模块

将用户口语化问题改写为更精准的检索查询，提升 RAG 召回率。
当前为占位实现——完整版等待 v1.0.2 迭代。
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RewrittenQuery:
    """重写后的查询"""
    original: str
    rewritten: str
    keywords: List[str]
    score: float = 1.0


class QueryRewriter:
    """查询重写器"""

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def rewrite(self, query: str, top_k: int = 3) -> List[RewrittenQuery]:
        """
        重写用户查询

        当前实现：返回原始查询 + 简单关键词扩展。
        完整版将在 v1.0.2 中接入 LLM 进行语义改写。
        """
        results = [RewrittenQuery(
            original=query,
            rewritten=query,
            keywords=self._extract_keywords(query),
            score=1.0,
        )]

        # 简单扩展：去掉语气词、补充同义词
        expanded = self._simple_expand(query)
        if expanded != query:
            results.append(RewrittenQuery(
                original=query,
                rewritten=expanded,
                keywords=self._extract_keywords(expanded),
                score=0.8,
            ))

        return results[:top_k]

    def _extract_keywords(self, text: str) -> List[str]:
        """简单关键词提取（中文按字符切分 2-4 字短语）"""
        # 简易实现：去标点，按 2-4 字滑动窗口
        import re
        cleaned = re.sub(r'[？?！!，,。.、\s]+', '', text)
        keywords = []
        for size in [4, 3, 2]:
            for i in range(len(cleaned) - size + 1):
                kw = cleaned[i:i + size]
                if kw not in keywords:
                    keywords.append(kw)
        return keywords[:10]

    def _simple_expand(self, query: str) -> str:
        """简单查询扩展"""
        # 去掉常见口语后缀
        import re
        expanded = re.sub(r'[是什么|为什么|怎么做|能告诉].*$', '', query)
        return expanded.strip() if expanded.strip() else query


class SimpleQueryRewriter(QueryRewriter):
    """简易重写器（无 LLM 依赖）"""
    pass
