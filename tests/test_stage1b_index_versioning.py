"""索引构建失败不能改变活动版本；成功用原子清单切换。"""

import json

import pytest


def test_publish_snapshot_atomically_switches_active_manifest(tmp_path):
    from src.retrieval.index_snapshot import active_version, publish_snapshot

    version = publish_snapshot(
        tmp_path,
        "knowledge",
        lambda directory: (directory / "index.json").write_text("ok", encoding="utf-8"),
    )

    assert active_version(tmp_path, "knowledge") == version
    manifest = json.loads((tmp_path / "knowledge" / "active.json").read_text(encoding="utf-8"))
    assert manifest["version"] == version
    assert (tmp_path / "knowledge" / version / "index.json").read_text(encoding="utf-8") == "ok"


def test_failed_snapshot_keeps_previous_active_version(tmp_path):
    from src.retrieval.index_snapshot import active_version, publish_snapshot

    first = publish_snapshot(
        tmp_path,
        "audio",
        lambda directory: (directory / "index.json").write_text("old", encoding="utf-8"),
    )

    def fail(directory):
        (directory / "partial").write_text("partial", encoding="utf-8")
        raise RuntimeError("build failed")

    with pytest.raises(RuntimeError):
        publish_snapshot(tmp_path, "audio", fail)

    assert active_version(tmp_path, "audio") == first
    assert list((tmp_path / "audio").glob("*.part")) == []
