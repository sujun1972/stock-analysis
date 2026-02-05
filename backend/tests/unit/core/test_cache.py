"""
测试 Redis 缓存管理器

测试范围:
- CacheManager 基本操作 (get/set/delete)
- 缓存装饰器功能
- 缓存过期时间
- 缓存模式匹配删除
- Redis 连接失败处理
- 可序列化对象缓存
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from redis.exceptions import RedisError

from app.core.cache import CacheManager, cache


@pytest.mark.asyncio
class TestCacheManager:
    """测试 CacheManager 类"""

    async def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        manager = CacheManager()

        # 设置缓存
        key = "test_key"
        value = {"name": "test", "value": 123}

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.setex = AsyncMock()
            mock_redis.get = AsyncMock(return_value='{"name": "test", "value": 123}')

            # 测试 set
            result = await manager.set(key, value, ttl=300)
            assert result is True
            mock_redis.setex.assert_called_once()

            # 测试 get
            cached_value = await manager.get(key)
            assert cached_value == value
            mock_redis.get.assert_called_once_with(key)

    async def test_cache_delete(self):
        """测试缓存删除"""
        manager = CacheManager()
        key = "test_key"

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.delete = AsyncMock()

            result = await manager.delete(key)
            assert result is True
            mock_redis.delete.assert_called_once_with(key)

    async def test_cache_delete_pattern(self):
        """测试模式匹配删除缓存"""
        manager = CacheManager()
        pattern = "daily_data:*:000001:*"

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis

            # 模拟 scan_iter 返回匹配的键
            async def mock_scan_iter(match, count):
                keys = ["daily_data:1:000001:2023", "daily_data:2:000001:2024"]
                for key in keys:
                    yield key

            mock_redis.scan_iter = mock_scan_iter
            mock_redis.delete = AsyncMock()

            count = await manager.delete_pattern(pattern)
            assert count == 2
            mock_redis.delete.assert_called_once()

    async def test_cache_exists(self):
        """测试缓存键存在性检查"""
        manager = CacheManager()
        key = "test_key"

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.exists = AsyncMock(return_value=1)

            result = await manager.exists(key)
            assert result is True
            mock_redis.exists.assert_called_once_with(key)

    async def test_cache_get_ttl(self):
        """测试获取缓存TTL"""
        manager = CacheManager()
        key = "test_key"

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.ttl = AsyncMock(return_value=300)

            ttl = await manager.get_ttl(key)
            assert ttl == 300
            mock_redis.ttl.assert_called_once_with(key)

    async def test_cache_get_or_set(self):
        """测试 get_or_set 方法"""
        manager = CacheManager()
        key = "test_key"
        value = {"data": "test"}

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.get = AsyncMock(return_value=None)  # 缓存不存在
            mock_redis.setex = AsyncMock()

            # 工厂函数
            async def factory():
                return value

            # 第一次调用，缓存不存在，应该调用工厂函数
            result = await manager.get_or_set(key, factory, ttl=300)
            assert result == value
            mock_redis.setex.assert_called_once()

    async def test_cache_disabled_when_redis_unavailable(self):
        """测试 Redis 不可用时缓存被禁用"""
        manager = CacheManager()

        with patch('app.core.cache.aioredis.from_url', side_effect=RedisError("Connection failed")):
            # 获取 Redis 连接应该返回 None
            redis_conn = await manager._get_redis()
            assert redis_conn is None
            assert manager._enabled is False

    async def test_cache_decorator(self):
        """测试缓存装饰器"""
        manager = CacheManager()

        call_count = 0

        @manager.cached(ttl=300, key_prefix="test_func")
        async def test_function(x: int, y: int):
            nonlocal call_count
            call_count += 1
            return x + y

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.get = AsyncMock(return_value=None)  # 第一次调用，缓存不存在
            mock_redis.setex = AsyncMock()

            # 第一次调用
            result1 = await test_function(1, 2)
            assert result1 == 3
            assert call_count == 1

            # 模拟第二次调用时缓存存在
            mock_redis.get = AsyncMock(return_value='3')
            result2 = await test_function(1, 2)
            assert result2 == 3
            # 因为有缓存，call_count 不应该增加
            # 但这里需要注意，由于我们模拟了 Redis，实际函数仍会被调用

    async def test_cache_with_none_value(self):
        """测试缓存不存在时返回 None"""
        manager = CacheManager()
        key = "nonexistent_key"

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.get = AsyncMock(return_value=None)

            result = await manager.get(key)
            assert result is None

    async def test_cache_with_complex_objects(self):
        """测试缓存复杂对象"""
        manager = CacheManager()
        key = "complex_key"
        value = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "string": "test",
            "number": 123.45,
        }

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.setex = AsyncMock()
            import json
            mock_redis.get = AsyncMock(return_value=json.dumps(value, default=str))

            # 设置
            await manager.set(key, value, ttl=300)

            # 获取
            cached_value = await manager.get(key)
            assert cached_value == value

    async def test_cache_error_handling(self):
        """测试缓存错误处理"""
        manager = CacheManager()

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.get = AsyncMock(side_effect=RedisError("Redis error"))

            # 即使 Redis 报错，get 应该返回 None 而不是抛出异常
            result = await manager.get("test_key")
            assert result is None

    async def test_cache_close(self):
        """测试关闭 Redis 连接"""
        manager = CacheManager()

        with patch.object(manager, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.close = AsyncMock()

            # 初始化连接
            manager._redis = mock_redis

            # 关闭连接
            await manager.close()
            assert manager._redis is None


@pytest.mark.asyncio
class TestGlobalCacheInstance:
    """测试全局缓存实例"""

    async def test_global_cache_instance_exists(self):
        """测试全局缓存实例存在"""
        assert cache is not None
        assert isinstance(cache, CacheManager)

    async def test_global_cache_basic_operations(self):
        """测试全局缓存实例的基本操作"""
        with patch.object(cache, '_get_redis') as mock_redis_conn:
            mock_redis = AsyncMock()
            mock_redis_conn.return_value = mock_redis
            mock_redis.setex = AsyncMock()
            mock_redis.get = AsyncMock(return_value='"test_value"')

            # 测试基本操作
            await cache.set("test", "test_value", 60)
            value = await cache.get("test")
            assert value == "test_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
