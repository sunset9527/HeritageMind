"""文档先进入隔离草稿区，不直接污染可检索知识目录。"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.models.platform import AuditLog
from src.services.upload_security import StagedUpload


def _db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def _staged(root: Path) -> StagedUpload:
    root.mkdir(parents=True, exist_ok=True)
    temp = root / ("c" * 32 + ".pdf.part")
    temp.write_bytes(b"%PDF-safe")
    return StagedUpload(
        temp_path=temp,
        storage_name="c" * 32 + ".pdf",
        original_name="研究资料.pdf",
        format="pdf",
        extension=".pdf",
        mime_type="application/pdf",
        size_bytes=9,
        content_sha256="d" * 64,
    )


def test_document_is_saved_as_pending_draft_outside_knowledge_corpus(tmp_path):
    from src.services.document_upload import persist_staged_document

    db, engine = _db()
    upload_root = tmp_path / "uploads"
    corpus_root = tmp_path / "crafts"
    try:
        row = persist_staged_document(
            db,
            staged=_staged(upload_root),
            storage_root=upload_root,
            craft_id="jingtailan",
            craft_name="景泰蓝",
            uploaded_by_user_id=5,
        )

        assert row.review_status == "draft"
        assert row.processing_status == "pending"
        assert row.storage_name == "c" * 32 + ".pdf"
        assert (upload_root / row.storage_name).exists()
        assert not corpus_root.exists()
        assert db.query(AuditLog).one().action == "document.uploaded"
    finally:
        db.close()
        engine.dispose()


def test_document_commit_failure_removes_published_file(tmp_path, monkeypatch):
    from src.services.document_upload import persist_staged_document

    db, engine = _db()
    staged = _staged(tmp_path)
    monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("commit")))
    try:
        try:
            persist_staged_document(
                db,
                staged=staged,
                storage_root=tmp_path,
                craft_id="jingtailan",
                craft_name="景泰蓝",
                uploaded_by_user_id=5,
            )
        except RuntimeError:
            pass
        assert list(tmp_path.glob("*.pdf")) == []
        assert list(tmp_path.glob("*.part")) == []
    finally:
        db.close()
        engine.dispose()


def test_documents_upload_contract_is_async_admin_draft():
    from api import app
    from src.deps import require_admin

    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/documents/upload" and "POST" in route.methods
    )
    assert route.status_code == 202
    assert require_admin in {item.call for item in route.dependant.dependencies}
