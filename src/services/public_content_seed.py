"""Initialize public pages from the reviewed local knowledge-source package."""

from collections import defaultdict
from pathlib import Path

from sqlalchemy.orm import Session

from src.models.platform import CraftEntry, SourceEvidence
from src.services.knowledge_manifest import KnowledgeManifest, ManifestDocument, load_manifest
from src.services.platform_content import make_slug


MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "knowledge_sources" / "manifest.json"


def _summary(document: ManifestDocument) -> str:
    """Use the package's authored abstract instead of generating a new claim."""
    for line in document.content.splitlines():
        line = line.strip()
        if line.startswith("摘要："):
            return line.removeprefix("摘要：").strip()
    return document.title


def _render_content(craft_name: str, documents: list[ManifestDocument]) -> str:
    sections = [f"{craft_name} · 来源化知识摘要"]
    for index, document in enumerate(documents, start=1):
        sections.extend((
            f"\n【资料 {index}】{document.title}",
            document.content,
            "资料来源：" + document.source_name,
            "原始链接：" + document.source_url,
        ))
    return "\n".join(sections)


def _add_missing_source_evidence(db: Session, craft: CraftEntry, document: ManifestDocument) -> None:
    existing = db.query(SourceEvidence).filter(
        SourceEvidence.subject_type == "craft",
        SourceEvidence.subject_id == craft.id,
        SourceEvidence.source_url == document.source_url,
    ).first()
    if existing is None:
        db.add(SourceEvidence(
            subject_type="craft",
            subject_id=craft.id,
            source_url=document.source_url,
            source_name=document.source_name,
            evidence_text=document.content,
        ))


def seed_curated_craft_entries(db: Session, manifest: KnowledgeManifest) -> dict[str, int]:
    """Publish absent/empty craft records without overwriting authored content.

    The content is assembled solely from reviewed manifest summaries and its
    source links. Existing non-empty entries are treated as human-managed data.
    """
    grouped: dict[str, list[ManifestDocument]] = defaultdict(list)
    for document in manifest.documents:
        if document.status == "published":
            grouped[document.craft_name].append(document)

    result = {"created": 0, "updated": 0, "skipped": 0}
    for craft_name, documents in grouped.items():
        craft = db.query(CraftEntry).filter(CraftEntry.name == craft_name).first()
        content = _render_content(craft_name, documents)
        if craft is None:
            craft = CraftEntry(
                name=craft_name,
                slug=make_slug(craft_name),
                summary=_summary(documents[0]),
                content=content,
                status="published",
            )
            db.add(craft)
            db.flush()
            result["created"] += 1
        elif not craft.summary.strip() and not craft.content.strip():
            craft.summary = _summary(documents[0])
            craft.content = content
            craft.status = "published"
            db.flush()
            result["updated"] += 1
        else:
            result["skipped"] += 1

        for document in documents:
            _add_missing_source_evidence(db, craft, document)
    db.flush()
    return result


def seed_public_content(db: Session) -> dict[str, object]:
    """Seed the public encyclopedia and the separately verified inheritor records."""
    crafts = seed_curated_craft_entries(db, load_manifest(MANIFEST_PATH))
    from src.seed_v20_content import import_inheritor_seed
    db.commit()
    inheritors = import_inheritor_seed(db, actor_id=None)
    return {"crafts": crafts, "inheritors_created": inheritors}


def main() -> None:
    from src.database import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        print(seed_public_content(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
