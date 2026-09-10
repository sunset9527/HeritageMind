"""v1.5 会话记忆工作流接线测试（离线）。"""

from src.workflow.state import create_initial_state
from src.workflow.graph import HeritageWorkflowGraph
from src.agents.dispatcher import DispatcherAgent
from langchain_core.messages import AIMessage


def test_initial_state_reserves_conversation_memory_fields():
    """每次工作流初始化都必须有独立的会话记忆字段，避免跨请求串话。"""
    state = create_initial_state("介绍昆曲")

    assert "thread_id" in state
    assert "conversation_context" in state
    assert "memory_preferences" in state
    assert state["conversation_context"] == ""
    assert state["memory_preferences"] == {}


def test_graph_forwards_session_context_and_thread_config():
    """服务层加载的上下文必须进入图状态，并用稳定 thread_id 调用图。"""
    captured = {}

    class FakeGraph:
        def stream(self, state, config):
            captured["state"] = state
            captured["config"] = config
            done = dict(state)
            done["final_response"] = "承接上一轮的回答"
            return iter([{"generate_response_standard": done}])

    workflow = HeritageWorkflowGraph()
    workflow.graph = FakeGraph()
    response = workflow.query(
        "它的代表剧目有哪些？",
        thread_id="session-1",
        conversation_context="用户：介绍昆曲\n助手：昆曲是……",
        memory_preferences={"preferred_crafts": ["京剧"]},
    )

    assert response.answer == "承接上一轮的回答"
    assert captured["state"]["conversation_context"].startswith("用户：介绍昆曲")
    assert captured["state"]["memory_preferences"]["preferred_crafts"] == ["京剧"]
    assert captured["config"]["configurable"]["thread_id"] == "session-1"


def test_dispatcher_analysis_prompt_includes_prior_turns():
    """指代问题的路由必须看得到同一会话的近期上下文。"""
    captured = {}

    class FakeLLM:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            captured["messages"] = messages
            return AIMessage(tool_calls=[{"name": "route_question", "id": "1", "args": {
                "required_experts": ["history_expert"], "complexity": "simple",
            }}])

    DispatcherAgent(llm=FakeLLM()).analyze_question(
        "它有哪些代表剧目？", conversation_context="用户：介绍昆曲\n助手：昆曲是……"
    )

    assert "介绍昆曲" in captured["messages"][1].content
