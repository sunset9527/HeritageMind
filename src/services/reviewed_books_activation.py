"""Validate and atomically activate the reviewed books projection."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from typing import Any


_INHERITOR_VOLUME = "国家级非物质文化遗产项目代表性传承人大典"
_FORBIDDEN_PROJECTS = {"申报地区或单位", "申报地区", "项目保护单位"}


def _read(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} 必须是 JSON 对象")
    return data


def validate_reviewed_candidate(metadata: dict[str, Any], audit: dict[str, Any]) -> None:
    """Enforce the release gates recorded in the approved rebuild design."""
    if audit.get("status") != "review_only_not_published":
        raise ValueError("候选审计状态无效")
    if audit.get("national_main_list_items") != 1219 or audit.get("national_main_list_unique_names") != 1218:
        raise ValueError("三批国家级主名录总数未通过核对")
    for batch, expected in (("second", 510), ("third", 191)):
        record = audit.get("ocr_main_list_audit", {}).get(batch, {})
        if record.get("official_count") != expected or record.get("covered_count") != expected:
            raise ValueError(f"{batch} 批主名录编号页未核齐")
        if record.get("missing_from_book"):
            raise ValueError(f"{batch} 批仍有缺失序号")
    projects = metadata.get("projects")
    if not isinstance(projects, list) or metadata.get("project_count") != len(projects):
        raise ValueError("候选项目数量或结构无效")
    if any(project.get("project_name") in _FORBIDDEN_PROJECTS for project in projects):
        raise ValueError("候选仍含有非项目字段")
    people = [person for project in projects for person in project.get("inheritors", [])]
    if metadata.get("person_count") != len(people) or len({person.get("name") for person in people}) != len(people):
        raise ValueError("传承人数量或去重结果无效")
    if audit.get("dedicated_volume_inheritor_profiles") != len(people):
        raise ValueError("传承人数量与指定传承人大典不一致")
    if (
        audit.get("inheritor_profiles_missing_biography")
        or audit.get("inheritor_profiles_missing_book_project_name")
        or metadata.get("unlinked_person_numbers")
        or audit.get("unlinked_inheritor_numbers")
    ):
        raise ValueError("仍有未完整关联的传承人")
    for person in people:
        evidence = person.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("传承人缺少公开证据")
        if not all(
            _INHERITOR_VOLUME in str(item.get("book_title", ""))
            and bool(item.get("excerpt"))
            for item in evidence
        ):
            raise ValueError("传承人证据必须来自指定传承人大典")


def activate_reviewed_candidate(
    corpus_path: Path | str,
    candidate_path: Path | str,
    audit_path: Path | str,
    backup_path: Path | str,
) -> dict[str, int]:
    """Back up the active projection and replace it only after validation."""
    corpus = Path(corpus_path)
    candidate = _read(Path(candidate_path))
    audit = _read(Path(audit_path))
    catalog = _read(corpus / "catalog.json")
    active = corpus / "craft_metadata.json"
    backup = Path(backup_path)
    if candidate.get("corpus_id") != catalog.get("corpus_id"):
        raise ValueError("候选与活动语料版本不一致")
    if not active.is_file():
        raise ValueError("找不到当前活动投影")
    if backup.exists():
        raise FileExistsError(f"备份已存在：{backup}")
    validate_reviewed_candidate(candidate, audit)
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(active, backup)
    temporary = active.with_name(f"{active.name}.reviewed.tmp")
    temporary.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, active)
    return {"project_count": len(candidate["projects"]), "inheritor_count": candidate["person_count"]}
