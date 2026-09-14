"""Integrity checks for the versioned retrieval evaluation dataset."""

from collections import Counter
from pathlib import Path

from src.evaluation.retrieval_metrics import load_retrieval_cases
from src.retrieval.document_loader import HeritageDocumentLoader


DATASET_PATH = Path(__file__).parents[1] / "data" / "evaluation" / "retrieval-v1.jsonl"
EXPECTED_COUNTS = {
    "direct": 40,
    "confusion": 30,
    "comparison": 25,
    "follow_up": 15,
    "out_of_scope": 10,
}


def test_retrieval_v1_has_fixed_case_mix_and_resolvable_evidence_ids():
    cases = load_retrieval_cases(DATASET_PATH)
    counts = Counter(case["category"] for case in cases)
    available_ids = {document["id"] for document in HeritageDocumentLoader().load_craft_documents()}

    assert len(cases) == 120
    assert counts == EXPECTED_COUNTS
    for case in cases:
        assert set(case["expected_evidence_ids"]) <= available_ids, case["id"]
