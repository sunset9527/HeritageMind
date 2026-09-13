from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.database import Base
from src.models.platform import CraftEntry, GraphChangeCandidate


def test_publish_craft_scans_candidates_only_after_publication():
    from src.services.platform_content import publish_craft_entry
    engine = create_engine("sqlite://", poolclass=StaticPool); Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)(); craft = CraftEntry(name="景泰蓝", slug="景泰蓝", content="景泰蓝使用铜。")
    db.add(craft); db.commit()
    publish_craft_entry(db, craft_id=craft.id, actor_id=None)
    assert craft.status == "published"
    assert db.query(GraphChangeCandidate).count() == 1
