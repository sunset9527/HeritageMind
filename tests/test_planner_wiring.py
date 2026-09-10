"""
v1.4 支柱 C：Planner 大纲式（只影响生成结构）测试，零网络。

覆盖：
① DispatcherAgent.plan_question 三分支（create_plan 工具调用 / content 口述 JSON / 失败→None）
② plan_question_node 写入 state['plan']（成功/降级 None）
③ should_plan 触发判定（complex / ≥2 专家 / planner_enabled 关闭）
④ _plan_outline_text 渲染（空/非空）
⑤ get_fusion_prompt 注入大纲（含/不含「回答结构要求」）
⑥ 图装配冒烟：编译后含 plan_question 节点
"""

import pytest
from langchain_core.messages import AIMessage

from config import settings
from src.agents.dispatcher import DispatcherAgent, QuestionPlan
from src.utils.prompts import get_fusion_prompt
from src.workflow.state import create_initial_state
from src.workflow.nodes import plan_question_node, should_plan, _plan_outline_text
from src.workflow.graph import HeritageWorkflowGraph


class _FakeLLM:
    """bind_tools 返回自身；invoke 返回预设 responder 的结果。"""

    def __init__(self, responder):
        self.responder = responder

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages):
        resp = self.responder(messages)
        return resp if resp is not None else AIMessage(content="")


def _make_agent(responder):
    return DispatcherAgent(llm=_FakeLLM(responder))


def _plan_call(args, name="create_plan"):
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "id": "call_p1", "type": "tool_call", "args": args}],
    )


# ---------------------------------------------------------------------------
# ① DispatcherAgent.plan_question 三分支
# ---------------------------------------------------------------------------

class TestPlanQuestion:

    def test_tool_call_full_fields(self):
        """① create_plan 工具调用 → 解析为 QuestionPlan。"""

        def responder(messages):
            return _plan_call({
                "aspects": ["工艺技术", "历史演变", "文化象征与传承现状"],
                "outline": "先概述两种技艺，再分工艺/历史两条线对比，最后落文化象征",
            })

        plan = _make_agent(responder).plan_question("景泰蓝和苏绣有何异同", complexity="complex")
        assert isinstance(plan, QuestionPlan)
        assert plan.aspects == ["工艺技术", "历史演变", "文化象征与传承现状"]
        assert "对比" in plan.outline
        assert plan.sub_questions is None

    def test_planner_prompt_messages(self):
        """SystemMessage 真正携带 PLANNER 提示词入参。"""
        captured = {}

        def responder(messages):
            captured["msgs"] = messages
            return _plan_call({"aspects": ["工艺"], "outline": "o"})

        _make_agent(responder).plan_question("什么是景泰蓝", complexity="complex")
        msgs = captured["msgs"]
        assert msgs[0].type == "system"
        assert "结构规划" in msgs[0].content
        assert msgs[1].type == "human"
        assert "什么是景泰蓝" in msgs[1].content

    def test_content_json_fallback(self):
        """② 无 tool_calls，content 为合法 JSON → 解析成功。"""

        def responder(messages):
            return AIMessage(content='{"aspects":["工艺","历史"],"outline":"先工艺后历史"}')

        plan = _make_agent(responder).plan_question("景泰蓝的历史", complexity="complex")
        assert plan is not None
        assert plan.aspects == ["工艺", "历史"]

    def test_content_json_with_fence_fallback(self):
        """② content 带 ```json 代码块 → 剥壳后解析成功。"""

        def responder(messages):
            return AIMessage(content='```json\n{"aspects":["工艺"],"outline":"大纲"}\n```')

        plan = _make_agent(responder).plan_question("景泰蓝的工艺", complexity="complex")
        assert plan is not None
        assert plan.aspects == ["工艺"]

    def test_tool_call_empty_aspects_returns_none(self):
        """① 工具调用但 aspects 为空 → None（跳过 plan 降级）。"""

        def responder(messages):
            return _plan_call({"aspects": [], "outline": ""})

        plan = _make_agent(responder).plan_question("景泰蓝", complexity="complex")
        assert plan is None

    def test_garbage_content_returns_none(self):
        """③ content 非法/无法理解 → None（最安全降级，不二次调 LLM）。"""

        def responder(messages):
            return AIMessage(content="我不确定该拆哪些方面。")

        plan = _make_agent(responder).plan_question("景泰蓝", complexity="complex")
        assert plan is None

    def test_aspects_deduplicated_and_stripped(self):
        """清洗：去重、去空串。"""

        def responder(messages):
            return _plan_call({"aspects": [" 工艺 ", "工艺", "", "历史"], "outline": "o"})

        plan = _make_agent(responder).plan_question("景泰蓝", complexity="complex")
        assert plan.aspects == ["工艺", "历史"]


# ---------------------------------------------------------------------------
# ②③④ 节点层
# ---------------------------------------------------------------------------

class TestPlanNodeAndHelpers:

    def test_plan_node_writes_plan(self, monkeypatch):
        plan = QuestionPlan(aspects=["工艺", "历史"], outline="先工艺后历史")

        class _FakeDispatcher:
            def plan_question(self, **kwargs):
                return plan

        monkeypatch.setattr("src.workflow.nodes.DispatcherAgent", _FakeDispatcher)
        state = dict(create_initial_state("景泰蓝和苏绣有何异同"))
        out = plan_question_node(state)
        assert out["plan"]["aspects"] == ["工艺", "历史"]
        assert out["plan"]["outline"] == "先工艺后历史"

    def test_plan_node_none_degrades(self, monkeypatch):
        class _FakeDispatcher:
            def plan_question(self, **kwargs):
                return None

        monkeypatch.setattr("src.workflow.nodes.DispatcherAgent", _FakeDispatcher)
        state = dict(create_initial_state("景泰蓝和苏绣有何异同"))
        out = plan_question_node(state)
        assert out["plan"] is None

    def test_plan_node_exception_degrades(self, monkeypatch):
        class _FakeDispatcher:
            def plan_question(self, **kwargs):
                raise RuntimeError("LLM 挂了")

        monkeypatch.setattr("src.workflow.nodes.DispatcherAgent", _FakeDispatcher)
        state = dict(create_initial_state("景泰蓝和苏绣有何异同"))
        out = plan_question_node(state)
        assert out["plan"] is None
        assert any("Planner" in e for e in out["errors"])

    def test_outline_text_render(self):
        state = {"plan": {"aspects": ["工艺", "历史"], "outline": "先工艺后历史"}}
        text = _plan_outline_text(state)
        assert text is not None
        assert "工艺" in text and "历史" in text
        assert "先工艺后历史" in text

    def test_outline_text_none(self):
        assert _plan_outline_text({}) is None
        assert _plan_outline_text({"plan": None}) is None
        assert _plan_outline_text({"plan": {"aspects": [], "outline": ""}}) is None


class TestShouldPlan:

    def _state(self, complexity="medium", experts=("craft_expert",)):
        st = create_initial_state("测试问题")
        st["complexity"] = complexity
        st["required_experts"] = list(experts)
        return st

    def test_complex_triggers(self):
        assert should_plan(self._state(complexity="complex", experts=("craft_expert",))) == "plan"

    def test_two_experts_triggers_even_medium(self):
        assert should_plan(self._state(complexity="medium", experts=("craft_expert", "history_expert"))) == "plan"

    def test_simple_single_expert_skips(self):
        assert should_plan(self._state(complexity="simple", experts=("craft_expert",))) == "skip_plan"

    def test_planner_disabled_skips_even_complex(self, monkeypatch):
        monkeypatch.setattr(settings, "planner_enabled", False)
        assert should_plan(self._state(complexity="complex", experts=("craft_expert", "history_expert"))) == "skip_plan"


# ---------------------------------------------------------------------------
# ⑤ 融合提示词注入
# ---------------------------------------------------------------------------

class TestFusionPromptOutline:

    def test_outline_injected_when_present(self):
        prompt = get_fusion_prompt(
            {"craft_expert": "a", "history_expert": "b"}, "q",
            plan_outline="子方面：\n1. 工艺\n组织顺序：先工艺"
        )
        assert "回答结构要求" in prompt
        assert "1. 工艺" in prompt

    def test_outline_absent_by_default(self):
        prompt = get_fusion_prompt({"craft_expert": "a", "history_expert": "b"}, "q")
        assert "回答结构要求" not in prompt


# ---------------------------------------------------------------------------
# ⑥ 图装配冒烟
# ---------------------------------------------------------------------------

class TestGraphAssembly:

    def test_graph_has_plan_node(self):
        wf = HeritageWorkflowGraph()
        assert "plan_question" in wf.graph.nodes
