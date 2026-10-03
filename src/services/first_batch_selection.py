"""Deterministic selection for the balanced first deep-research batch."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RegistryProject:
    document_key: str
    craft_name: str
    category: str


FIRST_BATCH_QUOTAS = {
    "传统手工技艺": 11,
    "传统戏剧": 10,
    "传统医药": 9,
    "民间美术": 10,
    "民间文学": 10,
    "民间舞蹈": 10,
    "民间音乐": 10,
    "民俗": 10,
    "曲艺": 10,
    "杂技与竞技": 10,
}


def select_first_batch(projects: Iterable[RegistryProject]) -> tuple[RegistryProject, ...]:
    """Select 100 official records, including all nine first-batch medicine items."""
    by_category: dict[str, list[RegistryProject]] = defaultdict(list)
    for project in projects:
        by_category[project.category].append(project)

    selected: list[RegistryProject] = []
    for category, quota in FIRST_BATCH_QUOTAS.items():
        candidates = by_category[category]
        if len(candidates) < quota:
            raise ValueError(f"{category}: expected at least {quota} registry projects, found {len(candidates)}")
        selected.extend(candidates[:quota])
    return tuple(selected)
