"""Safe administrator contracts; they never carry executable Agent code."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentConfigurationUpdate(BaseModel):
    enabled: bool = True
    display_name: Optional[str] = Field(default=None, max_length=80)
    capability: Optional[str] = Field(default=None, max_length=255)
    collaboration_priority: int = Field(default=100, ge=1, le=1000)
    parameters: dict[str, Any] = Field(default_factory=dict)
