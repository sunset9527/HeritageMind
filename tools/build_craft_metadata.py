"""Generate the source-backed craft metadata projection for the active books corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.craft_metadata import CraftMetadataError, build_craft_metadata


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从活动本地图书语料生成技艺候选元数据")
    parser.add_argument(
        "corpus_path",
        nargs="?",
        default=ROOT / "data" / "local_books_corpus",
        type=Path,
        help="含 active catalog.json 的语料目录",
    )
    args = parser.parse_args(argv)
    try:
        result = build_craft_metadata(args.corpus_path)
    except CraftMetadataError as error:
        parser.error(str(error))
    print(json.dumps({
        "corpus_id": result["corpus_id"],
        "source_count": result["source_count"],
        "project_count": result["project_count"],
        "output": str(args.corpus_path / "craft_metadata.json"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
