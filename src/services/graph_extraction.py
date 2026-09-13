"""Deterministic, review-first extraction from curated craft content."""

from src.services.platform_content import create_graph_candidate
from src.models.platform import GraphChangeCandidate


MATERIAL_PATTERNS = {"铜": "uses_material", "丝": "uses_material", "竹": "uses_material", "木": "uses_material", "纸": "uses_material"}


def extract_craft_candidates(db, craft) -> int:
    """Create pending candidates from explicit material statements only."""
    if craft.status != "published":
        return 0
    created = 0
    for material, relation in MATERIAL_PATTERNS.items():
        if material not in (craft.content or ""):
            continue
        exists = db.query(GraphChangeCandidate.id).filter_by(
            source_entity=craft.name, relation=relation, target_entity=material,
            source_url=f"internal://craft/{craft.slug}",
        ).first()
        if exists:
            continue
        candidate = create_graph_candidate(
            db, source_entity=craft.name, source_type="craft", relation=relation,
            target_entity=material, target_type="material",
            evidence_text=f"{craft.name}：{craft.content}", source_url=f"internal://craft/{craft.slug}",
        )
        created += 1
    return created
