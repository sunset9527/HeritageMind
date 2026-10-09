"""Read-only statistics for the public dashboard."""

from sqlalchemy.orm import Session

from src.models.knowledge import KnowledgeDocument
from src.models.platform import CraftEntry, SourceEvidence


def get_dashboard_summary(db: Session) -> dict[str, int]:
    """Count only published, current, source-backed platform content."""
    published_crafts = db.query(CraftEntry).filter(CraftEntry.status == "published").count()
    published_documents = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.status == "published",
        KnowledgeDocument.is_current.is_(True),
    ).count()
    traceable_crafts = db.query(CraftEntry).filter(
        CraftEntry.status == "published",
        db.query(SourceEvidence.id).filter(
            SourceEvidence.subject_type == "craft",
            SourceEvidence.subject_id == CraftEntry.id,
        ).exists(),
    ).count()
    return {
        "published_crafts": published_crafts,
        "published_documents": published_documents,
        "traceable_crafts": traceable_crafts,
    }
