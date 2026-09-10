"""登录用户的可解释偏好模型。"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String

from src.database import Base


class UserPreference(Base):
    """保存自动学习到的标准技艺与学习深度偏好。"""

    __tablename__ = "user_preferences"

    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    preferred_crafts = Column(JSON, nullable=False, default=list)
    preferred_profile = Column(String(20), nullable=True)
    profile_scores = Column(JSON, nullable=False, default=dict)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
