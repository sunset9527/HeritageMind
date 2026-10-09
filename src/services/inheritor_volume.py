"""Extract review candidates solely from the dedicated inheritor volume."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
from typing import Any

from src.services.local_books_audit import _INHERITOR_TITLE, _PERSON_HEADING, _inheritor_numbers


# These two pages have visibly damaged OCR headings. The name is still present on
# each page; the override is applied only when that exact page contains the name.
_OCR_HEADING_CORRECTIONS = {
    11: (25, "靳景祥"),
    140: (161, "格桑"),
    156: (177, "沈新培"),
}
_VISUALLY_VERIFIED_CODES = {156: "Ⅷ—37"}
_VISUAL_PAGE_TRANSCRIPTIONS = {
    11: "男，汉族，1928年生，河北藁城人。第一批国家级非物质文化遗产项目耿村民间故事代表性传承人。",
    156: "男，汉族，1948年生，浙江龙泉人。第一批国家级非物质文化遗产项目龙泉宝剑锻制技艺代表性传承人。",
}
_NAME = re.compile(r"^[\u4e00-\u9fff·]{2,16}$")
_PROJECT = re.compile(r"第一批国家级非物质文化遗产项目(.{2,80}?)代表性传承人")
_CATEGORY = frozenset({"民间文学", "民间音乐", "民间舞蹈", "传统戏剧", "曲艺", "传统美术", "传统技艺", "传统医药", "民俗"})
_ROMAN = {"I": "Ⅰ", "II": "Ⅱ", "III": "Ⅲ", "IV": "Ⅳ", "V": "Ⅴ", "VI": "Ⅵ", "VII": "Ⅶ", "VIII": "Ⅷ", "IX": "Ⅸ", "X": "Ⅹ"}


def _volume_pages(root: Path) -> tuple[dict[tuple[str, int], list[str]], dict[tuple[str, int], list[str]]]:
    texts: dict[tuple[str, int], list[str]] = defaultdict(list)
    document_ids: dict[tuple[str, int], list[str]] = defaultdict(list)
    for line in (root / "documents.jsonl").open(encoding="utf-8"):
        if not line.strip():
            continue
        row = json.loads(line)
        metadata = row.get("metadata", {})
        title, page = metadata.get("book_title"), metadata.get("page_start")
        if _INHERITOR_TITLE in str(title) and isinstance(page, int) and 13 <= page <= 249:
            key = (title, page)
            texts[key].append(str(row.get("content", "")))
            document_ids[key].append(str(row.get("id", "")))
    return texts, document_ids


def _profile_name(text: str, number: int) -> str:
    for match in _PERSON_HEADING.finditer(text):
        if int(match.group("number")) != number:
            continue
        for line in text[match.end():match.end() + 850].splitlines():
            value = line.strip()
            if value in _CATEGORY or not _NAME.fullmatch(value):
                continue
            if value in ("国家级非物质文化遗产项目", "代表性传承人大典"):
                continue
            return value
    return ""


def _book_code(text: str, number: int) -> str:
    if number in _VISUALLY_VERIFIED_CODES:
        return _VISUALLY_VERIFIED_CODES[number]
    for match in _PERSON_HEADING.finditer(text):
        if int(match.group("number")) != number:
            continue
        prefix = match.group("code").upper().replace("1", "I").replace("L", "I")
        normalized = _ROMAN.get(prefix, prefix)
        return f"{normalized}—{int(match.group('code_number'))}"
    if number == 11 and "I-14" in text:
        return "Ⅰ—14"
    return ""


def _project_name(text: str, name: str) -> str:
    lines = [
        line for line in text.splitlines()
        if not _PERSON_HEADING.fullmatch(line.strip()) and line.strip() != name
    ]
    flattened = re.sub(r"\s+", "", "\n".join(lines))
    match = _PROJECT.search(flattened)
    if not match:
        return ""
    return match.group(1).strip("，,。；;：:")


def _biography(text: str, name: str) -> str:
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if re.match(r"\s*[男女][，,]?", line)), None)
    if start is None:
        return ""
    prose: list[str] = []
    for line in lines[start:]:
        value = line.strip()
        if not value or value == name or value in _CATEGORY or _PERSON_HEADING.fullmatch(value):
            continue
        if re.search(r"[（(].*(?:摄|摄影|提供).*[）)]", value) and "。" not in value:
            if prose:
                break
            continue
        if "代表性传承人大典" in value or value == "国家级非物质文化遗产项目":
            continue
        prose.append(value)
        if len("".join(prose)) >= 700:
            break
    joined = "".join(prose)
    sentences = re.split(r"(?<=[。！？])", joined)
    return "".join(sentences[:5])[:650].strip()


def extract_inheritor_candidates(root: Path | str) -> dict[str, Any]:
    """Return page-cited people; unresolved OCR is explicit in the result."""
    pages, document_ids = _volume_pages(Path(root))
    number_pages = _inheritor_numbers(pages)
    for number, (page, name) in _OCR_HEADING_CORRECTIONS.items():
        if str(number) not in number_pages and any(
            p == page and name in "\n".join(chunks) for (_, p), chunks in pages.items()
        ):
            number_pages[str(number)] = page
    people: list[dict[str, Any]] = []
    for number in range(1, 227):
        page = number_pages.get(str(number))
        if page is None:
            continue
        key = next(((title, p) for title, p in pages if p == page), None)
        if key is None:
            continue
        text = "\n".join(pages[key])
        corrected_name = _OCR_HEADING_CORRECTIONS.get(number, (None, ""))[1]
        name = corrected_name if corrected_name and corrected_name in text else _profile_name(text, number)
        project_name = _project_name(text, name)
        biography = _biography(text, name)
        visually_transcribed = number in _VISUAL_PAGE_TRANSCRIPTIONS and name in text
        if visually_transcribed:
            biography = _VISUAL_PAGE_TRANSCRIPTIONS[number]
            if not project_name:
                project_name = _project_name(biography, name)
        evidence = {"book_title": key[0], "page": page, "document_ids": document_ids[key]}
        people.append({
            "sequence": number,
            "name": name,
            "project_name": project_name,
            "book_project_code": _book_code(text, number),
            "biography": {
                "text": biography,
                "status": "visually_transcribed_from_pdf" if visually_transcribed else "transcribed" if biography else "missing",
                "evidence": [evidence],
            },
            "evidence": evidence,
            "status": "pending_review" if name and project_name and biography else "needs_ocr_review",
        })
    return {
        "expected_count": 226,
        "found_count": len(people),
        "missing_numbers": [n for n in range(1, 227) if str(n) not in number_pages],
        "people": people,
    }
