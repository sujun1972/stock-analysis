#!/usr/bin/env python3
"""
并行执行器 - 统一的多进程/多线程执行接口

提供统一的并行计算接口，支持多种后端：
- multiprocessing: 多进程（CPU密集型，推荐）
- threading: 多线程（I/O密集型）
- ray: Ray分布式框架（可选）
- dask: Dask分布式框架（可选）

作者: Stock Analysis Team
创建: 2026-01-30
"""

import os
import sys
import time
import multiprocessing as mp
from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    Future,
    as_completed
)
from typing import Callable, List, Any, Optional, Dict, Iterator
from dataclasses import dataclass
from loguru import logger

# 尝试导入可选依赖
try:
    import ray
    HAS_RAY = True
except ImportError:
    HAS_RAY = False

try:
    import dask
    from dask.distributed import Client
    HAS_DASK = True
except ImportError:
    HAS_DASK = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


# ==================== 配置类 ====================

try:
    from ..config.features import ParallelComputingConfig
except ImportError:
    # 直接执行时的fallback
    from dataclasses import dataclass

    @dataclass
    class ParallelComputingConfig:
        """并行计算配置（Fallback）"""
        enable_parallel: bool = True
        n_workers: int = -1
        parallel_backend: str = 'multiprocessing'
        chunk_size: int = 100
        use_shared_memory: bool = False
        ray_address: str = None
        show_progress: bool = True
        timeout: int = 300


# ==================== 异常类 ====================

class ParallelExecutionError(Exception):
    """并行执行错误"""
    pass


class BackendNotAvailableError(Exception):
    """后端不可用错误"""
    pass


# ==================== 性能统计 ====================

@dataclass
class ExecutionStats:
    """执行统计"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_time: float = 0.0
    avg_task_time: float = 0.0
    speedup: float = 1.0
    efficiency: float = 1.0

    def to_dict(self) -> Dict:
        """转为字典"""
        return {
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'total_time': self.total_time,
            'avg_task_time': self.avg_task_time,
            'speedup': self.speedup,
            'efficiency': self.efficiency
        }


# ==================== 核心执行器 ====================

class ParallelExecutor:
    """
    统一的并行执行器

    支持4种后端：
    - multiprocessing: 标准多进程（推荐用于CPU密集型）
    - threading: 多线程（推荐用于I/O密集型）
    - ray: Ray分布式框架（需安装ray）
    - dask: Dask分布式框架（需安装dask）

    Example:
        >>> from src.config.features import ParallelComputingConfig
        >>> config = ParallelComputingConfig(n_workers=4)
        >>> executor = ParallelExecutor(config)
        >>> results = executor.map(lambda x: x**2, range(100))
        >>> executor.shutdown()
    """

    def __init__(self, config: ParallelComputingConfig):
        """
        初始化并行执行器

        Args:
            config: 并行计算配置
        """
        self.config = config
        self.executor = None
        self._start_time = None
        self._stats = ExecutionStats()

        # 检测worker数量
        self.n_workers = self._detect_workers(config.n_workers)

        # 创建执行器
        if config.enable_parallel and self.n_workers > 1:
            self.executor = self._create_executor()
            logger.debug(
                f"并行执行器已初始化: backend={config.parallel_backend}, "
                f"n_workers={self.n_workers}"
            )
        else:
            logger.debug("并行执行器禁用，将使用串行执行")

    def _detect_workers(self, n_workers: int) -> int:
        """
        检测实际worker数量

        Args:
            n_workers: 配置的worker数量
                -1: 自动检测（CPU核心数 - 1）
                1: 禁用并行
                >1: 指定数量

        Returns:
            实际worker数量
        """
        if n_workers == -1:
            # 自动检测：CPU核心数 - 1，最少1个
            cpu_count = mp.cpu_count()
            detected = max(1, cpu_count - 1)
            logger.debug(f"自动检测worker数量: {detected} (CPU核心数: {cpu_count})")
            return detected
        elif n_workers >= 1:
            return n_workers
        else:
            logger.warning(f"无效的n_workers={n_workers}，使用默认值1")
            return 1

    def _create_executor(self):
        """
        创建后端执行器

        Returns:
            执行器实例

        Raises:
            BackendNotAvailableError: 后端不可用
        """
        backend = self.config.parallel_backend

        if backend == 'multiprocessing':
            return self._create_multiprocessing_executor()
        elif backend == 'threading':
            return self._create_threading_executor()
        elif backend == 'ray':
            return self._create_ray_executor()
        elif backend == 'dask':
            return self._create_dask_executor()
        else:
            raise ValueError(
                f"不支持的后端: {backend}。"
                f"可用: multiprocessing, threading, ray, dask"
            )

    def _create_multiprocessing_executor(self):
        """创建多进程执行器"""
        return ProcessPoolExecutor(max_workers=self.n_workers)

    def _create_threading_executor(self):
        """创建多线程执行器"""
        return ThreadPoolExecutor(max_workers=self.n_workers)

    def _create_ray_executor(self):
        """创建Ray执行器"""
        if not HAS_RAY:
            raise BackendNotAvailableError(
                "Ray未安装。请运行: pip install ray"
            )

        # 初始化Ray
        if not ray.is_initialized():
            ray_address = self.config.ray_address or 'auto'
            try:
                ray.init(address=ray_address, ignore_reinit_error=True)
                logger.info(f"Ray已初始化: address={ray_address}")
            except Exception as e:
                raise BackendNotAvailableError(f"Ray初始化失败: {e}")

        return 'ray'  # 返回标识符

    def _create_dask_executor(self):
        """创建Dask执行器"""
        if not HAS_DASK:
            raise BackendNotAvailableError(
                "Dask未安装。请运行: pip install dask[complete]"
            )

        try:
            client = Client(processes=True, n_workers=self.n_workers)
            logger.info(f"Dask客户端已创建: {client}")
            return client
        except Exception as e:
            raise BackendNotAvailableError(f"Dask客户端创建失败: {e}")

    def map(
        self,
        func: Callable,
        tasks: List[Any],
        desc: str = "Processing",
        ignore_errors: bool = False
    ) -> List[Any]:
        """
        并行执行map操作

        Args:
            func: 待执行的函数（必须是可序列化的）
            tasks: 任务列表
            desc: 进度条描述
            ignore_errors: 是否忽略错误（True时返回部分结果）

        Returns:
            结果列表（与tasks顺序一致）

        Raises:
            ParallelExecutionError: 执行失败
        """
        if not tasks:
            logger.warning("任务列表为空，跳过执行")
            return []

        self._stats.total_tasks = len(tasks)
        self._start_time = time.time()

        try:
            # 串行降级
            if self.executor is None or self.n_workers == 1:
                results = self._map_serial(func, tasks, desc, ignore_errors)
            # 并行执行
            elif self.config.parallel_backend == 'ray':
                results = self._map_ray(func, tasks, desc, ignore_errors)
            elif self.config.parallel_backend == 'dask':
                results = self._map_dask(func, tasks, desc, ignore_errors)
            else:
                # multiprocessing / threading
                results = self._map_futures(func, tasks, desc, ignore_errors)

            # 统计
            self._stats.completed_tasks = len(results)
            self._stats.failed_tasks = self._stats.total_tasks - self._stats.completed_tasks
            self._stats.total_time = time.time() - self._start_time
            if self._stats.completed_tasks > 0:
                self._stats.avg_task_time = self._stats.total_time / self._stats.completed_tasks

            logger.debug(
                f"并行执行完成: {self._stats.completed_tasks}/{self._stats.total_tasks} "
                f"任务, 耗时 {self._stats.total_time:.2f}s"
            )

            return results

        except Exception as e:
            logger.error(f"并行执行失败: {e}")
            if not ignore_errors:
                # 如果是用户函数的错误，直接传播原始异常
                if isinstance(e, (ValueError, TypeError, KeyError, AttributeError, IndexError)):
                    raise
                # 其他异常包装为ParallelExecutionError
                raise ParallelExecutionError(f"执行失败: {e}") from e
            return []

    def _map_serial(
        self,
        func: Callable,
        tasks: List[Any],
        desc: str,
        ignore_errors: bool
    ) -> List[Any]:
        """串行执行（降级方案）"""
        logger.debug("使用串行执行")
        results = []

        iterator = tasks
        if self.config.show_progress and HAS_TQDM:
            iterator = tqdm(tasks, desc=desc, total=len(tasks))

        for task in iterator:
            try:
                result = func(task)
                results.append(result)
            except Exception as e:
                logger.warning(f"任务执行失败: {e}")
                if not ignore_errors:
                    raise

        return results

    def _map_futures(
        self,
        func: Callable,
        tasks: List[Any],
        desc: str,
        ignore_errors: bool
    ) -> List[Any]:
        """使用Futures执行（multiprocessing/threading）"""
        futures_to_task = {}

        # 提交所有任务
        for task in tasks:
            future = self.executor.submit(func, task)
            futures_to_task[future] = task

        # 收集结果（保持顺序）
        results = []
        task_to_result = {}

        iterator = as_completed(futures_to_task.keys())
        if self.config.show_progress and HAS_TQDM:
            iterator = tqdm(
                as_completed(futures_to_task.keys()),
                desc=desc,
                total=len(tasks)
            )

        for future in iterator:
            task = futures_to_task[future]
            try:
                result = future.result(timeout=self.config.timeout)
                task_to_result[id(task)] = result
            except Exception as e:
                logger.warning(f"任务执行失败: {e}")
                if not ignore_errors:
                    raise

        # 按原始顺序返回结果
        for task in tasks:
            if id(task) in task_to_result:
                results.append(task_to_result[id(task)])

        return results

    def _map_ray(
        self,
        func: Callable,
        tasks: List[Any],
        desc: str,
        ignore_errors: bool
    ) -> List[Any]:
        """使用Ray执行"""
        import ray

        # 将函数转为Ray remote函数
        @ray.remote
        def remote_func(task):
            return func(task)

        # 提交所有任务
        futures = [remote_func.remote(task) for task in tasks]

        # 收集结果
        results = []

        if self.config.show_progress and HAS_TQDM:
            for future in tqdm(futures, desc=desc):
                try:
                    result = ray.get(future, timeout=self.config.timeout)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Ray任务失败: {e}")
                    if not ignore_errors:
                        raise
        else:
            try:
                results = ray.get(futures, timeout=self.config.timeout)
            except Exception as e:
                logger.error(f"Ray批量获取失败: {e}")
                if not ignore_errors:
                    raise

        return results

    def _map_dask(
        self,
        func: Callable,
        tasks: List[Any],
        desc: str,
        ignore_errors: bool
    ) -> List[Any]:
        """使用Dask执行"""
        client = self.executor

        # 提交所有任务
        futures = client.map(func, tasks)

        # 收集结果
        try:
            results = client.gather(futures)
            return results
        except Exception as e:
            logger.error(f"Dask执行失败: {e}")
            if not ignore_errors:
                raise
            return []

    def submit(self, func: Callable, *args, **kwargs) -> Future:
        """
        提交单个任务

        Args:
            func: 待执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Future对象

        Raises:
            NotImplementedError: 当前后端不支持
        """
        if self.executor is None:
            raise NotImplementedError("串行模式不支持submit，请使用map")

        if self.config.parallel_backend in ['multiprocessing', 'threading']:
            return self.executor.submit(func, *args, **kwargs)
        else:
            raise NotImplementedError(
                f"后端{self.config.parallel_backend}暂不支持submit"
            )

    def shutdown(self, wait: bool = True):
        """
        关闭执行器

        Args:
            wait: 是否等待所有任务完成
        """
        if self.executor is None:
            return

        try:
            if self.config.parallel_backend in ['multiprocessing', 'threading']:
                self.executor.shutdown(wait=wait)
            elif self.config.parallel_backend == 'ray':
                if HAS_RAY and ray.is_initialized():
                    # 注意：不要关闭全局Ray，可能被其他代码使用
                    # ray.shutdown()
                    pass
            elif self.config.parallel_backend == 'dask':
                self.executor.close()

            logger.debug("并行执行器已关闭")

        except Exception as e:
            logger.warning(f"关闭执行器时出错: {e}")

    def get_stats(self) -> ExecutionStats:
        """
        获取性能统计

        Returns:
            ExecutionStats对象
        """
        # 计算加速比（需要基准）
        if hasattr(self, '_serial_time') and self._serial_time > 0:
            self._stats.speedup = self._serial_time / self._stats.total_time
            self._stats.efficiency = self._stats.speedup / self.n_workers

        return self._stats

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()


# ==================== 便捷函数 ====================

def parallel_map(
    func: Callable,
    tasks: List[Any],
    n_workers: int = -1,
    backend: str = 'multiprocessing',
    show_progress: bool = True,
    desc: str = "Processing"
) -> List[Any]:
    """
    便捷的并行map函数（自动管理执行器生命周期）

    Args:
        func: 待执行的函数
        tasks: 任务列表
        n_workers: worker数量（-1自动检测）
        backend: 后端类型
        show_progress: 是否显示进度条
        desc: 进度条描述

    Returns:
        结果列表

    Example:
        >>> results = parallel_map(lambda x: x**2, range(100), n_workers=4)
    """
    config = ParallelComputingConfig(
        enable_parallel=True,
        n_workers=n_workers,
        parallel_backend=backend,
        show_progress=show_progress
    )

    with ParallelExecutor(config) as executor:
        return executor.map(func, tasks, desc=desc)


