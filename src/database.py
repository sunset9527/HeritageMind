"""
数据库层 - SQLAlchemy引擎与会话管理

本地开发使用SQLite，生产环境使用PostgreSQL。
通过config.py中的DATABASE_URL统一配置。
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)

# 创建数据库引擎
# SQLite需要check_same_thread=False以支持多线程访问（Streamlit场景）
connect_args = {}
if "sqlite" in settings.database_url:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,  # 连接前检测有效性
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
    from src.models import User, ChatHistory  # noqa: F401 - 确保模型被注册
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
