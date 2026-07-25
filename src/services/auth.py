"""
认证服务 - JWT令牌生成、密码哈希、用户认证
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import settings
from src.models.user import User

logger = logging.getLogger(__name__)

# bcrypt密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对密码进行bcrypt哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, username: str) -> str:
    """
    创建JWT访问令牌

    Args:
        user_id: 用户ID
        username: 用户名

    Returns:
        str: JWT token字符串
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
    }
    token = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码JWT令牌

    Args:
        token: JWT token字符串

    Returns:
        dict或None: 解码后的payload，失败返回None
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT解码失败: {e}")
        return None


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名查找用户"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """根据邮箱查找用户"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """根据ID查找用户"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, username: str, email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
    """
    创建新用户

    Args:
        db: 数据库会话
        username: 用户名
        email: 邮箱
        password: 明文密码

    Returns:
        Tuple[User或None, 错误信息或None]
    """
    # 检查用户名是否已存在
    if get_user_by_username(db, username):
        return None, "用户名已存在"

    # 检查邮箱是否已存在
    if get_user_by_email(db, email):
        return None, "邮箱已被注册"

    try:
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"新用户注册: {username} (id={user.id})")
        return user, None
    except Exception as e:
        db.rollback()
        logger.error(f"创建用户失败: {e}")
        return None, f"注册失败: {str(e)}"


def authenticate_user(db: Session, username: str, password: str) -> Tuple[Optional[User], Optional[str]]:
    """
    验证用户登录

    Args:
        db: 数据库会话
        username: 用户名
        password: 明文密码

    Returns:
        Tuple[User或None, 错误信息或None]
    """
    user = get_user_by_username(db, username)
    if not user:
        return None, "用户名或密码错误"

    if not verify_password(password, user.password_hash):
        return None, "用户名或密码错误"

    return user, None
