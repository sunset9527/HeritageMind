"""The explicit manifest import must commit atomically or roll back."""

from pathlib import Path

import pytest


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_configured_manifest_import_commits_and_closes_the_session(monkeypatch):
    import src.services.knowledge_ingest as knowledge_ingest

    db = FakeSession()
    result = knowledge_ingest.IngestResult(created_count=591, updated_count=0, skipped_count=0, run_id=1)
    monkeypatch.setattr(knowledge_ingest, "init_db", lambda: None, raising=False)
    monkeypatch.setattr(knowledge_ingest, "SessionLocal", lambda: db, raising=False)
    monkeypatch.setattr(knowledge_ingest, "load_manifest", lambda _: object(), raising=False)
    monkeypatch.setattr(knowledge_ingest, "ingest_manifest", lambda *_args, **_kwargs: result)

    assert knowledge_ingest.run_configured_manifest_import(Path("manifest.json")) == result
    assert db.committed is True
    assert db.closed is True


def test_configured_manifest_import_rolls_back_when_ingestion_fails(monkeypatch):
    import src.services.knowledge_ingest as knowledge_ingest

    db = FakeSession()
    monkeypatch.setattr(knowledge_ingest, "init_db", lambda: None, raising=False)
    monkeypatch.setattr(knowledge_ingest, "SessionLocal", lambda: db, raising=False)
    monkeypatch.setattr(knowledge_ingest, "load_manifest", lambda _: object(), raising=False)

    def fail(*_args, **_kwargs):
        raise RuntimeError("invalid package")

    monkeypatch.setattr(knowledge_ingest, "ingest_manifest", fail)

    with pytest.raises(RuntimeError, match="invalid package"):
        knowledge_ingest.run_configured_manifest_import(Path("manifest.json"))

    assert db.rolled_back is True
    assert db.closed is True
