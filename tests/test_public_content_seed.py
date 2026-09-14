from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.platform import CraftEntry, SourceEvidence
from src.services.knowledge_manifest import load_manifest


def test_seed_curated_craft_entries_publishes_all_manifest_crafts_with_source_evidence():
    from src.services.public_content_seed import seed_curated_craft_entries

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    manifest = load_manifest(Path(__file__).parents[1] / "data" / "knowledge_sources" / "manifest.json")

    assert seed_curated_craft_entries(db, manifest) == {"created": 23, "updated": 0, "skipped": 0}
    assert db.query(CraftEntry).filter_by(status="published").count() == 23
    assert db.query(SourceEvidence).filter_by(subject_type="craft").count() == 46

    jingtailan = db.query(CraftEntry).filter_by(name="景泰蓝").one()
    assert jingtailan.summary.startswith("景泰蓝制作技艺")
    assert "资料来源" in jingtailan.content
    assert "https://www.ihchina.cn/art/detail/id/14341.html" in jingtailan.content
    assert seed_curated_craft_entries(db, manifest) == {"created": 0, "updated": 0, "skipped": 23}
