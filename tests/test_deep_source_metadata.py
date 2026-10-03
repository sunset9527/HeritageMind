"""Depth-layer metadata must be explicit before new research summaries are published."""

import json

import pytest


def _write_package(tmp_path, documents):
    package = tmp_path / "knowledge_sources"
    content_dir = package / "documents"
    content_dir.mkdir(parents=True)
    (content_dir / "registry.md").write_text("名录记录。", encoding="utf-8")
    (content_dir / "deep.md").write_text("可核验的工艺与地域摘要。", encoding="utf-8")
    manifest_path = package / "manifest.json"
    manifest_path.write_text(
        json.dumps({"dataset_version": "v2", "documents": documents}, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest_path


def _registry():
    return {
        "document_key": "mct-first-batch-001",
        "craft_name": "示例技艺",
        "title": "示例技艺：名录记录",
        "content_path": "documents/registry.md",
        "source_name": "文旅部",
        "source_url": "https://example.org/registry",
        "accessed_at": "2026-10-03",
        "license_note": "事实性名录记录",
        "status": "published",
        "evidence_layer": "registry_record",
    }


def _deep(**overrides):
    document = {
        "document_key": "example-craft-museum-001",
        "craft_name": "示例技艺",
        "title": "示例技艺：博物馆工艺摘要",
        "content_path": "documents/deep.md",
        "source_name": "示例博物馆",
        "source_url": "https://museum.example.org/craft",
        "accessed_at": "2026-10-03",
        "license_note": "自行整理事实摘要",
        "status": "published",
        "evidence_layer": "deep_summary",
        "evidence_dimensions": ["craft", "history_region"],
        "registry_document_key": "mct-first-batch-001",
    }
    document.update(overrides)
    return document


def test_load_manifest_exposes_linked_deep_source_metadata(tmp_path):
    from src.services.knowledge_manifest import load_manifest

    manifest = load_manifest(_write_package(tmp_path, [_registry(), _deep()]))
    deep = manifest.documents[1]

    assert deep.evidence_layer == "deep_summary"
    assert deep.evidence_dimensions == ("craft", "history_region")
    assert deep.registry_document_key == "mct-first-batch-001"


def test_load_manifest_rejects_deep_source_without_dimensions(tmp_path):
    from src.services.knowledge_manifest import ManifestValidationError, load_manifest

    deep = _deep()
    deep.pop("evidence_dimensions")

    with pytest.raises(ManifestValidationError, match="evidence_dimensions"):
        load_manifest(_write_package(tmp_path, [_registry(), deep]))


def test_load_manifest_rejects_deep_source_linked_to_another_project(tmp_path):
    from src.services.knowledge_manifest import ManifestValidationError, load_manifest

    registry = _registry()
    registry["craft_name"] = "另一项目"

    with pytest.raises(ManifestValidationError, match="craft_name"):
        load_manifest(_write_package(tmp_path, [registry, _deep()]))
