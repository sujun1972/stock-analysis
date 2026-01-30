"""
任务分片器单元测试

测试内容：
- 按大小分片
- 按数量分片
- 自适应分片
- DataFrame分片
- 便捷函数

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import numpy as np
import pandas as pd
from src.utils.task_partitioner import (
    TaskPartitioner,
    partition_for_parallel
)


# ==================== 按大小分片测试 ====================

class TestPartitionBySize:
    """按大小分片测试"""

    def test_basic_partition(self):
        """测试基础分片"""
        items = list(range(10))
        chunks = TaskPartitioner.partition_by_size(items, chunk_size=3)

        assert len(chunks) == 4
        assert chunks[0] == [0, 1, 2]
        assert chunks[1] == [3, 4, 5]
        assert chunks[2] == [6, 7, 8]
        assert chunks[3] == [9]

    def test_exact_division(self):
        """测试整除分片"""
        items = list(range(12))
        chunks = TaskPartitioner.partition_by_size(items, chunk_size=4)

        assert len(chunks) == 3
        assert all(len(c) == 4 for c in chunks)

    def test_single_chunk(self):
        """测试单个chunk"""
        items = list(range(5))
        chunks = TaskPartitioner.partition_by_size(items, chunk_size=10)

        assert len(chunks) == 1
        assert chunks[0] == items

    def test_chunk_size_one(self):
        """测试chunk_size=1"""
        items = list(range(5))
        chunks = TaskPartitioner.partition_by_size(items, chunk_size=1)

        assert len(chunks) == 5
        assert all(len(c) == 1 for c in chunks)

    def test_empty_items(self):
        """测试空列表"""
        chunks = TaskPartitioner.partition_by_size([], chunk_size=10)

        assert chunks == []

    def test_invalid_chunk_size(self):
        """测试无效的chunk_size"""
        items = list(range(10))

        with pytest.raises(ValueError):
            TaskPartitioner.partition_by_size(items, chunk_size=0)

        with pytest.raises(ValueError):
            TaskPartitioner.partition_by_size(items, chunk_size=-1)

    def test_preserves_order(self):
        """测试保持顺序"""
        items = list(range(25))
        chunks = TaskPartitioner.partition_by_size(items, chunk_size=7)

        # 合并后应该与原列表相同
        merged = []
        for chunk in chunks:
            merged.extend(chunk)

        assert merged == items


# ==================== 按数量分片测试 ====================

class TestPartitionByCount:
    """按数量分片测试"""

    def test_basic_partition(self):
        """测试基础分片"""
        items = list(range(10))
        chunks = TaskPartitioner.partition_by_count(items, n_chunks=3)

        assert len(chunks) == 3
        # 10个元素分3份：4, 3, 3
        assert len(chunks[0]) == 4
        assert len(chunks[1]) == 3
        assert len(chunks[2]) == 3

    def test_exact_division(self):
        """测试整除分片"""
        items = list(range(12))
        chunks = TaskPartitioner.partition_by_count(items, n_chunks=4)

        assert len(chunks) == 4
        assert all(len(c) == 3 for c in chunks)

    def test_more_chunks_than_items(self):
        """测试chunk数超过items数"""
        items = list(range(5))
        chunks = TaskPartitioner.partition_by_count(items, n_chunks=10)

        # 最多5个chunk
        assert len(chunks) == 5
        assert all(len(c) == 1 for c in chunks)

    def test_single_chunk(self):
        """测试单个chunk"""
        items = list(range(10))
        chunks = TaskPartitioner.partition_by_count(items, n_chunks=1)

        assert len(chunks) == 1
        assert chunks[0] == items

    def test_empty_items(self):
        """测试空列表"""
        chunks = TaskPartitioner.partition_by_count([], n_chunks=5)

        assert chunks == []

    def test_invalid_n_chunks(self):
        """测试无效的n_chunks"""
        items = list(range(10))

        with pytest.raises(ValueError):
            TaskPartitioner.partition_by_count(items, n_chunks=0)

        with pytest.raises(ValueError):
            TaskPartitioner.partition_by_count(items, n_chunks=-1)

    def test_balanced_distribution(self):
        """测试均衡分配"""
        items = list(range(100))
        chunks = TaskPartitioner.partition_by_count(items, n_chunks=7)

        # 100分7份：15, 15, 14, 14, 14, 14, 14
        chunk_sizes = [len(c) for c in chunks]

        # 最大和最小chunk大小差不超过1
        assert max(chunk_sizes) - min(chunk_sizes) <= 1

    def test_preserves_order(self):
        """测试保持顺序"""
        items = list(range(50))
        chunks = TaskPartitioner.partition_by_count(items, n_chunks=7)

        merged = []
        for chunk in chunks:
            merged.extend(chunk)

        assert merged == items


# ==================== 自适应分片测试 ====================

class TestAutoPartition:
    """自适应分片测试"""

    def test_basic_auto_partition(self):
        """测试基础自适应分片"""
        items = list(range(100))
        chunks = TaskPartitioner.auto_partition(items, n_workers=4)

        # 应该返回chunk列表
        assert isinstance(chunks, list)
        assert len(chunks) > 0

        # 验证所有元素都被包含
        merged = []
        for chunk in chunks:
            merged.extend(chunk)
        assert merged == items

    def test_auto_partition_with_memory_limit(self):
        """测试基于内存限制的自适应分片"""
        items = list(range(1000))

        chunks = TaskPartitioner.auto_partition(
            items,
            n_workers=4,
            data_size_mb=100,
            max_memory_mb=200
        )

        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_min_chunk_size(self):
        """测试最小chunk大小"""
        items = list(range(10))

        chunks = TaskPartitioner.auto_partition(
            items,
            n_workers=4,
            min_chunk_size=5
        )

        # 所有chunk大小应该 >= 5 或等于剩余元素数
        for chunk in chunks:
            assert len(chunk) >= min(5, len(items))

    def test_max_chunk_size(self):
        """测试最大chunk大小"""
        items = list(range(100))

        chunks = TaskPartitioner.auto_partition(
            items,
            n_workers=2,
            max_chunk_size=20
        )

        # 所有chunk大小应该 <= 20
        for chunk in chunks:
            assert len(chunk) <= 20

    def test_empty_items(self):
        """测试空列表"""
        chunks = TaskPartitioner.auto_partition([], n_workers=4)

        assert chunks == []

    def test_sufficient_chunks_for_workers(self):
        """测试生成足够的chunks给workers"""
        items = list(range(100))
        n_workers = 8

        chunks = TaskPartitioner.auto_partition(items, n_workers=n_workers)

        # chunks数量应该 >= n_workers（以充分利用并行）
        assert len(chunks) >= n_workers


# ==================== DataFrame分片测试 ====================

class TestDataFramePartition:
    """DataFrame分片测试"""

    @pytest.fixture
    def sample_dataframe(self):
        """生成测试DataFrame"""
        return pd.DataFrame({
            'a': np.arange(100),
            'b': np.arange(100, 200),
            'c': np.arange(200, 300)
        })

    def test_partition_by_rows_with_size(self, sample_dataframe):
        """测试按行分片（指定大小）"""
        df = sample_dataframe

        chunks = TaskPartitioner.partition_dataframe(
            df,
            by='rows',
            chunk_size=25
        )

        assert len(chunks) == 4
        assert all(isinstance(c, pd.DataFrame) for c in chunks)
        assert chunks[0].shape[0] == 25
        assert chunks[1].shape[0] == 25
        assert chunks[2].shape[0] == 25
        assert chunks[3].shape[0] == 25

    def test_partition_by_rows_with_count(self, sample_dataframe):
        """测试按行分片（指定数量）"""
        df = sample_dataframe

        chunks = TaskPartitioner.partition_dataframe(
            df,
            by='rows',
            n_chunks=3
        )

        assert len(chunks) == 3
        assert all(isinstance(c, pd.DataFrame) for c in chunks)

        # 验证总行数
        total_rows = sum(c.shape[0] for c in chunks)
        assert total_rows == 100

    def test_partition_by_columns_with_size(self, sample_dataframe):
        """测试按列分片"""
        df = sample_dataframe

        chunks = TaskPartitioner.partition_dataframe(
            df,
            by='columns',
            chunk_size=2
        )

        assert len(chunks) == 2
        assert chunks[0].shape[1] == 2
        assert chunks[1].shape[1] == 1

    def test_partition_by_columns_with_count(self, sample_dataframe):
        """测试按列分片（指定数量）"""
        df = sample_dataframe

        chunks = TaskPartitioner.partition_dataframe(
            df,
            by='columns',
            n_chunks=2
        )

        assert len(chunks) == 2

        # 验证总列数
        total_cols = sum(c.shape[1] for c in chunks)
        assert total_cols == 3

    def test_partition_invalid_by(self, sample_dataframe):
        """测试无效的by参数"""
        df = sample_dataframe

        with pytest.raises(ValueError):
            TaskPartitioner.partition_dataframe(
                df,
                by='invalid',
                chunk_size=10
            )

    def test_partition_missing_parameters(self, sample_dataframe):
        """测试缺少参数"""
        df = sample_dataframe

        with pytest.raises(ValueError):
            TaskPartitioner.partition_dataframe(df, by='rows')

    def test_partition_preserves_data(self, sample_dataframe):
        """测试分片后数据完整性"""
        df = sample_dataframe

        chunks = TaskPartitioner.partition_dataframe(
            df,
            by='rows',
            chunk_size=30
        )

        # 合并后应该与原数据相同
        merged = pd.concat(chunks, axis=0)
        pd.testing.assert_frame_equal(merged.sort_index(), df.sort_index())


# ==================== 最优chunk大小估算测试 ====================

class TestEstimateOptimalChunkSize:
    """最优chunk大小估算测试"""

    def test_basic_estimation(self):
        """测试基础估算"""
        chunk_size = TaskPartitioner.estimate_optimal_chunk_size(
            n_items=1000,
            n_workers=4
        )

        assert isinstance(chunk_size, int)
        assert chunk_size > 0

    def test_small_dataset(self):
        """测试小数据集"""
        chunk_size = TaskPartitioner.estimate_optimal_chunk_size(
            n_items=10,
            n_workers=4
        )

        # 小数据集应该返回较小的chunk_size
        assert chunk_size >= 1
        assert chunk_size <= 10

    def test_large_dataset(self):
        """测试大数据集"""
        chunk_size = TaskPartitioner.estimate_optimal_chunk_size(
            n_items=10000,
            n_workers=8
        )

        # 大数据集应该返回合理的chunk_size
        assert chunk_size > 1
        assert chunk_size < 10000

    def test_single_worker(self):
        """测试单worker"""
        chunk_size = TaskPartitioner.estimate_optimal_chunk_size(
            n_items=100,
            n_workers=1
        )

        assert chunk_size >= 1

    def test_overhead_ratio(self):
        """测试开销比例"""
        # 高开销应该导致更大的chunk_size
        chunk_size_high = TaskPartitioner.estimate_optimal_chunk_size(
            n_items=1000,
            n_workers=4,
            overhead_ratio=0.2
        )

        chunk_size_low = TaskPartitioner.estimate_optimal_chunk_size(
            n_items=1000,
            n_workers=4,
            overhead_ratio=0.05
        )

        assert chunk_size_high >= chunk_size_low


# ==================== 便捷函数测试 ====================

class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_partition_for_parallel_with_workers(self):
        """测试指定workers的便捷分片"""
        items = list(range(100))

        chunks = partition_for_parallel(items, n_workers=4)

        assert isinstance(chunks, list)
        assert len(chunks) > 0

        # 验证完整性
        merged = []
        for chunk in chunks:
            merged.extend(chunk)
        assert merged == items

    def test_partition_for_parallel_with_chunk_size(self):
        """测试指定chunk_size的便捷分片"""
        items = list(range(100))

        chunks = partition_for_parallel(items, chunk_size=25)

        assert len(chunks) == 4
        assert all(len(c) == 25 for c in chunks)

    def test_partition_for_parallel_auto_detect(self):
        """测试自动检测"""
        items = list(range(100))

        # 不指定参数，应该自动检测CPU核心数
        chunks = partition_for_parallel(items)

        assert isinstance(chunks, list)
        assert len(chunks) > 0


# ==================== 边界情况测试 ====================

class TestEdgeCases:
    """边界情况测试"""

    def test_single_item(self):
        """测试单个元素"""
        items = [42]

        chunks_size = TaskPartitioner.partition_by_size(items, chunk_size=10)
        assert chunks_size == [[42]]

        chunks_count = TaskPartitioner.partition_by_count(items, n_chunks=5)
        assert chunks_count == [[42]]

    def test_large_chunk_size(self):
        """测试chunk_size大于items数"""
        items = list(range(10))

        chunks = TaskPartitioner.partition_by_size(items, chunk_size=100)

        assert len(chunks) == 1
        assert chunks[0] == items

    def test_string_items(self):
        """测试字符串列表"""
        items = ['a', 'b', 'c', 'd', 'e', 'f', 'g']

        chunks = TaskPartitioner.partition_by_size(items, chunk_size=3)

        assert len(chunks) == 3
        assert chunks[0] == ['a', 'b', 'c']
        assert chunks[1] == ['d', 'e', 'f']
        assert chunks[2] == ['g']

    def test_dict_items(self):
        """测试字典列表"""
        items = [{'id': i} for i in range(10)]

        chunks = TaskPartitioner.partition_by_count(items, n_chunks=3)

        assert len(chunks) == 3

        # 验证完整性
        merged = []
        for chunk in chunks:
            merged.extend(chunk)
        assert merged == items


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
