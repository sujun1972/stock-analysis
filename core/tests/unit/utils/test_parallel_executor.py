"""
并行执行器单元测试

测试内容：
- ParallelExecutor基础功能
- 多种后端支持（multiprocessing/threading）
- 错误处理和异常安全
- 性能统计

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import time
import numpy as np
from src.utils.parallel_executor import (
    ParallelExecutor,
    ExecutionStats,
    ParallelExecutionError,
    BackendNotAvailableError,
    parallel_map
)
from src.config.features import ParallelComputingConfig


# ==================== 测试辅助函数 ====================

def square(x):
    """计算平方（可序列化的顶层函数）"""
    return x ** 2


def slow_square(x):
    """慢速平方（用于测试超时）"""
    time.sleep(0.05)
    return x ** 2


def failing_func(x):
    """可能失败的函数"""
    if x == 5:
        raise ValueError(f"Test error for x={x}")
    return x


# ==================== 基础功能测试 ====================

class TestParallelExecutorBasic:
    """ParallelExecutor基础功能测试"""

    def test_executor_initialization(self):
        """测试执行器初始化"""
        config = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            parallel_backend='multiprocessing'
        )

        executor = ParallelExecutor(config)

        assert executor.config == config
        assert executor.n_workers == 4
        assert executor.executor is not None

        executor.shutdown()

    def test_auto_detect_workers(self):
        """测试自动检测worker数量"""
        import multiprocessing as mp

        config = ParallelComputingConfig(n_workers=-1)
        executor = ParallelExecutor(config)

        # 应该是 CPU核心数 - 1
        expected = max(1, mp.cpu_count() - 1)
        assert executor.n_workers == expected

        executor.shutdown()

    def test_disabled_parallel(self):
        """测试禁用并行"""
        config = ParallelComputingConfig(enable_parallel=False)
        executor = ParallelExecutor(config)

        assert executor.executor is None  # 应该没有创建执行器

        executor.shutdown()


# ==================== Multiprocessing后端测试 ====================

class TestMultiprocessingBackend:
    """Multiprocessing后端测试"""

    def test_basic_map(self):
        """测试基础map操作"""
        config = ParallelComputingConfig(
            n_workers=4,
            parallel_backend='multiprocessing',
            show_progress=False
        )

        with ParallelExecutor(config) as executor:
            results = executor.map(square, range(10))

            assert results == [x**2 for x in range(10)]

    def test_large_dataset(self):
        """测试大数据集"""
        config = ParallelComputingConfig(
            n_workers=4,
            parallel_backend='multiprocessing',
            show_progress=False
        )

        data = list(range(100))
        expected = [x**2 for x in data]

        with ParallelExecutor(config) as executor:
            results = executor.map(square, data)

            assert results == expected

    def test_empty_tasks(self):
        """测试空任务列表"""
        config = ParallelComputingConfig(n_workers=4)

        with ParallelExecutor(config) as executor:
            results = executor.map(square, [])

            assert results == []

    def test_single_task(self):
        """测试单个任务"""
        config = ParallelComputingConfig(n_workers=4, show_progress=False)

        with ParallelExecutor(config) as executor:
            results = executor.map(square, [5])

            assert results == [25]


# ==================== Threading后端测试 ====================

class TestThreadingBackend:
    """Threading后端测试"""

    def test_threading_map(self):
        """测试threading后端"""
        config = ParallelComputingConfig(
            n_workers=4,
            parallel_backend='threading',
            show_progress=False
        )

        with ParallelExecutor(config) as executor:
            results = executor.map(square, range(10))

            assert results == [x**2 for x in range(10)]

    def test_threading_correctness(self):
        """测试threading结果正确性"""
        config = ParallelComputingConfig(
            n_workers=2,
            parallel_backend='threading',
            show_progress=False
        )

        data = list(range(50))
        expected = [x**2 for x in data]

        with ParallelExecutor(config) as executor:
            results = executor.map(square, data)

            assert results == expected


# ==================== 错误处理测试 ====================

class TestErrorHandling:
    """错误处理测试"""

    def test_ignore_errors_false(self):
        """测试ignore_errors=False时抛出异常"""
        config = ParallelComputingConfig(
            n_workers=2,
            show_progress=False
        )

        with ParallelExecutor(config) as executor:
            # 应该抛出异常
            with pytest.raises((ParallelExecutionError, ValueError)):
                executor.map(failing_func, range(10), ignore_errors=False)

    def test_ignore_errors_true(self):
        """测试ignore_errors=True时返回部分结果"""
        config = ParallelComputingConfig(
            n_workers=2,
            show_progress=False
        )

        with ParallelExecutor(config) as executor:
            results = executor.map(
                failing_func,
                range(10),
                ignore_errors=True
            )

            # 应该返回9个结果（跳过x=5）
            assert len(results) == 9
            assert 5 not in results

    def test_invalid_backend(self):
        """测试无效的后端"""
        config = ParallelComputingConfig(
            parallel_backend='invalid_backend'
        )

        with pytest.raises(ValueError):
            ParallelExecutor(config)


# ==================== 串行降级测试 ====================

class TestSerialFallback:
    """串行降级测试"""

    def test_serial_execution(self):
        """测试串行执行"""
        config = ParallelComputingConfig(
            enable_parallel=False
        )

        with ParallelExecutor(config) as executor:
            results = executor.map(square, range(10))

            assert results == [x**2 for x in range(10)]

    def test_single_worker(self):
        """测试单worker（串行）"""
        config = ParallelComputingConfig(
            n_workers=1,
            show_progress=False
        )

        with ParallelExecutor(config) as executor:
            results = executor.map(square, range(10))

            assert results == [x**2 for x in range(10)]

    def test_serial_error_handling(self):
        """测试串行模式的错误处理"""
        config = ParallelComputingConfig(enable_parallel=False)

        with ParallelExecutor(config) as executor:
            # ignore_errors=False应该抛出异常
            with pytest.raises(ValueError):
                executor.map(failing_func, range(10), ignore_errors=False)

            # ignore_errors=True应该返回部分结果
            results = executor.map(
                failing_func,
                range(10),
                ignore_errors=True
            )
            assert len(results) == 9


# ==================== 性能统计测试 ====================

class TestExecutionStats:
    """性能统计测试"""

    def test_stats_collection(self):
        """测试统计信息收集"""
        config = ParallelComputingConfig(
            n_workers=4,
            show_progress=False
        )

        with ParallelExecutor(config) as executor:
            executor.map(square, range(20))
            stats = executor.get_stats()

            assert isinstance(stats, ExecutionStats)
            assert stats.total_tasks == 20
            assert stats.completed_tasks == 20
            assert stats.failed_tasks == 0
            assert stats.total_time > 0
            assert stats.avg_task_time > 0

    def test_stats_with_failures(self):
        """测试带失败的统计"""
        config = ParallelComputingConfig(
            n_workers=2,
            show_progress=False
        )

        with ParallelExecutor(config) as executor:
            executor.map(failing_func, range(10), ignore_errors=True)
            stats = executor.get_stats()

            assert stats.total_tasks == 10
            assert stats.completed_tasks == 9
            assert stats.failed_tasks == 1

    def test_stats_to_dict(self):
        """测试统计信息转字典"""
        stats = ExecutionStats(
            total_tasks=10,
            completed_tasks=10,
            failed_tasks=0,
            total_time=1.5,
            avg_task_time=0.15
        )

        stats_dict = stats.to_dict()

        assert isinstance(stats_dict, dict)
        assert stats_dict['total_tasks'] == 10
        assert stats_dict['completed_tasks'] == 10
        assert stats_dict['total_time'] == 1.5


# ==================== 便捷函数测试 ====================

class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_parallel_map_function(self):
        """测试parallel_map便捷函数"""
        results = parallel_map(
            square,
            range(10),
            n_workers=2,
            show_progress=False
        )

        assert results == [x**2 for x in range(10)]

    def test_parallel_map_auto_workers(self):
        """测试自动检测worker数量"""
        results = parallel_map(
            square,
            range(10),
            n_workers=-1,
            show_progress=False
        )

        assert results == [x**2 for x in range(10)]

    def test_parallel_map_threading(self):
        """测试threading后端"""
        results = parallel_map(
            square,
            range(10),
            n_workers=2,
            backend='threading',
            show_progress=False
        )

        assert results == [x**2 for x in range(10)]


# ==================== 上下文管理器测试 ====================

class TestContextManager:
    """上下文管理器测试"""

    def test_with_statement(self):
        """测试with语句"""
        config = ParallelComputingConfig(n_workers=2, show_progress=False)

        with ParallelExecutor(config) as executor:
            results = executor.map(square, range(10))
            assert results == [x**2 for x in range(10)]

        # 退出with块后应该自动关闭

    def test_manual_shutdown(self):
        """测试手动关闭"""
        config = ParallelComputingConfig(n_workers=2)
        executor = ParallelExecutor(config)

        results = executor.map(square, range(10), desc="Test")
        assert results == [x**2 for x in range(10)]

        executor.shutdown()
        # 应该正常关闭，不抛出异常


# ==================== Submit方法测试 ====================

class TestSubmitMethod:
    """Submit方法测试"""

    def test_submit_single_task(self):
        """测试提交单个任务"""
        config = ParallelComputingConfig(
            n_workers=2,
            parallel_backend='multiprocessing'
        )

        with ParallelExecutor(config) as executor:
            future = executor.submit(square, 5)
            result = future.result()

            assert result == 25

    def test_submit_not_supported_serial(self):
        """测试串行模式不支持submit"""
        config = ParallelComputingConfig(enable_parallel=False)

        with ParallelExecutor(config) as executor:
            with pytest.raises(NotImplementedError):
                executor.submit(square, 5)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
