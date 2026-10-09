"""Explicitly import the reviewed local knowledge manifest into the configured database."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.knowledge_ingest import run_configured_manifest_import  # noqa: E402


if __name__ == "__main__":
    result = run_configured_manifest_import()
    print(
        f"知识资料导入完成：创建 {result.created_count}，"
        f"更新 {result.updated_count}，跳过 {result.skipped_count}，"
        f"导入批次 #{result.run_id}"
    )
