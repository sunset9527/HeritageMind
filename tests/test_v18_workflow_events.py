from src.workflow import state
import src.workflow.events as events
import src.workflow.nodes as nodes


def test_runtime_event_keeps_legacy_progress_fields_and_excludes_sensitive_values():
    event = state.create_runtime_event(
        "agent_message",
        run_id="run-123",
        step="collaborate",
        msg="历史专家提出补充",
        payload={
            "from_agent": "history_expert",
            "summary": "请补充年代依据。",
            "api_key": "secret",
            "system_prompt": "private",
        },
    )

    assert event == {
        "event": "agent_message",
        "run_id": "run-123",
        "step": "collaborate",
        "msg": "历史专家提出补充",
        "from_agent": "history_expert",
        "summary": "请补充年代依据。",
    }


def test_event_emitter_forwards_safe_event_to_optional_sink():
    received = []
    emitter = events.WorkflowEventEmitter("run-123", received.append)

    event = emitter.emit(
        "node_started",
        step="dispatch_to_experts",
        msg="开始调度专家",
        payload={"api_key": "secret"},
    )

    assert received == [event]
    assert event["event"] == "node_started"
    assert "api_key" not in event


def test_initial_state_keeps_request_scoped_event_emitter_out_of_response_fields():
    emitter = events.WorkflowEventEmitter("run-123")

    initial = state.create_initial_state("介绍景泰蓝", runtime_emitter=emitter)

    assert initial["runtime_emitter"] is emitter
    assert initial["run_id"] == "run-123"


def test_node_event_helper_is_a_noop_without_emitter_and_forwards_when_present():
    received = []
    workflow_state = {"runtime_emitter": events.WorkflowEventEmitter("run-123", received.append)}

    nodes.emit_workflow_event(
        workflow_state, "node_completed", step="collaborate", msg="协作完成"
    )
    nodes.emit_workflow_event({}, "node_started", step="ignored", msg="不应失败")

    assert received[0]["event"] == "node_completed"
    assert received[0]["step"] == "collaborate"


def test_base_workflow_graph_declares_optional_collaboration_path():
    graph = events.build_base_workflow_graph()

    assert {node["id"] for node in graph["nodes"]} >= {"analyze_question", "dispatch_to_experts", "collaborate", "generate_response"}
    assert {"source": "collaborate", "target": "fuse_knowledge"} in graph["edges"]
