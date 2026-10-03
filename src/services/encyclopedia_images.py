"""Resolve audited encyclopedia image records without inventing image URLs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


VALID_IMAGE_STATUSES = {"verified", "legacy_local", "pending_review", "unavailable"}


def load_image_manifest(path: Path) -> dict[str, dict[str, Any]]:
    """Load image records keyed by their exact public craft name."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    images: dict[str, dict[str, Any]] = {}
    for item in payload["images"]:
        craft_name = item["craft_name"]
        if craft_name in images:
            raise ValueError(f"duplicate craft_name: {craft_name}")
        if item["status"] not in VALID_IMAGE_STATUSES:
            raise ValueError(f"invalid image status: {item['status']}")
        if item["status"] == "verified":
            if not item["source_page_url"]:
                raise ValueError(f"verified image requires source_page_url: {craft_name}")
            if not item["source_name"] or not item["image_url"]:
                raise ValueError(f"verified image requires source metadata: {craft_name}")
        images[craft_name] = item
    return images


def resolve_encyclopedia_image(images: dict[str, dict[str, Any]], craft_name: str) -> dict[str, str | None]:
    """Return an explicit unavailable state when no reviewed image exists."""
    image = images.get(craft_name)
    if image is None:
        return {"url": None, "status": "unavailable"}
    status = image["status"]
    url = image["image_url"] if status in {"verified", "legacy_local"} else None
    return {"url": url, "status": status}
