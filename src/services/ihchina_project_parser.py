"""Offline parsers for IHChina project-detail candidate pages.

The parser intentionally returns review candidates only.  It neither fetches
pages nor downloads the media URLs it finds.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlparse


IHCHINA_HOST = "www.ihchina.cn"
INTRODUCTION_LIMIT = 500
_BLOCK_TAGS = frozenset({"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "br"})
_IMAGE_TAG = re.compile(r"<img\b(?P<attributes>[^>]*)>", re.IGNORECASE | re.DOTALL)
_ATTRIBUTE = re.compile(
    r"\b(?P<name>src|alt)\s*=\s*(?:\"(?P<double>[^\"]*)\"|'(?P<single>[^']*)')",
    re.IGNORECASE | re.DOTALL,
)
_INTRODUCTION_SECTION = re.compile(
    r"<(?:div|section|article|p)\b[^>]*(?:class|id)\s*=\s*(?:\"[^\"]*(?:introduction|intro|简介)[^\"]*\"|'[^']*(?:introduction|intro|简介)[^']*')[^>]*>(?P<content>.*?)</(?:div|section|article|p)>",
    re.IGNORECASE | re.DOTALL,
)
_H1 = re.compile(r"<h1\b[^>]*>(?P<content>.*?)</h1>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class ImageCandidate:
    image_url: str
    alt: str
    status: str = "pending_review"


@dataclass(frozen=True)
class IHChinaProjectDetail:
    craft_name: str | None
    project_sequence: str | None
    project_code: str | None
    category: str | None
    declaring_region_or_unit: str | None
    protection_unit: str | None
    introduction_excerpt: str | None
    image_candidates: tuple[ImageCandidate, ...]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        lines = [_collapse_whitespace(line) for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _text_from_html(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return parser.text()


def _extract_labeled_value(text: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        match = re.search(
            rf"(?:^|\||\n)\s*{re.escape(label)}\s*[：:]\s*(?P<value>[^|\n]+)",
            text,
        )
        if match:
            return match.group("value").strip() or None
    return None


def _extract_heading(text: str) -> str | None:
    for line in text.splitlines():
        if not any(line.startswith(f"{label}：") or line.startswith(f"{label}:") for label in _ALL_LABELS):
            return line
    return None


def _extract_project_name(html: str, text: str) -> str | None:
    match = _H1.search(html)
    if match:
        heading = _text_from_html(match.group("content"))
        if heading:
            return heading
    return _extract_heading(text)


def _extract_introduction(html: str, text: str) -> str | None:
    match = _INTRODUCTION_SECTION.search(html)
    if match:
        excerpt = _text_from_html(match.group("content"))
    else:
        excerpt = _extract_labeled_value(text, ("简介", "项目简介"))
    if not excerpt:
        lines = text.splitlines()
        metadata_end = max(
            (
                index
                for index, line in enumerate(lines)
                if "保护单位" in line or "申报地区或单位" in line
            ),
            default=-1,
        )
        body_lines: list[str] = []
        for line in lines[metadata_end + 1 :]:
            if line in {"相关传承人", "相关资讯", "相关学术"}:
                break
            if any(f"{label}：" in line or f"{label}:" in line for label in _ALL_LABELS):
                continue
            body_lines.append(line)
        excerpt = "".join(body_lines)
    if not excerpt:
        return None
    return excerpt[:INTRODUCTION_LIMIT]


def _attribute_values(attributes: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in _ATTRIBUTE.finditer(attributes):
        value = match.group("double") if match.group("double") is not None else match.group("single")
        values[match.group("name").lower()] = _collapse_whitespace(value)
    return values


_SOLAR_TERMS = frozenset(
    {
        "立春", "雨水", "惊蛰", "春分", "清明", "谷雨", "立夏", "小满", "芒种", "夏至", "小暑", "大暑",
        "立秋", "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至", "小寒", "大寒",
    }
)


def _extract_project_images(html: str, source_page_url: str) -> tuple[ImageCandidate, ...]:
    images: list[ImageCandidate] = []
    seen_urls: set[str] = set()
    for match in _IMAGE_TAG.finditer(html):
        attributes = _attribute_values(match.group("attributes"))
        source = attributes.get("src")
        if not source:
            continue
        image_url = urljoin(source_page_url, source)
        parsed = urlparse(image_url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != IHCHINA_HOST
            or not parsed.path.startswith("/Uploads/Picture/")
            or attributes.get("alt", "") in _SOLAR_TERMS
            or image_url in seen_urls
        ):
            continue
        seen_urls.add(image_url)
        images.append(ImageCandidate(image_url=image_url, alt=attributes.get("alt", "")))
    return tuple(images)


_ALL_LABELS = (
    "项目序号",
    "项目编号",
    "项目序号",
    "编号",
    "类别",
    "项目类别",
    "申报地区或单位",
    "申报地区",
    "保护单位",
    "简介",
    "项目简介",
)


def parse_ihchina_project_detail(html: str, source_page_url: str) -> IHChinaProjectDetail:
    """Parse one already-fetched IHChina detail page into review-only fields."""
    text = _text_from_html(html)
    return IHChinaProjectDetail(
        craft_name=_extract_project_name(html, text),
        project_sequence=_extract_labeled_value(text, ("项目序号",)),
        project_code=_extract_labeled_value(text, ("项目编号", "编号")),
        category=_extract_labeled_value(text, ("类别", "项目类别")),
        declaring_region_or_unit=_extract_labeled_value(text, ("申报地区或单位", "申报地区")),
        protection_unit=_extract_labeled_value(text, ("保护单位",)),
        introduction_excerpt=_extract_introduction(html, text),
        image_candidates=_extract_project_images(html, source_page_url),
    )
