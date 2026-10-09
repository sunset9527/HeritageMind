"""Evaluate the active book corpus with paired first-stage and reranked results."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from config import settings
from src.evaluation.retrieval_metrics import EvaluationDataError, evaluate_rankings, load_retrieval_cases
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.document_loader import HeritageDocumentLoader
from src.retrieval.reranker import CrossEncoderReranker
from src.retrieval.retriever import MultiSourceRetriever


def validate_book_cases(cases: Sequence[Mapping[str, Any]], documents: Sequence[Mapping[str, Any]]) -> None:
    """Reject stale IDs, unverifiable quotes, and changed book chunks."""
    by_id = {item["id"]: item for item in documents}
    if len(by_id) != len(documents):
        raise EvaluationDataError("图书语料存在重复文档 ID")
    seen = set()
    for case in cases:
        case_id = case["id"]
        if case_id in seen:
            raise EvaluationDataError(f"重复评测题：{case_id}")
        seen.add(case_id)
        expected = case["expected_evidence_ids"]
        if case["category"] == "out_of_scope":
            if expected:
                raise EvaluationDataError(f"库外题 {case_id} 不应有预期证据")
            continue
        if not expected or not case.get("answer") or not case.get("evidence_quote"):
            raise EvaluationDataError(f"题目 {case_id} 缺少答案或证据片段")
        page = case.get("source_page")
        if not isinstance(page, int) or page < 1:
            raise EvaluationDataError(f"题目 {case_id} 缺少有效页码")
        for doc_id in expected:
            if doc_id not in by_id:
                raise EvaluationDataError(f"题目 {case_id} 的证据 ID 不存在：{doc_id}")
            doc = by_id[doc_id]
            metadata = doc["metadata"]
            if not doc_id.startswith("book:") or metadata.get("corpus_id") != "heritage-books-v1":
                raise EvaluationDataError(f"题目 {case_id} 的证据不属于当前图书语料")
            digest = hashlib.sha256(doc["content"].encode("utf-8")).hexdigest()
            if digest != metadata.get("content_sha256"):
                raise EvaluationDataError(f"题目 {case_id} 的文档校验和不匹配")
            if metadata.get("page_start") != page or metadata.get("page_end") != page:
                raise EvaluationDataError(f"题目 {case_id} 的证据页码不匹配")
        if not any(case["evidence_quote"] in by_id[doc_id]["content"] for doc_id in expected):
            raise EvaluationDataError(f"题目 {case_id} 的证据片段在标注文档中不存在")


def compare_paired_methods(
    cases: Sequence[Mapping[str, Any]],
    first_stage: Callable[[str, int], list[dict[str, Any]]],
    rerank: Callable[[str, list[dict[str, Any]], int], list[dict[str, Any]]],
    *, candidate_k: int,
    top_k: int,
) -> dict[str, Any]:
    """Compare the same candidate list before and after a real reranker call."""
    if top_k < 1 or candidate_k < top_k:
        raise ValueError("candidate_k 必须不小于正数 top_k")
    rankings: dict[str, dict[str, list[str]]] = {"before": {}, "after": {}}
    per_case: list[dict[str, Any]] = []
    first_stage_ms = []
    rerank_ms = []
    candidate_hits = 0
    answerable_count = 0
    for case in cases:
        started = perf_counter()
        candidates = first_stage(case["question"], candidate_k)
        first_stage_ms.append((perf_counter() - started) * 1000)
        candidate_ids = [item["doc_id"] for item in candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise EvaluationDataError(f"题目 {case['id']} 的候选文档 ID 重复")
        before = candidate_ids[:top_k]
        started = perf_counter()
        after_items = rerank(case["question"], [dict(item) for item in candidates], top_k) if candidates else []
        rerank_ms.append((perf_counter() - started) * 1000)
        if any("rerank_score" not in item for item in after_items):
            raise RuntimeError(f"题目 {case['id']} 的重排结果缺少 rerank_score；模型可能已降级")
        after = [item["doc_id"] for item in after_items]
        if len(after) != len(set(after)) or not set(after) <= set(candidate_ids):
            raise EvaluationDataError(f"题目 {case['id']} 的重排结果不属于原候选池")
        rankings["before"][case["id"]] = before
        rankings["after"][case["id"]] = after
        expected = set(case["expected_evidence_ids"])
        if case["category"] != "out_of_scope":
            answerable_count += 1
            candidate_hits += bool(expected & set(candidate_ids))
        per_case.append({
            "id": case["id"], "category": case["category"], "candidate_ids": candidate_ids,
            "before": before, "after": after,
            "before_first_gold_rank": next((i for i, doc_id in enumerate(before, 1) if doc_id in expected), None),
            "after_first_gold_rank": next((i for i, doc_id in enumerate(after, 1) if doc_id in expected), None),
        })
    return {
        "metrics": {method: evaluate_rankings(cases, ranked) for method, ranked in rankings.items()},
        "candidate_recall": candidate_hits / answerable_count if answerable_count else 0.0,
        "rankings": rankings,
        "per_case": per_case,
        "latency_ms": {
            "first_stage": _latency_summary(first_stage_ms),
            "rerank_only": _latency_summary(rerank_ms),
            "combined": _latency_summary([a + b for a, b in zip(first_stage_ms, rerank_ms)]),
        },
    }


def _latency_summary(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {"median": 0.0, "p95": 0.0}
    ordered = sorted(samples)
    return {
        "median": round(statistics.median(ordered), 2),
        "p95": round(ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)], 2),
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare book retrieval with a verified local reranker")
    parser.add_argument("--dataset", type=Path, default=Path("data/evaluation/retrieval-books-v1.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("data/local_books_corpus/documents.jsonl"))
    parser.add_argument("--model-path", default=settings.reranker_model)
    parser.add_argument("--candidate-k", type=int, default=15)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    cases = load_retrieval_cases(args.dataset)
    loader = HeritageDocumentLoader(local_books_corpus_path=args.corpus.parent)
    documents = loader.load_craft_documents()
    validate_book_cases(cases, documents)
    with args.corpus.open("rb") as corpus_file:
        corpus_sha256 = hashlib.file_digest(corpus_file, "sha256").hexdigest()
    model = CrossEncoderReranker(args.model_path)
    original_enabled = settings.reranker_enabled
    settings.reranker_enabled = True
    try:
        load_started = perf_counter()
        model._load()
        model_load_seconds = round(perf_counter() - load_started, 2)
        if model._model is None:
            raise RuntimeError("本地 CrossEncoder 未加载；拒绝输出伪 rerank 指标")

        def rerank(question: str, candidates: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
            return model.rerank(question, candidates, top_k)

        bm25 = BM25Retriever()
        bm25.build_index(documents)
        bm25_result = compare_paired_methods(
            cases, lambda q, k: bm25.retrieve(q, top_k=k), rerank,
            candidate_k=args.candidate_k, top_k=args.top_k,
        )

        runtime = MultiSourceRetriever(document_loader=loader)

        def runtime_first(question: str, candidate_k: int) -> list[dict[str, Any]]:
            settings.reranker_enabled = False
            try:
                ranked = runtime.retrieve(question, top_k=candidate_k)
            finally:
                settings.reranker_enabled = True
            return [{**item, "doc_id": item["id"], "score": item.get("similarity", 0.0)} for item in ranked]

        runtime_result = compare_paired_methods(
            cases, runtime_first, rerank,
            candidate_k=args.candidate_k, top_k=args.top_k,
        )
    finally:
        settings.reranker_enabled = original_enabled

    report = {
        "configuration": {
            "top_k": args.top_k, "candidate_k": args.candidate_k,
            "reranker_model": args.model_path, "reranker_loaded": True,
            "model_load_seconds": model_load_seconds,
            "method_note": "Same candidate pool before/after. Runtime first stage uses MultiSourceRetriever without embeddings.",
        },
        "run_metadata": {
            "dataset": args.dataset.as_posix(), "dataset_case_count": len(cases),
            "corpus": args.corpus.as_posix(), "corpus_sha256": corpus_sha256,
            "document_count": len(documents), "git_commit": _git_commit(),
            "run_at_utc": datetime.now(UTC).isoformat(),
        },
        "methods": {"bm25": bm25_result, "runtime_keyword": runtime_result},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": args.output.as_posix(), "model_loaded": True,
        "bm25_metrics": bm25_result["metrics"], "runtime_keyword_metrics": runtime_result["metrics"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
