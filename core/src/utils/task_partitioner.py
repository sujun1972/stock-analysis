#!/usr/bin/env python3
"""
任务分片器 - 智能任务分片与负载均衡

提供多种分片策略：
- 按大小分片（chunk_size）
- 按数量分片（n_chunks）
- 自适应分片（基于数据大小和worker数量）

作者: Stock Analysis Team
创建: 2026-01-30
"""

import sys
import math
from typing import List, Any, TypeVar, Iterator
from loguru import logger

T = TypeVar('T')


class TaskPartitioner:
    """
    任务分片器

    提供智能任务分片功能，优化并行执行的负载均衡。

    Example:
        >>> stocks = ['stock_1', 'stock_2', ..., 'stock_1000']
        >>> chunks = TaskPartitioner.partition_by_size(stocks, chunk_size=100)
        >>> # 返回10个chunk，每个100只股票
    """

    @staticmethod
    def partition_by_size(
        items: List[T],
        chunk_size: int
    ) -> List[List[T]]:
        """
        按固定大小分片

        Args:
            items: 待分片的项目列表
            chunk_size: 每个chunk的大小

        Returns:
            分片后的列表（list of lists）

        Example:
            >>> items = list(range(10))
            >>> chunks = TaskPartitioner.partition_by_size(items, 3)
            >>> # [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
        """
        if chunk_size <= 0:
            raise ValueError(f"chunk_size必须 > 0，得到: {chunk_size}")

        if not items:
            return []

        chunks = []
        for i in range(0, len(items), chunk_size):
            chunks.append(items[i:i + chunk_size])

        logger.debug(
            f"按大小分片: {len(items)}个项目 -> {len(chunks)}个chunk "
            f"(chunk_size={chunk_size})"
        )

        return chunks

    @staticmethod
    def partition_by_count(
        items: List[T],
        n_chunks: int
    ) -> List[List[T]]:
        """
        按chunk数量分片（尽量均匀）

        Args:
            items: 待分片的项目列表
            n_chunks: 目标chunk数量

        Returns:
            分片后的列表

        Example:
            >>> items = list(range(10))
            >>> chunks = TaskPartitioner.partition_by_count(items, 3)
            >>> # [[0, 1, 2, 3], [4, 5, 6], [7, 8, 9]]
        """
        if n_chunks <= 0:
            raise ValueError(f"n_chunks必须 > 0，得到: {n_chunks}")

        if not items:
            return []

        # 确保chunk数不超过项目数
        n_chunks = min(n_chunks, len(items))

        # 计算每个chunk的基础大小
        base_size = len(items) // n_chunks
        remainder = len(items) % n_chunks

        chunks = []
        start = 0

        for i in range(n_chunks):
            # 前remainder个chunk多分配1个项目
            size = base_size + (1 if i < remainder else 0)
            chunks.append(items[start:start + size])
            start += size

        logger.debug(
            f"按数量分片: {len(items)}个项目 -> {n_chunks}个chunk "
            f"(大小范围: {base_size}-{base_size+1})"
        )

        return chunks

    @staticmethod
    def auto_partition(
        items: List[T],
        n_workers: int,
        data_size_mb: float = None,
        max_memory_mb: float = 1024,
        min_chunk_size: int = 1,
        max_chunk_size: int = None
    ) -> List[List[T]]:
        """
        自适应分片（基于worker数量和数据大小）

        策略：
        1. 如果提供数据大小，基于内存限制计算chunk_size
        2. 否则，基于worker数量均匀分片
        3. 确保chunk数量 >= worker数量（充分利用并行）

        Args:
            items: 待分片的项目列表
            n_workers: worker数量
            data_size_mb: 总数据大小（MB）
            max_memory_mb: 最大内存限制（MB）
            min_chunk_size: 最小chunk大小
            max_chunk_size: 最大chunk大小

        Returns:
            分片后的列表

        Example:
            >>> items = list(range(1000))
            >>> chunks = TaskPartitioner.auto_partition(items, n_workers=8)
        """
        if not items:
            return []

        n_items = len(items)

        # 策略1: 基于内存限制
        if data_size_mb is not None and data_size_mb > 0:
            # 估算单个item的大小
            item_size_mb = data_size_mb / n_items

            # 每个worker最多使用max_memory_mb / n_workers的内存
            max_items_per_chunk = int(
                (max_memory_mb / n_workers) / item_size_mb
            )

            chunk_size = max(min_chunk_size, max_items_per_chunk)

            if max_chunk_size:
                chunk_size = min(chunk_size, max_chunk_size)

            logger.debug(
                f"自适应分片（基于内存）: 数据{data_size_mb:.1f}MB, "
                f"chunk_size={chunk_size}"
            )

            return TaskPartitioner.partition_by_size(items, chunk_size)

        # 策略2: 基于worker数量均匀分片
        # 目标：chunk数量 = worker数量 * 2（更好的负载均衡）
        target_chunk_size = n_items // (n_workers * 2)
        target_chunk_size = max(target_chunk_size, 1)  # 至少为1

        # 应用min/max限制
        if min_chunk_size and target_chunk_size < min_chunk_size:
            target_chunk_size = min_chunk_size
        if max_chunk_size and target_chunk_size > max_chunk_size:
            target_chunk_size = max_chunk_size

        logger.debug(
            f"自适应分片（基于worker）: {n_items}个项目, "
            f"{n_workers}个worker -> chunk_size={target_chunk_size}"
        )

        return TaskPartitioner.partition_by_size(items, target_chunk_size)

    @staticmethod
    def partition_dataframe(
        df,  # pandas.DataFrame
        by: str = 'rows',
        chunk_size: int = None,
        n_chunks: int = None
    ) -> List:
        """
        分片Pandas DataFrame

        Args:
            df: Pandas DataFrame
            by: 分片维度 ('rows' 或 'columns')
            chunk_size: chunk大小（与n_chunks二选一）
            n_chunks: chunk数量

        Returns:
            DataFrame分片列表

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({'a': range(100), 'b': range(100)})
            >>> chunks = TaskPartitioner.partition_dataframe(df, by='rows', chunk_size=20)
        """
        if by == 'rows':
            items = df.index.tolist()
        elif by == 'columns':
            items = df.columns.tolist()
        else:
            raise ValueError(f"by必须是'rows'或'columns'，得到: {by}")

        # 分片索引
        if chunk_size is not None:
            index_chunks = TaskPartitioner.partition_by_size(items, chunk_size)
        elif n_chunks is not None:
            index_chunks = TaskPartitioner.partition_by_count(items, n_chunks)
        else:
            raise ValueError("必须提供chunk_size或n_chunks")

        # 切片DataFrame
        df_chunks = []
        for indices in index_chunks:
            if by == 'rows':
                chunk_df = df.loc[indices]
            else:  # columns
                chunk_df = df[indices]
            df_chunks.append(chunk_df)

        logger.debug(
            f"DataFrame分片: {df.shape} -> {len(df_chunks)}个chunk (by={by})"
        )

        return df_chunks

    @staticmethod
    def estimate_optimal_chunk_size(
        n_items: int,
        n_workers: int,
        overhead_ratio: float = 0.1
    ) -> int:
        """
        估算最优chunk大小（平衡并行度和开销）

        Args:
            n_items: 项目总数
            n_workers: worker数量
            overhead_ratio: 进程启动开销占比

        Returns:
            建议的chunk_size

        算法：
            chunk_size = sqrt(n_items / n_workers)
            确保chunk数量 >> worker数量，避免负载不均
        """
        if n_items <= 0 or n_workers <= 0:
            return 1

        # 简单策略：每个worker分配多个chunk（2-4倍）
        base_chunk_size = max(1, n_items // (n_workers * 3))

        # 考虑开销：chunk太小会增加通信成本
        min_chunk_size = max(1, int(n_items * overhead_ratio / n_workers))

        chunk_size = max(base_chunk_size, min_chunk_size)

        logger.debug(
            f"最优chunk估算: {n_items}项目, {n_workers}worker -> "
            f"chunk_size={chunk_size}"
        )

        return chunk_size


# ==================== 便捷函数 ====================

def partition_for_parallel(
    items: List[T],
    n_workers: int = None,
    chunk_size: int = None
) -> List[List[T]]:
    """
    便捷的并行分片函数

    自动选择最佳分片策略。

    Args:
        items: 待分片的项目
        n_workers: worker数量（优先使用）
        chunk_size: chunk大小

    Returns:
        分片列表

    Example:
        >>> stocks = ['stock_1', 'stock_2', ...]
        >>> chunks = partition_for_parallel(stocks, n_workers=8)
    """
    if chunk_size is not None:
        return TaskPartitioner.partition_by_size(items, chunk_size)
    elif n_workers is not None:
        return TaskPartitioner.auto_partition(items, n_workers)
    else:
        # 默认：自动检测CPU核心数
        import multiprocessing as mp
        n_workers = max(1, mp.cpu_count() - 1)
        return TaskPartitioner.auto_partition(items, n_workers)


