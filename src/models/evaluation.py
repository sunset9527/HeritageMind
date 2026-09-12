"""Persisted, explainable process-quality signals for one chat answer."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String

from src.database import Base


class AnswerEvaluation(Base):
    """One versioned rule evaluation per saved chat answer."""

    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(
        Integer,
        ForeignKey("chat_history.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    total_score = Column(Integer, nullable=False)
    rule_version = Column(String(32), nullable=False)
    score_details = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
