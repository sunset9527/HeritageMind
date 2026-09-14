from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.platform import CraftEntry, GraphChangeCandidate


def test_scan_published_crafts_creates_candidates_and_is_idempotent():
    from src.services.graph_scheduler import scan_published_crafts

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        CraftEntry(name="景泰蓝", slug="景泰蓝", content="景泰蓝使用铜作为胎体。", status="published"),
        CraftEntry(name="未发布条目", slug="未发布条目", content="使用竹。", status="draft"),
    ])
    db.commit()

    assert scan_published_crafts(db) == {"scanned": 1, "created": 1}
    assert db.query(GraphChangeCandidate).count() == 1
    assert scan_published_crafts(db) == {"scanned": 1, "created": 0}
