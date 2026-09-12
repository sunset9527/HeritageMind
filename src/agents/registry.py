"""Agent definitions used by routing and dynamic collaboration."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable, Iterable

from src.agents.craft_expert import CraftExpertAgent
from src.agents.heritage_expert import HeritageExpertAgent
from src.agents.history_expert import HistoryExpertAgent


@dataclass(frozen=True)
class AgentDefinition:
    """Stable, user-safe metadata and factory for one expert Agent."""

    id: str
    display_name: str
    icon: str
    capability: str
    factory: Callable[..., Any]

    def create(self, **kwargs: Any) -> Any:
        return self.factory(**kwargs)


class AgentRegistry:
    """Read-only collection that validates Router-selected Agent IDs."""

    def __init__(self, definitions: Iterable[AgentDefinition]):
        self._definitions = {definition.id: definition for definition in definitions}

    def resolve(self, agent_ids: Iterable[str]) -> list[AgentDefinition]:
        """Keep known Agent IDs once, preserving the Router's order."""
        resolved: list[AgentDefinition] = []
        seen: set[str] = set()
        for agent_id in agent_ids:
            if agent_id in seen:
                continue
            definition = self._definitions.get(agent_id)
            if definition is None:
                continue
            seen.add(agent_id)
            resolved.append(definition)
        return resolved

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self._definitions)

    @property
    def definitions(self) -> tuple[AgentDefinition, ...]:
        """Expose immutable registered definitions for safe configuration overlays."""
        return tuple(self._definitions.values())


@lru_cache(maxsize=1)
def get_default_agent_registry() -> AgentRegistry:
    """Return the built-in experts available in the current release."""
    return AgentRegistry(
        (
            AgentDefinition("craft_expert", "技艺知识专家", "🎨", "工艺流程与材料", CraftExpertAgent),
            AgentDefinition("history_expert", "历史文化专家", "📜", "起源、演变与文化意义", HistoryExpertAgent),
            AgentDefinition("heritage_expert", "传承现状专家", "🏛️", "保护、传承与学习路径", HeritageExpertAgent),
        )
    )
