from src.retrieval.document_loader import HeritageDocumentLoader
from src.services.knowledge_manifest import load_manifest
from src.services.public_content_seed import MANIFEST_PATH


def test_document_summary_counts_curated_documents_without_missing_metadata():
    summary = HeritageDocumentLoader().get_document_summary()

    assert summary["total_documents"] == 23 + len(load_manifest(MANIFEST_PATH).documents)
    assert summary["total_characters"] > 0
