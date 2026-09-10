"""
v1.4 支柱 B：Query Rewrite 接线测试（规则模式，零网络）

覆盖：
① select_best_query 规则候选选择：口语问法 → 正式 query 且保留技艺名
② select_best_query 无规则命中（已正式 query）→ 回退原文（method=original）
③ 专家 process(question, context, search_query=...) → 检索用 search_query；识别仍用原 question
④ 专家 process 不传 search_query → 检索回退原文（向后兼容）
⑤ _apply_retrieval_query 开关开/关 的 state 写入契约（search_query / search_query_meta）
⑥ create_initial_state 默认 search_query="" / search_query_meta=None
"""

import pytest

from config import settings
from src.retrieval.query_rewriter import select_best_query, RewrittenQuery
from src.workflow.state import create_initial_state
from src.workflow import nodes
from src.agents.craft_expert import CraftExpertAgent
from src.agents.history_expert import HistoryExpertAgent
from src.agents.heritage_expert import HeritageExpertAgent


# ---------------------------------------------------------------------------
# ① select_best_query
# ---------------------------------------------------------------------------

class TestSelectBestQuery:

    def test_rule_candidate_chosen_and_keeps_craft(self):
        """口语问法 → 取 rule 候选：'怎么做'→'制作流程'，且技艺名'景泰蓝'被保留。"""
        best = select_best_query("景泰蓝怎么做")
        assert best.method == "rule"
        assert "景泰蓝" in best.rewritten
        assert "制作流程" in best.rewritten
        assert best.rewritten != best.original

    def test_no_rule_hit_returns_original(self):
        """已是正式 query、无同义词/术语展开命中 → 回退 candidates[0]（method=original）。"""
        best = select_best_query("东阳木雕的雕刻技法")
        assert best.method == "original"
        assert best.rewritten == "东阳木雕的雕刻技法"

    def test_empty_query_returns_same(self):
        best = select_best_query("")
        assert best.rewritten == ""

    def test_pronoun_query_uses_previous_turn_for_retrieval(self):
        best = select_best_query(
            "它的代表剧目有哪些？", conversation_context="用户：介绍昆曲\n助手：昆曲是……"
        )
        assert "介绍昆曲" in best.rewritten


# ---------------------------------------------------------------------------
# ② 专家 process(search_query=...) 注入
# ---------------------------------------------------------------------------

class RecordingRetriever:
    """记录每次 retrieve 收到的 query，返回空结果（避免依赖真实文档）。"""

    def __init__(self):
        self.seen = None

    def retrieve(self, query, top_k=None, filter_type=None):
        self.seen = query
        return []


class _FakeLLM:
    """占位 llm：process 内 _generate_answer 被替换，永不触发真实调用。"""


EXPERT_CLASSES = [
    (CraftExpertAgent, "craft_expert"),
    (HistoryExpertAgent, "history_expert"),
    (HeritageExpertAgent, "heritage_expert"),
]


@pytest.fixture
def make_agent():
    """构造注入 RecordingRetriever + 替换 _generate_answer 的专家实例。"""
    def _make(cls):
        rec = RecordingRetriever()
        agent = cls(llm=_FakeLLM(), retriever=rec)
        # 不触发网络：answer 直接返回桩文本
        agent._generate_answer = lambda question, craft_name, docs: "（测试回答）"
        return agent, rec
    return _make


class TestExpertSearchQueryInjection:

    @pytest.mark.parametrize("cls,_", EXPERT_CLASSES)
    def test_search_query_used_for_retrieval(self, make_agent, cls, _):
        """检索 query = search_query（改写结果），而非原始 question。"""
        agent, rec = make_agent(cls)
        result = agent.process("苏绣怎么做", {"key_entities": ["苏绣"]}, search_query="苏绣 刺绣 制作流程")
        assert result["success"] is True
        assert rec.seen == "苏绣 刺绣 制作流程"

    @pytest.mark.parametrize("cls,_", EXPERT_CLASSES)
    def test_without_search_query_falls_back_to_question(self, make_agent, cls, _):
        """不传 search_query（旧调用方/关闭改写）→ 检索仍用原始 question。"""
        agent, rec = make_agent(cls)
        agent.process("苏绣怎么做", {"key_entities": ["苏绣"]})
        assert rec.seen == "苏绣怎么做"

    def test_craft_identification_uses_original_question(self, make_agent):
        """识别仍基于原 question（口语问法也能认出'苏绣'），不受改写 query 影响。"""
        agent, rec = make_agent(CraftExpertAgent)
        result = agent.process(
            "苏绣怎么做", {}, search_query="苏绣 刺绣 制作流程"
        )
        assert rec.seen == "苏绣 刺绣 制作流程"
        assert result["craft_name"] == "苏绣"


# ---------------------------------------------------------------------------
# ③ _apply_retrieval_query state 写入契约
# ---------------------------------------------------------------------------

class TestApplyRetrievalQuery:

    def test_enabled_writes_search_query_and_meta(self, monkeypatch):
        best = RewrittenQuery(
            original="景泰蓝怎么做",
            rewritten="景泰蓝 铜胎掐丝珐琅 制作流程",
            method="rule",
            score=0.85,
        )
        monkeypatch.setattr(nodes, "select_best_query", lambda q, top_k=3: best)
        st = dict(create_initial_state("景泰蓝怎么做"))
        nodes._apply_retrieval_query(st, "景泰蓝怎么做")
        assert st["search_query"] == "景泰蓝 铜胎掐丝珐琅 制作流程"
        assert st["search_query_meta"]["method"] == "rule"
        assert st["search_query_meta"]["score"] == 0.85
        assert st["search_query_meta"]["original"] == "景泰蓝怎么做"

    def test_disabled_leaves_search_query_equal_question(self, monkeypatch):
        monkeypatch.setattr(settings, "query_rewriting_enabled", False)
        st = dict(create_initial_state("景泰蓝怎么做"))
        nodes._apply_retrieval_query(st, "景泰蓝怎么做")
        assert st["search_query"] == "景泰蓝怎么做"
        assert st["search_query_meta"] is None

    def test_select_best_query_error_falls_back_to_question(self, monkeypatch):
        def boom(q, top_k=3):
            raise RuntimeError("模拟改写失败")
        monkeypatch.setattr(nodes, "select_best_query", boom)
        st = dict(create_initial_state("景泰蓝怎么做"))
        nodes._apply_retrieval_query(st, "景泰蓝怎么做")
        assert st["search_query"] == "景泰蓝怎么做"
        assert st["search_query_meta"] is None
