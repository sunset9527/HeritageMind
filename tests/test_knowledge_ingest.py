"""Curated knowledge imports must be transactional and idempotent."""

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.platform import CraftEntry


def _manifest():
    from src.services.knowledge_manifest import KnowledgeManifest, ManifestDocument

    content = "景泰蓝以铜胎、掐丝和点蓝等工序著称。"
    document = ManifestDocument(
        document_key="jingtailan-overview-001",
        craft_name="景泰蓝",
        title="景泰蓝制作技艺概述",
        content_path=Path("documents/jingtailan-overview.md"),
        content=content,
        content_sha256=sha256(content.encode("utf-8")).hexdigest(),
        source_name="示例权威机构",
        source_url="https://example.org/jingtailan",
        accessed_at="2026-09-14",
        license_note="仅保存自行整理摘要与来源链接",
        status="published",
    )
    return KnowledgeManifest(dataset_version="v1", documents=(document,))


def _make_db():
    from src.models.knowledge import KnowledgeDocument, KnowledgeIngestRun  # noqa: F401

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(CraftEntry(name="景泰蓝", slug="景泰蓝", summary="", content="", status="published"))
    db.commit()
    return db


def _make_empty_db():
    from src.models.knowledge import KnowledgeDocument, KnowledgeIngestRun  # noqa: F401

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ingest_published_document_creates_source_evidence_and_is_idempotent():
    from src.models.knowledge import KnowledgeDocument, KnowledgeIngestRun
    from src.models.platform import SourceEvidence
    from src.services.knowledge_ingest import ingest_manifest

    db = _make_db()
    first = ingest_manifest(db, _manifest(), actor_id=None)
    second = ingest_manifest(db, _manifest(), actor_id=None)

    document = db.query(KnowledgeDocument).one()
    evidence = db.query(SourceEvidence).one()
    runs = db.query(KnowledgeIngestRun).order_by(KnowledgeIngestRun.id).all()

    assert first.created_count == 1
    assert first.skipped_count == 0
    assert second.created_count == 0
    assert second.skipped_count == 1
    assert document.document_key == "jingtailan-overview-001"
    assert document.status == "published"
    assert document.version == 1
    assert evidence.subject_type == "knowledge_document"
    assert evidence.subject_id == document.id
    assert len(runs) == 2
    assert runs[0].created_count == 1
    assert runs[1].skipped_count == 1


def test_ingest_changed_document_creates_a_new_current_version():
    from src.models.knowledge import KnowledgeDocument, KnowledgeIngestRun
    from src.services.knowledge_ingest import ingest_manifest

    db = _make_db()
    initial = _manifest()
    changed_content = "景泰蓝以铜胎、掐丝、点蓝和烧蓝等工序著称。"
    changed_document = replace(
        initial.documents[0],
        content=changed_content,
        content_sha256=sha256(changed_content.encode("utf-8")).hexdigest(),
    )
    changed = replace(initial, dataset_version="v2", documents=(changed_document,))

    ingest_manifest(db, initial, actor_id=None)
    result = ingest_manifest(db, changed, actor_id=None)

    versions = db.query(KnowledgeDocument).order_by(KnowledgeDocument.version).all()
    run = db.get(KnowledgeIngestRun, result.run_id)
    assert result.updated_count == 1
    assert [(row.version, row.is_current) for row in versions] == [(1, False), (2, True)]
    assert run.updated_count == 1


def test_ingest_creates_a_draft_craft_entry_when_the_aggregate_is_missing():
    from src.models.knowledge import KnowledgeDocument
    from src.services.knowledge_ingest import ingest_manifest

    db = _make_empty_db()
    ingest_manifest(db, _manifest(), actor_id=None)

    craft = db.query(CraftEntry).one()
    document = db.query(KnowledgeDocument).one()
    assert craft.name == "景泰蓝"
    assert craft.status == "draft"
    assert document.craft_entry_id == craft.id
