"""阶段 1B 文档上传、索引维护任务和 worker 心跳模型。"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from src.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ReviewStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PUBLISHED = "published"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


# 文档与维护任务使用同一套处理状态，但保留业务语义清晰的公开名称。
DocumentProcessingStatus = ProcessingStatus


class MaintenanceJobKind(str, enum.Enum):
    KNOWLEDGE_INDEX = "knowledge_index"
    IMAGE_INDEX = "image_index"
    AUDIO_INDEX = "audio_index"


class DocumentUpload(Base):
    __tablename__ = "document_uploads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uploaded_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    craft_id = Column(String(120), nullable=False, index=True)
    craft_name = Column(String(100), nullable=False, index=True)
    storage_name = Column(String(255), nullable=False, unique=True)
    original_name = Column(String(255), nullable=False)
    extension = Column(String(16), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    content_sha256 = Column(String(64), nullable=False, index=True)
    parsed_storage_name = Column(String(255), nullable=True)
    char_count = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=False, default=0)
    ocr_page_count = Column(Integer, nullable=False, default=0)
    review_status = Column(
        String(20), nullable=False, default=ReviewStatus.DRAFT.value, index=True
    )
    processing_status = Column(
        String(20), nullable=False, default=ProcessingStatus.PENDING.value, index=True
    )
    attempts = Column(Integer, nullable=False, default=0)
    error_code = Column(String(80), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class MaintenanceJob(Base):
    __tablename__ = "maintenance_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kind = Column(String(40), nullable=False, index=True)
    status = Column(
        String(20), nullable=False, default=ProcessingStatus.PENDING.value, index=True
    )
    attempts = Column(Integer, nullable=False, default=0)
    input_count = Column(Integer, nullable=False, default=0)
    input_chars = Column(Integer, nullable=False, default=0)
    output_version = Column(String(120), nullable=True)
    error_code = Column(String(80), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    worker_id = Column(String(128), primary_key=True)
    version = Column(String(64), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    status = Column(String(20), nullable=False, default="unknown")
    dependencies_json = Column(Text, nullable=False, default="{}")
    last_error_code = Column(String(80), nullable=True)
