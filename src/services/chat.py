"""
聊天历史服务 - 保存与检索聊天记录
"""

import logging
from typing import Optional, List, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.models.chat import ChatHistory

logger = logging.getLogger(__name__)


def save_chat_history(
    db: Session,
    user_id: int,
    question: str,
    answer: str,
    user_profile: str = "curious",
    agents_used: Optional[List[str]] = None,
    has_gaps: bool = False,
    session_id: Optional[str] = None,
) -> ChatHistory:
    """
    保存聊天历史记录

    Args:
        db: 数据库会话
        user_id: 用户ID
        question: 用户问题
        answer: 系统回答
        user_profile: 用户画像
        agents_used: 参与的Agent列表
        has_gaps: 是否存在知识缺口

    Returns:
        ChatHistory: 保存的记录
    """
    chat = ChatHistory(
        user_id=user_id,
        question=question,
        answer=answer,
        user_profile=user_profile,
        agents_used=agents_used or [],
        has_gaps=has_gaps,
        session_id=session_id,
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    logger.info(f"聊天历史已保存: user_id={user_id}, chat_id={chat.id}")
    return chat


def get_user_history(
    db: Session,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> List[ChatHistory]:
    """
    获取用户的聊天历史（按时间倒序）

    Args:
        db: 数据库会话
        user_id: 用户ID
        limit: 每页条数
        offset: 偏移量

    Returns:
        List[ChatHistory]: 聊天历史列表
    """
    return (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .order_by(desc(ChatHistory.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_user_history_count(db: Session, user_id: int) -> int:
    """获取用户聊天历史总数"""
    return (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .count()
    )


def get_chat_detail(db: Session, chat_id: int, user_id: int) -> Optional[ChatHistory]:
    """
    获取单条聊天详情（仅允许查看自己的记录）

    Args:
        db: 数据库会话
        chat_id: 聊天记录ID
        user_id: 用户ID（用于权限校验）

    Returns:
        ChatHistory或None
    """
    return (
        db.query(ChatHistory)
        .filter(ChatHistory.id == chat_id, ChatHistory.user_id == user_id)
        .first()
    )
