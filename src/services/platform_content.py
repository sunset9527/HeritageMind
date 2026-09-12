"""Business rules for curated public platform content."""

from datetime import datetime, timezone
from re import sub

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.platform import AuditLog, GraphChangeCandidate, InheritorProfile, SourceEvidence


def make_slug(value: str) -> str:
    """Use a stable URL-safe slug while retaining Chinese names when present."""
    slug = sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", value.strip()).strip("-").lower()
    if not slug:
        raise ValueError("name is required")
    return slug


def _audit(db: Session, actor_id: int | None, action: str, subject_type: str, subject_id: int, detail: str = "") -> None:
    db.add(AuditLog(
        actor_user_id=actor_id,
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        detail=detail,
    ))


def create_inheritor_profile(
    db: Session, *, actor_id: int, name: str, craft_name: str, region: str = "",
    biography: str = "", recognition: str = "", lineage: str = "", representative_works: str = "",
) -> InheritorProfile:
    profile = InheritorProfile(
        name=name.strip(), slug=make_slug(name), craft_name=craft_name.strip(), region=region.strip(),
        biography=biography.strip(), recognition=recognition.strip(), lineage=lineage.strip(),
        representative_works=representative_works.strip(),
    )
    db.add(profile)
    db.flush()
    _audit(db, actor_id, "inheritor.created", "inheritor", profile.id)
    db.flush()
    return profile


def add_source_evidence(
    db: Session, *, subject_type: str, subject_id: int, source_url: str,
    source_name: str, evidence_text: str, actor_id: int | None,
) -> SourceEvidence:
    if not source_url.startswith(("https://", "http://")):
        raise ValueError("source_url must be an http(s) URL")
    if not source_name.strip() or not evidence_text.strip():
        raise ValueError("source name and evidence text are required")
    evidence = SourceEvidence(
        subject_type=subject_type, subject_id=subject_id, source_url=source_url.strip(),
        source_name=source_name.strip(), evidence_text=evidence_text.strip(),
    )
    db.add(evidence)
    db.flush()
    _audit(db, actor_id, "source.created", subject_type, subject_id)
    db.flush()
    return evidence


def publish_inheritor_profile(db: Session, *, profile_id: int, actor_id: int) -> InheritorProfile:
    profile = db.get(InheritorProfile, profile_id)
    if profile is None:
        raise ValueError("inheritor profile not found")
    evidence = db.scalar(select(SourceEvidence.id).where(
        SourceEvidence.subject_type == "inheritor", SourceEvidence.subject_id == profile_id
    ))
    if evidence is None:
        raise ValueError("a published inheritor profile requires source evidence")
    profile.status = "published"
    _audit(db, actor_id, "inheritor.published", "inheritor", profile.id)
    db.flush()
    return profile


def create_graph_candidate(
    db: Session, *, source_entity: str, source_type: str, relation: str,
    target_entity: str, target_type: str, evidence_text: str, source_url: str,
) -> GraphChangeCandidate:
    fields = (source_entity, source_type, relation, target_entity, target_type, evidence_text, source_url)
    if not all(value and value.strip() for value in fields):
        raise ValueError("graph candidate fields are required")
    existing = db.scalar(select(GraphChangeCandidate).where(
        GraphChangeCandidate.source_entity == source_entity.strip(),
        GraphChangeCandidate.relation == relation.strip(),
        GraphChangeCandidate.target_entity == target_entity.strip(),
        GraphChangeCandidate.source_url == source_url.strip(),
    ))
    if existing is not None:
        return existing
    candidate = GraphChangeCandidate(
        source_entity=source_entity.strip(), source_type=source_type.strip(), relation=relation.strip(),
        target_entity=target_entity.strip(), target_type=target_type.strip(),
        evidence_text=evidence_text.strip(), source_url=source_url.strip(),
    )
    db.add(candidate)
    db.flush()
    return candidate


def approve_graph_candidate(db: Session, *, candidate_id: int, actor_id: int) -> GraphChangeCandidate:
    candidate = db.get(GraphChangeCandidate, candidate_id)
    if candidate is None:
        raise ValueError("graph candidate not found")
    if candidate.status == "rejected":
        raise ValueError("rejected candidate cannot be approved")
    candidate.status = "approved"
    candidate.reviewed_by_user_id = actor_id
    candidate.reviewed_at = datetime.now(timezone.utc)
    _audit(db, actor_id, "graph_candidate.approved", "graph_candidate", candidate.id)
    db.flush()
    return candidate
