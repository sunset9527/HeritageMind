"""v1.6 Router：结构化执行路线的离线契约。"""

from langchain_core.messages import AIMessage

from src.agents.dispatcher import DispatcherAgent


class _FakeLLM:
    """只替代外部模型边界，保留 Dispatcher 的真实解析逻辑。"""

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages):
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "route_question",
                    "id": "route-v16-1",
                    "type": "tool_call",
                    "args": {
                        "intent_analysis": "查询景泰蓝的起源地域",
                        "required_experts": ["history_expert"],
                        "reasoning": "本地图谱可直接回答技艺与地域关系",
                        "key_entities": ["景泰蓝"],
                        "complexity": "simple",
                        "question_type": "factual",
                        "execution_route": "graph",
                        "use_memory": False,
                        "route_reason": "问题询问明确实体关系，优先查询本地知识图谱",
                    },
                }
            ],
        )


def test_router_preserves_graph_execution_route_from_tool_call():
    analysis = DispatcherAgent(llm=_FakeLLM()).analyze_question("景泰蓝发源于哪里？")

    assert analysis.question_type == "factual"
    assert analysis.execution_route == "graph"
    assert analysis.use_memory is False
    assert analysis.route_reason == "问题询问明确实体关系，优先查询本地知识图谱"
