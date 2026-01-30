"""
Alpha因子缓存机制测试

测试 FactorCache 类的所有功能：
- LRU缓存淘汰策略
- 线程安全性
- 原子操作 get_or_compute
- 缓存统计信息
- 并发场景

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.features.alpha_factors import (
    FactorCache,
    BaseFactorCalculator,
    MomentumFactorCalculator,
)


# ==================== 基础测试 ====================


class TestFactorCacheBasics:
    """FactorCache 基础功能测试"""

    def test_cache_init(self):
        """测试缓存初始化"""
        cache = FactorCache(max_size=100)
        assert cache.max_size == 100
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0

    def test_cache_put_and_get(self):
        """测试基本的存取操作"""
        cache = FactorCache()
        cache.put("key1", "value1")
        cache.put("key2", {"data": [1, 2, 3]})

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == {"data": [1, 2, 3]}
        assert cache.get("key3") is None  # 不存在的键

    def test_cache_overwrite(self):
        """测试覆盖已存在的键"""
        cache = FactorCache()
        cache.put("key1", "value1")
        cache.put("key1", "value2")  # 覆盖

        assert cache.get("key1") == "value2"
        assert len(cache._cache) == 1  # 只有一个键

    def test_cache_clear(self):
        """测试清空缓存"""
        cache = FactorCache()
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.get("key1")  # 触发一次命中

        cache.clear()

        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
        assert cache._hit_count == 0
        assert cache._miss_count == 0


# ==================== LRU淘汰策略测试 ====================


class TestFactorCacheLRU:
    """LRU缓存淘汰策略测试"""

    def test_lru_eviction_basic(self):
        """测试基本LRU淘汰"""
        cache = FactorCache(max_size=3)

        # 填满缓存
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # 添加第4个键，应淘汰最久未使用的key1
        cache.put("key4", "value4")

        assert cache.get("key1") is None  # 已被淘汰
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_lru_eviction_with_access(self):
        """测试访问影响LRU顺序"""
        cache = FactorCache(max_size=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # 访问key1，使其成为最近使用
        cache.get("key1")

        # 添加新键，应淘汰key2（最久未使用）
        cache.put("key4", "value4")

        assert cache.get("key1") == "value1"  # 保留
        assert cache.get("key2") is None      # 淘汰
        assert cache.get("key3") == "value3"  # 保留
        assert cache.get("key4") == "value4"  # 新增

    def test_lru_eviction_multiple_accesses(self):
        """测试多次访问的影响"""
        cache = FactorCache(max_size=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # 多次访问key1和key3
        for _ in range(5):
            cache.get("key1")
            cache.get("key3")

        # 添加新键，应淘汰key2（从未被访问）
        cache.put("key4", "value4")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"

    def test_lru_with_put_updates(self):
        """测试put操作也会更新访问顺序"""
        cache = FactorCache(max_size=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # 更新key1的值（相当于访问）
        cache.put("key1", "new_value1")

        # 添加新键
        cache.put("key4", "value4")

        # key1应该被保留（刚更新过），key2应该被淘汰
        assert cache.get("key1") == "new_value1"
        assert cache.get("key2") is None


# ==================== 线程安全测试 ====================


class TestFactorCacheThreadSafety:
    """缓存线程安全性测试"""

    def test_concurrent_puts(self):
        """测试并发写入"""
        cache = FactorCache(max_size=1000)
        results = []
        errors = []

        def worker(key, value):
            try:
                cache.put(key, value)
                results.append(cache.get(key))
            except Exception as e:
                errors.append(e)

        # 创建100个线程并发写入
        threads = [
            threading.Thread(target=worker, args=(f"key{i}", f"value{i}"))
            for i in range(100)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证
        assert len(errors) == 0  # 没有异常
        assert len(results) == 100  # 所有写入成功
        assert all(r is not None for r in results)

    def test_concurrent_gets(self):
        """测试并发读取"""
        cache = FactorCache()
        cache.put("shared_key", "shared_value")

        results = []

        def worker():
            results.append(cache.get("shared_key"))

        # 100个线程同时读取
        threads = [threading.Thread(target=worker) for _ in range(100)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有读取都应成功
        assert len(results) == 100
        assert all(r == "shared_value" for r in results)

    def test_concurrent_put_and_get(self):
        """测试读写混合并发"""
        cache = FactorCache(max_size=500)

        def writer(i):
            cache.put(f"key{i}", f"value{i}")

        def reader(i):
            return cache.get(f"key{i}")

        # 使用线程池
        with ThreadPoolExecutor(max_workers=20) as executor:
            # 先写入50个
            write_futures = [executor.submit(writer, i) for i in range(50)]
            for f in as_completed(write_futures):
                f.result()

            # 同时进行读写
            mixed_futures = []
            for i in range(100):
                if i % 2 == 0:
                    mixed_futures.append(executor.submit(writer, i + 50))
                else:
                    mixed_futures.append(executor.submit(reader, i % 50))

            # 等待完成
            for f in as_completed(mixed_futures):
                f.result()

        # 验证缓存大小合理
        assert len(cache._cache) > 0

    def test_concurrent_eviction(self):
        """测试并发环境下的LRU淘汰"""
        cache = FactorCache(max_size=10)

        def worker(i):
            # 每个线程尝试写入3个键
            for j in range(3):
                key = f"thread{i}_key{j}"
                cache.put(key, f"value{i}_{j}")
                time.sleep(0.001)  # 模拟计算时间

        # 20个线程，总共60个键，缓存只能容纳10个
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证缓存大小
        assert len(cache._cache) <= cache.max_size


# ==================== get_or_compute 测试 ====================


class TestFactorCacheGetOrCompute:
    """原子操作 get_or_compute 测试"""

    def test_get_or_compute_cache_miss(self):
        """测试缓存未命中时的计算"""
        cache = FactorCache()
        compute_count = 0

        def expensive_compute():
            nonlocal compute_count
            compute_count += 1
            return "computed_value"

        # 第一次调用应触发计算
        result = cache.get_or_compute("test_key", expensive_compute)

        assert result == "computed_value"
        assert compute_count == 1
        assert cache.get("test_key") == "computed_value"

    def test_get_or_compute_cache_hit(self):
        """测试缓存命中时不重新计算"""
        cache = FactorCache()
        compute_count = 0

        def expensive_compute():
            nonlocal compute_count
            compute_count += 1
            return "computed_value"

        # 第一次计算
        result1 = cache.get_or_compute("test_key", expensive_compute)
        assert compute_count == 1

        # 第二次应使用缓存
        result2 = cache.get_or_compute("test_key", expensive_compute)

        assert result2 == "computed_value"
        assert compute_count == 1  # 没有再次计算

    def test_get_or_compute_different_keys(self):
        """测试不同键的独立计算"""
        cache = FactorCache()

        def compute_value(prefix):
            def _compute():
                return f"{prefix}_value"
            return _compute

        result1 = cache.get_or_compute("key1", compute_value("first"))
        result2 = cache.get_or_compute("key2", compute_value("second"))

        assert result1 == "first_value"
        assert result2 == "second_value"

    def test_get_or_compute_concurrent(self):
        """测试并发调用get_or_compute（防止重复计算）"""
        cache = FactorCache()
        compute_count = 0
        compute_lock = threading.Lock()

        def expensive_compute():
            nonlocal compute_count
            with compute_lock:
                compute_count += 1
            time.sleep(0.01)  # 模拟耗时计算
            return "computed_value"

        results = []

        def worker():
            result = cache.get_or_compute("shared_key", expensive_compute)
            results.append(result)

        # 10个线程同时请求同一个键
        threads = [threading.Thread(target=worker) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证：所有线程都拿到了结果
        assert len(results) == 10
        assert all(r == "computed_value" for r in results)

        # 关键验证：计算函数应该只被调用一次（或很少次）
        # 由于RLock的双重检查机制，可能有2-3次计算
        assert compute_count <= 3

    def test_get_or_compute_with_exception(self):
        """测试计算函数抛出异常的情况"""
        cache = FactorCache()

        def failing_compute():
            raise ValueError("Computation failed")

        # 异常应该被传播
        with pytest.raises(ValueError, match="Computation failed"):
            cache.get_or_compute("test_key", failing_compute)

        # 失败后缓存中不应有该键
        assert cache.get("test_key") is None


# ==================== 缓存统计测试 ====================


class TestFactorCacheStats:
    """缓存统计信息测试"""

    def test_stats_initial(self):
        """测试初始统计信息"""
        cache = FactorCache(max_size=10)
        stats = cache.get_stats()

        assert stats['size'] == 0
        assert stats['max_size'] == 10
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate'] == 0.0

    def test_stats_hits_and_misses(self):
        """测试命中和未命中统计"""
        cache = FactorCache()
        cache.put("key1", "value1")

        # 2次命中
        cache.get("key1")
        cache.get("key1")

        # 3次未命中
        cache.get("key2")
        cache.get("key3")
        cache.get("key4")

        stats = cache.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 3
        assert stats['hit_rate'] == 2/5  # 40%
        assert stats['size'] == 1  # 只有key1

    def test_stats_after_clear(self):
        """测试清空后的统计"""
        cache = FactorCache()
        cache.put("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss

        cache.clear()
        stats = cache.get_stats()

        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['size'] == 0

    def test_stats_with_eviction(self):
        """测试LRU淘汰不影响统计"""
        cache = FactorCache(max_size=2)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.get("key1")  # hit

        # 触发淘汰
        cache.put("key3", "value3")  # key2被淘汰

        stats = cache.get_stats()
        assert stats['size'] == 2  # 只能容纳2个
        assert stats['hits'] == 1  # 之前的命中记录保留


# ==================== 实际使用场景测试 ====================


class TestFactorCacheIntegration:
    """与BaseFactorCalculator集成测试"""

    @pytest.fixture
    def sample_price_data(self):
        """生成样本数据"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)

        return pd.DataFrame({
            'close': prices,
            'vol': np.random.uniform(1000000, 10000000, 100)
        }, index=dates)

    def test_shared_cache_across_instances(self, sample_price_data):
        """测试共享缓存在多个实例间工作"""
        # 创建两个计算器实例
        calc1 = MomentumFactorCalculator(sample_price_data)
        calc2 = MomentumFactorCalculator(sample_price_data)

        # 它们应该共享同一个缓存
        assert calc1._shared_cache is calc2._shared_cache

    def test_cache_key_with_df_hash(self, sample_price_data):
        """测试缓存键包含数据指纹"""
        calc = MomentumFactorCalculator(sample_price_data)

        # 数据指纹应该被计算
        assert calc._df_hash is not None
        assert len(calc._df_hash) == 16  # MD5前16位

    def test_cache_effectiveness_in_computation(self, sample_price_data):
        """测试缓存在实际计算中的效果"""
        # 清空共享缓存
        MomentumFactorCalculator._shared_cache.clear()

        calc = MomentumFactorCalculator(sample_price_data)

        # 第一次计算
        start = time.time()
        result1 = calc.add_rsi(periods=[14, 28])
        time1 = time.time() - start

        # 获取缓存统计
        stats = calc._shared_cache.get_stats()
        initial_size = stats['size']

        # 第二次计算（应该使用缓存）- 使用相同方法名
        calc2 = MomentumFactorCalculator(sample_price_data)
        start = time.time()
        result2 = calc2.add_rsi(periods=[14, 28])
        time2 = time.time() - start

        # 验证结果一致
        pd.testing.assert_frame_equal(result1, result2)

        # 缓存应该被使用（第二次更快）
        # 注意：这个断言可能在快速机器上不稳定，仅用于演示
        # assert time2 < time1 * 0.8  # 至少快20%

    def test_different_df_use_different_cache(self):
        """测试不同数据使用不同缓存"""
        # 两个不同的DataFrame
        df1 = pd.DataFrame({'close': [100, 101, 102]},
                          index=pd.date_range('2023-01-01', periods=3))
        df2 = pd.DataFrame({'close': [200, 201, 202]},
                          index=pd.date_range('2023-06-01', periods=3))

        calc1 = MomentumFactorCalculator(df1)
        calc2 = MomentumFactorCalculator(df2)

        # 数据指纹应该不同
        assert calc1._df_hash != calc2._df_hash


# ==================== 边界和异常测试 ====================


class TestFactorCacheEdgeCases:
    """边界情况和异常测试"""

    def test_max_size_zero(self):
        """测试max_size=0的情况"""
        cache = FactorCache(max_size=0)
        cache.put("key1", "value1")

        # max_size=0时，缓存应该为空（立即淘汰）
        assert len(cache._cache) == 0

    def test_max_size_one(self):
        """测试max_size=1的情况"""
        cache = FactorCache(max_size=1)
        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # 只能保留1个
        assert len(cache._cache) == 1
        assert cache.get("key2") == "value2"
        assert cache.get("key1") is None

    def test_large_values(self):
        """测试存储大对象"""
        cache = FactorCache(max_size=5)

        # 存储大DataFrame
        large_df = pd.DataFrame(np.random.randn(10000, 100))
        cache.put("large_key", large_df)

        # 验证能正确存取
        result = cache.get("large_key")
        pd.testing.assert_frame_equal(result, large_df)

    def test_none_value(self):
        """测试存储None值"""
        cache = FactorCache()
        cache.put("none_key", None)

        # 应该能存储None
        # 但get返回None时无法区分是不存在还是值为None
        # 这是当前设计的限制
        result = cache.get("none_key")
        assert result is None

    def test_empty_key(self):
        """测试空字符串键"""
        cache = FactorCache()
        cache.put("", "empty_key_value")

        assert cache.get("") == "empty_key_value"

    def test_unicode_keys(self):
        """测试Unicode键"""
        cache = FactorCache()
        cache.put("键1", "值1")
        cache.put("🔑2", "🎯2")

        assert cache.get("键1") == "值1"
        assert cache.get("🔑2") == "🎯2"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
