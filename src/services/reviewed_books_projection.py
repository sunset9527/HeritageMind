"""Build a review-only national catalogue projection from traceable sources."""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from difflib import SequenceMatcher
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from src.services.inheritor_volume import extract_inheritor_candidates
from src.services.local_books_audit import audit_local_books
from src.services.shandong_book_profiles import extract_shandong_profiles


DEFAULT_CORPUS = Path(__file__).resolve().parents[2] / "data" / "local_books_corpus"
DEFAULT_FIRST = Path(__file__).resolve().parents[2] / "data" / "knowledge_sources" / "official_national_batch_1.json"
DEFAULT_LATER = Path(__file__).resolve().parents[2] / "data" / "knowledge_sources" / "official_national_batches_2_3.json"


def _name_key(name: str) -> str:
    return re.sub(r"\s+", "", name).replace("(", "（").replace(")", "）")


def _match_project(projects: dict[str, dict[str, Any]], person_project_name: str) -> dict[str, Any] | None:
    exact = projects.get(_name_key(person_project_name))
    if exact is not None:
        return exact
    base = re.split(r"[（(]", _name_key(person_project_name), maxsplit=1)[0]
    if base == _name_key(person_project_name):
        matches = [project for project in projects.values() if base.startswith(_name_key(project["project_name"]))]
        return matches[0] if len(matches) == 1 else None
    matches = [project for project in projects.values() if _name_key(project["project_name"]) == base]
    return matches[0] if len(matches) == 1 else None


def _first_batch_project_by_code(
    projects: dict[str, dict[str, Any]], code: str, person_project_name: str
) -> dict[str, Any] | None:
    if not code:
        return None
    matches = [
        project for project in projects.values()
        if any(entry["batch"] == "first" and entry["code"] == code for entry in project["catalogue_entries"])
    ]
    if len(matches) != 1:
        return None
    if person_project_name:
        official = _name_key(matches[0]["project_name"])
        extracted = _name_key(person_project_name)
        if SequenceMatcher(None, official, extracted).ratio() < 0.55:
            return None
    return matches[0]


def _book_pages(root: Path) -> dict[tuple[str, int], list[dict[str, Any]]]:
    pages: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for line in (root / "documents.jsonl").open(encoding="utf-8"):
        if not line.strip():
            continue
        document = json.loads(line)
        metadata = document.get("metadata", {})
        title, page = metadata.get("book_title"), metadata.get("page_start")
        if isinstance(title, str) and isinstance(page, int):
            pages[(title, page)].append(document)
    return pages


def _description_source(
    pages: dict[tuple[str, int], list[dict[str, Any]]],
    *,
    batch: str,
    project_name: str,
    page_hint: int | None,
    ocr_name: str | None,
    sequence: int | None = None,
) -> tuple[str, dict[str, Any] | None]:
    official_base = re.split(r"[（(]", _name_key(project_name), maxsplit=1)[0]
    name_mismatch = bool(ocr_name and not _name_key(ocr_name).startswith(official_base))
    title_marker = {
        "first": "第一批国家级非物质文化遗产名录图典",
        "second": "第二批国家级非物质文化遗产名录简介",
        "third": "第三批国家级非物质文化遗产名录图典 上",
    }[batch]
    for (title, page), documents in sorted(pages.items(), key=lambda item: item[0][1]):
        if title_marker not in title or page < 25 or (page_hint is not None and page != page_hint):
            continue
        for document in documents:
            description = ""
            if not name_mismatch:
                description = _full_project_body(document["content"], ocr_name or project_name, title)
                if not description and ocr_name is None and official_base != _name_key(project_name):
                    description = _full_project_body(document["content"], official_base, title)
            extraction = "heading_match"
            if not description and sequence is not None:
                description = _sequence_verified_description(document["content"], sequence)
                extraction = "sequence_verified_page_fallback"
            if not description:
                continue
            continuation, continuation_pages, continuation_ids = _following_continuation(
                pages, title=title, page=page, initial_text=description,
            )
            description += continuation
            evidence = {
                "book_title": title,
                "chapter_title": str(document["metadata"].get("chapter_title", "")),
                "page": page,
                "document_id": document["id"],
                "document_ids": [document["id"], *continuation_ids],
                "pages": [page, *continuation_pages],
                "excerpt": description[:280],
                "extraction": extraction,
            }
            return description, evidence
    return "", None


def _source_page_evidence(
    pages: dict[tuple[str, int], list[dict[str, Any]]], *, batch: str, page_hint: int | None,
) -> dict[str, Any] | None:
    """Retain an audited official sequence page even when its prose needs review."""
    if page_hint is None:
        return None
    title_marker = {
        "first": "第一批国家级非物质文化遗产名录图典",
        "second": "第二批国家级非物质文化遗产名录简介",
        "third": "第三批国家级非物质文化遗产名录图典 上",
    }[batch]
    for (title, page), documents in pages.items():
        if page != page_hint or title_marker not in title or not documents:
            continue
        document = documents[0]
        excerpt = re.sub(r"\s+", " ", str(document.get("content", ""))).strip()[:280]
        return {
            "book_title": title,
            "chapter_title": str(document.get("metadata", {}).get("chapter_title", "")),
            "page": page,
            "document_id": document["id"],
            "document_ids": [document["id"]],
            "pages": [page],
            "excerpt": excerpt,
            "extraction": "official_sequence_page",
        }
    return None


def _sequence_verified_description(text: str, sequence: int) -> str:
    """Read a page whose printed sequence and project code have both survived OCR.

    This is only a fallback for a page already joined to the official catalogue by
    its unique sequence.  It is deliberately stricter than free-text matching:
    the page must carry the sequence, an application-region label, and a project
    code before we use its own opening prose.
    """
    lines = text.splitlines()
    sequence_index = next((
        index for index, line in enumerate(lines)
        if line.strip() == str(sequence)
    ), None)
    if sequence_index is None:
        return ""
    nearby = lines[sequence_index + 1:sequence_index + 14]
    if not any("申报地区或单位" in line for line in nearby):
        return ""
    code_index = next((
        sequence_index + 1 + index for index, line in enumerate(nearby)
        if re.fullmatch(r"[0-9IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩlN+]{1,8}\s*[-－—]+\s*\d{1,3}", line.strip(), re.IGNORECASE)
    ), None)
    if code_index is None:
        return ""
    prose = re.sub(r"\s+", "", "".join(lines[code_index + 1:]))
    first = re.match(r"[^。！？]{12,220}[。！？]", prose)
    if first is None:
        return ""
    description = first.group(0)
    blocked = ("申报地区或单位", "项目保护单位", "名录图典", "目录", "索引", "附录")
    if any(marker in description for marker in blocked):
        return ""
    second = re.match(r"[^。！？]{12,190}[。！？]", prose[first.end():])
    if second is not None and not any(marker in second.group(0) for marker in blocked):
        description += second.group(0)
    return description


_BODY_LABELS = re.compile(
    r"^(?:申报地区或单位|项目保护单位|第一批国家级非物质文化遗产名录图典|第二批国家级非物质文化遗产名录简介|"
    r"第三批国家级非物质文化遗产名录图典|民间文学|传统音乐|传统舞蹈|传统戏剧|曲艺|传统体育、游艺与杂技|传统美术|传统技艺|传统医药|民俗).*$"
)
_TRUNCATED_CATEGORY_LABELS = frozenset({"民间文", "民间音", "民间舞", "传统戏", "传统体", "传统美", "传统技", "传统医"})
_NEXT_PROJECT = re.compile(r"(?m)^(?P<name>[\u4e00-\u9fff·《》()（）]{2,50})\s*$\n^申报地区或单位[：:].*$")


def _full_project_body(text: str, project_name: str, book_title: str) -> str:
    """Read all prose on a verified project page, without catalogue labels."""
    if not _is_catalogue_title(book_title) or re.match(r"\s*(?:目录|附录|索引)", text):
        return ""
    heading = re.search(rf"(?m)^\s*(?:\d{{1,4}}\s*)?{re.escape(project_name)}\s*$", text)
    if heading is None:
        return ""
    section = text[heading.end():]
    if "申报地区或单位" not in section[:500]:
        return ""
    return _clean_book_body(section)


def _following_continuation(
    pages: dict[tuple[str, int], list[dict[str, Any]]], *, title: str, page: int, initial_text: str,
) -> tuple[str, list[int], list[str]]:
    """Append adjacent continuation pages only until the next project heading."""
    collected = initial_text
    fragments: list[str] = []
    page_numbers: list[int] = []
    document_ids: list[str] = []
    next_page = page + 1
    while collected and collected[-1] not in "。！？" and len(page_numbers) < 4:
        documents = pages.get((title, next_page), [])
        if not documents:
            break
        document = documents[0]
        fragment = _continuation_body(str(document.get("content", "")))
        if not fragment:
            break
        fragments.append(fragment)
        page_numbers.append(next_page)
        document_ids.append(str(document.get("id", "")))
        collected += fragment
        next_page += 1
    return "".join(fragments), page_numbers, document_ids


def _continuation_body(text: str) -> str:
    next_project = _NEXT_PROJECT.search(text)
    if next_project is not None:
        text = text[:next_project.start()]
    return _clean_book_body(text)


def _clean_book_body(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in _TRUNCATED_CATEGORY_LABELS or _BODY_LABELS.match(line):
            continue
        if line.startswith("*") or re.fullmatch(r"[0-9]{1,4}", line):
            continue
        if re.fullmatch(r"[IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\s*[-－—]\s*\d+", line):
            continue
        lines.append(line)
    body = re.sub(r"\s+", "", "".join(lines))
    if any(marker in body for marker in ("目录", "索引", "附录")):
        return ""
    return body


def _is_catalogue_title(book_title: str) -> bool:
    return "国家级" in book_title and any(marker in book_title for marker in ("名录", "图典"))


def _new_project(name: str) -> dict[str, Any]:
    return {
        "craft_id": sha256(_name_key(name).encode("utf-8")).hexdigest()[:16],
        "project_name": name,
        "catalogue_entries": [],
        "category": {"value": None, "status": "missing", "evidence": []},
        "regions": [],
        "inheritors": [],
        "description": {"text": "", "status": "missing", "evidence": []},
        "sources": [],
        "status": "pending_review",
    }


def _public_inheritor(person: dict[str, Any]) -> dict[str, Any]:
    """Adapt a transcribed person record to the active public projection schema."""
    evidence = person["evidence"]
    biography = person["biography"]["text"]
    return {
        **person,
        "evidence": [{
            **evidence,
            "excerpt": biography,
        }],
    }


def build_review_candidate(
    corpus_path: Path | str = DEFAULT_CORPUS,
    *,
    first_path: Path | str = DEFAULT_FIRST,
    later_path: Path | str = DEFAULT_LATER,
) -> dict[str, Any]:
    """Join official sequence facts to book pages without publishing guesses."""
    root = Path(corpus_path)
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    if catalog.get("status") != "active":
        raise ValueError("只能从活动语料生成候选投影")
    first = json.loads(Path(first_path).read_text(encoding="utf-8"))
    later = json.loads(Path(later_path).read_text(encoding="utf-8"))
    batches = [first, *later["batches"]]
    audit = audit_local_books(root)
    pages = _book_pages(root)
    projects: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for batch in batches:
        batch_key = batch["batch"]
        for item in sorted(batch["items"], key=lambda value: value["sequence"]):
            name = item["name"]
            project = projects.setdefault(_name_key(name), _new_project(name))
            profile = (
                audit["batches"][batch_key]["profiles"].get(str(item["sequence"]))
                if batch_key in audit["batches"] else None
            )
            page_hint = profile["page"] if profile is not None else None
            if batch_key != "first" and profile is None:
                description, evidence = "", None
            else:
                description, evidence = _description_source(
                    pages,
                    batch=batch_key,
                    project_name=name,
                    page_hint=page_hint,
                    ocr_name=profile["name"] if profile is not None else None,
                    sequence=item["sequence"],
                )
            if evidence is None:
                evidence = _source_page_evidence(pages, batch=batch_key, page_hint=page_hint)
            project["catalogue_entries"].append({
                "batch": batch_key,
                "sequence": item["sequence"],
                "code": item["code"],
                "source_url": batch["source_url"],
                "book_page": page_hint if batch_key != "first" else evidence["page"] if evidence else None,
                "ocr_name": profile["name"] if profile is not None else None,
            })
            if description and evidence and not project["description"]["text"]:
                project["description"] = {"text": description, "status": "mentioned", "evidence": [evidence]}
            if evidence and not any(item.get("document_id") == evidence["document_id"] for item in project["sources"]):
                project["sources"].append(evidence)
    provincial_profiles = extract_shandong_profiles(root)
    for profile in provincial_profiles:
        if profile["status"] not in ("toc_confirmed", "book_title_corrected"):
            continue
        project = projects.setdefault(_name_key(profile["project_name"]), _new_project(profile["project_name"]))
        evidence = profile["evidence"]
        project["sources"].append(evidence)
        if profile["region"] and not any(item["value"] == profile["region"] for item in project["regions"]):
            project["regions"].append({"value": profile["region"], "status": "mentioned", "evidence": [evidence]})
    person_audit = extract_inheritor_candidates(root)
    unlinked_people: list[int] = []
    for person in person_audit["people"]:
        project = _match_project(projects, person["project_name"])
        if project is None:
            project = _first_batch_project_by_code(projects, person["book_project_code"], person["project_name"])
        if project is None:
            unlinked_people.append(person["sequence"])
            continue
        project["inheritors"].append(_public_inheritor(person))
    return {
        "corpus_id": catalog["corpus_id"],
        "project_count": len(projects),
        "projects": list(projects.values()),
        "people": person_audit["people"],
        "person_count": len(person_audit["people"]),
        "unlinked_person_numbers": unlinked_people,
        "provincial_profile_count": len(provincial_profiles),
        "provincial_confirmed_count": sum(p["status"] in ("toc_confirmed", "book_title_corrected") for p in provincial_profiles),
        "provincial_review_queue": [p for p in provincial_profiles if p["status"] not in ("toc_confirmed", "book_title_corrected")],
    }
