"""
DataFrameMemoryPool 单元测试

测试内容:
- 内存池基本功能（acquire/release）
- 内存重用逻辑
- 线程安全性
- 统计信息准确性
- 作用域内存块（RAII）
- 全局内存池

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import numpy as np
import threading
import time
from typing import List

from src.utils.memory_pool import (
    DataFrameMemoryPool,
    MemoryPoolStats,
    ScopedMemoryBlock,
    get_global_memory_pool,
    reset_global_memory_pool,
    acquire_array,
    release_array,
    get_memory_pool_stats
)


class TestMemoryPoolStats:
    """测试内存池统计信息"""

    def test_reuse_rate_calculation(self):
        """测试重用率计算"""
        stats = MemoryPoolStats(
            total_alloc_count=100,
            total_reuse_count=400
        )

        # 重用率 = 400 / (100 + 400) = 0.8
        assert stats.get_reuse_rate() == 0.8

    def test_reuse_rate_zero_division(self):
        """测试零除处理"""
        stats = MemoryPoolStats(
            total_alloc_count=0,
            total_reuse_count=0
        )

        assert stats.get_reuse_rate() == 0.0

    def test_to_dict(self):
        """测试转换为字典"""
        stats = MemoryPoolStats(
            total_alloc_count=50,
            total_reuse_count=150,
            active_pools=5,
            total_memory_mb=123.45
        )

        result = stats.to_dict()

        assert result['total_allocations'] == 50
        assert result['total_reuses'] == 150
        assert result['reuse_rate'] == 0.75
        assert result['active_pools'] == 5
        assert result['total_memory_mb'] == 123.45


class TestDataFrameMemoryPool:
    """测试DataFrame内存池"""

    def test_initialization(self):
        """测试初始化"""
        pool = DataFrameMemoryPool(max_pools_per_shape=20, enable_stats=True)

        assert pool.max_pools_per_shape == 20
        assert pool.enable_stats is True
        assert len(pool.pools) == 0

    def test_acquire_new_array(self):
        """测试获取新数组"""
        pool = DataFrameMemoryPool()

        arr = pool.acquire(shape=(100, 10), dtype=np.float64)

        assert arr.shape == (100, 10)
        assert arr.dtype == np.float64
        assert pool.stats.total_alloc_count == 1
        assert pool.stats.total_reuse_count == 0

    def test_acquire_with_fill_value(self):
        """测试获取填充数组"""
        pool = DataFrameMemoryPool()

        arr = pool.acquire(shape=(50, 5), fill_value=3.14)

        assert arr.shape == (50, 5)
        assert np.all(arr == 3.14)

    def test_release_and_reuse(self):
        """测试释放和重用"""
        pool = DataFrameMemoryPool(max_pools_per_shape=5)

        # 第一次获取（新建）
        arr1 = pool.acquire(shape=(100, 10))
        assert pool.stats.total_alloc_count == 1

        # 释放
        pool.release(arr1)

        # 第二次获取（重用）
        arr2 = pool.acquire(shape=(100, 10))
        assert pool.stats.total_alloc_count == 1  # 没有增加
        assert pool.stats.total_reuse_count == 1  # 重用了

        # 验证是同一个数组对象
        assert arr2 is arr1

    def test_different_shapes(self):
        """测试不同形状的数组"""
        pool = DataFrameMemoryPool()

        arr1 = pool.acquire(shape=(100, 10))
        arr2 = pool.acquire(shape=(50, 5))
        arr3 = pool.acquire(shape=(100, 10))  # 与arr1相同，但arr1还未释放，需要再分配

        # 应该有3次新分配（两个不同形状各一次，相同形状因未释放再分配一次）
        assert pool.stats.total_alloc_count == 3

        pool.release(arr1)
        pool.release(arr2)

        # 再次获取相同形状
        arr4 = pool.acquire(shape=(100, 10))  # 重用arr1
        arr5 = pool.acquire(shape=(50, 5))  # 重用arr2

        assert pool.stats.total_alloc_count == 3  # 没有新分配
        assert pool.stats.total_reuse_count == 2

    def test_pool_size_limit(self):
        """测试池大小限制"""
        pool = DataFrameMemoryPool(max_pools_per_shape=3)

        # 创建并释放5个相同形状的数组
        arrays = [pool.acquire(shape=(10, 5)) for _ in range(5)]

        for arr in arrays:
            pool.release(arr)

        # 池中只应保留3个（max_pools_per_shape=3）
        key = (10, 5, np.dtype('float64'))
        assert len(pool.pools[key]) == 3

    def test_acquire_like(self):
        """测试acquire_like方法"""
        pool = DataFrameMemoryPool()

        reference = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
        arr = pool.acquire_like(reference, fill_value=0.0)

        assert arr.shape == reference.shape
        assert arr.dtype == reference.dtype
        assert np.all(arr == 0.0)

    def test_clear_all(self):
        """测试清空所有池"""
        pool = DataFrameMemoryPool()

        arr1 = pool.acquire(shape=(100, 10))
        arr2 = pool.acquire(shape=(50, 5))

        pool.release(arr1)
        pool.release(arr2)

        assert len(pool.pools) > 0

        pool.clear()

        assert len(pool.pools) == 0

    def test_clear_specific_shape(self):
        """测试清空特定形状的池"""
        pool = DataFrameMemoryPool()

        arr1 = pool.acquire(shape=(100, 10))
        arr2 = pool.acquire(shape=(50, 5))

        pool.release(arr1)
        pool.release(arr2)

        # 清空(100, 10)形状的池
        pool.clear(shape=(100, 10))

        key1 = (100, 10, np.dtype('float64'))
        key2 = (50, 5, np.dtype('float64'))

        assert key1 not in pool.pools or len(pool.pools[key1]) == 0
        assert key2 in pool.pools and len(pool.pools[key2]) > 0

    def test_invalid_shape(self):
        """测试无效形状"""
        pool = DataFrameMemoryPool()

        # 非元组
        with pytest.raises((ValueError, TypeError)):
            pool.acquire(shape=[100, 10])

        # 不是二维
        with pytest.raises(ValueError):
            pool.acquire(shape=(100,))

        # 负数维度
        with pytest.raises(ValueError):
            pool.acquire(shape=(-10, 5))

        # 零维度
        with pytest.raises(ValueError):
            pool.acquire(shape=(0, 10))

    def test_invalid_array_release(self):
        """测试释放无效数组"""
        pool = DataFrameMemoryPool()

        # 释放None
        pool.release(None)  # 应该不报错，只警告

        # 释放非NumPy数组
        pool.release("not an array")  # 应该不报错，只警告

        # 释放一维数组
        arr_1d = np.array([1, 2, 3])
        pool.release(arr_1d)  # 应该不报错，只警告

    def test_thread_safety(self):
        """测试线程安全"""
        pool = DataFrameMemoryPool(max_pools_per_shape=100)

        results = []
        errors = []

        def worker(worker_id: int):
            try:
                for i in range(50):
                    # 获取数组
                    arr = pool.acquire(shape=(100, 10), fill_value=float(worker_id))

                    # 简单计算
                    arr[:, 0] = arr[:, 0] * 2

                    # 释放数组
                    pool.release(arr)

                results.append(worker_id)
            except Exception as e:
                errors.append((worker_id, e))

        # 启动10个线程
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证
        assert len(errors) == 0, f"线程错误: {errors}"
        assert len(results) == 10

        # 验证统计信息合理性
        stats = pool.get_stats()
        assert stats.total_alloc_count > 0
        assert stats.total_reuse_count > 0

    def test_memory_stats_update(self):
        """测试内存统计更新"""
        pool = DataFrameMemoryPool()

        # 创建一些数组
        arr1 = pool.acquire(shape=(1000, 100), dtype=np.float64)
        arr2 = pool.acquire(shape=(500, 50), dtype=np.float32)

        pool.release(arr1)
        pool.release(arr2)

        stats = pool.get_stats()

        # 验证内存占用被计算
        assert stats.total_memory_mb > 0
        assert stats.active_pools == 2  # 两种不同shape

    def test_repr(self):
        """测试字符串表示"""
        pool = DataFrameMemoryPool()

        arr = pool.acquire(shape=(100, 10))
        pool.release(arr)

        repr_str = repr(pool)

        assert "DataFrameMemoryPool" in repr_str
        assert "allocs=" in repr_str
        assert "reuses=" in repr_str
        assert "reuse_rate=" in repr_str


class TestScopedMemoryBlock:
    """测试作用域内存块"""

    def test_basic_usage(self):
        """测试基本用法"""
        pool = DataFrameMemoryPool()

        with ScopedMemoryBlock(pool, shape=(100, 10)) as arr:
            assert arr.shape == (100, 10)
            arr[:, 0] = 999

        # 退出with块后，数组应该被释放
        # 验证：再次获取应该重用
        stats_before = pool.stats.total_reuse_count
        arr2 = pool.acquire(shape=(100, 10))
        stats_after = pool.stats.total_reuse_count

        assert stats_after == stats_before + 1  # 重用了

    def test_with_fill_value(self):
        """测试填充值"""
        pool = DataFrameMemoryPool()

        with ScopedMemoryBlock(pool, shape=(50, 5), fill_value=3.14) as arr:
            assert np.all(arr == 3.14)

    def test_exception_handling(self):
        """测试异常处理（确保资源释放）"""
        pool = DataFrameMemoryPool()

        try:
            with ScopedMemoryBlock(pool, shape=(100, 10)) as arr:
                arr[:, 0] = 100
                raise ValueError("模拟异常")
        except ValueError:
            pass

        # 即使有异常，数组也应该被释放
        arr2 = pool.acquire(shape=(100, 10))
        assert pool.stats.total_reuse_count == 1  # 重用了


class TestGlobalMemoryPool:
    """测试全局内存池"""

    def test_get_global_pool(self):
        """测试获取全局池"""
        reset_global_memory_pool()  # 重置

        pool1 = get_global_memory_pool()
        pool2 = get_global_memory_pool()

        # 应该是同一个实例
        assert pool1 is pool2

    def test_reset_global_pool(self):
        """测试重置全局池"""
        pool1 = get_global_memory_pool()
        arr = pool1.acquire(shape=(100, 10))
        pool1.release(arr)

        assert len(pool1.pools) > 0

        reset_global_memory_pool()

        pool2 = get_global_memory_pool()
        # 新实例
        assert len(pool2.pools) == 0

    def test_acquire_release_convenience_functions(self):
        """测试便捷函数"""
        reset_global_memory_pool()

        # 使用便捷函数
        arr = acquire_array(shape=(100, 10), fill_value=0.0)

        assert arr.shape == (100, 10)
        assert np.all(arr == 0.0)

        release_array(arr)

        # 验证统计
        stats = get_memory_pool_stats()
        assert stats.total_alloc_count == 1

        # 再次获取（应该重用）
        arr2 = acquire_array(shape=(100, 10))
        stats2 = get_memory_pool_stats()

        assert stats2.total_reuse_count == 1


@pytest.mark.performance
class TestMemoryPoolPerformance:
    """性能测试"""

    def test_reuse_efficiency(self):
        """测试重用效率"""
        pool = DataFrameMemoryPool(max_pools_per_shape=20)

        # 模拟真实使用场景：循环中频繁获取/释放
        num_iterations = 1000

        for i in range(num_iterations):
            arr = pool.acquire(shape=(1000, 50))
            arr[:, 0] = i  # 简单操作
            pool.release(arr)

        stats = pool.get_stats()

        # 验证重用率
        # 第一次是新建，之后都应该重用
        assert stats.total_alloc_count == 1
        assert stats.total_reuse_count == num_iterations - 1
        assert stats.get_reuse_rate() > 0.99  # 99%以上重用率

    def test_multiple_shapes_efficiency(self):
        """测试多种形状的效率"""
        pool = DataFrameMemoryPool(max_pools_per_shape=10)

        shapes = [
            (100, 10),
            (200, 20),
            (300, 30),
            (100, 10),  # 重复
            (200, 20),  # 重复
        ]

        for shape in shapes * 100:  # 重复100次
            arr = pool.acquire(shape=shape)
            pool.release(arr)

        stats = pool.get_stats()

        # 应该只有3次新分配（3种不同shape）
        assert stats.total_alloc_count == 3
        assert stats.total_reuse_count > 400  # 大部分是重用


@pytest.mark.integration
class TestMemoryPoolIntegration:
    """集成测试"""

    def test_real_world_scenario(self):
        """真实场景：因子计算中使用内存池"""
        pool = DataFrameMemoryPool(max_pools_per_shape=20)

        def calculate_rolling_features(data: np.ndarray, window: int = 20):
            """模拟滚动计算特征"""
            n_rows, n_cols = data.shape
            result_shape = (n_rows - window + 1, n_cols)

            # 从内存池获取临时数组
            temp_array = pool.acquire(shape=result_shape, fill_value=0.0)

            try:
                # 滚动计算
                for i in range(n_cols):
                    for j in range(window, n_rows + 1):
                        window_data = data[j - window:j, i]
                        temp_array[j - window, i] = np.mean(window_data)

                # 复制结果（因为temp_array会被释放）
                result = temp_array.copy()

            finally:
                # 归还到池中
                pool.release(temp_array)

            return result

        # 模拟处理多只股票
        for stock_idx in range(50):
            # 每只股票100天×5个特征
            stock_data = np.random.randn(100, 5)

            # 计算特征
            features = calculate_rolling_features(stock_data, window=20)

            assert features.shape == (81, 5)

        # 验证内存池效率
        stats = pool.get_stats()
        assert stats.total_alloc_count < 10  # 新分配很少
        assert stats.total_reuse_count > 40  # 大部分重用
        assert stats.get_reuse_rate() > 0.8  # 重用率80%以上


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
