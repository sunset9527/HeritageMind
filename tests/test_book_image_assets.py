from __future__ import annotations

import json
from pathlib import Path

import fitz
from PIL import Image


def _write_png(path: Path, *, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    Image.new("RGB", size, color).save(path)


def _write_source_pdf(path: Path, image_dir: Path) -> None:
    small = image_dir / "small.png"
    large = image_dir / "large.png"
    _write_png(small, size=(20, 20), color=(255, 0, 0))
    _write_png(large, size=(120, 80), color=(0, 120, 255))
    document = fitz.open()
    page = document.new_page(width=360, height=240)
    page.insert_image(fitz.Rect(10, 10, 30, 30), filename=small)
    page.insert_image(fitz.Rect(80, 40, 320, 200), filename=large)
    document.save(path)
    document.close()


def _write_active_corpus(corpus: Path) -> None:
    (corpus / "catalog.json").write_text(json.dumps({
        "corpus_id": "books-v1",
        "status": "active",
        "sources": [{
            "sha256": "source-sha",
            "book_title": "非遗图典",
            "format": "pdf",
        }],
    }, ensure_ascii=False), encoding="utf-8")
    (corpus / "craft_metadata.json").write_text(json.dumps({
        "corpus_id": "books-v1",
        "projects": [{
            "craft_id": "craft-jtl",
            "project_name": "景泰蓝制作技艺",
            "sources": [{"book_title": "非遗图典", "page": 1}],
        }],
    }, ensure_ascii=False), encoding="utf-8")


def test_build_extracts_largest_embedded_image_for_the_project_source_page(tmp_path: Path):
    from src.services.book_image_assets import BookImageAssetBuilder

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_active_corpus(corpus)
    source_pdf = tmp_path / "source.pdf"
    _write_source_pdf(source_pdf, tmp_path)

    manifest = BookImageAssetBuilder(
        corpus,
        source_files={"source-sha": source_pdf},
    ).build()

    image = manifest["images"]["craft-jtl"]
    assert image["status"] == "extracted"
    assert image["book_title"] == "非遗图典"
    assert image["page"] == 1
    assert image["method"] == "embedded"
    assert (corpus / image["file_path"]).is_file()
    with Image.open(corpus / image["file_path"]) as extracted:
        assert extracted.size == (120, 80)


def test_resolve_source_files_matches_the_catalog_checksum(tmp_path: Path):
    from hashlib import sha256
    from src.services.book_image_assets import resolve_source_files

    library = tmp_path / "library"
    library.mkdir()
    source = library / "非遗图典.pdf"
    source.write_bytes(b"book-bytes")
    catalog = {"sources": [{"sha256": sha256(b"book-bytes").hexdigest()}]}

    resolved = resolve_source_files(library, catalog)

    assert resolved == {sha256(b"book-bytes").hexdigest(): source}


def test_build_keeps_a_completed_asset_when_resuming_without_its_source_file(tmp_path: Path):
    from src.services.book_image_assets import BookImageAssetBuilder

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_active_corpus(corpus)
    image_path = corpus / "images" / "craft-jtl.png"
    image_path.parent.mkdir()
    _write_png(image_path, size=(120, 80), color=(0, 120, 255))
    (corpus / "book_images.json").write_text(json.dumps({
        "corpus_id": "books-v1",
        "selection_version": 3,
        "images": {"craft-jtl": {
            "status": "extracted", "book_title": "非遗图典", "page": 1,
            "method": "embedded", "selection_version": 3, "file_path": "images/craft-jtl.png",
        }},
    }, ensure_ascii=False), encoding="utf-8")

    manifest = BookImageAssetBuilder(corpus, source_files={}).build()

    assert manifest["images"]["craft-jtl"]["status"] == "extracted"


def test_build_crops_the_largest_colored_picture_from_a_scanned_project_page(tmp_path: Path):
    from src.services.book_image_assets import BookImageAssetBuilder

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_active_corpus(corpus)
    page_image = tmp_path / "scanned-page.png"
    scan = Image.new("RGB", (400, 600), "white")
    for x in range(80, 320):
        for y in range(180, 420):
            scan.putpixel((x, y), (30, 120, 200))
    scan.save(page_image)
    source_pdf = tmp_path / "source.pdf"
    document = fitz.open()
    page = document.new_page(width=400, height=600)
    page.insert_image(page.rect, filename=page_image)
    document.save(source_pdf)
    document.close()

    manifest = BookImageAssetBuilder(corpus, source_files={"source-sha": source_pdf}).build()

    asset = manifest["images"]["craft-jtl"]
    assert asset["method"] == "scan_crop"
    with Image.open(corpus / asset["file_path"]) as extracted:
        assert extracted.size[0] < 400
        assert extracted.size[1] < 600


def test_build_renders_the_source_page_when_it_has_no_extractable_picture(tmp_path: Path):
    from src.services.book_image_assets import BookImageAssetBuilder

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_active_corpus(corpus)
    source_pdf = tmp_path / "text-only.pdf"
    document = fitz.open()
    page = document.new_page(width=240, height=360)
    page.insert_text((32, 80), "Source-book page")
    document.save(source_pdf)
    document.close()

    manifest = BookImageAssetBuilder(corpus, source_files={"source-sha": source_pdf}).build()

    asset = manifest["images"]["craft-jtl"]
    assert asset["status"] == "extracted"
    assert asset["method"] == "page_preview"
    with Image.open(corpus / asset["file_path"]) as preview:
        assert preview.size == (240, 360)


def test_manifest_write_replaces_the_file_atomically(tmp_path: Path, monkeypatch):
    from src.services.book_image_assets import _write_json

    path = tmp_path / "book_images.json"
    replaced = []
    original_replace = Path.replace

    def record_replace(source: Path, destination: Path):
        replaced.append((source, destination))
        return original_replace(source, destination)

    monkeypatch.setattr(Path, "replace", record_replace)
    _write_json(path, {"images": {}})

    assert json.loads(path.read_text(encoding="utf-8")) == {"images": {}}
    assert len(replaced) == 1
    assert replaced[0][1] == path
