"""Explicitly build the local, copyright-restricted heritage-books retrieval corpus."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.local_books_corpus import (  # noqa: E402
    LocalBooksCorpusBuilder,
    LocalBooksCorpusError,
    activate_staged_corpus,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将本地 PDF/EPUB 非遗书籍构建为可溯源检索语料；不会上传或提交原文。"
    )
    parser.add_argument("--library", required=True, type=Path, help="含 PDF/EPUB 原件的本地知识库目录")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "local_books_corpus",
        help="本地 corpus 输出目录（默认：data/local_books_corpus，已被 Git 忽略）",
    )
    parser.add_argument("--corpus-id", default="heritage-books-v1", help="本次语料版本标识")
    parser.add_argument("--chunk-chars", default=1200, type=int, help="单个检索片段的最大字符数（默认：1200）")
    parser.add_argument("--dry-run", action="store_true", help="仅检查书库目录和支持的文件，不解析、不写入、不激活")
    parser.add_argument("--activate", action="store_true", help="构建成功后将 staged corpus 切换为默认检索语料")
    arguments = parser.parse_args()
    if arguments.dry_run and arguments.activate:
        parser.error("--dry-run 不能与 --activate 同时使用")
    return arguments


def main() -> int:
    arguments = parse_args()
    try:
        builder = LocalBooksCorpusBuilder(
            arguments.library,
            arguments.output,
            chunk_chars=arguments.chunk_chars,
        )
        result = (
            builder.preflight(corpus_id=arguments.corpus_id)
            if arguments.dry_run
            else builder.build(corpus_id=arguments.corpus_id)
        )
        print(
            f"图书语料{'预检' if arguments.dry_run else '构建'}完成："
            f"来源 {result.source_count} 本，片段 {result.document_count} 条，空页 {result.empty_page_count} 页。"
        )
        if arguments.activate:
            activate_staged_corpus(arguments.output)
            print(f"已激活语料集：{result.corpus_id}。默认检索现在只读取该本地图书语料。")
    except (LocalBooksCorpusError, OSError, ValueError) as error:
        print(f"图书语料构建失败：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
