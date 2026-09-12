def test_inheritor_seed_has_six_source_backed_profiles():
    from src.seed_v20_content import INHERITOR_SEED
    assert len(INHERITOR_SEED) == 6
    assert all(item["source_url"].startswith("https://www.ihchina.cn/") for item in INHERITOR_SEED)
    assert all(item["name"] and item["craft_name"] and item["evidence_text"] for item in INHERITOR_SEED)


def test_seed_import_is_idempotent_and_publishes_only_source_backed_records():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from src.database import Base
    from src.models import InheritorProfile, SourceEvidence
    from src.models.user import User
    from src.seed_v20_content import import_inheritor_seed

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(User(id=1, username="admin", email="admin@example.com", password_hash="hash", role="admin")); db.commit()
    assert import_inheritor_seed(db, actor_id=1) == 6
    assert import_inheritor_seed(db, actor_id=1) == 0
    assert db.query(InheritorProfile).filter_by(status="published").count() == 6
    assert db.query(SourceEvidence).filter_by(subject_type="inheritor").count() == 6
