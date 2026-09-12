import src.agents as agents
import src.agents.dispatcher as dispatcher
import src.workflow.nodes as workflow_nodes
from src.agents.registry import AgentDefinition, AgentRegistry


class ToolBindingLlm:
    def __init__(self):
        self.tool_calls = []

    def bind_tools(self, tools):
        self.tool_calls.append(tools)
        return self


def test_default_registry_keeps_router_order_and_filters_unknown_agents():
    registry = agents.get_default_agent_registry()

    resolved = registry.resolve(
        ["history_expert", "unknown_expert", "craft_expert", "history_expert"]
    )

    assert [agent.id for agent in resolved] == ["history_expert", "craft_expert"]


def test_router_tool_schema_uses_registered_agent_ids():
    registry = AgentRegistry(
        [
            AgentDefinition("visual_expert", "视觉专家", "👁️", "图片理解", lambda: object()),
            AgentDefinition("craft_expert", "技艺专家", "🎨", "工艺流程", lambda: object()),
        ]
    )

    tool = dispatcher.build_question_analysis_tool(registry)

    assert tool["function"]["parameters"]["properties"]["required_experts"]["items"]["enum"] == [
        "visual_expert",
        "craft_expert",
    ]


def test_dispatcher_binds_router_tool_from_injected_registry():
    llm = ToolBindingLlm()
    registry = AgentRegistry(
        [AgentDefinition("visual_expert", "视觉专家", "👁️", "图片理解", lambda: object())]
    )

    dispatcher.DispatcherAgent(llm=llm, agent_registry=registry)

    assert llm.tool_calls[0][0]["function"]["parameters"]["properties"]["required_experts"]["items"]["enum"] == [
        "visual_expert"
    ]


def test_dispatcher_accepts_only_agents_from_its_registry():
    registry = AgentRegistry(
        [AgentDefinition("visual_expert", "视觉专家", "👁️", "图片理解", lambda: object())]
    )
    instance = dispatcher.DispatcherAgent(llm=ToolBindingLlm(), agent_registry=registry)

    analysis = instance._build_analysis(
        "请识别这张图片",
        {"required_experts": ["unknown_expert", "visual_expert"], "complexity": "simple"},
    )

    assert analysis is not None
    assert analysis.required_experts == ["visual_expert"]


def test_workflow_builds_only_the_router_selected_registered_agents():
    sentinel = object()
    registry = AgentRegistry(
        [AgentDefinition("visual_expert", "视觉专家", "👁️", "图片理解", lambda **_: sentinel)]
    )

    selected = workflow_nodes.build_expert_map(
        registry, ["unknown_expert", "visual_expert"], retriever=object()
    )

    assert selected == {"visual_expert": sentinel}
