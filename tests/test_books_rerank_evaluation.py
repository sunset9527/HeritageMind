"""Book-corpus evaluation must keep evidence and reranking auditable."""

from collections import Counter
from hashlib import sha256
from pathlib import Path

import pytest

from src.evaluation.retrieval_metrics import EvaluationDataError
from src.evaluation.retrieval_metrics import load_retrieval_cases
from src.evaluation.run_books_rerank import compare_paired_methods, validate_book_cases
from src.retrieval.document_loader import HeritageDocumentLoader


DATASET = Path(__file__).parents[1] / "data" / "evaluation" / "retrieval-books-v1.jsonl"
LOCAL_CORPUS = Path(__file__).parents[1] / "data" / "local_books_corpus" / "catalog.json"


def test_versioned_book_cases_resolve_to_current_corpus_and_cover_all_books():
    cases = load_retrieval_cases(DATASET)
    counts = Counter(case["category"] for case in cases)
    assert counts == {"direct": 60, "paraphrase": 40, "out_of_scope": 20}
    if not LOCAL_CORPUS.is_file():
        pytest.skip("本机图书语料未安装；证据校验需在有活动语料的环境运行")
    documents = HeritageDocumentLoader().load_craft_documents()
    validate_book_cases(cases, documents)
    by_id = {document["id"]: document for document in documents}
    covered_books = {
        by_id[case["expected_evidence_ids"][0]]["metadata"]["source_id"]
        for case in cases if case["category"] != "out_of_scope"
    }
    assert len(covered_books) == 10


def _doc(doc_id: str, content: str) -> dict:
    return {
        "id": doc_id,
        "content": content,
        "metadata": {
            "corpus_id": "heritage-books-v1",
            "book_title": "示例图书",
            "page_start": 12,
            "page_end": 12,
            "content_sha256": sha256(content.encode("utf-8")).hexdigest(),
        },
    }


def test_book_cases_require_verifiable_quote_and_current_document_id():
    documents = [_doc("book:one:p12:c1", "王习三把国画技法引入内画创作。")]
    answerable = {
        "id": "b01", "question": "谁将国画技法用于内画？", "category": "direct",
        "answer": "王习三", "expected_evidence_ids": ["book:one:p12:c1"],
        "evidence_quote": "把国画技法引入内画", "source_page": 12,
    }
    out_of_scope = {
        "id": "o01", "question": "明日股价是多少？", "category": "out_of_scope",
        "expected_evidence_ids": [],
    }
    validate_book_cases([answerable, out_of_scope], documents)

    with pytest.raises(EvaluationDataError, match="证据片段"):
        validate_book_cases([{**answerable, "evidence_quote": "并不存在的句子"}, out_of_scope], documents)
    with pytest.raises(EvaluationDataError, match="不存在"):
        validate_book_cases([{**answerable, "expected_evidence_ids": ["curated:old"]}, out_of_scope], documents)


def test_paired_comparison_uses_same_candidates_and_records_improvement():
    cases = [
        {"id": "b01", "question": "问题", "category": "direct", "expected_evidence_ids": ["gold"]},
        {"id": "o01", "question": "库外", "category": "out_of_scope", "expected_evidence_ids": []},
    ]
    seen = []

    def first_stage(question, candidate_k):
        assert candidate_k == 2
        return [
            {"doc_id": "wrong", "content": "无关", "score": 2.0},
            {"doc_id": "gold", "content": "答案", "score": 1.0},
        ]

    def rerank(question, candidates, top_k):
        seen.append((question, [item["doc_id"] for item in candidates], top_k))
        return [{**item, "rerank_score": float(item["doc_id"] == "gold")}
                for item in reversed(candidates)][:top_k]

    report = compare_paired_methods(cases, first_stage, rerank, candidate_k=2, top_k=1)

    assert len(seen) == 2
    assert all(item[1] == ["wrong", "gold"] for item in seen)
    assert report["metrics"]["before"]["recall_at_1"] == 0.0
    assert report["metrics"]["after"]["recall_at_1"] == 1.0
    assert report["candidate_recall"] == 1.0
    assert report["rankings"]["after"]["b01"] == ["gold"]


def test_paired_comparison_rejects_silent_reranker_fallback():
    cases = [
        {"id": "b01", "question": "问题", "category": "direct", "expected_evidence_ids": ["gold"]},
        {"id": "o01", "question": "库外", "category": "out_of_scope", "expected_evidence_ids": []},
    ]
    def first_stage(_question, _k):
        return [{"doc_id": "gold", "content": "答案", "score": 1.0}]

    def fallback(_question, candidates, _k):
        return candidates

    with pytest.raises(RuntimeError, match="rerank_score"):
        compare_paired_methods(cases, first_stage, fallback, candidate_k=1, top_k=1)
