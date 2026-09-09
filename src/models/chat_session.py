"""登录用户的持久化聊天会话模型。"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String

from src.database import Base


class ChatSession(Base):
    """一组连续问答的所有权和排序信息。"""

    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(120), nullable=False, default="新对话")
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_active_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id})>"
