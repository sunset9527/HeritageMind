"""User-safe runtime events emitted while a workflow is executing."""

from typing import Any, Callable, Optional


EVENT_TYPES = frozenset(
    {
        "workflow_started",
        "node_started",
        "node_completed",
        "node_skipped",
        "node_fallback",
        "workflow_graph_updated",
        "agent_message",
        "done",
        "error",
    }
)


def build_base_workflow_graph() -> dict[str, list[dict[str, str]]]:
    """Return the user-visible DAG skeleton before Router selects experts."""
    nodes = [
        {"id": "analyze_question", "label": "问题分析"},
        {"id": "plan_question", "label": "问题规划"},
        {"id": "dispatch_to_experts", "label": "专家分派"},
        {"id": "query_graph", "label": "知识图谱查询"},
        {"id": "collect_responses", "label": "收集专家回答"},
        {"id": "collaborate", "label": "专家协作"},
        {"id": "fuse_knowledge", "label": "知识融合"},
        {"id": "detect_gaps", "label": "知识缺口检测"},
        {"id": "generate_response", "label": "生成回答"},
    ]
    edges = [
        {"source": "analyze_question", "target": "plan_question"},
        {"source": "analyze_question", "target": "dispatch_to_experts"},
        {"source": "plan_question", "target": "dispatch_to_experts"},
        {"source": "dispatch_to_experts", "target": "query_graph"},
        {"source": "query_graph", "target": "collect_responses"},
        {"source": "collect_responses", "target": "collaborate"},
        {"source": "collaborate", "target": "fuse_knowledge"},
        {"source": "fuse_knowledge", "target": "detect_gaps"},
        {"source": "detect_gaps", "target": "generate_response"},
    ]
    return {"nodes": nodes, "edges": edges}

_SENSITIVE_KEY_PARTS = (
    "api_key",
    "authorization",
    "password",
    "secret",
    "system_prompt",
    "conversation_context",
    "retrieval_context",
)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if not any(part in str(key).lower() for part in _SENSITIVE_KEY_PARTS)
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    return value


def create_runtime_event(
    event: str,
    *,
    run_id: str,
    step: str,
    msg: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a backwards-compatible, safe SSE payload."""
    if event not in EVENT_TYPES:
        raise ValueError(f"unsupported workflow event: {event}")
    result: dict[str, Any] = {
        "event": event,
        "run_id": run_id,
        "step": step,
        "msg": msg,
    }
    result.update(_sanitize(payload or {}))
    return result


class WorkflowEventEmitter:
    """Emit safe runtime events to an optional request-scoped sink."""

    def __init__(self, run_id: str, sink: Optional[Callable[[dict[str, Any]], None]] = None):
        self.run_id = run_id
        self._sink = sink

    def emit(
        self,
        event: str,
        *,
        step: str,
        msg: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        value = create_runtime_event(
            event,
            run_id=self.run_id,
            step=step,
            msg=msg,
            payload=payload,
        )
        if self._sink is not None:
            self._sink(value)
        return value
