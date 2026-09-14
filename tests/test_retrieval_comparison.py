"""Tests for side-by-side retrieval baseline reporting."""

from src.evaluation.run_retrieval_comparison import evaluate_methods


def test_evaluate_methods_keeps_same_cases_for_every_retriever():
    cases = [
        {"id": "q1", "question": "问题", "category": "direct", "expected_evidence_ids": ["a"]},
        {"id": "ood", "question": "库外", "category": "out_of_scope", "expected_evidence_ids": []},
    ]
    results = {
        "bm25": {"rankings": {"q1": ["a"], "ood": ["x"]}, "rejected": {"ood": False}},
        "rrf": {"rankings": {"q1": ["x", "a"], "ood": ["x"]}, "rejected": {"ood": False}},
    }

    report = evaluate_methods(cases, results)

    assert set(report) == {"bm25", "rrf"}
    assert report["bm25"]["recall_at_1"] == 1.0
    assert report["rrf"]["mrr"] == 0.5
    assert report["rrf"]["correct_rejection_rate"] == 0.0
