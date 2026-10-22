"""媒体上传的文件、数据库与音频 sidecar 事务边界。"""

from pathlib import Path
import re

import pytest
from fastapi import HTTPException
from io import BytesIO
from PIL import Image
from starlette.datastructures import Headers, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.models.audio_transcript import AudioTranscript, AudioTranscriptStatus
from src.models.media import MediaDocument
from src.models.platform import AuditLog
from src.services.upload_security import StagedUpload


def _db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def _staged(root: Path, *, extension: str = ".png", data: bytes = b"safe") -> StagedUpload:
    storage_name = "a" * 32 + extension
    temp_path = root / f"{storage_name}.part"
    root.mkdir(parents=True, exist_ok=True)
    temp_path.write_bytes(data)
    return StagedUpload(
        temp_path=temp_path,
        storage_name=storage_name,
        original_name="../../" if False else f"用户原名{extension}",
        format="png" if extension == ".png" else "mp3",
        extension=extension,
        mime_type="image/png" if extension == ".png" else "audio/mpeg",
        size_bytes=len(data),
        content_sha256="b" * 64,
    )


def _valid_png_upload() -> UploadFile:
    output = BytesIO()
    Image.new("RGB", (2, 2), "blue").save(output, format="PNG")
    return UploadFile(
        BytesIO(output.getvalue()),
        filename="原图.png",
        headers=Headers({"content-type": "image/png"}),
    )


def test_media_upload_publishes_uuid_file_and_commits_draft_with_audit(tmp_path):
    from src.services.media import persist_staged_media

    db, engine = _db()
    try:
        staged = _staged(tmp_path)
        doc = persist_staged_media(
            db,
            staged=staged,
            storage_root=tmp_path,
            craft_id="jingtailan",
            craft_name="景泰蓝",
            media_type="image",
            title="测试图",
            uploaded_by_user_id=7,
        )

        assert re.fullmatch(r"[0-9a-f]{32}\.png", doc.filename)
        assert doc.original_name == "用户原名.png"
        assert doc.craft_id == "jingtailan"
        assert doc.status == "draft"
        assert (tmp_path / "image" / doc.filename).read_bytes() == b"safe"
        assert list((tmp_path / "image").glob("*.part")) == []
        assert db.query(AuditLog).one().action == "media.uploaded"
    finally:
        db.close()
        engine.dispose()


def test_media_upload_creates_audio_sidecar_in_same_commit(tmp_path):
    from src.services.media import persist_staged_media

    db, engine = _db()
    try:
        doc = persist_staged_media(
            db,
            staged=_staged(tmp_path, extension=".mp3"),
            storage_root=tmp_path,
            craft_id="suxiu",
            craft_name="苏绣",
            media_type="audio",
            uploaded_by_user_id=3,
        )

        transcript = db.query(AudioTranscript).filter_by(media_id=doc.id).one()
        assert transcript.status == AudioTranscriptStatus.UPLOADED.value
        assert transcript.attempts == 0
        assert db.query(MediaDocument).count() == 1
        assert db.query(AuditLog).count() == 1
    finally:
        db.close()
        engine.dispose()


def test_media_upload_removes_final_file_when_database_commit_fails(tmp_path, monkeypatch):
    from src.services.media import persist_staged_media

    db, engine = _db()
    staged = _staged(tmp_path)
    monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    try:
        with pytest.raises(RuntimeError, match="db down"):
            persist_staged_media(
                db,
                staged=staged,
                storage_root=tmp_path,
                craft_id="jingtailan",
                craft_name="景泰蓝",
                media_type="image",
                uploaded_by_user_id=1,
            )
        assert list(tmp_path.rglob("*.png")) == []
        assert list(tmp_path.rglob("*.part")) == []
    finally:
        db.close()
        engine.dispose()


def test_media_upload_rolls_back_and_cleans_part_when_atomic_publish_fails(tmp_path, monkeypatch):
    import src.services.media as media_service

    db, engine = _db()
    staged = _staged(tmp_path)
    monkeypatch.setattr(media_service.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("disk")))
    try:
        with pytest.raises(OSError, match="disk"):
            media_service.persist_staged_media(
                db,
                staged=staged,
                storage_root=tmp_path,
                craft_id="jingtailan",
                craft_name="景泰蓝",
                media_type="image",
                uploaded_by_user_id=1,
            )
        assert db.query(MediaDocument).count() == 0
        assert not staged.temp_path.exists()
    finally:
        db.close()
        engine.dispose()


def test_media_endpoint_rejects_conflicting_craft_identity_before_writing(tmp_path, monkeypatch):
    import asyncio
    import api

    db, engine = _db()
    monkeypatch.setattr(api.settings, "media_storage_path", str(tmp_path))
    user = type("Admin", (), {"id": 9})()
    try:
        with pytest.raises(HTTPException) as error:
            asyncio.run(
                api.upload_media_file(
                    file=_valid_png_upload(),
                    craft_id="jingtailan",
                    craft_name="苏绣",
                    media_type="image",
                    title="",
                    current_user=user,
                    db=db,
                )
            )
        assert error.value.status_code == 400
        assert db.query(MediaDocument).count() == 0
        assert list(tmp_path.rglob("*")) == []
    finally:
        db.close()
        engine.dispose()
