"""Build a traceable, craft-centred metadata projection from the active books corpus."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any


class CraftMetadataError(RuntimeError):
    """Raised when the active local corpus cannot safely be projected."""


_CATEGORY_ALIASES = {
    "民间文学": "民间文学",
    "传统音乐": "传统音乐",
    "民间音乐": "传统音乐",
    "传统舞蹈": "传统舞蹈",
    "民间舞蹈": "传统舞蹈",
    "传统戏剧": "传统戏剧",
    "戏曲": "传统戏剧",
    "曲艺": "曲艺",
    "传统体育、游艺与杂技": "传统体育、游艺与杂技",
    "杂技与竞技": "传统体育、游艺与杂技",
    "传统美术": "传统美术",
    "民间美术": "传统美术",
    "传统技艺": "传统技艺",
    "传统手工技艺": "传统技艺",
    "传统医药": "传统医药",
    "民俗": "民俗",
}
_CATEGORIES = tuple(_CATEGORY_ALIASES)
_CATEGORY_PATTERN = re.compile(
    rf"(?m)^\s*(?P<category>{'|'.join(map(re.escape, _CATEGORIES))})(?:类)?[：:、，\s]{{0,16}}"
    r"(?P<project>[\u4e00-\u9fff·（）()]{2,36}?(?:制作技艺|烧制技艺|织造技艺|印染技艺|锻制技艺|雕刻技艺|刺绣|剪纸|皮影戏|木偶戏|戏曲|舞|歌|传说|习俗|技艺))"
)
_PROJECT_PATTERN = re.compile(
    r"(?P<project>[\u4e00-\u9fff·（）()]{2,36}?"
    r"(?:制作技艺|烧制技艺|织造技艺|印染技艺|锻制技艺|雕刻技艺|刺绣|剪纸|皮影戏|木偶戏|戏曲|舞|歌|传说|习俗|技艺))"
)
_SURNAME_CHARS = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳"
    "鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊"
    "纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯管卢莫经房裘缪干解应宗丁宣邓单杭洪"
    "包诸左石崔吉龚程嵇邢裴陆荣翁荀羊惠甄曲家封芮储靳松井段富巫乌焦巴弓牧山谷车侯班仰秋仲伊宫宁仇栾暴甘厉戎祖武符刘景詹束龙叶幸司欧"
)
_INHERITOR_PATTERN = re.compile(
    r"(?P<recognition>(?:国家级|省级|市级|县级)?(?:代表性)?传承人)"
    rf"(?:有|为|：|:)?\s*(?P<name>[{_SURNAME_CHARS}][\u4e00-\u9fff·]{{1,3}})(?=[，。、；;（）()\s]|$)"
)
_CATALOGUE_ITEM_PATTERN = re.compile(
    r"(?m)^\s*[IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]{1,6}\s*-\s*\d+\s*$"
)
_REGION_PATTERN = re.compile(
    "|".join(map(re.escape, (
        "北京市", "天津市", "上海市", "重庆市", "河北省", "山西省", "辽宁省", "吉林省", "黑龙江省",
        "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省", "河南省", "湖北省", "湖南省",
        "广东省", "海南省", "四川省", "贵州省", "云南省", "陕西省", "甘肃省", "青海省", "台湾省",
        "内蒙古自治区", "广西壮族自治区", "西藏自治区", "宁夏回族自治区", "新疆维吾尔自治区",
        "香港特别行政区", "澳门特别行政区",
    )))
)
_EXCERPT_LIMIT = 280
_DESCRIPTION_LIMIT = 900
_NON_NAME_FRAGMENTS = ("严重", "萎缩", "日益", "减少", "稀少", "不足", "困难", "画作", "作品", "表演", "场景")
_NON_PROJECT_NAMES = frozenset({
    "申报地区或单位", "申报地区", "项目保护单位", "保护单位", "项目名称", "序号", "编号",
})


def build_craft_metadata(corpus_path: Path | str) -> dict[str, Any]:
    """Project the active corpus into source-backed candidate craft metadata.

    The function intentionally uses conservative, local rules.  A record is never
    inferred from a person name alone; each emitted item has at least one source
    fragment from the active corpus.
    """
    root = Path(corpus_path)
    catalog = _read_active_catalog(root)
    documents_path = root / "documents.jsonl"
    if not documents_path.is_file():
        raise CraftMetadataError("活动语料缺少 documents.jsonl")

    documents: list[dict[str, Any]] = []
    for line in documents_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise CraftMetadataError(f"活动语料 documents.jsonl 无效：{error}") from error
        documents.append(document)

    projects: OrderedDict[str, dict[str, Any]] = OrderedDict()
    category_context: dict[str, str] = {}
    for document in documents:
        _add_document_projects(projects, document, category_context)
    known_project_pattern = _known_project_pattern(projects)
    if known_project_pattern is not None:
        for document in documents:
            _attach_known_project_mentions(projects, document, known_project_pattern)

    result = {
        "corpus_id": catalog["corpus_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": catalog.get("source_count", 0),
        "project_count": len(projects),
        "projects": list(projects.values()),
    }
    _write_atomically(root / "craft_metadata.json", result)
    return result


def _read_active_catalog(root: Path) -> dict[str, Any]:
    catalog_path = root / "catalog.json"
    if not catalog_path.is_file():
        raise CraftMetadataError("未找到活动语料 catalog.json")
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CraftMetadataError(f"活动语料 catalog.json 无效：{error}") from error
    if catalog.get("status") != "active" or not isinstance(catalog.get("corpus_id"), str):
        raise CraftMetadataError("仅允许从 status=active 的语料生成元数据")
    return catalog


def _add_document_projects(
    projects: OrderedDict[str, dict[str, Any]],
    document: dict[str, Any],
    category_context: dict[str, str],
) -> None:
    text = document.get("content")
    metadata = document.get("metadata")
    document_id = document.get("id")
    if not isinstance(text, str) or not isinstance(metadata, dict) or not isinstance(document_id, str):
        return
    evidence = _evidence(document_id, text, metadata)
    book_title = str(metadata.get("book_title", ""))
    can_create_projects = _is_catalogue_source(book_title)
    heading_category = _category_heading(text)
    if heading_category:
        category_context[book_title] = heading_category
    current_category = category_context.get(book_title)

    if can_create_projects and current_category:
        for project_name, region, segment in _catalogue_entries(text):
            project = projects.setdefault(_normalized_project_name(project_name), _new_project(project_name))
            catalogue_evidence = _evidence(document_id, segment, metadata)
            _append_unique_evidence(project["sources"], catalogue_evidence)
            if current_category:
                _set_category(project, current_category, catalogue_evidence)
            if region:
                _append_region(project, region, catalogue_evidence)

    category_by_project = {
        match.group("project"): _CATEGORY_ALIASES[match.group("category")]
        for match in _CATEGORY_PATTERN.finditer(text)
        if _is_valid_project_name(match.group("project"))
    }
    raw_project_names = [match.group("project") for match in _PROJECT_PATTERN.finditer(text)]
    explicit_project_names = list(category_by_project) if can_create_projects else []
    for project_name in explicit_project_names:
        project = projects.setdefault(_normalized_project_name(project_name), _new_project(project_name))
        _append_unique_evidence(project["sources"], evidence)
        _set_category(project, category_by_project[project_name], evidence)

    project_names = list(OrderedDict.fromkeys(
        explicit_project_names + _resolve_project_names(raw_project_names, projects)
    ))
    for project_name in project_names:
        key = _normalized_project_name(project_name)
        project = projects.setdefault(key, _new_project(project_name))
        _append_unique_evidence(project["sources"], evidence)
        category = category_by_project.get(project_name)
        if category:
            _set_category(project, category, evidence)
        profile_text = _profile_description(text, project_name, book_title)
        if profile_text:
            _append_description(project["description"], _evidence(document_id, profile_text, metadata))

    # Multiple project names on one page make an automatic person-to-project
    # association ambiguous, so leave those candidates out rather than guessing.
    if len(project_names) != 1 or not _is_inheritor_volume(book_title):
        return
    project = projects[_normalized_project_name(project_names[0])]
    for match in _INHERITOR_PATTERN.finditer(text):
        _append_inheritor(project, match.group("name"), match.group("recognition"), evidence)


def _new_project(project_name: str) -> dict[str, Any]:
    return {
        "craft_id": sha256(_normalized_project_name(project_name).encode("utf-8")).hexdigest()[:16],
        "project_name": project_name,
        "category": {"value": None, "status": "missing", "evidence": []},
        "regions": [],
        "inheritors": [],
        "description": {"text": "", "status": "mentioned", "evidence": []},
        "sources": [],
        "status": "mentioned",
    }


def _known_project_pattern(projects: OrderedDict[str, dict[str, Any]]) -> re.Pattern[str] | None:
    names = [item["project_name"] for item in projects.values() if len(item["project_name"]) >= 3]
    if not names:
        return None
    return re.compile("|".join(re.escape(name) for name in sorted(names, key=len, reverse=True)))


def _attach_known_project_mentions(
    projects: OrderedDict[str, dict[str, Any]],
    document: dict[str, Any],
    known_project_pattern: re.Pattern[str],
) -> None:
    """Attach every explicit mention from all books after authoritative names exist."""
    text = document.get("content")
    metadata = document.get("metadata")
    document_id = document.get("id")
    if not isinstance(text, str) or not isinstance(metadata, dict) or not isinstance(document_id, str):
        return
    matches = list(known_project_pattern.finditer(text))
    matched_keys: set[str] = set()
    for match in matches:
        project = projects[_normalized_project_name(match.group(0))]
        matched_keys.add(_normalized_project_name(match.group(0)))
        evidence = _evidence(document_id, text, metadata, focus_start=match.start(), focus_end=match.end())
        _append_unique_evidence(project["sources"], evidence)
        profile_text = _profile_description(text, match.group(0), str(metadata.get("book_title", "")))
        if profile_text:
            _append_description(project["description"], _evidence(document_id, profile_text, metadata))
    if len(matched_keys) == 1 and _is_inheritor_volume(str(metadata.get("book_title", ""))):
        project = projects[matched_keys.pop()]
        for match in _INHERITOR_PATTERN.finditer(text):
            evidence = _evidence(document_id, text, metadata, focus_start=match.start(), focus_end=match.end())
            _append_inheritor(project, match.group("name"), match.group("recognition"), evidence)


def _resolve_project_names(raw_names: list[str], projects: OrderedDict[str, dict[str, Any]]) -> list[str]:
    """Reuse known names when prose wraps a project mention in a sentence.

    A raw suffix match such as ``张三参观了景泰蓝制作技艺`` is not a valid
    project label.  Once an explicit heading/category has established
    ``景泰蓝制作技艺``, the wrapped mention can safely attach more evidence to it.
    Unknown wrapped matches are discarded rather than becoming false projects.
    """
    known_names = [item["project_name"] for item in projects.values()]
    resolved: list[str] = []
    for raw_name in raw_names:
        if raw_name in _CATEGORIES:
            continue
        known_name = next((name for name in known_names if name in raw_name), None)
        if known_name:
            resolved.append(known_name)
        # New candidates are created only from an explicit category declaration or
        # an official catalogue item.  A free-text suffix match merely enriches a
        # project already established by those sources.
    return list(OrderedDict.fromkeys(resolved))


def _category_heading(text: str) -> str | None:
    for label, category in _CATEGORY_ALIASES.items():
        if re.search(rf"{re.escape(label)}\s*[（(]\s*(?:共计|共)", text):
            return category
    return None


def _is_catalogue_source(book_title: str) -> bool:
    return "国家级" in book_title and any(marker in book_title for marker in ("名录", "图典"))


def _catalogue_entries(text: str) -> list[tuple[str, str | None, str]]:
    """Read title-and-region entries whose official Roman-numeral code is present."""
    matches = list(_CATALOGUE_ITEM_PATTERN.finditer(text))
    if len(matches) < 2:
        return []
    entries: list[tuple[str, str | None, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        segment = text[match.end():end].strip()
        normalized = re.sub(r"\s+", "", segment)
        region_match = _REGION_PATTERN.search(normalized)
        if region_match is None:
            continue
        name = normalized[:region_match.start()].strip("-—·，、:：")
        if not _is_valid_project_name(name):
            continue
        entries.append((name, region_match.group(0), segment))
    return entries


def _is_valid_project_name(name: str) -> bool:
    return (
        2 <= len(name) <= 48
        and "共计" not in name
        and name not in _NON_PROJECT_NAMES
        and not any(name.startswith(label) for label in ("申报地区", "项目保护单位"))
        and not re.search(r"[0-9A-Za-z\[\]-]", name)
        and not name.startswith("族")
        and name not in _CATEGORY_ALIASES
        and name not in _CATEGORY_ALIASES.values()
    )


def _is_inheritor_volume(book_title: str) -> bool:
    return "国家级非物质文化遗产项目代表性传承人大典" in book_title


def _profile_description(text: str, project_name: str, book_title: str) -> str:
    """Keep a project page's own prose, never a catalogue or an incidental mention."""
    if not _is_catalogue_source(book_title) or re.match(r"\s*(?:目录|附录|索引)", text):
        return ""
    heading = re.search(rf"(?m)^\s*(?:\d{{1,4}}\s*)?{re.escape(project_name)}\s*$", text)
    if heading is None:
        return ""
    section = text[heading.end():]
    if "申报地区或单位" not in section[:500]:
        return ""
    # The first project sentence can follow noisy captions and OCR metadata.
    # OCR wraps prose mid-sentence; match after removing those line breaks.
    prose = re.sub(r"\s+", "", section)
    preferred = re.search(
        rf"{re.escape(project_name)}(?:是|为|源于|起源于|发源于|流传于|主要|属于|形成于|由|位于|兴起于|始于)[^。！？]{{2,220}}[。！？]",
        prose,
    )
    match = preferred or re.search(rf"{re.escape(project_name)}[^。！？]{{18,220}}[。！？]", prose)
    if match is None:
        return ""
    description = re.sub(r"\s+", "", match.group(0))
    blocked = ("申报地区或单位", "项目保护单位", "名录图典", "目录", "索引", "附录")
    if any(marker in description for marker in blocked):
        return ""
    following = re.match(r"[^。！？]{12,190}[。！？]", prose[match.end():])
    if following is not None:
        next_sentence = following.group(0)
        if not any(marker in next_sentence for marker in blocked) and not re.match(r"\d{1,4}[IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]", next_sentence):
            description += next_sentence
    return description[:_DESCRIPTION_LIMIT]


def _set_category(project: dict[str, Any], category: str, evidence: dict[str, Any]) -> None:
    current = project["category"]
    if current["value"] in (None, category):
        if current["value"] is None:
            current["value"] = category
            current["status"] = "verified"
        _append_unique_evidence(current["evidence"], evidence)
        project["status"] = "verified"


def _append_region(project: dict[str, Any], region: str, evidence: dict[str, Any]) -> None:
    existing = next((item for item in project["regions"] if item["value"] == region), None)
    if existing is None:
        project["regions"].append({"value": region, "status": "verified", "evidence": [evidence]})
    else:
        _append_unique_evidence(existing["evidence"], evidence)
    project["status"] = "verified"


def _append_inheritor(project: dict[str, Any], name: str, recognition: str, evidence: dict[str, Any]) -> None:
    name = name.rstrip("等")
    if not name or any(fragment in name for fragment in _NON_NAME_FRAGMENTS):
        return
    existing = next(
        (item for item in project["inheritors"] if item["name"] == name and item["recognition"] == recognition),
        None,
    )
    if existing is None:
        project["inheritors"].append({
            "name": name,
            "recognition": recognition,
            "status": "verified",
            "evidence": [evidence],
        })
    else:
        _append_unique_evidence(existing["evidence"], evidence)
    project["status"] = "verified"


def _normalized_project_name(value: str) -> str:
    return re.sub(r"[\s（）()]", "", value)


def _evidence(
    document_id: str,
    text: str,
    metadata: dict[str, Any],
    *,
    focus_start: int | None = None,
    focus_end: int | None = None,
) -> dict[str, Any]:
    if focus_start is None or focus_end is None:
        excerpt_text = text
    else:
        start = max(0, focus_start - _EXCERPT_LIMIT // 2)
        end = min(len(text), focus_end + _EXCERPT_LIMIT // 2)
        excerpt_text = text[start:end]
    excerpt = re.sub(r"\s+", " ", excerpt_text).strip()[:_EXCERPT_LIMIT]
    return {
        "book_title": str(metadata.get("book_title", "")),
        "chapter_title": str(metadata.get("chapter_title", "")),
        "page": metadata.get("page_start"),
        "document_id": document_id,
        "excerpt": excerpt,
    }


def _append_unique_evidence(items: list[dict[str, Any]], evidence: dict[str, Any]) -> None:
    if not any(item["document_id"] == evidence["document_id"] for item in items):
        items.append(evidence)


def _append_description(description: dict[str, Any], evidence: dict[str, Any]) -> None:
    if any(item["document_id"] == evidence["document_id"] for item in description["evidence"]):
        return
    description["evidence"].append(evidence)
    joined = "\n".join(item["excerpt"] for item in description["evidence"])
    description["text"] = joined[:_DESCRIPTION_LIMIT]


def _write_atomically(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, newline="\n") as temporary:
        json.dump(content, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)
