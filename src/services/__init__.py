"""
服务层包
"""

from src.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_user_by_username,
    get_user_by_email,
    get_user_by_id,
    create_user,
    authenticate_user,
)
from src.services.chat import (
    save_chat_history,
    get_user_history,
    get_user_history_count,
    get_chat_detail,
)
from src.services.session_memory import (
    create_session,
    get_session_for_user,
    get_conversation_context,
    get_session_turns,
    list_user_sessions,
    update_user_preferences,
)

__all__ = [
    # Auth
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "get_user_by_username",
    "get_user_by_email",
    "get_user_by_id",
    "create_user",
    "authenticate_user",
    # Chat
    "save_chat_history",
    "get_user_history",
    "get_user_history_count",
    "get_chat_detail",
    "create_session",
    "get_session_for_user",
    "get_conversation_context",
    "get_session_turns",
    "list_user_sessions",
    "update_user_preferences",
]
