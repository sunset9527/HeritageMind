"""Persisted safe display and availability overrides for built-in Agents."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String

from src.database import Base


class AgentConfiguration(Base):
    __tablename__ = "agent_configurations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    display_name = Column(String(80), nullable=True)
    capability = Column(String(255), nullable=True)
    collaboration_priority = Column(Integer, nullable=False, default=100)
    parameters = Column(JSON, nullable=False, default=dict)
    updated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
