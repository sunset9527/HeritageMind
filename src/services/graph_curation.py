"""Apply reviewed graph changes while preserving the source evidence."""

from sqlalchemy.orm import Session

from src.graph.heritage_graph import HeritageKnowledgeGraph
from src.models.platform import GraphChangeCandidate


def merge_approved_candidate(
    db: Session, *, candidate_id: int, graph: HeritageKnowledgeGraph
) -> GraphChangeCandidate:
    candidate = db.get(GraphChangeCandidate, candidate_id)
    if candidate is None:
        raise ValueError("graph candidate not found")
    if candidate.status != "approved":
        raise ValueError("only an approved graph candidate can be merged")

    graph.add_node(candidate.source_entity, candidate.source_type, candidate.source_entity)
    graph.add_node(candidate.target_entity, candidate.target_type, candidate.target_entity)
    graph.add_edge(
        candidate.source_entity,
        candidate.target_entity,
        candidate.relation,
        {"source_url": candidate.source_url, "evidence": candidate.evidence_text, "candidate_id": candidate.id},
    )
    return candidate
