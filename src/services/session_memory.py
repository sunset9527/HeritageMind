"""v1.5 MySQL 会话、跨轮上下文与用户偏好服务。"""

from datetime import datetime, timezone
from typing import Iterable, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.models.chat_session import ChatSession
from src.models.chat import ChatHistory
from src.models.user_preference import UserPreference


KNOWN_CRAFTS = (
    "东阳木雕", "剪纸", "京剧", "景德镇瓷器", "景泰蓝", "钧瓷", "缂丝", "龙泉青瓷",
    "苗族蜡染", "木版年画", "南京云锦", "泥人张", "皮影戏", "漆器", "汝瓷", "蜀锦",
    "苏绣", "唐三彩", "芜湖铁画", "宜兴紫砂", "玉雕", "竹编", "壮锦",
)
KNOWN_CRAFT_SET = set(KNOWN_CRAFTS)
KNOWN_PROFILES = {"curious", "learner", "researcher"}
CONTEXT_TURN_LIMIT = 4
CONTEXT_CHAR_LIMIT = 2400
from src.models.chat_session import ChatSession


def create_session(db: Session, user_id: int, first_question: str = "") -> ChatSession:
    """创建一个归属于登录用户的会话。"""
    title = (first_question or "新对话").strip()[:120] or "新对话"
    chat_session = ChatSession(user_id=user_id, title=title)
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session


def get_session_for_user(db: Session, session_id: str, user_id: int) -> Optional[ChatSession]:
    """返回属于当前用户的会话；不存在或越权均返回 ``None``。"""
    return (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )


def list_user_sessions(db: Session, user_id: int, limit: int = 20) -> List[ChatSession]:
    """按最后活跃时间倒序列出用户会话。"""
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.last_active_at))
        .limit(limit)
        .all()
    )


def touch_session(db: Session, chat_session: ChatSession) -> None:
    """刷新会话活跃时间；由保存本轮记录的调用方使用。"""
    chat_session.last_active_at = datetime.now(timezone.utc)
    db.add(chat_session)


def get_session_turns(
    db: Session, session_id: str, user_id: int, limit: int = 50, offset: int = 0
) -> List[ChatHistory]:
    """按正序获取一个已经过归属校验的会话轮次。"""
    if get_session_for_user(db, session_id, user_id) is None:
        return []
    return (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == session_id, ChatHistory.user_id == user_id)
        .order_by(ChatHistory.created_at.asc(), ChatHistory.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_conversation_context(
    db: Session,
    session_id: str,
    user_id: int,
    turn_limit: int = CONTEXT_TURN_LIMIT,
    char_limit: int = CONTEXT_CHAR_LIMIT,
) -> str:
    """把近期轮次压缩为提示词上下文，超长时整轮淘汰最旧记录。"""
    if get_session_for_user(db, session_id, user_id) is None:
        return ""
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == session_id, ChatHistory.user_id == user_id)
        .order_by(desc(ChatHistory.created_at), desc(ChatHistory.id))
        .limit(turn_limit)
        .all()
    )
    rows.reverse()
    rendered = [f"用户：{row.question}\n助手：{row.answer}" for row in rows]
    while rendered and len("\n\n".join(rendered)) > char_limit:
        rendered.pop(0)
    return "\n\n".join(rendered)


def update_user_preferences(
    db: Session,
    user_id: int,
    craft_names: Iterable[str],
    user_profile: Optional[str],
) -> UserPreference:
    """仅从标准技艺和显式画像选择中学习可解释的偏好。"""
    pref = db.get(UserPreference, user_id)
    if pref is None:
        pref = UserPreference(user_id=user_id, preferred_crafts=[], profile_scores={})
        db.add(pref)
        db.flush()

    crafts = list(pref.preferred_crafts or [])
    for raw_name in craft_names or []:
        name = str(raw_name).strip()
        if name in KNOWN_CRAFT_SET and name not in crafts:
            crafts.append(name)
    pref.preferred_crafts = crafts[:5]

    scores = dict(pref.profile_scores or {})
    if user_profile in KNOWN_PROFILES:
        scores[user_profile] = int(scores.get(user_profile, 0)) + 1
        pref.preferred_profile = max(scores, key=scores.get)
    pref.profile_scores = scores
    pref.updated_at = datetime.now(timezone.utc)
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref


def extract_known_crafts(*texts: str) -> List[str]:
    """从用户输入和工作流元数据中提取按项目白名单校验的技艺名称。"""
    merged = "\n".join(text for text in texts if text)
    return [craft for craft in KNOWN_CRAFTS if craft in merged]
