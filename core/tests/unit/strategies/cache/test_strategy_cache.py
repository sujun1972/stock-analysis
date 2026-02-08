"""
测试 StrategyCache 和 CodeCache
"""

import pytest
from datetime import timedelta
from unittest.mock import Mock
from src.strategies.cache.strategy_cache import StrategyCache, CodeCache


class TestStrategyCache:
    """测试 StrategyCache"""

    @pytest.fixture
    def cache(self):
        """创建缓存实例"""
        return StrategyCache(ttl_minutes=1)

    def test_init(self, cache):
        """测试初始化"""
        assert cache._memory_cache == {}
        assert cache._cache_timestamps == {}
        assert cache.redis is None
        assert cache.ttl == timedelta(minutes=1)

    def test_set_and_get(self, cache):
        """测试设置和获取"""
        # 设置
        cache.set('key1', 'value1')

        # 获取
        value = cache.get('key1')
        assert value == 'value1'

    def test_get_nonexistent(self, cache):
        """测试获取不存在的键"""
        value = cache.get('nonexistent')
        assert value is None

    def test_cache_expiration(self, cache):
        """测试缓存过期"""
        # 设置非常短的TTL
        cache.ttl = timedelta(seconds=0)

        cache.set('key1', 'value1')

        # 应该已经过期
        value = cache.get('key1')
        assert value is None

    def test_invalidate(self, cache):
        """测试使缓存失效"""
        cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'

        cache.invalidate('key1')
        assert cache.get('key1') is None

    def test_clear(self, cache):
        """测试清除所有缓存"""
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        cache.clear()

        assert cache.get('key1') is None
        assert cache.get('key2') is None
        assert len(cache._memory_cache) == 0

    def test_get_stats(self, cache):
        """测试获取统计信息"""
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        stats = cache.get_stats()

        assert stats['total_keys'] == 2
        assert stats['valid_keys'] == 2
        assert stats['expired_keys'] == 0
        assert stats['ttl_minutes'] == 1.0
        assert stats['redis_enabled'] is False

    def test_cleanup_expired(self, cache):
        """测试清理过期缓存"""
        # 设置短TTL
        cache.ttl = timedelta(seconds=0)

        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # 现在都应该过期了
        cache.cleanup_expired()

        assert len(cache._memory_cache) == 0
        assert len(cache._cache_timestamps) == 0

    def test_repr(self, cache):
        """测试字符串表示"""
        cache.set('key1', 'value1')

        repr_str = repr(cache)
        assert 'StrategyCache' in repr_str
        assert 'valid=' in repr_str
        assert 'ttl=' in repr_str


class TestCodeCache:
    """测试 CodeCache"""

    @pytest.fixture
    def cache(self):
        """创建代码缓存实例"""
        return CodeCache(max_size=3)

    def test_init(self, cache):
        """测试初始化"""
        assert cache._cache == {}
        assert cache._access_count == {}
        assert cache.max_size == 3

    def test_set_and_get(self, cache):
        """测试设置和获取"""
        module = Mock()

        cache.set('hash1', module)
        assert cache.get('hash1') is module

    def test_get_nonexistent(self, cache):
        """测试获取不存在的模块"""
        assert cache.get('nonexistent') is None

    def test_access_count(self, cache):
        """测试访问计数"""
        module = Mock()
        cache.set('hash1', module)

        # 第一次访问
        cache.get('hash1')
        assert cache._access_count['hash1'] == 2  # set时为1，get时+1

        # 第二次访问
        cache.get('hash1')
        assert cache._access_count['hash1'] == 3

    def test_eviction(self, cache):
        """测试缓存淘汰"""
        # 填满缓存
        cache.set('hash1', Mock())
        cache.set('hash2', Mock())
        cache.set('hash3', Mock())

        # 增加访问次数，使hash1最少使用
        cache.get('hash2')
        cache.get('hash3')

        # 添加第4个，应该淘汰hash1
        cache.set('hash4', Mock())

        assert 'hash1' not in cache._cache
        assert 'hash2' in cache._cache
        assert 'hash3' in cache._cache
        assert 'hash4' in cache._cache

    def test_invalidate(self, cache):
        """测试使缓存失效"""
        module = Mock()
        cache.set('hash1', module)

        cache.invalidate('hash1')

        assert cache.get('hash1') is None

    def test_clear(self, cache):
        """测试清除所有缓存"""
        cache.set('hash1', Mock())
        cache.set('hash2', Mock())

        cache.clear()

        assert len(cache._cache) == 0
        assert len(cache._access_count) == 0

    def test_get_stats(self, cache):
        """测试获取统计信息"""
        cache.set('hash1', Mock())
        cache.set('hash2', Mock())
        cache.get('hash1')  # 增加访问次数

        stats = cache.get_stats()

        assert stats['total_modules'] == 2
        assert stats['max_size'] == 3
        assert stats['usage_rate'] == pytest.approx(2/3)
        assert stats['total_accesses'] == 3  # 2次set + 1次get

    def test_repr(self, cache):
        """测试字符串表示"""
        cache.set('hash1', Mock())

        repr_str = repr(cache)
        assert 'CodeCache' in repr_str
        assert 'size=1/3' in repr_str
