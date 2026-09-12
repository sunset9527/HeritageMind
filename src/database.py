"""
数据库层 - SQLAlchemy引擎与会话管理

支持 MySQL / SQLite / PostgreSQL，通过 config.py 的 DATABASE_URL 切换。
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)

# 创建数据库引擎
connect_args = {}
engine_kwargs = {}

if "sqlite" in settings.database_url:
    connect_args["check_same_thread"] = False
elif "mysql" in settings.database_url:
    # MySQL 字符集和连接池配置
    connect_args["charset"] = "utf8mb4"
    engine_kwargs["pool_size"] = 10
    engine_kwargs["pool_recycle"] = 3600
    engine_kwargs["max_overflow"] = 20

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,
    **engine_kwargs,
)

# 会话工厂
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy声明式基类"""
    pass


def init_db():
    """
    初始化数据库，创建所有表。
    开发阶段使用，生产环境应使用Alembic迁移。
    """
    from src.models import (  # noqa: F401 - 确保模型被注册
        User, ChatHistory, AnswerEvaluation, UserFeedback, AgentConfiguration,
    )
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")


def get_db():
    """
    获取数据库会话（FastAPI依赖注入用）。
    用法: db = next(get_db())
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
