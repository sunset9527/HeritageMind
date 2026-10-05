import json

from src.retrieval.document_loader import HeritageDocumentLoader


def test_document_summary_counts_curated_documents_without_missing_metadata():
    loader = HeritageDocumentLoader()
    summary = loader.get_document_summary()

    assert summary["total_documents"] == len(loader.load_craft_documents())
    assert summary["total_characters"] > 0


def test_document_summary_uses_book_title_when_active_book_documents_have_no_craft_name(tmp_path):
    corpus_path = tmp_path / "local_books_corpus"
    corpus_path.mkdir()
    (corpus_path / "catalog.json").write_text(json.dumps({"corpus_id": "books", "status": "active"}), encoding="utf-8")
    (corpus_path / "documents.jsonl").write_text(json.dumps({
        "id": "book:1:p1:c1", "content": "图书资料", "char_count": 4,
        "metadata": {"book_title": "非遗图典", "page_start": 1},
    }, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = HeritageDocumentLoader(base_path=tmp_path / "crafts").get_document_summary()

    assert summary["crafts"] == ["非遗图典"]
