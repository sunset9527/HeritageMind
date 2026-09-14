"""Run a transparent local BM25 retrieval baseline for retrieval-v1."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.evaluation.retrieval_metrics import evaluate_rankings, load_retrieval_cases
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.document_loader import HeritageDocumentLoader


def run_bm25_baseline(
    cases: Sequence[Mapping[str, Any]],
    retriever: Any,
    *,
    top_k: int = 5,
    rejection_threshold: float = 0.0,
) -> dict[str, Any]:
    """Run one deterministic retriever and retain every ranking and failure."""
    rankings: dict[str, list[str]] = {}
    rejected: dict[str, bool] = {}
    failures: list[dict[str, Any]] = []

    for case in cases:
        results = retriever.retrieve(case["question"], top_k=top_k)
        result_ids = [item["doc_id"] for item in results]
        rankings[case["id"]] = result_ids
        top_score = float(results[0]["score"]) if results else float("-inf")
        rejected[case["id"]] = not results or top_score <= rejection_threshold

    metrics = evaluate_rankings(cases, rankings, rejected)
    for case in cases:
        expected = set(case["expected_evidence_ids"])
        ranking = rankings[case["id"]]
        if case["category"] == "out_of_scope":
            if not rejected[case["id"]]:
                failures.append({"id": case["id"], "reason": "not_rejected", "ranking": ranking})
        elif not any(item in expected for item in ranking):
            failures.append({"id": case["id"], "reason": "evidence_not_retrieved", "ranking": ranking})

    return {
        "metrics": metrics,
        "rankings": rankings,
        "rejected": rejected,
        "failures": failures,
        "configuration": {"method": "bm25", "top_k": top_k, "rejection_threshold": rejection_threshold},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the retrieval-v1 BM25 baseline.")
    parser.add_argument("--dataset", type=Path, default=Path("data/evaluation/retrieval-v1.jsonl"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rejection-threshold", type=float, default=0.0)
    args = parser.parse_args()

    cases = load_retrieval_cases(args.dataset)
    published_documents = [
        document for document in HeritageDocumentLoader().load_craft_documents()
        if document["metadata"].get("publication_status") == "published"
    ]
    retriever = BM25Retriever()
    retriever.build_index(published_documents)
    output = run_bm25_baseline(
        cases, retriever, top_k=args.top_k, rejection_threshold=args.rejection_threshold,
    )
    output["run_metadata"] = {
        "dataset": str(args.dataset).replace("\\", "/"),
        "dataset_case_count": len(cases),
        "published_document_count": len(published_documents),
        "run_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "corpus_scope": "published_curated_documents_only",
    }
    output_path = args.output or Path("data/evaluation/reports") / (
        f"retrieval-v1-bm25-{datetime.now().strftime('%Y%m%d')}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(output_path), "metrics": output["metrics"], "failures": len(output["failures"])}, ensure_ascii=False))


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


if __name__ == "__main__":
    main()
