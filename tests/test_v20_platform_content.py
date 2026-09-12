"""v2.0 platform content must remain source-backed and reviewable."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.user import User


def make_db():
    from src.models.platform import (  # noqa: F401 - registers metadata
        AuditLog,
        GraphChangeCandidate,
        InheritorProfile,
        SourceEvidence,
    )

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_published_inheritor_requires_source_and_records_audit_event():
    from src.services.platform_content import (
        add_source_evidence,
        create_inheritor_profile,
        publish_inheritor_profile,
    )
    from src.models.platform import AuditLog

    db = make_db()
    db.add(User(id=1, username="admin", email="admin@example.com", password_hash="hash", role="admin"))
    db.commit()

    profile = create_inheritor_profile(
        db,
        actor_id=1,
        name="Example Inheritor",
        craft_name="Test Craft",
        region="Test Region",
        biography="A source-backed demonstration profile.",
    )

    try:
        publish_inheritor_profile(db, profile_id=profile.id, actor_id=1)
        assert False, "publication without a source must fail"
    except ValueError as error:
        assert "source" in str(error).lower()

    add_source_evidence(
        db,
        subject_type="inheritor",
        subject_id=profile.id,
        source_url="https://www.ihchina.cn/example",
        source_name="Official ICH source",
        evidence_text="Example Inheritor is associated with Test Craft.",
        actor_id=1,
    )
    published = publish_inheritor_profile(db, profile_id=profile.id, actor_id=1)

    assert published.status == "published"
    assert [item.action for item in db.query(AuditLog).all()] == [
        "inheritor.created",
        "source.created",
        "inheritor.published",
    ]


def test_graph_candidates_deduplicate_and_only_approved_candidate_is_mergeable():
    from src.services.platform_content import (
        approve_graph_candidate,
        create_graph_candidate,
    )

    db = make_db()
    db.add(User(id=1, username="admin", email="admin@example.com", password_hash="hash", role="admin"))
    db.commit()

    first = create_graph_candidate(
        db,
        source_entity="Example Inheritor",
        source_type="inheritor",
        relation="mastered_by",
        target_entity="Test Craft",
        target_type="craft",
        evidence_text="The source establishes the association.",
        source_url="https://www.ihchina.cn/example",
    )
    duplicate = create_graph_candidate(
        db,
        source_entity="Example Inheritor",
        source_type="inheritor",
        relation="mastered_by",
        target_entity="Test Craft",
        target_type="craft",
        evidence_text="The source establishes the association.",
        source_url="https://www.ihchina.cn/example",
    )

    assert duplicate.id == first.id
    assert first.status == "pending"
    approved = approve_graph_candidate(db, candidate_id=first.id, actor_id=1)
    assert approved.status == "approved"
    assert approved.reviewed_by_user_id == 1
