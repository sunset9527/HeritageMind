"""Versioned, source-backed documents used by the curated knowledge base."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from src.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint("document_key", "version", name="uq_knowledge_document_key_version"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    craft_entry_id = Column(Integer, ForeignKey("craft_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    document_key = Column(String(160), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    content_sha256 = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="draft", index=True)
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    source_name = Column(String(255), nullable=False)
    source_url = Column(String(500), nullable=False)
    accessed_at = Column(String(10), nullable=False)
    license_note = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class KnowledgeIngestRun(Base):
    __tablename__ = "knowledge_ingest_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_version = Column(String(80), nullable=False, index=True)
    created_count = Column(Integer, nullable=False, default=0)
    updated_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    error_summary = Column(Text, nullable=False, default="")
    started_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
