"""v1.5 MySQL 会话持久化测试（SQLite 内存数据库，零网络）。"""

import importlib.util
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models import ChatHistory, ChatSession, UserPreference  # noqa: F401 - register metadata
import src.services.session_memory as session_memory


def test_session_memory_service_module_is_available():
    """会话职责必须从现有聊天历史服务中拆出独立模块。"""
    assert importlib.util.find_spec("src.services.session_memory") is not None


def test_session_memory_exposes_session_creation_boundary():
    """调用方只应通过 create_session 创建归属明确的会话。"""
    assert callable(getattr(session_memory, "create_session", None))


def test_create_session_persists_owned_title():
    """首轮提问应创建可归属用户、可展示的会话记录。"""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    session = session_memory.create_session(db, user_id=7, first_question="介绍昆曲的历史")

    assert session.user_id == 7
    assert session.title == "介绍昆曲的历史"
    assert len(session.id) == 36
    assert db.get(ChatSession, session.id).id == session.id


def test_conversation_context_keeps_recent_turns_in_time_order():
    """记忆只保留当前会话最近四轮，并按用户可读的时间顺序传给工作流。"""
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    session = session_memory.create_session(db, user_id=7, first_question="介绍昆曲")
    now = datetime.now(timezone.utc)
    for index in range(5):
        db.add(ChatHistory(
            user_id=7,
            session_id=session.id,
            question=f"问题{index}",
            answer=f"回答{index}",
            user_profile="curious",
            created_at=now + timedelta(seconds=index),
        ))
    db.commit()

    context = session_memory.get_conversation_context(db, session.id, user_id=7)

    assert "问题0" not in context
    assert context.index("问题1") < context.index("问题4")
    assert "用户：问题4" in context
    assert "助手：回答4" in context


def test_preferences_keep_known_crafts_and_learn_selected_profile():
    """偏好仅吸收标准技艺，并从显式学习深度选择得出稳定默认值。"""
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    pref = session_memory.update_user_preferences(
        db, user_id=7, craft_names=["景泰蓝", "不存在的技艺"], user_profile="learner"
    )
    pref = session_memory.update_user_preferences(
        db, user_id=7, craft_names=["苏绣", "景泰蓝"], user_profile="learner"
    )

    assert pref.preferred_crafts == ["景泰蓝", "苏绣"]
    assert pref.preferred_profile == "learner"
    assert pref.profile_scores["learner"] == 2
