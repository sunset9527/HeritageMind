"""Project published platform records into the in-memory knowledge graph."""

from sqlalchemy.orm import Session

from src.graph.heritage_graph import HeritageKnowledgeGraph
from src.models.platform import CraftEntry, InheritorProfile


MANAGED_PROPERTY = "platform_database_projection"


def sync_published_platform_nodes(db: Session, graph: HeritageKnowledgeGraph) -> dict[str, int]:
    """Refresh only source-backed, published database nodes without inventing relations."""
    managed_node_ids = [
        node_id for node_id, attrs in graph.graph.nodes(data=True)
        if attrs.get("properties", {}).get(MANAGED_PROPERTY)
    ]
    graph.graph.remove_nodes_from(managed_node_ids)

    crafts = db.query(CraftEntry).filter(CraftEntry.status == "published").all()
    craft_node_ids: dict[str, str] = {}
    for craft in crafts:
        node_id = f"platform:craft:{craft.id}"
        craft_node_ids[craft.name] = node_id
        graph.add_node(node_id, "craft", craft.name, {
            MANAGED_PROPERTY: True,
            "slug": craft.slug,
            "summary": craft.summary,
        })

    inheritors = db.query(InheritorProfile).filter(InheritorProfile.status == "published").all()
    for inheritor in inheritors:
        node_id = f"platform:inheritor:{inheritor.id}"
        graph.add_node(node_id, "inheritor", inheritor.name, {
            MANAGED_PROPERTY: True,
            "slug": inheritor.slug,
            "region": inheritor.region,
        })
        craft_node_id = craft_node_ids.get(inheritor.craft_name)
        if craft_node_id:
            graph.add_edge(node_id, craft_node_id, "mastered_by", {MANAGED_PROPERTY: True})

    return {"crafts": len(crafts), "inheritors": len(inheritors)}
