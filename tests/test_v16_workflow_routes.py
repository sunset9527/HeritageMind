"""v1.6 工作流路线状态的离线接线测试。"""

from src.agents.dispatcher import QuestionAnalysis
from src.workflow.nodes import analyze_question_node, query_graph_node
from src.workflow.nodes import NODES
from src.workflow.state import create_initial_state
from src.workflow.graph import HeritageWorkflowGraph


def test_analyze_node_stores_structured_route(monkeypatch):
    class _Dispatcher:
        def __init__(self, **_kwargs):
            pass

        def analyze_question(self, question, conversation_context=None):
            return QuestionAnalysis(
                intent_analysis="查询实体关系",
                required_experts=["history_expert"],
                reasoning="图谱优先",
                key_entities=["景泰蓝"],
                complexity="simple",
                question_type="factual",
                execution_route="graph",
                use_memory=False,
                route_reason="询问明确实体关系",
            )

    monkeypatch.setattr("src.workflow.nodes.DispatcherAgent", _Dispatcher)

    result = analyze_question_node(dict(create_initial_state("景泰蓝发源于哪里？")))

    assert result["route"] == {
        "question_type": "factual",
        "execution_route": "graph",
        "use_memory": False,
        "reason": "询问明确实体关系",
    }


def test_graph_query_node_is_registered_for_v16_workflow():
    assert "query_graph" in NODES


def test_graph_query_node_records_graph_evidence_and_trace_for_graph_route():
    state = dict(create_initial_state("景泰蓝发源于哪里？"))
    state["key_entities"] = ["景泰蓝"]
    state["route"] = {
        "question_type": "factual",
        "execution_route": "graph",
        "use_memory": False,
        "reason": "查询实体关系",
    }

    result = query_graph_node(state)

    assert result["graph_evidence"]
    assert result["workflow_trace"][-1]["node"] == "query_graph"
    assert result["workflow_trace"][-1]["status"] == "completed"
    assert {
        "title": result["graph_evidence"][0]["title"],
        "source": "local_knowledge_graph",
    } in result["citations"]


def test_compiled_workflow_registers_graph_query_node():
    assert "query_graph" in HeritageWorkflowGraph().graph.nodes
