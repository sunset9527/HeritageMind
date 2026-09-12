"""Safe configuration overlays for already registered Agent definitions."""

from dataclasses import replace
from typing import Any, Iterable, Mapping

from sqlalchemy.orm import Session

from src.agents.registry import AgentDefinition, AgentRegistry
from src.models.agent_configuration import AgentConfiguration


ALLOWED_PARAMETERS = {"max_messages"}


def build_configured_registry(
    default_registry: AgentRegistry,
    configurations: Iterable[Mapping[str, Any]],
) -> AgentRegistry:
    """Apply recognized display/enable overrides without admitting unknown executable Agents."""
    by_id = {str(config.get("agent_id", "")): config for config in configurations}
    definitions: list[AgentDefinition] = []
    for definition in default_registry.definitions:
        config = by_id.get(definition.id)
        if config and config.get("enabled") is False:
            continue
        if config is None:
            definitions.append(definition)
            continue
        display_name = str(config.get("display_name") or definition.display_name).strip()
        capability = str(config.get("capability") or definition.capability).strip()
        definitions.append(replace(
            definition,
            display_name=display_name or definition.display_name,
            capability=capability or definition.capability,
        ))
    return AgentRegistry(definitions) if definitions else default_registry


def load_configured_registry(db: Session, default_registry: AgentRegistry) -> AgentRegistry:
    """Build the registry for one new request from persisted safe overrides."""
    configurations = [
        {
            "agent_id": row.agent_id,
            "enabled": row.enabled,
            "display_name": row.display_name,
            "capability": row.capability,
            "collaboration_priority": row.collaboration_priority,
            "parameters": row.parameters or {},
        }
        for row in list_configuration_overrides(db)
    ]
    return build_configured_registry(default_registry, configurations)


def list_configuration_overrides(db: Session) -> list[AgentConfiguration]:
    return db.query(AgentConfiguration).order_by(AgentConfiguration.agent_id).all()


def update_configuration(
    db: Session,
    *,
    agent_id: str,
    values: Mapping[str, Any],
    updated_by_user_id: int,
    default_registry: AgentRegistry,
) -> AgentConfiguration:
    """Persist only a validated override for a pre-registered Agent."""
    if agent_id not in default_registry.ids:
        raise ValueError("未知 Agent，不能在后台创建可执行专家")
    parameters = dict(values.get("parameters") or {})
    if set(parameters) - ALLOWED_PARAMETERS:
        raise ValueError("包含不允许的 Agent 参数")
    if "max_messages" in parameters and (
        not isinstance(parameters["max_messages"], int) or not 1 <= parameters["max_messages"] <= 10
    ):
        raise ValueError("max_messages 必须是 1 到 10 的整数")
    row = db.query(AgentConfiguration).filter(AgentConfiguration.agent_id == agent_id).first()
    if row is None:
        row = AgentConfiguration(agent_id=agent_id)
        db.add(row)
    row.enabled = bool(values.get("enabled", True))
    row.display_name = (str(values.get("display_name") or "").strip() or None)
    row.capability = (str(values.get("capability") or "").strip() or None)
    row.collaboration_priority = int(values.get("collaboration_priority", 100))
    row.parameters = parameters
    row.updated_by_user_id = updated_by_user_id
    db.flush()
    return row


def serialize_registered_agents(db: Session, default_registry: AgentRegistry) -> list[dict[str, Any]]:
    """List all built-ins, with optional persisted overrides merged for admin display."""
    rows = {row.agent_id: row for row in list_configuration_overrides(db)}
    result: list[dict[str, Any]] = []
    for definition in default_registry.definitions:
        row = rows.get(definition.id)
        result.append({
            "agent_id": definition.id,
            "enabled": True if row is None else row.enabled,
            "display_name": (row.display_name if row and row.display_name else definition.display_name),
            "capability": (row.capability if row and row.capability else definition.capability),
            "collaboration_priority": 100 if row is None else row.collaboration_priority,
            "parameters": {} if row is None else (row.parameters or {}),
            "has_override": row is not None,
        })
    return result
