"""Collect one IHChina national-project page as a review-only candidate.

The command never downloads media and never imports the result into the
published knowledge base.  It requires an explicit acknowledgement of the
source site's terms before making any network request.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable
from urllib.parse import quote, urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.ihchina_project_parser import IHCHINA_HOST, parse_ihchina_project_detail
from src.services.official_source_discovery import extract_ihchina_project_candidates


CANDIDATE_DIRECTORY = ROOT / "data" / "knowledge_sources" / "candidates" / "ihchina-projects"
SOURCE_NAME = "中国非物质文化遗产网·中国非物质文化遗产数字博物馆"
FetchHtml = Callable[[str], str]
Pause = Callable[[float], None]


def _normalize_name(value: str) -> str:
    normalized = re.sub(r"\s+", "", value).strip()
    return re.sub(r"-中国非物质文化遗产网.*$", "", normalized)


def _search_url(craft_name: str) -> str:
    return f"https://{IHCHINA_HOST}/search_result/keyword/{quote(craft_name)}"


def _allowed_ihchina_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.netloc == IHCHINA_HOST


def _candidate_urls(candidates: object) -> list[dict[str, str]]:
    return [{"url": candidate.url, "title": candidate.title} for candidate in candidates]


def _base_record(craft_name: str, candidates: object, status: str) -> dict[str, object]:
    return {
        "dataset_version": "ihchina-project-candidate-v1",
        "query_name": craft_name,
        "status": status,
        "publication_status": "candidate",
        "searched_at": date.today().isoformat(),
        "source_name": SOURCE_NAME,
        "project_detail_candidates": _candidate_urls(candidates),
        "license_note": "候选资料仅供人工核验；图片未下载、未镜像、未获再发布授权。",
    }


def collect_project_candidate(
    craft_name: str,
    fetch_html: FetchHtml,
    *,
    max_candidates: int = 3,
    pause: Pause = time.sleep,
    delay: float = 2.0,
) -> dict[str, object]:
    """Fetch at most one uniquely exact IHChina detail candidate for review."""
    if max_candidates < 1:
        raise ValueError("max_candidates must be at least 1")
    if delay < 0:
        raise ValueError("delay cannot be negative")

    search_url = _search_url(craft_name)
    search_candidates = extract_ihchina_project_candidates(fetch_html(search_url))[:max_candidates]
    exact_candidates = [
        candidate for candidate in search_candidates if _normalize_name(candidate.title) == _normalize_name(craft_name)
    ]
    if not search_candidates:
        return _base_record(craft_name, search_candidates, "not_found")
    if len(exact_candidates) != 1:
        return _base_record(craft_name, search_candidates, "ambiguous")

    detail_candidate = exact_candidates[0]
    if not _allowed_ihchina_url(detail_candidate.url):
        return _base_record(craft_name, search_candidates, "parse_failed")

    pause(delay)
    detail = parse_ihchina_project_detail(fetch_html(detail_candidate.url), detail_candidate.url)

    record = _base_record(craft_name, search_candidates, "needs_review")
    record.update(
        {
            "source_page_url": detail_candidate.url,
            "matched_craft_name": detail_candidate.title,
            "detail_page_title": detail.craft_name,
            "detail_title_matches_query": (
                detail.craft_name is not None
                and _normalize_name(detail.craft_name) == _normalize_name(craft_name)
            ),
            "project_sequence": detail.project_sequence,
            "project_code": detail.project_code,
            "category": detail.category,
            "declaring_region_or_unit": detail.declaring_region_or_unit,
            "protection_unit": detail.protection_unit,
            "introduction_excerpt": detail.introduction_excerpt,
            "image_candidates": [
                {
                    "image_url": image.image_url,
                    "alt": image.alt,
                    "context": "详情页图片候选",
                    "source_page_url": detail_candidate.url,
                    "status": image.status,
                }
                for image in detail.image_candidates
            ],
        }
    )
    return record


def _fetch_ihchina_html(url: str) -> str:
    if not _allowed_ihchina_url(url):
        raise RuntimeError(f"refusing non-IHChina URL: {url}")
    marker = "__IHCHINA_EFFECTIVE_URL__"
    result = subprocess.run(
        [
            "curl.exe",
            "--ssl-no-revoke",
            "--http1.1",
            "--location",
            "--retry",
            "1",
            "--retry-delay",
            "2",
            "--connect-timeout",
            "15",
            "--max-time",
            "45",
            "--silent",
            "--show-error",
            "--write-out",
            f"\n{marker}%{{url_effective}}",
            url,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"curl exited with {result.returncode}")
    body, separator, effective_url = result.stdout.rpartition(marker)
    if not separator or not _allowed_ihchina_url(effective_url.strip()):
        raise RuntimeError("request redirected outside the allowed IHChina host")
    return body.rstrip("\r\n")


def _default_output_path(craft_name: str) -> Path:
    digest = hashlib.sha256(craft_name.encode("utf-8")).hexdigest()[:12]
    return CANDIDATE_DIRECTORY / f"{digest}.json"


def _failure_record(craft_name: str, error: str) -> dict[str, object]:
    record = _base_record(craft_name, [], "fetch_failed")
    record["error"] = error
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("craft_name", help="the exact national-project name to search")
    parser.add_argument(
        "--acknowledge-ihchina-terms",
        action="store_true",
        help="confirm that this is a low-frequency, review-only source collection",
    )
    parser.add_argument("--output", type=Path, help="candidate JSON path")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between requests (default: 2)")
    parser.add_argument("--max-candidates", type=int, default=3, help="maximum search candidates to inspect (default: 3)")
    args = parser.parse_args()
    if not args.acknowledge_ihchina_terms:
        parser.error("--acknowledge-ihchina-terms is required before any request")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    if args.max_candidates < 1:
        parser.error("--max-candidates must be at least 1")

    try:
        record = collect_project_candidate(
            args.craft_name,
            _fetch_ihchina_html,
            max_candidates=args.max_candidates,
            delay=args.delay,
        )
    except RuntimeError as exc:
        record = _failure_record(args.craft_name, str(exc))
    output_path = args.output or _default_output_path(args.craft_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{record['status']}: {output_path}")


if __name__ == "__main__":
    main()
