"""v1.6 API 响应元数据契约。"""

from src.workflow.state import create_initial_state, state_to_response


def test_workflow_response_exposes_route_trace_and_citations():
    state = dict(create_initial_state("景泰蓝发源于哪里？"))
    state["final_response"] = "景泰蓝发源于北京。"
    state["route"] = {
        "question_type": "factual",
        "execution_route": "graph",
        "use_memory": False,
        "reason": "查询实体关系",
    }
    state["workflow_trace"] = [
        {"node": "query_graph", "status": "completed", "elapsed_ms": 4, "message": "命中关系"}
    ]
    state["citations"] = [{"title": "景泰蓝 —发源于→ 北京", "source": "local_knowledge_graph"}]

    response = state_to_response(state)

    assert response.metadata["route"] == state["route"]
    assert response.metadata["workflow_trace"] == state["workflow_trace"]
    assert response.citations == state["citations"]
