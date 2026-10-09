"""Build source-backed encyclopedia images for the active local-books corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.book_image_assets import BookImageAssetBuilder, BookImageAssetError, resolve_source_files  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从活动图书来源页抽取百科配图")
    parser.add_argument("library_path", type=Path, help="原始 PDF/EPUB 图书目录")
    parser.add_argument("corpus_path", nargs="?", type=Path, default=ROOT / "data" / "local_books_corpus")
    args = parser.parse_args(argv)
    try:
        catalog = json.loads((args.corpus_path / "catalog.json").read_text(encoding="utf-8"))
        sources = resolve_source_files(args.library_path, catalog)
        manifest = BookImageAssetBuilder(args.corpus_path, source_files=sources).build()
    except (BookImageAssetError, OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    images = manifest["images"].values()
    print(json.dumps({
        "corpus_id": manifest["corpus_id"],
        "matched_source_books": len(sources),
        "extracted_images": sum(item["status"] == "extracted" for item in images),
        "unavailable_images": sum(item["status"] == "unavailable" for item in images),
        "output": str(args.corpus_path / "book_images.json"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
