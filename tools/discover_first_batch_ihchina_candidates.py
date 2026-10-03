"""Discover official IHChina project-detail candidates for the balanced first batch.

This writes review candidates only.  It never publishes a knowledge document.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import quote

from src.services.first_batch_selection import RegistryProject, select_first_batch
from src.services.knowledge_manifest import load_manifest
from src.services.official_source_discovery import extract_ihchina_project_candidates


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "knowledge_sources" / "manifest.json"
OUTPUT_PATH = ROOT / "data" / "knowledge_sources" / "candidates" / "first-batch-ihchina-v1.json"


def _first_batch_projects() -> tuple[RegistryProject, ...]:
    manifest = load_manifest(MANIFEST_PATH)
    projects = []
    for document in manifest.documents:
        if document.evidence_layer != "registry_record":
            continue
        category_match = re.search(r"^- 门类：(.+)$", document.content, re.MULTILINE)
        if category_match is None:
            raise ValueError(f"{document.document_key}: registry record is missing a category")
        projects.append(RegistryProject(document.document_key, document.craft_name, category_match.group(1)))
    return select_first_batch(projects)


def _fetch_search_html(craft_name: str) -> str:
    url = f"https://www.ihchina.cn/search_result/keyword/{quote(craft_name)}"
    result = subprocess.run(
        [
            "curl.exe", "--ssl-no-revoke", "--http1.1", "--location", "--retry", "1",
            "--retry-delay", "1", "--connect-timeout", "15", "--max-time", "45", "--silent",
            "--show-error", url,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"curl exited with {result.returncode}")
    return result.stdout


def _load_existing() -> dict[str, object]:
    if not OUTPUT_PATH.exists():
        return {"dataset_version": "candidate-v1-2026-10-03", "candidates": []}
    return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))


def upsert_candidate_record(
    records: list[dict[str, object]],
    refreshed: dict[str, object],
) -> list[dict[str, object]]:
    """Replace a prior attempt so a transient failure remains retryable."""
    key = refreshed["registry_document_key"]
    return [
        refreshed if record["registry_document_key"] == key else record
        for record in records
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10, help="maximum unresolved projects to query")
    parser.add_argument("--delay", type=float, default=0.8, help="delay between source requests")
    args = parser.parse_args()

    payload = _load_existing()
    candidates_payload = payload["candidates"]
    completed = {
        item["registry_document_key"]
        for item in candidates_payload
        if item["status"] == "candidate"
    }
    unresolved = [project for project in _first_batch_projects() if project.document_key not in completed]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    for project in unresolved[:args.limit]:
        try:
            candidates = extract_ihchina_project_candidates(_fetch_search_html(project.craft_name))
            status = "candidate" if candidates else "unresolved"
            error = None
        except RuntimeError as exc:
            candidates = []
            status = "unresolved"
            error = str(exc)
        refreshed = {
            "registry_document_key": project.document_key,
            "craft_name": project.craft_name,
            "category": project.category,
            "source_name": "中国非物质文化遗产网·中国非物质文化遗产数字博物馆",
            "searched_at": date.today().isoformat(),
            "status": status,
            "error": error,
            "project_detail_candidates": [candidate.__dict__ for candidate in candidates],
        }
        payload["candidates"] = upsert_candidate_record(candidates_payload, refreshed)
        candidates_payload = payload["candidates"]
        OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{project.document_key}: {status} ({len(candidates)} candidates)")
        time.sleep(args.delay)


if __name__ == "__main__":
    main()
