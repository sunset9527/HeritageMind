"""Count traceable main-list projects and profiles in the active local books.

This is an audit, not a publishing step. OCR misses remain explicit gaps.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
from typing import Any


_BATCHES = {
    "second": ("第二批国家级非物质文化遗产名录简介", 519, 1028),
    "third": ("第三批国家级非物质文化遗产名录图典 上", 1029, 1219),
}
_INHERITOR_TITLE = "国家级非物质文化遗产项目代表性传承人大典"
_CODE = re.compile(r"^[IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ1lN]{1,6}\s*[-－—]+\s*\d{1,3}$", re.IGNORECASE)
_OCR_CODE = re.compile(r"^[0-9IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩlN+]{1,8}\s*[-－—]+\s*\d{1,3}$", re.IGNORECASE)
_COMBINED_HEADING = re.compile(
    r"^(?P<number>\d{3,4})\s*[.:]?\s*(?P<code>[IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩlN+]{1,8}\s*[-－—]+\s*\d{1,3})$",
    re.IGNORECASE,
)
_PERSON_HEADING = re.compile(
    r"(?m)^\s*(?P<number>\d{1,3})\s*[.．]?\s*(?P<code>[IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ1lN]{1,6})\s*[-－—]+\s*(?P<code_number>\d{1,3})"
)
_CATEGORY_LINES = frozenset({
    "民间文学", "传统音乐", "民间音乐", "传统舞蹈", "民间舞蹈", "传统戏剧", "曲艺",
    "传统体育、游艺与杂技", "传统美术", "民间美术", "传统技艺", "传统手工技艺", "传统医药", "民俗",
})
_OCR_PAGE_SEQUENCE_CORRECTIONS = {
    # PDF pages manually checked against their displayed title and official list.
    # These are OCR faults, not substitutions of project content.
    "second": {
        (410, "856"): 855,  # 维吾尔族刺绣; OCR incremented the printed sequence
        (411, "857"): 856,  # 满族刺绣; same one-step OCR increment
        (417, "VI-87"): 863,  # 灰塑; OCR dropped the sequence line
    },
}


def _pages(documents_path: Path) -> dict[tuple[str, int], list[str]]:
    pages: dict[tuple[str, int], list[str]] = defaultdict(list)
    for line in documents_path.open(encoding="utf-8"):
        if not line.strip():
            continue
        document = json.loads(line)
        metadata = document.get("metadata", {})
        title = metadata.get("book_title")
        page = metadata.get("page_start")
        content = document.get("content")
        if isinstance(title, str) and isinstance(page, int) and isinstance(content, str):
            pages[(title, page)].append(content)
    return pages


def _candidate_name(lines: list[str], start: int) -> str | None:
    for line in lines[start:start + 5]:
        value = line.strip()
        if (
            not value or value.isdigit() or _CODE.fullmatch(value)
            or value.startswith(("申报地区", "项目保护", "目录", "附录", "索引", "（", "("))
            or value in _CATEGORY_LINES or "名录" in value
        ):
            continue
        if 2 <= len(value) <= 75 and re.search(r"[\u4e00-\u9fff]", value):
            return value
    return None


def _has_project_code(lines: list[str], start: int) -> bool:
    """Accept common OCR variants such as ``3II-99`` beside a numbered title.

    A number alone is not enough: appendices also contain item numbers.  The
    project code is the second independent signal which keeps those pages out.
    """
    return any(_OCR_CODE.fullmatch(line.strip()) for line in lines[start:start + 5])


def _batch_profiles(
    pages: dict[tuple[str, int], list[str]],
    title_marker: str,
    low: int,
    high: int,
    *,
    page_corrections: dict[tuple[int, str], int] | None = None,
) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for (title, page), chunks in sorted(pages.items(), key=lambda item: item[0][1]):
        if title_marker not in title:
            continue
        if low == 519 and not 50 <= page <= 650:
            continue
        if low == 1029 and not 25 <= page <= 470:
            continue
        lines = "\n".join(chunks).splitlines()
        for index, line in enumerate(lines):
            raw_heading = line.strip()
            sequence: int | None = None
            code_on_heading = False
            if (page_corrections or {}).get((page, raw_heading)) is not None:
                sequence = (page_corrections or {})[(page, raw_heading)]
                code_on_heading = "-" in raw_heading
            elif raw_heading.isdigit() and low <= int(raw_heading) <= high:
                sequence = int(raw_heading)
            else:
                combined = _COMBINED_HEADING.fullmatch(raw_heading)
                if combined is not None and low <= int(combined.group("number")) <= high:
                    sequence = int(combined.group("number"))
                    code_on_heading = True
                # OCR can append one stray glyph to a three-digit sequence.
                elif (
                    raw_heading.isdigit() and len(raw_heading) == 4
                    and low <= int(raw_heading[:3]) <= high
                    and _has_project_code(lines, index + 1)
                ):
                    sequence = int(raw_heading[:3])
            if sequence is None or str(sequence) in profiles:
                continue
            name = _candidate_name(lines, index + 1)
            has_region = any("申报地区或单位" in value for value in lines[index + 1:index + 30])
            if not name or not (has_region or code_on_heading or _has_project_code(lines, index + 1)):
                continue
            profiles[str(sequence)] = {
                "name": name,
                "book_title": title,
                "page": page,
            }
    return profiles


def _inheritor_numbers(pages: dict[tuple[str, int], list[str]]) -> dict[str, int]:
    candidates: dict[int, list[int]] = defaultdict(list)
    for (title, page), chunks in pages.items():
        if _INHERITOR_TITLE not in title or not 13 <= page <= 249:
            continue
        for match in _PERSON_HEADING.finditer("\n".join(chunks)):
            number = int(match.group("number"))
            if 1 <= number <= 226:
                candidates[number].append(page)
    return {
        str(number): min(found_pages, key=lambda page: abs(page - number - 12))
        for number, found_pages in sorted(candidates.items())
    }


def audit_local_books(root: Path | str) -> dict[str, Any]:
    """Return a page-linked audit without changing the active projection."""
    pages = _pages(Path(root) / "documents.jsonl")
    batches = {}
    for key, (title, low, high) in _BATCHES.items():
        profiles = _batch_profiles(
            pages, title, low, high, page_corrections=_OCR_PAGE_SEQUENCE_CORRECTIONS.get(key),
        )
        batches[key] = {
            "expected_count": high - low + 1,
            "found_count": len(profiles),
            "missing_numbers": [number for number in range(low, high + 1) if str(number) not in profiles],
            "profiles": profiles,
        }
    people = _inheritor_numbers(pages)
    return {
        "batches": batches,
        "inheritor_volume": {
            "expected_first_batch_count": 226,
            "found_count": len(people),
            "missing_numbers": [number for number in range(1, 227) if str(number) not in people],
            "profile_numbers": people,
        },
    }


def _base_project_name(name: str) -> str:
    return re.split(r"[（(]", name, maxsplit=1)[0].replace(" ", "").strip()


def compare_official_catalogue(audit: dict[str, Any], official_path: Path | str) -> dict[str, Any]:
    """Keep OCR gaps and spelling disagreements visible beside official facts."""
    official = json.loads(Path(official_path).read_text(encoding="utf-8"))
    result: dict[str, Any] = {}
    for batch in official["batches"]:
        key = batch["batch"]
        profiles = audit["batches"][key]["profiles"]
        missing: list[int] = []
        disagreements: list[dict[str, Any]] = []
        covered = 0
        for item in sorted(batch["items"], key=lambda row: row["sequence"]):
            sequence = item["sequence"]
            profile = profiles.get(str(sequence))
            if profile is None:
                missing.append(sequence)
                continue
            covered += 1
            if _base_project_name(item["name"]) != _base_project_name(profile["name"]):
                disagreements.append({
                    "sequence": sequence,
                    "official_name": item["name"],
                    "ocr_name": profile["name"],
                    "page": profile["page"],
                })
        result[key] = {
            "official_count": len(batch["items"]),
            "covered_count": covered,
            "missing_from_book": missing,
            "name_disagreements": disagreements,
        }
    return result
