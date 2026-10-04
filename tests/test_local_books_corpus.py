"""Local heritage books must produce a traceable, switchable retrieval corpus."""

import json
from pathlib import Path
import subprocess
import sys

import pytest


def _fake_pdf_pages(_path, **_kwargs):
    return [
        {"page": 1, "text": "第一章 景泰蓝\n景泰蓝以铜胎、掐丝和点蓝工艺著称。", "source": "text", "char_count": 24},
        {"page": 2, "text": "", "source": "empty", "char_count": 0},
        {"page": 3, "text": "烧制后需要磨光和镀金。", "source": "ocr", "char_count": 12},
    ]


def test_building_books_corpus_is_traceable_and_ignores_empty_pages(tmp_path):
    from src.services.local_books_corpus import LocalBooksCorpusBuilder

    library = tmp_path / "library"
    library.mkdir()
    (library / "非遗图典.pdf").write_bytes(b"fixture")
    output = tmp_path / "corpus"

    result = LocalBooksCorpusBuilder(
        library,
        output,
        pdf_page_parser=_fake_pdf_pages,
        chunk_chars=200,
    ).build(corpus_id="heritage-books-v1")

    assert result.source_count == 1
    assert result.empty_page_count == 1
    assert result.document_count == 2
    catalog = json.loads((output / "catalog.json").read_text(encoding="utf-8"))
    documents = [json.loads(line) for line in (output / "documents.jsonl").read_text(encoding="utf-8").splitlines()]
    assert catalog["corpus_id"] == "heritage-books-v1"
    assert catalog["status"] == "staged"
    assert all(item["metadata"]["book_title"] == "非遗图典" for item in documents)
    assert [(item["metadata"]["page_start"], item["metadata"]["page_end"]) for item in documents] == [(1, 1), (3, 3)]
    assert documents[1]["metadata"]["extraction_method"] == "ocr"


def test_rebuilding_unchanged_library_keeps_document_ids_stable(tmp_path):
    from src.services.local_books_corpus import LocalBooksCorpusBuilder

    library = tmp_path / "library"
    library.mkdir()
    (library / "非遗图典.pdf").write_bytes(b"fixture")
    output = tmp_path / "corpus"
    builder = LocalBooksCorpusBuilder(library, output, pdf_page_parser=_fake_pdf_pages)

    builder.build(corpus_id="heritage-books-v1")
    first = (output / "documents.jsonl").read_text(encoding="utf-8")
    builder.build(corpus_id="heritage-books-v1")

    assert (output / "documents.jsonl").read_text(encoding="utf-8") == first


def test_preflight_checks_books_without_running_pdf_or_ocr_parsing(tmp_path):
    from src.services.local_books_corpus import LocalBooksCorpusBuilder

    library = tmp_path / "library"
    library.mkdir()
    (library / "非遗图典.pdf").write_bytes(b"fixture")

    def parser_must_not_run(*_args, **_kwargs):
        raise AssertionError("preflight must not parse pages")

    result = LocalBooksCorpusBuilder(library, tmp_path / "corpus", pdf_page_parser=parser_must_not_run).preflight()

    assert result.source_count == 1
    assert result.document_count == 0
    assert result.empty_page_count == 0


def test_activate_switches_only_after_a_staged_corpus_exists(tmp_path):
    from src.services.local_books_corpus import activate_staged_corpus

    output = tmp_path / "corpus"
    output.mkdir()
    (output / "catalog.json").write_text(
        json.dumps({"corpus_id": "heritage-books-v1", "status": "staged"}), encoding="utf-8"
    )
    (output / "documents.jsonl").write_text("{}\n", encoding="utf-8")

    activate_staged_corpus(output)

    catalog = json.loads((output / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["status"] == "active"


def test_active_local_books_replace_legacy_documents_in_default_loader(tmp_path):
    from src.retrieval.document_loader import HeritageDocumentLoader

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "catalog.json").write_text(
        json.dumps({"corpus_id": "heritage-books-v1", "status": "active"}), encoding="utf-8"
    )
    (corpus / "documents.jsonl").write_text(
        json.dumps({"id": "book:1", "content": "图书中的可检索正文", "char_count": 9, "metadata": {"book_title": "图典"}}) + "\n",
        encoding="utf-8",
    )
    legacy = tmp_path / "crafts"
    legacy.mkdir()
    (legacy / "景泰蓝.txt").write_text("旧资料", encoding="utf-8")

    documents = HeritageDocumentLoader(base_path=str(legacy), local_books_corpus_path=corpus).load_craft_documents()

    assert [item["id"] for item in documents] == ["book:1"]


def test_book_corpus_command_exposes_build_and_activate_options():
    project = Path(__file__).parents[1]
    completed = subprocess.run(
        [sys.executable, "tools/build_local_books_corpus.py", "--help"],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--library" in completed.stdout
    assert "--activate" in completed.stdout


def test_page_checkpoint_is_visible_and_resume_starts_at_first_unfinished_page(tmp_path):
    from src.services.local_books_corpus import LocalBooksCorpusBuilder

    library = tmp_path / "library"
    library.mkdir()
    (library / "非遗图典.pdf").write_bytes(b"fixture")
    output = tmp_path / "corpus"
    first_starts = []

    def failing_reader(_path, *, start_page=1):
        first_starts.append(start_page)
        yield {"page": 1, "text": "第一页资料", "source": "text", "char_count": 5}
        raise RuntimeError("OCR interrupted")

    first = LocalBooksCorpusBuilder(
        library, output, pdf_page_reader=failing_reader, pdf_page_counter=lambda _: 2
    )
    with pytest.raises(RuntimeError, match="OCR interrupted"):
        first.build()

    progress = json.loads((output / "progress.json").read_text(encoding="utf-8"))
    assert first_starts == [1]
    assert progress["completed_unit_count"] == 1
    assert progress["total_unit_count"] == 2
    assert progress["percent"] == 50.0
    assert (output / "documents.jsonl").read_text(encoding="utf-8").count("第一页资料") == 1
    assert not (output / "catalog.json").exists()

    resumed_starts = []

    def resumed_reader(_path, *, start_page=1):
        resumed_starts.append(start_page)
        yield {"page": 2, "text": "第二页资料", "source": "ocr", "char_count": 5}

    result = LocalBooksCorpusBuilder(
        library, output, pdf_page_reader=resumed_reader, pdf_page_counter=lambda _: 2
    ).build()

    assert resumed_starts == [2]
    assert result.document_count == 2
    assert json.loads((output / "progress.json").read_text(encoding="utf-8"))["percent"] == 100.0
    assert json.loads((output / "catalog.json").read_text(encoding="utf-8"))["status"] == "staged"


def test_progress_command_reads_checkpoint_without_requiring_library(tmp_path):
    output = tmp_path / "corpus"
    output.mkdir()
    (output / "progress.json").write_text(
        json.dumps({"status": "running", "completed_unit_count": 17, "total_unit_count": 100, "percent": 17.0}),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "tools/build_local_books_corpus.py", "--output", str(output), "--progress"],
        cwd=Path(__file__).parents[1], text=True, capture_output=True, check=False,
    )

    assert completed.returncode == 0
    assert "17" in completed.stdout
    assert "17.0" in completed.stdout
