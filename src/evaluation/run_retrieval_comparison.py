"""Compare BM25, local BGE vector retrieval and RRF on retrieval-v1."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from src.evaluation.retrieval_metrics import evaluate_rankings, load_retrieval_cases
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.document_loader import HeritageDocumentLoader
from src.retrieval.fusion import reciprocal_rank_fusion


def evaluate_methods(
    cases: Sequence[Mapping[str, Any]], results_by_method: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Evaluate every method against the exact same immutable set of cases."""
    return {
        method: evaluate_rankings(cases, payload["rankings"], payload.get("rejected", {}))
        for method, payload in results_by_method.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare retrieval methods on retrieval-v1.")
    parser.add_argument("--dataset", type=Path, default=Path("data/evaluation/retrieval-v1.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-path", default=r"E:/huggingface/model")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=10)
    args = parser.parse_args()

    from langchain_huggingface import HuggingFaceEmbeddings

    cases = load_retrieval_cases(args.dataset)
    documents = [
        item for item in HeritageDocumentLoader().load_craft_documents()
        if item["metadata"].get("publication_status") == "published"
    ]
    bm25 = BM25Retriever()
    bm25.build_index(documents)
    embeddings = HuggingFaceEmbeddings(
        model_name=args.model_path,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
    )
    matrix = np.asarray(embeddings.embed_documents([item["content"] for item in documents]), dtype=float)

    def vector_search(question: str, top_k: int) -> list[dict[str, Any]]:
        query = np.asarray(embeddings.embed_query(question), dtype=float)
        scores = matrix @ query
        indices = np.argsort(-scores)[:top_k]
        return [{
            "doc_id": documents[index]["id"], "content": documents[index]["content"],
            "metadata": documents[index]["metadata"], "score": float(scores[index]),
        } for index in indices]

    results: dict[str, dict[str, dict[str, Any]]] = {
        "bm25": {"rankings": {}, "rejected": {}},
        "vector_bge_m3": {"rankings": {}, "rejected": {}},
        "rrf": {"rankings": {}, "rejected": {}},
    }
    for case in cases:
        bm25_results = bm25.retrieve(case["question"], top_k=args.candidate_k)
        vector_results = vector_search(case["question"], args.candidate_k)
        rrf_results = reciprocal_rank_fusion([bm25_results, vector_results])[:args.top_k]
        for method, ranked in (("bm25", bm25_results[:args.top_k]), ("vector_bge_m3", vector_results[:args.top_k]), ("rrf", rrf_results)):
            results[method]["rankings"][case["id"]] = [item["doc_id"] for item in ranked]
            # Retrieval alone has no calibrated knowledge-gap classifier; do not fabricate rejection.
            results[method]["rejected"][case["id"]] = False

    report = {
        "metrics": evaluate_methods(cases, results),
        "configuration": {"top_k": args.top_k, "candidate_k": args.candidate_k, "model_path": args.model_path},
        "run_metadata": {
            "dataset": str(args.dataset).replace("\\", "/"), "dataset_case_count": len(cases),
            "published_document_count": len(documents), "run_at_utc": datetime.now(UTC).isoformat(),
            "git_commit": _git_commit(), "corpus_scope": "published_curated_documents_only",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(args.output), "metrics": report["metrics"]}, ensure_ascii=False))


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


if __name__ == "__main__":
    main()
