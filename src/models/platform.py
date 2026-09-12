"""Persisted, source-backed content primitives for the v2 platform."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from src.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CraftEntry(Base):
    __tablename__ = "craft_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=False, default="")
    content = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="draft", index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class InheritorProfile(Base):
    __tablename__ = "inheritor_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    craft_name = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, default="")
    recognition = Column(String(255), nullable=False, default="")
    biography = Column(Text, nullable=False, default="")
    lineage = Column(Text, nullable=False, default="")
    representative_works = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="draft", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class SourceEvidence(Base):
    __tablename__ = "source_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_type = Column(String(32), nullable=False, index=True)
    subject_id = Column(Integer, nullable=False, index=True)
    source_url = Column(String(500), nullable=False)
    source_name = Column(String(255), nullable=False)
    evidence_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class GraphChangeCandidate(Base):
    __tablename__ = "graph_change_candidates"
    __table_args__ = (
        UniqueConstraint(
            "source_entity", "relation", "target_entity", "source_url",
            name="uq_graph_candidate_fact_source",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_entity = Column(String(160), nullable=False, index=True)
    source_type = Column(String(32), nullable=False)
    relation = Column(String(64), nullable=False)
    target_entity = Column(String(160), nullable=False, index=True)
    target_type = Column(String(32), nullable=False)
    evidence_text = Column(Text, nullable=False)
    source_url = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_reason = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    subject_type = Column(String(32), nullable=False)
    subject_id = Column(Integer, nullable=False)
    detail = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
