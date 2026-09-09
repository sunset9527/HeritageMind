"""
FastAPI 依赖注入 - 数据库会话、当前用户认证

提供可复用的依赖函数，供API端点使用。
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.services.auth import decode_access_token, get_user_by_id
from src.models.user import User

logger = logging.getLogger(__name__)

# OAuth2密码流认证 — token从 /auth/login 获取
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_db():
    """
    获取数据库会话依赖。
    每次API请求自动创建和关闭会话。

    用法:
        @app.get("/something")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    从JWT token解析当前登录用户。

    用于需要认证的端点：
        @app.get("/auth/me")
        def me(current_user: User = Depends(get_current_user)):
            ...

    Raises:
        HTTPException 401: token无效或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证身份凭证，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # auto_error=False 后，token 可能为 None（未携带 Authorization header）
    if token is None:
        raise credentials_exception

    # 解码JWT
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # 提取用户ID
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    # 查找用户
    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    return user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    可选的当前用户——token不存在时不报错，返回None。

    用于"登录可选"的端点（如/query——未登录也能用，但登录后自动保存历史）。
    """
    if token is None:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        return None

    return get_user_by_id(db, user_id)
