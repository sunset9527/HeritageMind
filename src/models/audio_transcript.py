"""音频转写 sidecar 数据模型（v1.4）

转写状态机 UPLOADED → TRANSCRIBING → INDEXED | FAILED 独立存于此表，
避免对既有 media_documents 加列（该表在 MySQL 已存在且无迁移脚本）。

full_text 存完整转写文本：转写是 CPU 重活，失败重试时若 full_text 已存在
则跳过二次转写、只重切块入向量索引（省钱 + 幂等）。
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import LONGTEXT

from src.database import Base


class AudioTranscriptStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"          # 已入队待转写
    TRANSCRIBING = "TRANSCRIBING"  # worker 正在转写（attempts 已 +1）
    INDEXED = "INDEXED"            # 转写 + 向量入库完成
    FAILED = "FAILED"              # 达到最大尝试仍失败，保留 error 供人工审计


class AudioTranscript(Base):
    __tablename__ = "audio_transcripts"
    __table_args__ = (
        UniqueConstraint("media_id", name="uq_audio_transcripts_media_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(
        Integer,
        ForeignKey("media_documents.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的 media_documents.id（业务键，唯一）",
    )
    craft_name = Column(String(100), nullable=False, index=True, comment="冗余快照，检索展示免 join")
    status = Column(String(20), nullable=False, default=AudioTranscriptStatus.UPLOADED.value, index=True)
    attempts = Column(Integer, nullable=False, default=0, comment="已尝试转写次数")
    language = Column(String(20), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    full_text = Column(
        LONGTEXT().with_variant(Text(), "sqlite"),
        nullable=True,
        comment="完整转写文本（MySQL LONGTEXT / SQLite TEXT）",
    )
    chunk_count = Column(Integer, nullable=False, default=0, comment="入库 chroma 的分块数")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    started_at = Column(DateTime(timezone=True), nullable=True, comment="最近一次转写开始（陈旧回收用）")
    finished_at = Column(DateTime(timezone=True), nullable=True)
