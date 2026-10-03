"""Public encyclopedia image resolution is explicit and never invents a URL."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_image_manifest_resolves_legacy_image_and_marks_unmapped_craft_unavailable(tmp_path):
    from src.services.encyclopedia_images import load_image_manifest, resolve_encyclopedia_image

    path = tmp_path / "image_manifest.json"
    path.write_text(json.dumps({
        "version": "v1",
        "images": [{
            "craft_name": "剪纸",
            "image_url": "/crafts/剪纸.jpg",
            "source_page_url": "",
            "source_name": "本地历史资源",
            "source_kind": "legacy_local",
            "status": "legacy_local",
            "accessed_at": "2026-10-03",
            "license_note": "既有本地展示资源。",
        }],
    }, ensure_ascii=False), encoding="utf-8")

    images = load_image_manifest(path)

    assert resolve_encyclopedia_image(images, "剪纸") == {
        "url": "/crafts/剪纸.jpg",
        "status": "legacy_local",
    }
    assert resolve_encyclopedia_image(images, "土家族民间故事") == {
        "url": None,
        "status": "unavailable",
    }


def test_image_manifest_rejects_verified_image_without_a_source_page(tmp_path):
    from src.services.encyclopedia_images import load_image_manifest

    path = tmp_path / "image_manifest.json"
    path.write_text(json.dumps({
        "version": "v1",
        "images": [{
            "craft_name": "土家族民间故事",
            "image_url": "https://example.invalid/tujia.jpg",
            "source_page_url": "",
            "source_name": "某机构",
            "source_kind": "government",
            "status": "verified",
            "accessed_at": "2026-10-03",
            "license_note": "仅外链展示。",
        }],
    }, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="source_page_url"):
        load_image_manifest(path)


def test_pending_candidate_url_is_not_published_to_the_frontend():
    from src.services.encyclopedia_images import resolve_encyclopedia_image

    image = resolve_encyclopedia_image({
        "傣族慢轮制陶技艺": {
            "image_url": "https://www.ynich.cn/files/old/attached/image/20170927/20170927165006_94408.jpg",
            "status": "pending_review",
        },
    }, "傣族慢轮制陶技艺")

    assert image == {"url": None, "status": "pending_review"}


def test_public_encyclopedia_list_serialization_adds_image_without_full_content():
    from api import _serialize_encyclopedia_entry

    entry = SimpleNamespace(name="剪纸", slug="剪纸", summary="剪纸摘要", content="正文")
    image = _serialize_encyclopedia_entry(entry, {
        "剪纸": {"image_url": "/crafts/剪纸.jpg", "status": "legacy_local"},
    })

    assert image == {
        "name": "剪纸",
        "slug": "剪纸",
        "summary": "剪纸摘要",
        "image": {"url": "/crafts/剪纸.jpg", "status": "legacy_local"},
    }


def test_public_encyclopedia_detail_serialization_includes_content_and_image():
    from api import _serialize_encyclopedia_entry

    entry = SimpleNamespace(name="剪纸", slug="剪纸", summary="剪纸摘要", content="正文")

    detail = _serialize_encyclopedia_entry(
        entry,
        {"剪纸": {"image_url": "/crafts/剪纸.jpg", "status": "legacy_local"}},
        include_content=True,
    )

    assert detail["content"] == "正文"
    assert detail["image"] == {"url": "/crafts/剪纸.jpg", "status": "legacy_local"}


def test_production_image_manifest_covers_every_existing_local_craft_image():
    from src.services.encyclopedia_images import load_image_manifest, resolve_encyclopedia_image

    root = Path(__file__).parents[1]
    images = load_image_manifest(root / "data" / "knowledge_sources" / "image_manifest.json")
    local_crafts = {
        path.stem for path in (root / "frontend" / "public" / "crafts").glob("*.jpg")
    }

    assert local_crafts
    assert {
        craft_name
        for craft_name in local_crafts
        if resolve_encyclopedia_image(images, craft_name)["status"] == "legacy_local"
    } == local_crafts
