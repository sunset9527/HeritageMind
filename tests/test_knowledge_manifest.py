"""Knowledge-source manifest validation must be deterministic and offline."""

import hashlib
import json

import pytest


def _write_manifest(tmp_path, documents):
    package = tmp_path / "knowledge_sources"
    documents_dir = package / "documents"
    documents_dir.mkdir(parents=True)
    (documents_dir / "jingtailan-history.md").write_text("景泰蓝的资料正文。", encoding="utf-8")
    (package / "manifest.json").write_text(
        json.dumps({"dataset_version": "v1", "documents": documents}, ensure_ascii=False),
        encoding="utf-8",
    )
    return package / "manifest.json"


def _valid_document(**overrides):
    document = {
        "document_key": "jingtailan-history-001",
        "craft_name": "景泰蓝",
        "title": "景泰蓝制作技艺概述",
        "content_path": "documents/jingtailan-history.md",
        "source_name": "示例权威机构",
        "source_url": "https://example.org/jingtailan",
        "accessed_at": "2026-09-14",
        "license_note": "仅保存自行整理摘要与来源链接",
        "status": "published",
    }
    document.update(overrides)
    return document


def test_load_manifest_normalizes_document_and_hashes_utf8_content(tmp_path):
    from src.services.knowledge_manifest import load_manifest

    manifest_path = _write_manifest(tmp_path, [_valid_document()])
    manifest = load_manifest(manifest_path)

    assert manifest.dataset_version == "v1"
    assert len(manifest.documents) == 1
    document = manifest.documents[0]
    assert document.document_key == "jingtailan-history-001"
    assert document.content == "景泰蓝的资料正文。"
    assert document.content_sha256 == hashlib.sha256(document.content.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    ("override", "expected_message"),
    [
        ({"source_url": "ftp://example.org/bad"}, "source_url"),
        ({"status": "ready"}, "status"),
        ({"content_path": "../outside.md"}, "content_path"),
    ],
)
def test_load_manifest_rejects_invalid_document_fields(tmp_path, override, expected_message):
    from src.services.knowledge_manifest import ManifestValidationError, load_manifest

    manifest_path = _write_manifest(tmp_path, [_valid_document(**override)])

    with pytest.raises(ManifestValidationError, match=expected_message):
        load_manifest(manifest_path)


def test_load_manifest_rejects_duplicate_document_key(tmp_path):
    from src.services.knowledge_manifest import ManifestValidationError, load_manifest

    manifest_path = _write_manifest(tmp_path, [_valid_document(), _valid_document(title="重复资料")])

    with pytest.raises(ManifestValidationError, match="jingtailan-history-001"):
        load_manifest(manifest_path)


def test_load_manifest_rejects_duplicate_content_even_with_distinct_keys(tmp_path):
    from src.services.knowledge_manifest import ManifestValidationError, load_manifest

    manifest_path = _write_manifest(tmp_path, [_valid_document()])
    duplicate_path = manifest_path.parent / "documents" / "duplicate.md"
    duplicate_path.write_text("景泰蓝的资料正文。", encoding="utf-8")
    duplicate = _valid_document(
        document_key="jingtailan-history-002",
        title="相同正文的重复资料",
        content_path="documents/duplicate.md",
        source_url="https://example.org/jingtailan-duplicate",
    )
    manifest_path.write_text(
        json.dumps({"dataset_version": "v1", "documents": [_valid_document(), duplicate]}, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ManifestValidationError, match="duplicate content hash"):
        load_manifest(manifest_path)
