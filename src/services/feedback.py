"""Feedback persistence with chat ownership enforcement."""

from typing import Literal

from sqlalchemy.orm import Session

from src.models.chat import ChatHistory
from src.models.feedback import UserFeedback


FeedbackSentiment = Literal["up", "down"]


def set_feedback(
    db: Session,
    *,
    user_id: int,
    chat_id: int,
    sentiment: FeedbackSentiment | None,
    comment: str | None,
) -> UserFeedback | None:
    """Upsert or cancel the caller's one feedback record for an owned chat answer."""
    chat = db.query(ChatHistory).filter(ChatHistory.id == chat_id, ChatHistory.user_id == user_id).first()
    if chat is None:
        raise ValueError("聊天记录不存在或无权反馈")
    if sentiment not in {"up", "down", None}:
        raise ValueError("反馈类型无效")
    normalized_comment = (comment or "").strip() or None
    if normalized_comment and len(normalized_comment) > 500:
        raise ValueError("反馈意见不能超过500字")

    feedback = db.query(UserFeedback).filter(
        UserFeedback.user_id == user_id, UserFeedback.chat_id == chat_id
    ).first()
    if sentiment is None:
        if feedback is not None:
            db.delete(feedback)
            db.flush()
        return None
    if feedback is None:
        feedback = UserFeedback(user_id=user_id, chat_id=chat_id, sentiment=sentiment, comment=normalized_comment)
        db.add(feedback)
    else:
        feedback.sentiment = sentiment
        feedback.comment = normalized_comment
    db.flush()
    return feedback
