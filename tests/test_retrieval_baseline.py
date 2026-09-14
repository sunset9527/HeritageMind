"""Tests for the reproducible BM25 baseline runner."""

from src.evaluation.run_retrieval_baseline import run_bm25_baseline


class FakeRetriever:
    def __init__(self, responses):
        self.responses = responses

    def retrieve(self, question, top_k):
        return self.responses[question][:top_k]


def test_bm25_baseline_records_rankings_failures_and_threshold_rejection():
    cases = [
        {"id": "q1", "question": "可回答", "category": "direct", "expected_evidence_ids": ["e1"]},
        {"id": "q2", "question": "库外", "category": "out_of_scope", "expected_evidence_ids": []},
    ]
    retriever = FakeRetriever({
        "可回答": [{"doc_id": "e1", "score": 2.0}],
        "库外": [{"doc_id": "e2", "score": 0.0}],
    })

    output = run_bm25_baseline(cases, retriever, top_k=5, rejection_threshold=0.0)

    assert output["metrics"]["recall_at_1"] == 1.0
    assert output["metrics"]["correct_rejection_rate"] == 1.0
    assert output["rankings"]["q1"] == ["e1"]
    assert output["failures"] == []
