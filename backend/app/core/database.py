"""
数据库连接和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import Generator, AsyncGenerator
from contextlib import asynccontextmanager

from app.core.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 连接池预检查
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 最大溢出连接数
    echo=settings.is_development,  # 开发环境打印SQL
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话

    Yields:
        Session: SQLAlchemy数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 创建异步数据库引擎
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.is_development,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession
)


def reset_async_engine():
    """
    重新初始化异步数据库引擎和会话工厂

    用于 Celery fork pool worker 中解决事件循环冲突问题。
    当全局的 async_engine 绑定到父进程的事件循环时，
    fork 出的子进程必须重新创建引擎以使用新的事件循环。

    Note:
        此函数应该在创建新事件循环后立即调用，确保数据库引擎
        绑定到正确的事件循环。
    """
    global async_engine, AsyncSessionLocal

    # 创建新的异步引擎（旧引擎会在进程退出时自动清理）
    async_engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.is_development,
    )

    # 重新创建会话工厂
    AsyncSessionLocal = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=async_engine,
        class_=AsyncSession
    )


@asynccontextmanager
async def get_async_db():
    """
    获取异步数据库会话（上下文管理器）

    Usage:
        async with get_async_db() as db:
            result = await db.execute(query)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
