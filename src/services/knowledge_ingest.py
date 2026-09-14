"""Database import for validated curated knowledge manifests."""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models.knowledge import KnowledgeDocument, KnowledgeIngestRun
from src.models.platform import CraftEntry, SourceEvidence
from src.services.knowledge_manifest import KnowledgeManifest
from src.services.platform_content import make_slug


@dataclass(frozen=True)
class IngestResult:
    created_count: int
    updated_count: int
    skipped_count: int
    run_id: int


def ingest_manifest(db: Session, manifest: KnowledgeManifest, *, actor_id: int | None) -> IngestResult:
    """Persist a validated package; re-importing an existing key is a no-op."""
    run = KnowledgeIngestRun(dataset_version=manifest.dataset_version)
    db.add(run)
    db.flush()

    created_count = 0
    updated_count = 0
    skipped_count = 0
    for item in manifest.documents:
        existing = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.document_key == item.document_key,
            KnowledgeDocument.is_current.is_(True),
        ).first()
        version = 1
        if existing is not None:
            if existing.content_sha256 == item.content_sha256:
                skipped_count += 1
                continue
            existing.is_current = False
            version = existing.version + 1
            updated_count += 1

        craft = db.query(CraftEntry).filter(CraftEntry.name == item.craft_name).first()
        if craft is None:
            craft = CraftEntry(
                name=item.craft_name,
                slug=make_slug(item.craft_name),
                summary="",
                content="",
                status="draft",
            )
            db.add(craft)
            db.flush()
        document = KnowledgeDocument(
            craft_entry_id=craft.id,
            document_key=item.document_key,
            title=item.title,
            content=item.content,
            content_sha256=item.content_sha256,
            version=version,
            status=item.status,
            source_name=item.source_name,
            source_url=item.source_url,
            accessed_at=item.accessed_at,
            license_note=item.license_note,
        )
        db.add(document)
        db.flush()
        db.add(SourceEvidence(
            subject_type="knowledge_document",
            subject_id=document.id,
            source_url=item.source_url,
            source_name=item.source_name,
            evidence_text=item.content,
        ))
        created_count += 1

    run.created_count = created_count
    run.updated_count = updated_count
    run.skipped_count = skipped_count
    run.completed_at = datetime.now(timezone.utc)
    db.flush()
    return IngestResult(
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        run_id=run.id,
    )
