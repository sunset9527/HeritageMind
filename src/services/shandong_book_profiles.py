"""Locate candidate project pages in the two Shandong provincial volumes."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any


_TITLE = "山东省省级非物质文化遗产名录图典"
_HEADING = re.compile(r"(?m)^([\u4e00-\u9fff·（）()、]{2,35})\n[（(]([^\n]{2,45})[）)]\n")
_BAD_NAME = ("名录", "目录", "索引", "附录", "项目保护", "非物质文化遗产", "传统体育、")
# Page headings were checked against the same book's contents. The six unclear
# contents entries were additionally read from the original PDF title banners.
_BOOK_TITLE_CORRECTIONS = {
    (1, 49): ("闵子寒传说", "闵子骞传说"),
    (1, 138): ("海阳天秧歌", "海阳大秧歌"),
    (1, 223): ("东路郴子", "东路梆子"),
    (1, 254): ("贾家注村逸戏", "贾家洼村傀儡戏"),
    (1, 361): ("伏里王陶", "伏里土陶"),
    (1, 433): ("邦城古筝制作技艺", "郓城古筝制作技艺"),
    (1, 490): ("渔民节祭礼仪式", "渔民节祭祀仪式"),
    (2, 39): ("范与陶山的故事", "范蠡与陶山的故事"),
    (2, 84): ("临溜成语典故", "临淄成语典故"),
    (2, 87): ("天禹治水的传说", "大禹治水的传说"),
    (2, 108): ("阳谷寿张黄河号", "阳谷寿张黄河夯号"),
    (2, 111): ("东平碱号子", "东平号子"),
    (2, 250): ("青州花健", "青州花毽"),
    (2, 342): ("德州古项制作技艺", "德州古埙制作技艺"),
    (2, 351): ("柔皮纸制作技艺", "桑皮纸制作技艺"),
    (2, 372): ("武定府酱莱制作技艺", "武定府酱菜制作技艺"),
    (2, 381): ("强想堂白酒传统酿造技艺", "强恕堂白酒传统酿造技艺"),
    (2, 402): ("扳倒并白酒传统酿造技艺", "扳倒井白酒传统酿造技艺"),
    (2, 456): ("宁阳斗蟋", "宁阳斗蟋"),
    (2, 468): ("胶东花饼悸习俗", "胶东花饽饽习俗"),
}


def extract_shandong_profiles(root: Path | str) -> list[dict[str, Any]]:
    """Return page-backed candidates; a profile is not automatically a published item."""
    profiles: list[dict[str, Any]] = []
    rows = [json.loads(line) for line in (Path(root) / "documents.jsonl").open(encoding="utf-8") if line.strip()]
    contents_pages: dict[str, str] = {}
    for row in rows:
        metadata = row.get("metadata", {})
        title, page = metadata.get("book_title"), metadata.get("page_start")
        if isinstance(title, str) and _TITLE in title and isinstance(page, int) and page <= 21:
            contents_pages[title] = contents_pages.get(title, "") + re.sub(r"\s+", "", str(row.get("content", "")))
    for row in rows:
        metadata = row.get("metadata", {})
        title, page = metadata.get("book_title"), metadata.get("page_start")
        if not isinstance(title, str) or _TITLE not in title or not isinstance(page, int):
            continue
        end_page = 519 if "第1卷" in title else 530 if "第2卷" in title else 0
        if not 22 <= page < end_page:
            continue
        content = str(row.get("content", ""))
        match = _HEADING.search(content[:240])
        if match is None:
            continue
        ocr_name, region = (part.strip() for part in match.groups())
        if any(word in ocr_name for word in _BAD_NAME) or re.search(r"[\dA-Za-z]", ocr_name):
            continue
        volume = 1 if "第1卷" in title else 2
        correction = _BOOK_TITLE_CORRECTIONS.get((volume, page))
        name = correction[1] if correction and correction[0] == ocr_name else ocr_name
        toc_match = name in contents_pages.get(title, "")
        status = "book_title_corrected" if correction and correction[0] == ocr_name else "toc_confirmed" if toc_match else "needs_ocr_review"
        profiles.append({
            "project_name": name,
            "ocr_name": ocr_name,
            "region": region,
            "evidence": {
                "book_title": title,
                "page": page,
                "document_id": str(row.get("id", "")),
                "excerpt": content[match.end():match.end() + 280],
                "title_correction": "同书目录／PDF 标题核读" if status == "book_title_corrected" else "",
            },
            "status": status,
        })
    return sorted(profiles, key=lambda item: (item["evidence"]["book_title"], item["evidence"]["page"]))
