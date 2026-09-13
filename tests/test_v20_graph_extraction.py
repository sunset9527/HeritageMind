from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.platform import CraftEntry, GraphChangeCandidate


def test_extract_published_craft_creates_pending_source_backed_candidate():
    from src.services.graph_extraction import extract_craft_candidates

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    craft = CraftEntry(name="景泰蓝", slug="景泰蓝", content="景泰蓝使用铜作为胎体。", status="published")
    db.add(craft); db.commit()

    assert extract_craft_candidates(db, craft) == 1
    candidate = db.query(GraphChangeCandidate).one()
    assert (candidate.source_entity, candidate.relation, candidate.target_entity, candidate.status) == ("景泰蓝", "uses_material", "铜", "pending")
    assert extract_craft_candidates(db, craft) == 0
