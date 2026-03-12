"""
Redis 分布式锁工具

用于防止并发执行相同的任务
"""

import redis
import time
from contextlib import contextmanager
from typing import Optional
from loguru import logger

from app.core.config import settings


class RedisLock:
    """Redis 分布式锁"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    @contextmanager
    def acquire(
        self,
        lock_key: str,
        timeout: int = 300,  # 锁超时时间（秒）
        blocking: bool = True,  # 是否阻塞等待
        blocking_timeout: Optional[int] = 10  # 阻塞等待超时（秒）
    ):
        """
        获取分布式锁

        Args:
            lock_key: 锁的键名
            timeout: 锁的过期时间（防止死锁）
            blocking: 是否阻塞等待锁释放
            blocking_timeout: 阻塞等待的最长时间

        Yields:
            是否成功获取锁

        Example:
            with redis_lock.acquire('my_task:2024-01-01') as acquired:
                if acquired:
                    # 执行任务
                    pass
                else:
                    # 锁已被占用
                    logger.warning("任务正在执行中")
        """
        lock_value = f"{time.time()}"  # 使用时间戳作为锁值
        acquired = False

        try:
            if blocking:
                # 阻塞模式：循环等待直到获取锁或超时
                start_time = time.time()
                while True:
                    # 尝试设置锁（NX=只在不存在时设置，EX=设置过期时间）
                    acquired = self.redis.set(
                        lock_key,
                        lock_value,
                        nx=True,
                        ex=timeout
                    )

                    if acquired:
                        logger.debug(f"成功获取锁: {lock_key}")
                        break

                    # 检查是否超时
                    if blocking_timeout and (time.time() - start_time) > blocking_timeout:
                        logger.warning(f"等待锁超时: {lock_key}")
                        break

                    # 等待一小段时间后重试
                    time.sleep(0.5)
            else:
                # 非阻塞模式：尝试一次
                acquired = self.redis.set(
                    lock_key,
                    lock_value,
                    nx=True,
                    ex=timeout
                )
                if acquired:
                    logger.debug(f"成功获取锁: {lock_key}")
                else:
                    logger.debug(f"锁已被占用: {lock_key}")

            yield acquired

        finally:
            # 释放锁（只有持有锁的进程才能释放）
            if acquired:
                try:
                    # 使用 Lua 脚本确保原子性删除
                    lua_script = """
                    if redis.call("get", KEYS[1]) == ARGV[1] then
                        return redis.call("del", KEYS[1])
                    else
                        return 0
                    end
                    """
                    self.redis.eval(lua_script, 1, lock_key, lock_value)
                    logger.debug(f"释放锁: {lock_key}")
                except Exception as e:
                    logger.error(f"释放锁失败: {lock_key}, 错误: {e}")


# 创建全局 Redis 客户端和锁实例
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=2,  # 使用 DB 2 存储锁信息
        decode_responses=True,
        socket_connect_timeout=5
    )
    redis_lock = RedisLock(redis_client)
    logger.info("✅ Redis 分布式锁初始化成功")
except Exception as e:
    logger.error(f"❌ Redis 分布式锁初始化失败: {e}")
    redis_lock = None
