"""The knowledge document schema must have a real Alembic migration."""

import importlib.util
from pathlib import Path


def test_knowledge_document_migration_declares_the_next_revision():
    migration_path = Path(__file__).parents[1] / "migrations" / "versions" / "006_add_knowledge_documents.py"
    spec = importlib.util.spec_from_file_location("migration_006", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "006"
    assert module.down_revision == "005"
