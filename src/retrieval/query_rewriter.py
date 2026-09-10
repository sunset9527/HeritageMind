"""
查询重写模块 — 将口语化非遗问题改写为标准检索查询

基础模式：关键词扩展 + 同义词替换（无 LLM 依赖）
LLM 模式：语义改写 + 多候选生成 + 术语标准化
"""

import logging
import re
from typing import List, Optional
from dataclasses import dataclass, field

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class RewrittenQuery:
    """重写后的查询"""
    original: str
    rewritten: str
    keywords: List[str] = field(default_factory=list)
    score: float = 1.0
    method: str = "rule"


class QueryRewriter:
    """
    查询重写器

    使用方式：
        rewriter = QueryRewriter(use_llm=True)
        queries = rewriter.rewrite("景泰蓝怎么做")
        # → ["景泰蓝 制作流程", "铜胎掐丝珐琅 工艺流程", ...]
    """

    # 非遗术语同义词映射（口语→标准术语）
    SYNONYMS = {
        "怎么做": "制作流程",
        "咋做": "制作流程",
        "是什么": "定义 特征",
        "有啥": "种类 类型",
        "哪些": "种类 类型",
        "哪里": "产地 发源地",
        "谁": "传承人",
        "啥时候": "历史 起源",
    }

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm and settings.query_rewriting_enabled
        self._llm = None

    def rewrite(self, query: str, top_k: int = 3) -> List[RewrittenQuery]:
        """重写用户查询，返回多个候选"""
        results: List[RewrittenQuery] = []

        # 原始查询（保留）
        results.append(RewrittenQuery(
            original=query,
            rewritten=query,
            keywords=self._extract_keywords(query),
            score=1.0,
            method="original",
        ))

        # 规则重写
        rule_rewritten = self._rule_rewrite(query)
        if rule_rewritten != query:
            results.append(RewrittenQuery(
                original=query,
                rewritten=rule_rewritten,
                keywords=self._extract_keywords(rule_rewritten),
                score=0.85,
                method="rule",
            ))

        # LLM 重写（如果启用）
        if self.use_llm and len(results) < top_k:
            llm_results = self._llm_rewrite(query)
            for r in llm_results:
                if r.rewritten not in {x.rewritten for x in results}:
                    results.append(r)

        return results[:top_k]

    def _rule_rewrite(self, query: str) -> str:
        """规则改写：去口语 + 同义词替换 + 术语展开"""
        q = query.strip()

        # 替换口语表达
        for informal, formal in self.SYNONYMS.items():
            q = q.replace(informal, formal)

        # 特定术语展开
        if "景泰蓝" in q and "铜胎" not in q and "珐琅" not in q:
            q = q.replace("景泰蓝", "景泰蓝 铜胎掐丝珐琅")
        if "苏绣" in q and "刺绣" not in q:
            q = q.replace("苏绣", "苏绣 刺绣")

        # 去掉纯疑问词
        q = re.sub(r'[？?！!]+', '', q)
        q = re.sub(r'\s+', ' ', q).strip()

        return q if q else query

    def _llm_rewrite(self, query: str) -> List[RewrittenQuery]:
        """LLM 语义改写（生成 2 个候选）"""
        if self._llm is None:
            try:
                from src.utils.llm import create_llm
                self._llm = create_llm(temperature=0.3, max_tokens=200)
            except Exception as e:
                logger.warning(f"LLM 重写不可用: {e}")
                return []

        prompt = f"""将以下用户口语问题改写为 2 个不同的检索查询。
要求：使用标准术语、去除口语、每个不超过30字。

用户问题：{query}

输出格式（每行一个查询，不要序号）：
"""
        try:
            resp = self._llm.invoke(prompt)
            text = resp.content if hasattr(resp, 'content') else str(resp)
            lines = [l.strip().lstrip('0123456789. -') for l in text.strip().split('\n') if l.strip()]
            return [
                RewrittenQuery(
                    original=query,
                    rewritten=line,
                    keywords=self._extract_keywords(line),
                    score=0.7,
                    method="llm",
                )
                for line in lines[:2]
            ]
        except Exception as e:
            logger.warning(f"LLM 重写失败: {e}")
            return []

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """提取关键词"""
        stopwords = {"的", "了", "是", "在", "和", "与", "或", "什么", "如何", "怎么",
                     "吗", "呢", "吧", "有", "被", "把", "从", "到", "对", "让", "请",
                     "一个", "哪些", "哪个", "哪里", "啥", "为什么", "可以", "这个"}
        try:
            import jieba
            words = [w.strip() for w in jieba.cut(text)
                     if len(w.strip()) >= 2 and w.strip() not in stopwords]
        except ImportError:
            words = [w for w in text.split() if len(w) >= 2 and w not in stopwords]
        return words[:8] or [text]


class SimpleQueryRewriter(QueryRewriter):
    """简易重写器（仅规则，无 LLM）"""
    def __init__(self):
        super().__init__(use_llm=False)


def select_best_query(
    query: str, top_k: int = 3, conversation_context: Optional[str] = None
) -> RewrittenQuery:
    """从 QueryRewriter 候选里选出用于检索的最佳查询（纯函数，供检索链路接线调用）。

    策略：
    - 优先 method="rule" 且改写后 != 原句 的候选；
    - 其次（仅当 settings.query_rewriting_use_llm 开启时存在）取 LLM 候选；
    - 否则回退到第一条（= 原始查询，method="original"）。
    改写不会替换掉原始技艺名，故不影响 craft_name_boost / grouping 的 query 匹配。
    """
    retrieval_query = query
    # 规则改写不能理解“它/这个”等指代；仅在有近期会话时补入上一轮用户主题，供检索使用。
    if conversation_context and any(token in query for token in ("它", "这个", "该技艺", "上述")):
        previous_questions = [
            line.removeprefix("用户：").strip()
            for line in conversation_context.splitlines()
            if line.startswith("用户：")
        ]
        if previous_questions:
            retrieval_query = f"{previous_questions[-1]} {query}"
    try:
        use_llm = bool(getattr(settings, "query_rewriting_use_llm", False))
        candidates = QueryRewriter(use_llm=use_llm).rewrite(retrieval_query, top_k=top_k)
    except Exception as e:
        logger.warning(f"查询改写失败，回退原文: {e}")
        return RewrittenQuery(original=query, rewritten=query, method="original", score=1.0)

    if not candidates:
        return RewrittenQuery(original=query, rewritten=query, method="original", score=1.0)

    for cand in candidates:
        if cand.method == "rule" and cand.rewritten != cand.original:
            return cand
    for cand in candidates:
        if cand.method == "llm" and cand.rewritten != cand.original:
            return cand
    # 第一条恒为 original
    return candidates[0]
