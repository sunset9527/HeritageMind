"""Evidence-level retrieval evaluation that does not filter failed cases."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


OUT_OF_SCOPE = "out_of_scope"
REQUIRED_FIELDS = {"id", "question", "category", "expected_evidence_ids"}


class EvaluationDataError(ValueError):
    """Raised when a versioned evaluation set or result set is incomplete."""


def load_retrieval_cases(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate JSONL cases without skipping malformed lines."""
    dataset_path = Path(path)
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for line_number, raw_line in enumerate(dataset_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            raise EvaluationDataError(f"评测集第 {line_number} 行为空，不能静默跳过")
        try:
            case = json.loads(raw_line)
        except json.JSONDecodeError as error:
            raise EvaluationDataError(f"评测集第 {line_number} 行不是合法 JSON") from error
        _validate_case(case, line_number)
        case_id = case["id"]
        if case_id in seen_ids:
            raise EvaluationDataError(f"评测集存在重复 id：{case_id}")
        seen_ids.add(case_id)
        cases.append(case)

    if not cases:
        raise EvaluationDataError("评测集不能为空")
    return cases


def evaluate_rankings(
    cases: Sequence[Mapping[str, Any]],
    rankings: Mapping[str, Sequence[str]],
    rejected: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Compute evidence Recall@k, MRR and out-of-scope rejection accuracy.

    Every dataset case must have a ranking entry.  This prevents a baseline
    from improving its displayed score by discarding questions it cannot run.
    """
    rejected = rejected or {}
    case_ids = {case["id"] for case in cases}
    ranking_ids = set(rankings)
    unknown = ranking_ids - case_ids
    missing = case_ids - ranking_ids
    if unknown:
        raise EvaluationDataError(f"结果包含未知评测 id：{sorted(unknown)}")
    if missing:
        raise EvaluationDataError(f"结果缺少评测 id：{sorted(missing)}")
    if set(rejected) - case_ids:
        raise EvaluationDataError(f"拒答结果包含未知评测 id：{sorted(set(rejected) - case_ids)}")

    answerable: list[tuple[Mapping[str, Any], int | None]] = []
    out_of_scope: list[Mapping[str, Any]] = []
    by_category: dict[str, list[tuple[Mapping[str, Any], int | None]]] = defaultdict(list)

    for case in cases:
        _validate_case(case)
        case_id = case["id"]
        result_ids = rankings[case_id]
        if not all(isinstance(item, str) and item for item in result_ids):
            raise EvaluationDataError(f"评测 {case_id} 的排序结果必须是非空字符串 ID 列表")
        if case["category"] == OUT_OF_SCOPE:
            out_of_scope.append(case)
            continue
        expected = set(case["expected_evidence_ids"])
        first_rank = next((index for index, item in enumerate(result_ids, 1) if item in expected), None)
        answerable.append((case, first_rank))
        by_category[case["category"]].append((case, first_rank))

    if not answerable:
        raise EvaluationDataError("评测集至少需要一条可回答问题")
    if not out_of_scope:
        raise EvaluationDataError("评测集至少需要一条知识库外问题")

    def recall_at(k: int, values: Iterable[tuple[Mapping[str, Any], int | None]]) -> float:
        values = list(values)
        return sum(rank is not None and rank <= k for _, rank in values) / len(values)

    def mean_reciprocal_rank(values: Iterable[tuple[Mapping[str, Any], int | None]]) -> float:
        values = list(values)
        return sum(0.0 if rank is None else 1.0 / rank for _, rank in values) / len(values)

    report: dict[str, Any] = {
        "answerable_count": len(answerable),
        "out_of_scope_count": len(out_of_scope),
        "recall_at_1": recall_at(1, answerable),
        "recall_at_3": recall_at(3, answerable),
        "recall_at_5": recall_at(5, answerable),
        "mrr": mean_reciprocal_rank(answerable),
        "correct_rejection_rate": sum(bool(rejected.get(case["id"], False)) for case in out_of_scope)
        / len(out_of_scope),
        "by_category": {},
    }
    for category, values in by_category.items():
        report["by_category"][category] = {
            "count": len(values),
            "recall_at_1": recall_at(1, values),
            "recall_at_3": recall_at(3, values),
            "recall_at_5": recall_at(5, values),
            "mrr": mean_reciprocal_rank(values),
        }
    report["by_category"][OUT_OF_SCOPE] = {
        "count": len(out_of_scope),
        "correct_rejection_rate": report["correct_rejection_rate"],
    }
    return report


def _validate_case(case: Mapping[str, Any], line_number: int | None = None) -> None:
    location = f"第 {line_number} 行" if line_number is not None else f"评测 {case.get('id', '<unknown>')}"
    if not isinstance(case, Mapping):
        raise EvaluationDataError(f"{location} 必须是对象")
    missing = REQUIRED_FIELDS - set(case)
    if missing:
        raise EvaluationDataError(f"{location} 缺少字段：{sorted(missing)}")
    if not isinstance(case["id"], str) or not case["id"].strip():
        raise EvaluationDataError(f"{location} 的 id 必须是非空字符串")
    if not isinstance(case["question"], str) or not case["question"].strip():
        raise EvaluationDataError(f"{location} 的 question 必须是非空字符串")
    if not isinstance(case["category"], str) or not case["category"].strip():
        raise EvaluationDataError(f"{location} 的 category 必须是非空字符串")
    evidence_ids = case["expected_evidence_ids"]
    if not isinstance(evidence_ids, list) or not all(isinstance(item, str) and item for item in evidence_ids):
        raise EvaluationDataError(f"{location} 的 expected_evidence_ids 必须是字符串列表")
    if case["category"] == OUT_OF_SCOPE and evidence_ids:
        raise EvaluationDataError(f"{location} 的知识库外问题必须没有期望证据")
    if case["category"] != OUT_OF_SCOPE and not evidence_ids:
        raise EvaluationDataError(f"{location} 的可回答问题必须标注期望证据")
