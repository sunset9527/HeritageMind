"""用户收藏数据模型"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from src.database import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    craft_name = Column(String(100), nullable=False, comment="收藏的技艺名称")
    chat_id = Column(Integer, ForeignKey("chat_history.id", ondelete="SET NULL"), nullable=True)
    note = Column(String(500), default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
