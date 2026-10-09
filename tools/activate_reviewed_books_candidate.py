"""Validate and activate the reviewed books projection.

Run python -X utf8 tools/activate_reviewed_books_candidate.py --check first.
Run without --check only after the validation succeeds.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.reviewed_books_activation import (  # noqa: E402
    activate_reviewed_candidate,
    validate_reviewed_candidate,
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只校验，不替换活动投影")
    arguments = parser.parse_args()
    corpus = PROJECT_ROOT / "data" / "local_books_corpus"
    output = PROJECT_ROOT / "data" / "knowledge_sources" / "candidates" / "books-rebuild"
    candidate = output / "candidate.json"
    audit = output / "audit.json"
    if arguments.check:
        validate_reviewed_candidate(_read(candidate), _read(audit))
        print(json.dumps({"status": "validated"}, ensure_ascii=False))
        return
    result = activate_reviewed_candidate(
        corpus, candidate, audit,
        corpus / "backups" / "craft_metadata.pre-reviewed-books-rebuild.json",
    )
    print(json.dumps({"status": "activated", **result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
