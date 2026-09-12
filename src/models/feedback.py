"""User-owned feedback on a persisted chat answer."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from src.database import Base


class UserFeedback(Base):
    """One mutable up/down feedback record for a user and answer pair."""

    __tablename__ = "user_feedback"
    __table_args__ = (UniqueConstraint("user_id", "chat_id", name="uq_feedback_user_chat"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id = Column(Integer, ForeignKey("chat_history.id", ondelete="CASCADE"), nullable=False, index=True)
    sentiment = Column(String(8), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
