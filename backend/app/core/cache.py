"""
Redis 缓存管理器

提供异步缓存功能，支持装饰器模式和手动缓存管理
"""

import json
import hashlib
from typing import Any, Optional, Callable, Union
from functools import wraps
from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings


class CacheManager:
    """Redis 缓存管理器"""

    def __init__(self):
        """初始化缓存管理器"""
        self._redis: Optional[aioredis.Redis] = None
        self._enabled = settings.REDIS_ENABLED

    async def _get_redis(self) -> Optional[aioredis.Redis]:
        """获取 Redis 连接（懒加载）"""
        if not self._enabled:
            return None

        if self._redis is None:
            try:
                self._redis = await aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
                # 测试连接
                await self._redis.ping()
            except (RedisError, Exception) as e:
                print(f"Redis connection failed: {e}. Caching disabled.")
                self._enabled = False
                self._redis = None

        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在返回 None
        """
        redis = await self._get_redis()
        if redis is None:
            return None

        try:
            value = await redis.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (RedisError, json.JSONDecodeError) as e:
            print(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 表示使用默认值

        Returns:
            是否设置成功
        """
        redis = await self._get_redis()
        if redis is None:
            return False

        if ttl is None:
            ttl = settings.CACHE_DEFAULT_TTL

        try:
            serialized = json.dumps(value, default=str, ensure_ascii=False)
            await redis.setex(key, ttl, serialized)
            return True
        except (RedisError, TypeError) as e:
            print(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        redis = await self._get_redis()
        if redis is None:
            return False

        try:
            await redis.delete(key)
            return True
        except RedisError as e:
            print(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有缓存键

        Args:
            pattern: 匹配模式（支持 * 和 ? 通配符）

        Returns:
            删除的键数量
        """
        redis = await self._get_redis()
        if redis is None:
            return 0

        try:
            keys = []
            async for key in redis.scan_iter(match=pattern, count=100):
                keys.append(key)

            if keys:
                await redis.delete(*keys)
            return len(keys)
        except RedisError as e:
            print(f"Cache delete_pattern error for pattern {pattern}: {e}")
            return 0

    async def get_or_set(
        self, key: str, factory: Callable, ttl: Optional[int] = None
    ) -> Any:
        """
        获取缓存，如果不存在则调用 factory 生成并缓存

        Args:
            key: 缓存键
            factory: 生成值的异步函数
            ttl: 过期时间（秒）

        Returns:
            缓存值或新生成的值
        """
        cached = await self.get(key)
        if cached is not None:
            return cached

        value = await factory()
        await self.set(key, value, ttl)
        return value

    async def exists(self, key: str) -> bool:
        """
        检查缓存键是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        redis = await self._get_redis()
        if redis is None:
            return False

        try:
            return await redis.exists(key) > 0
        except RedisError as e:
            print(f"Cache exists error for key {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """
        获取缓存键的剩余过期时间

        Args:
            key: 缓存键

        Returns:
            剩余秒数，-1 表示永不过期，-2 表示键不存在
        """
        redis = await self._get_redis()
        if redis is None:
            return -2

        try:
            return await redis.ttl(key)
        except RedisError as e:
            print(f"Cache get_ttl error for key {key}: {e}")
            return -2

    async def close(self):
        """关闭 Redis 连接"""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    def _make_cache_key(
        self, prefix: str, func_name: str, args: tuple, kwargs: dict
    ) -> str:
        """
        生成缓存键

        Args:
            prefix: 键前缀
            func_name: 函数名
            args: 位置参数
            kwargs: 关键字参数

        Returns:
            缓存键
        """
        # 过滤掉 self 参数
        filtered_args = args[1:] if args and hasattr(args[0], '__class__') else args

        # 创建参数的哈希值（避免键过长）
        arg_str = f"{filtered_args}:{sorted(kwargs.items())}"
        arg_hash = hashlib.md5(arg_str.encode()).hexdigest()[:16]

        return f"{prefix}:{func_name}:{arg_hash}"

    def cached(
        self, ttl: Optional[int] = None, key_prefix: str = ""
    ) -> Callable:
        """
        缓存装饰器

        Args:
            ttl: 过期时间（秒）
            key_prefix: 键前缀

        Returns:
            装饰器函数

        Example:
            @cache.cached(ttl=300, key_prefix="stock_list")
            async def get_stock_list(self, market: str = None):
                # ... 业务逻辑
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 如果缓存未启用，直接调用原函数
                if not self._enabled:
                    return await func(*args, **kwargs)

                # 生成缓存键
                cache_key = self._make_cache_key(
                    key_prefix or func.__name__, func.__name__, args, kwargs
                )

                # 尝试从缓存获取
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # 调用原函数
                result = await func(*args, **kwargs)

                # 缓存结果
                await self.set(cache_key, result, ttl)

                return result

            return wrapper

        return decorator


# 全局缓存实例
cache = CacheManager()
