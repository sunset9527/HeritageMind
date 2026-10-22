"""版本化索引目录与原子活动版本清单。"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4


def _kind_root(root: Path | str, kind: str) -> Path:
    if not kind or any(char not in "abcdefghijklmnopqrstuvwxyz_" for char in kind):
        raise ValueError("非法索引类型")
    result = Path(root) / kind
    result.mkdir(parents=True, exist_ok=True)
    return result


def active_version(root: Path | str, kind: str) -> str | None:
    manifest = _kind_root(root, kind) / "active.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        version = str(data["version"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
    version_dir = manifest.parent / version
    return version if version_dir.is_dir() else None


def cleanup_partial_snapshots(root: Path | str, kind: str) -> int:
    """清理由崩溃或硬终止遗留的临时目录/清单，不触碰已发布版本。"""
    parent = _kind_root(root, kind)
    removed = 0
    for candidate in parent.glob("*.part"):
        if candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink(missing_ok=True)
        removed += 1
    return removed


def publish_snapshot(
    root: Path | str,
    kind: str,
    builder: Callable[[Path], object],
) -> str:
    """在临时版本中构建，完成后才原子切换小型活动清单。"""
    cleanup_partial_snapshots(root, kind)
    parent = _kind_root(root, kind)
    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:12]
    temporary = parent / f"{version}.part"
    final = parent / version
    manifest_part = parent / "active.json.part"
    temporary.mkdir()
    try:
        builder(temporary)
        os.replace(temporary, final)
        manifest_part.write_text(
            json.dumps(
                {
                    "version": version,
                    "activated_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.replace(manifest_part, parent / "active.json")
        return version
    except Exception:
        manifest_part.unlink(missing_ok=True)
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
