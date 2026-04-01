"""
数据库连接和会话管理

连接池容量规划（PostgreSQL max_connections=200）：
  同步引擎：pool_size=5, max_overflow=10  -> 最多 15 个连接
  异步引擎：pool_size=5, max_overflow=10  -> 最多 15 个连接
  Core psycopg2 池：min=2, max=20         -> 最多 20 个连接
  ─────────────────────────────────────────────────────
  三套合计上限：约 50 个，远低于数据库限制 200，留有充足余量。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import Generator
from contextlib import asynccontextmanager

from app.core.config import settings

# 连接池参数常量——三处引擎共用，修改一处即全局生效
_POOL_SIZE = 5
_MAX_OVERFLOW = 10

# 创建同步数据库引擎（供 Repository 层同步调用）
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=_POOL_SIZE,
    max_overflow=_MAX_OVERFLOW,
    echo=settings.is_development,
)

# 创建同步会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：获取同步数据库会话，用完自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 创建异步数据库引擎（供 async Service/endpoint 调用）
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    pool_size=_POOL_SIZE,
    max_overflow=_MAX_OVERFLOW,
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
    在 Celery fork pool worker 中重新初始化异步引擎。

    fork 出的子进程继承了父进程的 async_engine，但该引擎绑定到父进程
    的事件循环，在子进程中使用会触发 "attached to a different loop" 错误。
    此函数在子进程创建新事件循环后立即调用，确保引擎绑定到正确的循环。
    """
    global async_engine, AsyncSessionLocal

    async_engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        pool_pre_ping=True,
        pool_size=_POOL_SIZE,
        max_overflow=_MAX_OVERFLOW,
        echo=settings.is_development,
    )

    AsyncSessionLocal = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=async_engine,
        class_=AsyncSession
    )


@asynccontextmanager
async def get_async_db():
    """
    获取异步数据库会话（上下文管理器）。

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
