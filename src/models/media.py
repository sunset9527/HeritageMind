"""多媒体文档数据模型"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum as SAEnum
from src.database import Base
import enum


class MediaType(str, enum.Enum):
    IMAGE = "image"
    AUDIO = "audio"


class MediaDocument(Base):
    __tablename__ = "media_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    craft_name = Column(String(100), nullable=False, index=True, comment="关联的技艺名称")
    media_type = Column(SAEnum(MediaType), nullable=False, comment="媒体类型: image/audio")
    filename = Column(String(255), nullable=False, comment="存储文件名（UUID）")
    original_name = Column(String(255), nullable=False, comment="原始文件名")
    mime_type = Column(String(50), nullable=False)
    size = Column(Integer, nullable=False, comment="文件大小（字节）")
    title = Column(String(255), default="", comment="标题/描述")
    status = Column(String(20), default="draft", comment="审核状态: draft/reviewed/published")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
