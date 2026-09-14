"""Manual graph-candidate scans for published curated content."""

from sqlalchemy.orm import Session

from src.models.platform import CraftEntry
from src.services.graph_extraction import extract_craft_candidates


def scan_published_crafts(db: Session) -> dict[str, int]:
    """Extract any missing review candidates from all published craft entries.

    This is deliberately invoked by an administrator, never from application startup.
    Re-running it is safe because extraction de-duplicates source-backed facts.
    """
    crafts = db.query(CraftEntry).filter(CraftEntry.status == "published").all()
    created = sum(extract_craft_candidates(db, craft) for craft in crafts)
    return {"scanned": len(crafts), "created": created}
