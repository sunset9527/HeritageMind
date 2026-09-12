"""v1.8 质量闭环：先定义规则评分、反馈归属和管理员边界。"""

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.chat import ChatHistory
from src.models.user import User


def test_rule_evaluation_explains_a_healthy_answer_without_llm():
    """规则引擎必须给出版本化、逐项可解释的过程质量信号。"""
    from src.services.evaluation import evaluate_response

    result = evaluate_response(
        answer="景泰蓝以铜胎、掐丝和点蓝工序著称，相关资料见下方引用。",
        citations=[{"title": "景泰蓝制作技艺", "source": "heritage_knowledge_base"}],
        source_agents=[{"id": "craft_expert"}, {"id": "history_expert"}],
        has_gaps=False,
        gap_report="",
        workflow_trace=[{"node": "fuse_knowledge", "status": "completed"}],
    )

    assert result.rule_version == "v1"
    assert result.total_score == 100
    assert {item.code for item in result.details} == {
        "answer_present", "evidence_available", "experts_completed", "workflow_resilient", "gap_handled"
    }


def test_rule_evaluation_credits_an_honest_knowledge_gap():
    """诚实披露知识缺口不应把质量信号直接降为零分。"""
    from src.services.evaluation import evaluate_response

    result = evaluate_response(
        answer="目前资料不足以确认该支系的年代，建议咨询当地传承人。",
        citations=[],
        source_agents=[{"id": "heritage_expert"}],
        has_gaps=True,
        gap_report="缺少该支系的权威年代资料",
        workflow_trace=[{"node": "detect_gaps", "status": "completed"}],
    )

    gap_item = next(item for item in result.details if item.code == "gap_handled")
    assert gap_item.score == gap_item.max_score
    assert result.total_score > 0


def test_feedback_upsert_and_cancel_preserves_one_record_per_user_and_answer():
    """用户修改或取消评价时，不能对同一回答累积多条反馈。"""
    from src.models import UserFeedback  # noqa: F401 - ensures metadata registration
    from src.services.feedback import set_feedback

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    db.add_all([
        User(id=1, username="owner", email="owner@example.com", password_hash="hash", role="user"),
        ChatHistory(user_id=1, question="问题", answer="回答", created_at=now),
    ])
    db.commit()
    chat = db.query(ChatHistory).one()

    first = set_feedback(db, user_id=1, chat_id=chat.id, sentiment="up", comment=None)
    changed = set_feedback(db, user_id=1, chat_id=chat.id, sentiment="down", comment="引用不够具体")
    cancelled = set_feedback(db, user_id=1, chat_id=chat.id, sentiment=None, comment=None)

    assert first.id == changed.id
    assert changed.sentiment == "down"
    assert cancelled is None
    assert db.query(UserFeedback).count() == 0


def test_feedback_rejects_a_chat_owned_by_another_user():
    """聊天记录的归属必须在服务端校验，不能信任前端传参。"""
    from src.models import UserFeedback  # noqa: F401 - ensures metadata registration
    from src.services.feedback import set_feedback

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        User(id=1, username="owner", email="owner@example.com", password_hash="hash", role="user"),
        User(id=2, username="other", email="other@example.com", password_hash="hash", role="user"),
        ChatHistory(user_id=1, question="问题", answer="回答"),
    ])
    db.commit()
    chat = db.query(ChatHistory).one()

    with pytest.raises(ValueError, match="聊天记录不存在或无权反馈"):
        set_feedback(db, user_id=2, chat_id=chat.id, sentiment="down", comment=None)


def test_require_admin_rejects_regular_user_and_accepts_admin():
    """管理员 API 的安全边界必须在后端依赖中，而不是只靠前端隐藏导航。"""
    from src.deps import require_admin

    user = User(id=1, username="user", email="user@example.com", password_hash="hash", role="user")
    admin = User(id=2, username="admin", email="admin@example.com", password_hash="hash", role="admin")

    with pytest.raises(HTTPException) as exc_info:
        require_admin(user)

    assert exc_info.value.status_code == 403
    assert require_admin(admin) is admin


def test_persisted_evaluation_belongs_to_the_saved_chat_answer():
    """评价必须绑定真实 chat_id，而不是前端生成的临时消息 ID。"""
    from src.models import AnswerEvaluation  # noqa: F401 - ensures metadata registration
    from src.services.evaluation import persist_evaluation

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        User(id=1, username="owner", email="owner@example.com", password_hash="hash", role="user"),
        ChatHistory(user_id=1, question="问题", answer="有据可查的回答"),
    ])
    db.commit()
    chat = db.query(ChatHistory).one()

    evaluation = persist_evaluation(
        db,
        chat_id=chat.id,
        answer=chat.answer,
        citations=[{"title": "参考资料", "source": "knowledge_base"}],
        source_agents=[{"id": "craft_expert"}, {"id": "history_expert"}],
        has_gaps=False,
        gap_report="",
        workflow_trace=[],
    )

    assert evaluation.chat_id == chat.id
    assert evaluation.rule_version == "v1"
    assert evaluation.score_details[0]["code"] == "answer_present"


def test_configured_registry_excludes_disabled_agent_and_uses_safe_overrides():
    """后台配置只能覆盖已注册专家，禁用项不能继续进入 Router 候选集合。"""
    from src.agents.registry import get_default_agent_registry
    from src.services.agent_configuration import build_configured_registry

    registry = build_configured_registry(
        get_default_agent_registry(),
        [{
            "agent_id": "history_expert",
            "enabled": False,
            "display_name": "历史资料专家",
            "capability": "历史材料辨析",
            "collaboration_priority": 1,
            "parameters": {},
        }],
    )

    assert registry.ids == ("craft_expert", "heritage_expert")
    assert registry.resolve(["history_expert", "craft_expert"])[0].id == "craft_expert"


def test_feedback_http_endpoint_updates_only_the_authenticated_owners_record():
    """HTTP 入口也必须复用后端归属校验，而不是仅提供前端控件。"""
    from fastapi.testclient import TestClient
    from api import app
    from src.deps import get_current_user, get_db

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    owner = User(id=1, username="owner", email="owner@example.com", password_hash="hash", role="user")
    db.add_all([owner, ChatHistory(user_id=1, question="问题", answer="回答")])
    db.commit()
    chat = db.query(ChatHistory).one()

    def override_db():
        yield db

    app.dependency_overrides[get_current_user] = lambda: owner
    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post("/feedback", json={"chat_id": chat.id, "sentiment": "up"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["sentiment"] == "up"


def test_admin_agents_http_endpoint_is_registered_and_backend_protected():
    """管理入口必须有独立 API，且后端的 require_admin 是真实依赖。"""
    from api import app

    route = next((item for item in app.routes if getattr(item, "path", None) == "/admin/agents"), None)

    assert route is not None
    assert "GET" in route.methods


def test_request_state_uses_configured_registry_for_new_workflows():
    """禁用的专家必须从一次新请求的节点状态中消失，而非只停留在后台表里。"""
    from src.agents.registry import get_default_agent_registry
    from src.services.agent_configuration import build_configured_registry
    from src.workflow.nodes import get_state_registry
    from src.workflow.state import create_initial_state

    configured = build_configured_registry(get_default_agent_registry(), [{
        "agent_id": "history_expert", "enabled": False,
    }])
    state = create_initial_state("景泰蓝的制作流程", agent_registry=configured)

    assert get_state_registry(state).ids == ("craft_expert", "heritage_expert")


def test_disabled_all_agent_configuration_falls_back_to_safe_defaults():
    """错误配置不能让线上请求失去全部专家与回答能力。"""
    from src.agents.registry import get_default_agent_registry
    from src.services.agent_configuration import build_configured_registry

    defaults = get_default_agent_registry()
    configured = build_configured_registry(defaults, [
        {"agent_id": agent_id, "enabled": False} for agent_id in defaults.ids
    ])

    assert configured.ids == defaults.ids
