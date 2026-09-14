"""Deterministic tests for evidence-level retrieval evaluation metrics."""

import pytest

from src.evaluation.retrieval_metrics import (
    EvaluationDataError,
    evaluate_rankings,
    load_retrieval_cases,
)


def test_evaluate_rankings_calculates_recall_mrr_and_rejection_by_case_type():
    cases = [
        {"id": "direct-1", "question": "直问", "category": "direct", "expected_evidence_ids": ["a"]},
        {"id": "confusion-1", "question": "混淆", "category": "confusion", "expected_evidence_ids": ["b", "c"]},
        {"id": "ood-1", "question": "库外", "category": "out_of_scope", "expected_evidence_ids": []},
    ]
    rankings = {
        "direct-1": ["x", "a", "b"],
        "confusion-1": ["c", "x", "b"],
        "ood-1": ["x"],
    }
    rejected = {"ood-1": True}

    report = evaluate_rankings(cases, rankings, rejected)

    assert report["answerable_count"] == 2
    assert report["out_of_scope_count"] == 1
    assert report["recall_at_1"] == 0.5
    assert report["recall_at_3"] == 1.0
    assert report["recall_at_5"] == 1.0
    assert report["mrr"] == 0.75
    assert report["correct_rejection_rate"] == 1.0
    assert report["by_category"]["direct"]["mrr"] == 0.5
    assert report["by_category"]["confusion"]["mrr"] == 1.0


def test_evaluate_rankings_does_not_silently_drop_missing_or_unknown_cases():
    cases = [{"id": "q1", "question": "问题", "category": "direct", "expected_evidence_ids": ["a"]}]

    with pytest.raises(EvaluationDataError, match="q1"):
        evaluate_rankings(cases, rankings={})

    with pytest.raises(EvaluationDataError, match="unknown"):
        evaluate_rankings(cases, rankings={"q1": ["a"], "unknown": ["b"]})


def test_load_retrieval_cases_requires_unique_ids_and_explicit_expected_evidence(tmp_path):
    dataset = tmp_path / "retrieval.jsonl"
    dataset.write_text(
        '{"id":"q1","question":"问题","category":"direct","expected_evidence_ids":["a"]}\n'
        '{"id":"q1","question":"重复","category":"direct","expected_evidence_ids":["b"]}\n',
        encoding="utf-8",
    )

    with pytest.raises(EvaluationDataError, match="重复"):
        load_retrieval_cases(dataset)


def test_load_retrieval_cases_allows_out_of_scope_only_with_empty_evidence(tmp_path):
    dataset = tmp_path / "retrieval.jsonl"
    dataset.write_text(
        '{"id":"ood-1","question":"库外问题","category":"out_of_scope","expected_evidence_ids":[]}\n',
        encoding="utf-8",
    )

    assert load_retrieval_cases(dataset)[0]["id"] == "ood-1"
