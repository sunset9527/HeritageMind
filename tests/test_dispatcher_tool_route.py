"""
DispatcherAgent 路由原生 function-calling 测试。

覆盖 analyze_question 的三分支降级，全部通过 Fake LLM 注入，零网络调用：
① tool_calls 命中（route_question）→ args 解析
② content 口述 JSON（含 ```json 剥壳）→ JSON 兜底
③ 全失败 → 关键词 fallback
另覆盖：白名单清洗、system 消息真正入参、空专家列表降级。
"""

import pytest
from langchain_core.messages import AIMessage

from src.agents.dispatcher import DispatcherAgent, QuestionAnalysis


class FakeToolLLM:
    """bind_tools 返回自身；invoke 返回预设 responder 的结果。"""

    def __init__(self, responder):
        self.responder = responder
        self.tools = None
        self.last_messages = None

    def bind_tools(self, tools, **kwargs):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.last_messages = messages
        resp = self.responder(messages)
        return resp if resp is not None else AIMessage(content="")


def _make_agent(responder):
    return DispatcherAgent(llm=FakeToolLLM(responder))


def _tool_call(args, name="route_question"):
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "id": "call_1", "type": "tool_call", "args": args}],
    )


def test_tool_calls_route_full_fields():
    """① tool_calls 命中：args 被正确解析为 QuestionAnalysis。"""

    def responder(messages):
        return _tool_call(
            {
                "intent_analysis": "对比两种技艺",
                "required_experts": ["craft_expert", "history_expert"],
                "reasoning": "涉及工艺与历史",
                "key_entities": ["景泰蓝", "苏绣"],
                "complexity": "medium",
            }
        )

    analysis = _make_agent(responder).analyze_question("景泰蓝和苏绣有何异同")
    assert isinstance(analysis, QuestionAnalysis)
    assert analysis.required_experts == ["craft_expert", "history_expert"]
    assert analysis.complexity == "medium"
    assert analysis.key_entities == ["景泰蓝", "苏绣"]
    assert analysis.intent_analysis == "对比两种技艺"


def test_messages_include_real_system_prompt():
    """system 提示词真正以 SystemMessage 入参（此前从未进入 LLM）。"""
    captured = {}

    def responder(messages):
        captured["msgs"] = messages
        return _tool_call({"required_experts": ["craft_expert"], "complexity": "simple"})

    _make_agent(responder).analyze_question("什么是景泰蓝")
    msgs = captured["msgs"]
    assert msgs[0].type == "system"
    assert "调度专家" in msgs[0].content
    assert msgs[1].type == "human"
    assert "什么是景泰蓝" in msgs[1].content


def test_content_json_fallback():
    """② 无 tool_calls，content 为合法 JSON → JSON 兜底成功。"""

    def responder(messages):
        return AIMessage(
            content='{"intent_analysis":"意图","required_experts":["craft_expert"],"reasoning":"理由","key_entities":[],"complexity":"simple"}'
        )

    analysis = _make_agent(responder).analyze_question("什么是景泰蓝")
    assert analysis.required_experts == ["craft_expert"]
    assert analysis.complexity == "simple"


def test_content_json_with_fence_fallback():
    """② content 带 ```json 代码块 → 剥壳后解析成功。"""

    def responder(messages):
        return AIMessage(content='```json\n{"required_experts":["history_expert"],"complexity":"simple"}\n```')

    analysis = _make_agent(responder).analyze_question("景泰蓝的历史")
    assert analysis.required_experts == ["history_expert"]


def test_unknown_experts_normalized():
    """白名单清洗：未知 token / 重复 token 被剔除或去重。"""

    def responder(messages):
        return _tool_call(
            {
                "required_experts": ["craft_expert", "王师傅", "craft_expert", "heritage_expert"],
                "complexity": "不确定的复杂度",
            }
        )

    analysis = _make_agent(responder).analyze_question("皮影戏的传承现状")
    assert analysis.required_experts == ["craft_expert", "heritage_expert"]
    # complexity 非法时按专家数回推：2 个 → medium
    assert analysis.complexity == "medium"


def test_tool_call_empty_experts_falls_back_to_keywords():
    """① tool_calls 命中但 required_experts 为空 → 关键词 fallback。"""

    def responder(messages):
        return _tool_call({"required_experts": [], "complexity": "simple"})

    analysis = _make_agent(responder).analyze_question("什么是景泰蓝")
    assert "craft_expert" in analysis.required_experts


def test_invalid_output_falls_back_to_keywords():
    """③ 无 tool_calls 且 content 非法 → 关键词 fallback。"""

    def responder(messages):
        return AIMessage(content="抱歉，我没法理解这个问题。")

    analysis = _make_agent(responder).analyze_question("什么是景泰蓝")
    assert "craft_expert" in analysis.required_experts
