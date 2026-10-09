"""Write a review-only books projection and a source coverage audit.

Run: python tools/build_reviewed_books_candidate.py
The active `data/local_books_corpus/craft_metadata.json` is never changed here.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.local_books_audit import audit_local_books, compare_official_catalogue  # noqa: E402
from src.services.reviewed_books_projection import (  # noqa: E402
    DEFAULT_CORPUS, DEFAULT_LATER, build_review_candidate,
)


OUTPUT = PROJECT_ROOT / "data" / "knowledge_sources" / "candidates" / "books-rebuild"


def main() -> None:
    output = OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    candidate = build_review_candidate()
    audit = audit_local_books(DEFAULT_CORPUS)
    compare = compare_official_catalogue(audit, DEFAULT_LATER)
    catalogue = json.loads((DEFAULT_CORPUS / "catalog.json").read_text(encoding="utf-8"))
    provincial_confirmed = Counter()
    provincial_review = Counter()
    project_page_evidence = Counter()
    for project in candidate["projects"]:
        for evidence in project["sources"]:
            title = evidence.get("book_title", "")
            if "山东省省级非物质文化遗产名录图典" in title:
                provincial_confirmed[title] += 1
            elif "国家级" in title and "名录" in title:
                project_page_evidence[title] += 1
    for profile in candidate["provincial_review_queue"]:
        provincial_review[profile["evidence"]["book_title"]] += 1
    sources = []
    for source in catalogue["sources"]:
        title = source["book_title"]
        unmeasured_project_coverage = (
            "通识读本" in title or "中国的非物质文化遗产 (" in title
            or "第三批国家级非物质文化遗产名录图典 下" in title
            or "传承人大典" in title
        )
        row = {
            "book_title": title,
            "format": source["format"],
            "source_id": source["source_id"],
            "confirmed_project_pages": None if unmeasured_project_coverage else provincial_confirmed[title] + project_page_evidence[title],
            "project_pages_needing_ocr_review": provincial_review[title],
            "confirmed_inheritor_profiles": candidate["person_count"] if "传承人大典" in title else 0,
            "count_basis": (
                "省级图典项目页，名称经本书目录或原 PDF 标题核对" if "山东省省级" in title
                else "国家级名录项目页提取出可用正文" if "国家级" in title and "名录" in title
                else "第三批扩展项目续页；未逐项核齐，不能以主名录正文数表示覆盖" if "第三批国家级非物质文化遗产名录图典 下" in title
                else "本书传承人编号人物页" if "传承人大典" in title
                else "通识读本；项目零散提及，不作为独立名录计数"
            ),
        }
        sources.append(row)
    report = {
        "corpus_id": candidate["corpus_id"],
        "status": "review_only_not_published",
        "national_main_list_items": 1219,
        "national_main_list_unique_names": 1218,
        "national_extension_items_by_notice": {"after_first_batch": 147, "after_second_batch": 164},
        "national_extension_count_basis": "国务院第二、三批公布通知；扩展项目另列且不重复增加主项目名数",
        "provincial_profile_pages_detected": candidate["provincial_profile_count"],
        "provincial_profile_pages_book_confirmed": candidate["provincial_confirmed_count"],
        "provincial_profile_pages_needing_ocr_review": len(candidate["provincial_review_queue"]),
        "candidate_unique_project_names": candidate["project_count"],
        "candidate_descriptions_with_book_page_evidence": sum(
            bool(project["description"]["text"]) for project in candidate["projects"]
        ),
        "dedicated_volume_inheritor_profiles": candidate["person_count"],
        "inheritor_profiles_missing_biography": [
            person["sequence"] for person in candidate["people"] if not person["biography"]["text"]
        ],
        "inheritor_profiles_ocr_project_name_missing": [
            person["sequence"] for person in candidate["people"] if not person["project_name"]
        ],
        "inheritor_profiles_missing_book_project_name": candidate["unlinked_person_numbers"],
        "inheritor_profiles_linked_by_book_code": [
            person["sequence"]
            for person in candidate["people"]
            if not person["project_name"] and person["sequence"] not in candidate["unlinked_person_numbers"]
        ],
        "unlinked_inheritor_numbers": candidate["unlinked_person_numbers"],
        "ocr_main_list_audit": compare,
        "sources": sources,
    }
    (output / "candidate.json").write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "candidate": str(output / "candidate.json"),
        "audit": str(output / "audit.json"),
        "projects": candidate["project_count"],
        "inheritors": candidate["person_count"],
        "status": report["status"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
