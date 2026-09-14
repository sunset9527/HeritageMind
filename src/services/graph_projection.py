"""Project published platform records and curated sources into the knowledge graph."""

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from src.graph.heritage_graph import HeritageKnowledgeGraph
from src.models.platform import CraftEntry, InheritorProfile


logger = logging.getLogger(__name__)


MANAGED_PROPERTY = "platform_database_projection"
CURATED_SOURCE_PROPERTY = "curated_source_projection"
CURATED_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "knowledge_sources" / "manifest.json"


def sync_curated_source_nodes(
    graph: HeritageKnowledgeGraph,
    manifest_path: Path = CURATED_MANIFEST_PATH,
) -> int:
    """Refresh published, traceable knowledge-source nodes without inventing claims.

    Each manifest item becomes one ``source`` node and a ``has_source`` edge from
    the matching craft. The graph therefore exposes where expanded retrieval
    knowledge came from, while the source URL remains available in node details.
    """
    managed_node_ids = [
        node_id for node_id, attrs in graph.graph.nodes(data=True)
        if attrs.get("properties", {}).get(CURATED_SOURCE_PROPERTY)
    ]
    graph.graph.remove_nodes_from(managed_node_ids)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        logger.warning("无法加载知识来源清单 %s: %s", manifest_path, error)
        return 0

    craft_ids = {
        attrs.get("name"): node_id
        for node_id, attrs in graph.graph.nodes(data=True)
        if attrs.get("type") == "craft"
    }
    source_count = 0
    for document in manifest.get("documents", []):
        if document.get("status") != "published":
            continue

        craft_name = document.get("craft_name")
        craft_node_id = craft_ids.get(craft_name)
        if not craft_node_id:
            # A manifest entry remains visible even if the base graph has not yet
            # been refreshed with that craft. This fallback carries no inferred data.
            craft_node_id = f"curated:craft:{craft_name}"
            graph.add_node(craft_node_id, "craft", craft_name, {CURATED_SOURCE_PROPERTY: True})
            craft_ids[craft_name] = craft_node_id

        source_node_id = f"curated:source:{document['document_key']}"
        graph.add_node(source_node_id, "source", document.get("title", document["document_key"]), {
            CURATED_SOURCE_PROPERTY: True,
            "source_name": document.get("source_name", ""),
            "source_url": document.get("source_url", ""),
            "accessed_at": document.get("accessed_at", ""),
        })
        graph.add_edge(craft_node_id, source_node_id, "has_source", {CURATED_SOURCE_PROPERTY: True})
        source_count += 1

    return source_count


def sync_published_platform_nodes(db: Session, graph: HeritageKnowledgeGraph) -> dict[str, int]:
    """Refresh only source-backed, published database nodes without inventing relations."""
    managed_node_ids = [
        node_id for node_id, attrs in graph.graph.nodes(data=True)
        if attrs.get("properties", {}).get(MANAGED_PROPERTY)
    ]
    graph.graph.remove_nodes_from(managed_node_ids)

    crafts = db.query(CraftEntry).filter(CraftEntry.status == "published").all()
    base_craft_node_ids = {
        attrs.get("name"): node_id
        for node_id, attrs in graph.graph.nodes(data=True)
        if attrs.get("type") == "craft"
        and not attrs.get("properties", {}).get(MANAGED_PROPERTY)
    }
    craft_node_ids: dict[str, str] = {}
    for craft in crafts:
        # The 23 curated crafts already exist in the base graph. Reuse those
        # nodes so importing public-page content does not create a duplicate.
        node_id = base_craft_node_ids.get(craft.name)
        if node_id is None:
            node_id = f"platform:craft:{craft.id}"
            graph.add_node(node_id, "craft", craft.name, {
                MANAGED_PROPERTY: True,
                "slug": craft.slug,
                "summary": craft.summary,
            })
        craft_node_ids[craft.name] = node_id

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
