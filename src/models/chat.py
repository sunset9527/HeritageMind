"""
聊天历史模型
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from src.database import Base


class ChatHistory(Base):
    """聊天历史表"""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True, comment="v1.5 会话ID")
    question = Column(Text, nullable=False, comment="用户问题")
    answer = Column(Text, nullable=False, comment="系统回答")
    user_profile = Column(String(20), default="curious", nullable=False, comment="用户画像: curious/learner/researcher")
    agents_used = Column(JSON, nullable=True, comment="参与的Agent列表")
    has_gaps = Column(Boolean, default=False, comment="是否存在知识缺口")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<ChatHistory(id={self.id}, user_id={self.user_id}, profile='{self.user_profile}')>"
