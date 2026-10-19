"""阶段 1A 公共媒体只能读取已发布内容。"""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import api
from src.database import Base
from src.models.media import MediaDocument, MediaType
from src.retrieval import multimodal_search


def _resolve(coroutine):
    """运行不包含异步 I/O 的路由函数，避免 Windows 沙箱创建 socketpair。"""
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return completed.value
    raise AssertionError("测试路由意外执行了异步 I/O")


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all(
        [
            MediaDocument(
                craft_name="景泰蓝",
                media_type=MediaType.IMAGE,
                filename="published.jpg",
                original_name="published.jpg",
                mime_type="image/jpeg",
                size=10,
                title="已发布图片",
                status="published",
            ),
            MediaDocument(
                craft_name="景泰蓝",
                media_type=MediaType.IMAGE,
                filename="draft.jpg",
                original_name="draft.jpg",
                mime_type="image/jpeg",
                size=10,
                title="草稿图片",
                status="draft",
            ),
        ]
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_public_media_list_returns_only_published_rows(db):
    response = _resolve(api.list_media_files(db=db))

    assert response.total == 1
    assert [item.filename for item in response.items] == ["published.jpg"]


def test_admin_media_list_returns_all_rows(db):
    response = _resolve(api.list_admin_media_files(db=db))

    assert response.total == 2
    assert {item.filename for item in response.items} == {"published.jpg", "draft.jpg"}
    by_filename = {item.filename: item for item in response.items}
    assert by_filename["published.jpg"].url == "/media/file/image/published.jpg"
    assert by_filename["draft.jpg"].url == ""


def test_public_media_detail_hides_draft_as_not_found(db):
    draft_id = db.query(MediaDocument.id).filter_by(filename="draft.jpg").scalar()

    with pytest.raises(HTTPException) as exc_info:
        _resolve(api.get_media_file(draft_id, db=db))

    assert exc_info.value.status_code == 404


def test_public_media_detail_returns_published_row(db):
    published_id = db.query(MediaDocument.id).filter_by(filename="published.jpg").scalar()

    response = _resolve(api.get_media_file(published_id, db=db))

    assert response.filename == "published.jpg"


def test_public_media_file_hides_draft_and_serves_published(db, tmp_path, monkeypatch):
    media_root = tmp_path / "media"
    image_root = media_root / "image"
    image_root.mkdir(parents=True)
    (image_root / "draft.jpg").write_bytes(b"draft")
    (image_root / "published.jpg").write_bytes(b"published")
    monkeypatch.setattr(api, "STORAGE_ROOT", media_root)

    with pytest.raises(HTTPException) as exc_info:
        _resolve(api.serve_media_file("image", "draft.jpg", db=db))
    assert exc_info.value.status_code == 404

    published = _resolve(api.serve_media_file("image", "published.jpg", db=db))
    assert published.path == str(image_root / "published.jpg")
    assert (image_root / "published.jpg").read_bytes() == b"published"


def test_public_image_searches_exclude_drafts(db, monkeypatch):
    from src.retrieval import image_embeddings

    monkeypatch.setattr(multimodal_search, "_get_embedding", lambda _text: None)
    monkeypatch.setattr(image_embeddings, "image_to_embedding", lambda _content: None)

    text_results = multimodal_search.search_images_by_text(db, "景泰蓝", top_k=10)
    similar_results = multimodal_search.search_similar_images(db, b"not-an-image", top_k=10)

    assert [result["id"] for result in text_results] == [
        db.query(MediaDocument.id).filter_by(filename="published.jpg").scalar()
    ]
    assert [result["id"] for result in similar_results] == [
        db.query(MediaDocument.id).filter_by(filename="published.jpg").scalar()
    ]


def test_public_audio_search_excludes_drafts(db, monkeypatch):
    published = MediaDocument(
        craft_name="昆曲",
        media_type=MediaType.AUDIO,
        filename="published.wav",
        original_name="published.wav",
        mime_type="audio/wav",
        size=10,
        title="已发布访谈",
        status="published",
    )
    draft = MediaDocument(
        craft_name="昆曲",
        media_type=MediaType.AUDIO,
        filename="draft.wav",
        original_name="draft.wav",
        mime_type="audio/wav",
        size=10,
        title="草稿访谈",
        status="draft",
    )
    db.add_all([published, draft])
    db.commit()

    class FakeAudioStore:
        def search(self, *_args, **_kwargs):
            return [
                {
                    "media_id": published.id,
                    "craft_name": "昆曲",
                    "title": published.title,
                    "snippet": "已发布内容",
                    "score": 0.9,
                },
                {
                    "media_id": draft.id,
                    "craft_name": "昆曲",
                    "title": draft.title,
                    "snippet": "草稿内容",
                    "score": 0.8,
                },
            ]

    monkeypatch.setattr(api, "get_audio_store", lambda: FakeAudioStore())

    response = _resolve(api.search_audio("访谈", top_k=10, db=db))

    assert response.total == 1
    assert [result.media_id for result in response.results] == [published.id]
