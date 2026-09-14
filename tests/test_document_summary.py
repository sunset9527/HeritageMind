from src.retrieval.document_loader import HeritageDocumentLoader


def test_document_summary_counts_curated_documents_without_missing_metadata():
    summary = HeritageDocumentLoader().get_document_summary()

    assert summary["total_documents"] == 69
    assert summary["total_characters"] > 0
