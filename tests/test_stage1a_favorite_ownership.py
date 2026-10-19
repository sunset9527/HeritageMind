"""阶段 1A 收藏关联聊天时必须校验资源归属。"""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import api
from src.database import Base
from src.models.chat import ChatHistory
from src.models.chat_session import ChatSession
from src.models.favorite import Favorite
from src.models.user import User


def _resolve(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return completed.value
    raise AssertionError("测试路由意外执行了异步 I/O")


@pytest.fixture()
def favorite_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    owner = User(
        username="owner",
        email="owner@example.com",
        password_hash="hash",
        role="user",
    )
    other = User(
        username="other",
        email="other@example.com",
        password_hash="hash",
        role="user",
    )
    db.add_all([owner, other])
    db.flush()
    chat = ChatHistory(user_id=owner.id, question="问题", answer="回答")
    db.add(chat)
    db.commit()
    try:
        yield db, owner, other, chat
    finally:
        db.close()
        engine.dispose()


def test_owner_can_favorite_own_chat(favorite_context):
    db, owner, _other, chat = favorite_context

    response = _resolve(api.add_favorite(
        craft_name="景泰蓝",
        chat_id=chat.id,
        note="复习",
        current_user=owner,
        db=db,
    ))

    assert response["id"] == db.query(Favorite.id).scalar()
    assert db.query(Favorite).one().chat_id == chat.id


def test_user_cannot_favorite_another_users_chat(favorite_context):
    db, _owner, other, chat = favorite_context

    with pytest.raises(HTTPException) as exc_info:
        _resolve(api.add_favorite(
            craft_name="景泰蓝",
            chat_id=chat.id,
            note="越权",
            current_user=other,
            db=db,
        ))

    assert exc_info.value.status_code == 404
    assert db.query(Favorite).count() == 0


def test_user_cannot_favorite_a_missing_chat(favorite_context):
    db, owner, _other, _chat = favorite_context

    with pytest.raises(HTTPException) as exc_info:
        _resolve(api.add_favorite(
            craft_name="景泰蓝",
            chat_id=99999,
            note="不存在",
            current_user=owner,
            db=db,
        ))

    assert exc_info.value.status_code == 404
    assert db.query(Favorite).count() == 0


def test_favorite_without_chat_remains_supported(favorite_context):
    db, owner, _other, _chat = favorite_context

    _resolve(api.add_favorite(
        craft_name="景泰蓝",
        chat_id=None,
        note="仅收藏技艺",
        current_user=owner,
        db=db,
    ))

    assert db.query(Favorite).one().chat_id is None


def test_chat_detail_and_session_messages_hide_another_users_resources(favorite_context):
    db, owner, other, chat = favorite_context
    session = ChatSession(user_id=owner.id, title="私有会话")
    db.add(session)
    db.flush()
    chat.session_id = session.id
    db.commit()

    with pytest.raises(HTTPException) as detail_error:
        _resolve(api.get_chat_detail_endpoint(chat.id, current_user=other, db=db))
    with pytest.raises(HTTPException) as session_error:
        _resolve(api.get_chat_session_messages(
            session.id,
            current_user=other,
            db=db,
        ))

    assert detail_error.value.status_code == 404
    assert session_error.value.status_code == 404
