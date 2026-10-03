"""Offline parsers for candidate links returned by official source search pages."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re
from urllib.parse import urljoin


IHCHINA_BASE_URL = "https://www.ihchina.cn"
_PROJECT_LINK = re.compile(
    r'<a\s+[^>]*href="(?P<href>/project_details/\d+(?:\.html)?)"[^>]*>(?P<title>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class OfficialSourceCandidate:
    url: str
    title: str


def extract_ihchina_project_candidates(html: str) -> list[OfficialSourceCandidate]:
    """Extract unique project-detail links from an IHChina search-result page."""
    candidates: list[OfficialSourceCandidate] = []
    seen_urls: set[str] = set()
    for match in _PROJECT_LINK.finditer(html):
        url = urljoin(IHCHINA_BASE_URL, unescape(match.group("href")))
        title = unescape(_HTML_TAG.sub("", match.group("title"))).strip()
        if not title or title == "查看更多" or url in seen_urls:
            continue
        seen_urls.add(url)
        candidates.append(OfficialSourceCandidate(url=url, title=title))
    return candidates
