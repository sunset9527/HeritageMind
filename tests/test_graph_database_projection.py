from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.graph.heritage_graph import HeritageKnowledgeGraph
from src.models.platform import CraftEntry, InheritorProfile


def test_sync_published_platform_nodes_reflects_database_changes_without_unreviewed_edges():
    from src.services.graph_projection import sync_published_platform_nodes

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    craft = CraftEntry(name="测试技艺", slug="test-craft", status="published")
    inheritor = InheritorProfile(name="测试传承人", slug="test-inheritor", craft_name="测试技艺", status="published")
    db.add_all([craft, inheritor]); db.commit()
    graph = HeritageKnowledgeGraph()

    assert sync_published_platform_nodes(db, graph) == {"crafts": 1, "inheritors": 1}
    assert graph.get_node(f"platform:craft:{craft.id}")["name"] == "测试技艺"
    assert graph.get_neighbors(f"platform:inheritor:{inheritor.id}")[0]["node"]["name"] == "测试技艺"

    craft.status = "draft"; db.commit()
    sync_published_platform_nodes(db, graph)
    assert graph.get_node(f"platform:craft:{craft.id}") is None


def test_sync_published_platform_nodes_reuses_the_existing_base_craft_node():
    from src.services.graph_projection import sync_published_platform_nodes

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    craft = CraftEntry(name="景泰蓝", slug="jingtailan", status="published")
    inheritor = InheritorProfile(name="测试景泰蓝传承人", slug="test-jingtailan", craft_name="景泰蓝", status="published")
    db.add_all([craft, inheritor]); db.commit()
    graph = HeritageKnowledgeGraph()
    assert graph.load_from_json()

    sync_published_platform_nodes(db, graph)

    assert graph.get_node(f"platform:craft:{craft.id}") is None
    assert graph.graph.has_edge(f"platform:inheritor:{inheritor.id}", "jingtailan")
