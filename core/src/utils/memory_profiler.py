"""
内存监控工具
提供内存使用分析和监控功能

核心功能:
- 上下文管理器监控代码块内存使用
- 实时内存使用追踪
- 内存泄漏检测
- 内存使用报告生成

使用场景:
- 性能调优
- 内存泄漏检测
- 生产环境监控

作者: Stock Analysis Team
创建: 2026-01-30
"""

import psutil
import os
import gc
from typing import Optional, Dict, List, Callable, Any
from contextlib import contextmanager
from loguru import logger
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time


@dataclass
class MemorySnapshot:
    """内存快照"""
    timestamp: datetime
    rss_mb: float  # 物理内存(MB)
    vms_mb: float  # 虚拟内存(MB)
    percent: float  # 内存使用百分比
    available_mb: float  # 可用内存(MB)
    operation: Optional[str] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'rss_mb': round(self.rss_mb, 2),
            'vms_mb': round(self.vms_mb, 2),
            'percent': round(self.percent, 2),
            'available_mb': round(self.available_mb, 2),
            'operation': self.operation
        }


@dataclass
class MemoryUsageReport:
    """内存使用报告"""
    operation_name: str
    start_snapshot: MemorySnapshot
    end_snapshot: MemorySnapshot
    peak_rss_mb: float = 0.0
    peak_vms_mb: float = 0.0
    delta_rss_mb: float = 0.0
    delta_vms_mb: float = 0.0
    duration_seconds: float = 0.0
    snapshots: List[MemorySnapshot] = field(default_factory=list)

    def __post_init__(self):
        """计算增量"""
        self.delta_rss_mb = self.end_snapshot.rss_mb - self.start_snapshot.rss_mb
        self.delta_vms_mb = self.end_snapshot.vms_mb - self.start_snapshot.vms_mb
        self.duration_seconds = (
            self.end_snapshot.timestamp - self.start_snapshot.timestamp
        ).total_seconds()

        # 计算峰值
        if self.snapshots:
            self.peak_rss_mb = max(s.rss_mb for s in self.snapshots)
            self.peak_vms_mb = max(s.vms_mb for s in self.snapshots)
        else:
            self.peak_rss_mb = self.end_snapshot.rss_mb
            self.peak_vms_mb = self.end_snapshot.vms_mb

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'operation': self.operation_name,
            'start_rss_mb': round(self.start_snapshot.rss_mb, 2),
            'end_rss_mb': round(self.end_snapshot.rss_mb, 2),
            'delta_rss_mb': round(self.delta_rss_mb, 2),
            'peak_rss_mb': round(self.peak_rss_mb, 2),
            'duration_seconds': round(self.duration_seconds, 3),
            'memory_rate_mb_per_sec': round(
                self.delta_rss_mb / max(self.duration_seconds, 0.001), 2
            )
        }

    def __str__(self) -> str:
        """格式化输出"""
        sign = '+' if self.delta_rss_mb >= 0 else ''
        return (
            f"[内存监控] {self.operation_name}: "
            f"使用 {sign}{self.delta_rss_mb:.1f}MB, "
            f"峰值 {self.peak_rss_mb:.1f}MB, "
            f"当前 {self.end_snapshot.rss_mb:.1f}MB, "
            f"耗时 {self.duration_seconds:.2f}s"
        )


class MemoryProfiler:
    """
    内存分析器

    功能:
    - 监控代码块内存使用
    - 追踪峰值内存
    - 检测内存泄漏
    - 生成内存报告

    使用示例:
        profiler = MemoryProfiler()

        with profiler.profile("计算特征"):
            features = calculate_features(data)

        # 查看报告
        report = profiler.get_last_report()
        print(report)
    """

    def __init__(self, enable_tracking: bool = True):
        """
        初始化内存分析器

        参数:
            enable_tracking: 是否启用追踪
        """
        self.enable_tracking = enable_tracking
        self.process = psutil.Process(os.getpid())
        self.reports: List[MemoryUsageReport] = []
        self.lock = threading.Lock()

    @contextmanager
    def profile(
        self,
        operation_name: str,
        track_interval: float = 0.1,
        log_result: bool = True,
        force_gc_before: bool = False,
        force_gc_after: bool = False
    ):
        """
        内存分析上下文管理器

        参数:
            operation_name: 操作名称
            track_interval: 追踪间隔（秒）
            log_result: 是否记录日志
            force_gc_before: 操作前强制垃圾回收
            force_gc_after: 操作后强制垃圾回收

        用法:
            with profiler.profile("计算因子"):
                features = calculate_features(data)
        """
        if not self.enable_tracking:
            yield
            return

        # 操作前垃圾回收
        if force_gc_before:
            gc.collect()

        # 开始快照
        start_snapshot = self._take_snapshot(operation_name)

        # 追踪线程
        snapshots = []
        stop_tracking = threading.Event()

        def track_memory():
            while not stop_tracking.is_set():
                snapshot = self._take_snapshot(operation_name)
                snapshots.append(snapshot)
                time.sleep(track_interval)

        tracking_thread = None
        if track_interval > 0:
            tracking_thread = threading.Thread(target=track_memory, daemon=True)
            tracking_thread.start()

        try:
            yield

        finally:
            # 停止追踪
            if tracking_thread:
                stop_tracking.set()
                tracking_thread.join(timeout=1.0)

            # 操作后垃圾回收
            if force_gc_after:
                gc.collect()

            # 结束快照
            end_snapshot = self._take_snapshot(operation_name)

            # 生成报告
            report = MemoryUsageReport(
                operation_name=operation_name,
                start_snapshot=start_snapshot,
                end_snapshot=end_snapshot,
                snapshots=snapshots
            )

            with self.lock:
                self.reports.append(report)

            # 记录日志
            if log_result:
                logger.info(str(report))

    def _take_snapshot(self, operation: Optional[str] = None) -> MemorySnapshot:
        """获取内存快照"""
        mem_info = self.process.memory_info()
        vm_info = psutil.virtual_memory()

        return MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=mem_info.rss / 1024 / 1024,
            vms_mb=mem_info.vms / 1024 / 1024,
            percent=self.process.memory_percent(),
            available_mb=vm_info.available / 1024 / 1024,
            operation=operation
        )

    def get_current_memory_mb(self) -> float:
        """获取当前内存使用(MB)"""
        mem_info = self.process.memory_info()
        return mem_info.rss / 1024 / 1024

    def get_last_report(self) -> Optional[MemoryUsageReport]:
        """获取最后一次报告"""
        with self.lock:
            return self.reports[-1] if self.reports else None

    def get_all_reports(self) -> List[MemoryUsageReport]:
        """获取所有报告"""
        with self.lock:
            return self.reports.copy()

    def clear_reports(self):
        """清空报告"""
        with self.lock:
            self.reports.clear()

    def detect_memory_leak(
        self,
        func: Callable,
        iterations: int = 10,
        threshold_mb: float = 10.0
    ) -> Dict:
        """
        检测内存泄漏

        参数:
            func: 要检测的函数
            iterations: 迭代次数
            threshold_mb: 泄漏阈值(MB)

        返回:
            检测结果字典
        """
        logger.info(f"开始内存泄漏检测: {iterations}次迭代")

        snapshots = []

        for i in range(iterations):
            gc.collect()
            snapshot_before = self._take_snapshot(f"iteration_{i}")

            # 执行函数
            func()

            gc.collect()
            snapshot_after = self._take_snapshot(f"iteration_{i}")

            snapshots.append({
                'iteration': i,
                'before_mb': snapshot_before.rss_mb,
                'after_mb': snapshot_after.rss_mb,
                'delta_mb': snapshot_after.rss_mb - snapshot_before.rss_mb
            })

        # 分析趋势
        total_growth = snapshots[-1]['after_mb'] - snapshots[0]['before_mb']
        avg_growth_per_iter = total_growth / iterations

        has_leak = total_growth > threshold_mb

        result = {
            'has_leak': has_leak,
            'total_growth_mb': round(total_growth, 2),
            'avg_growth_per_iteration_mb': round(avg_growth_per_iter, 2),
            'iterations': iterations,
            'threshold_mb': threshold_mb,
            'snapshots': snapshots
        }

        if has_leak:
            logger.warning(
                f"检测到内存泄漏: "
                f"总增长 {total_growth:.1f}MB, "
                f"平均每次 {avg_growth_per_iter:.2f}MB"
            )
        else:
            logger.info(f"未检测到明显内存泄漏")

        return result


# 全局分析器实例
_global_profiler: Optional[MemoryProfiler] = None
_global_profiler_lock = threading.Lock()


def get_global_profiler() -> MemoryProfiler:
    """获取全局内存分析器（单例）"""
    global _global_profiler

    if _global_profiler is None:
        with _global_profiler_lock:
            if _global_profiler is None:
                _global_profiler = MemoryProfiler(enable_tracking=True)

    return _global_profiler


@contextmanager
def memory_profiler(
    operation_name: str,
    track_interval: float = 0.0,
    log_result: bool = True,
    force_gc: bool = False
):
    """
    内存分析上下文管理器（便捷函数）

    参数:
        operation_name: 操作名称
        track_interval: 追踪间隔（0=不追踪）
        log_result: 是否记录日志
        force_gc: 是否前后强制垃圾回收

    用法:
        with memory_profiler("计算因子"):
            features = calculate_features(data)

        # 输出:
        # [内存监控] 计算因子: 使用 +580.3MB, 峰值 2134.7MB, ...
    """
    profiler = get_global_profiler()

    with profiler.profile(
        operation_name=operation_name,
        track_interval=track_interval,
        log_result=log_result,
        force_gc_before=force_gc,
        force_gc_after=force_gc
    ):
        yield


def get_current_memory_usage() -> Dict:
    """
    获取当前内存使用情况（便捷函数）

    返回:
        内存使用字典
    """
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    vm_info = psutil.virtual_memory()

    return {
        'process_rss_mb': round(mem_info.rss / 1024 / 1024, 2),
        'process_vms_mb': round(mem_info.vms / 1024 / 1024, 2),
        'process_percent': round(process.memory_percent(), 2),
        'system_total_mb': round(vm_info.total / 1024 / 1024, 2),
        'system_available_mb': round(vm_info.available / 1024 / 1024, 2),
        'system_percent': round(vm_info.percent, 2)
    }


def log_memory_usage(prefix: str = ""):
    """
    记录当前内存使用（便捷函数）

    参数:
        prefix: 日志前缀
    """
    usage = get_current_memory_usage()
    logger.info(
        f"{prefix}内存使用: "
        f"进程 {usage['process_rss_mb']:.1f}MB "
        f"({usage['process_percent']:.1f}%), "
        f"系统可用 {usage['system_available_mb']:.1f}MB"
    )


class MemoryBudget:
    """
    内存预算管理器

    用于限制操作的内存使用上限

    使用示例:
        budget = MemoryBudget(max_mb=1000)

        with budget.allocate(500):  # 分配500MB预算
            # 执行操作
            pass

        # 如果超出预算会抛出异常
    """

    def __init__(self, max_mb: float):
        """
        初始化内存预算

        参数:
            max_mb: 最大内存预算(MB)
        """
        self.max_mb = max_mb
        self.allocated_mb = 0.0
        self.lock = threading.Lock()

    @contextmanager
    def allocate(self, required_mb: float):
        """
        分配内存预算

        参数:
            required_mb: 需要的内存(MB)
        """
        with self.lock:
            if self.allocated_mb + required_mb > self.max_mb:
                raise MemoryError(
                    f"内存预算不足: "
                    f"需要 {required_mb}MB, "
                    f"已用 {self.allocated_mb}MB, "
                    f"预算 {self.max_mb}MB"
                )

            self.allocated_mb += required_mb
            logger.debug(
                f"分配内存预算: {required_mb}MB "
                f"(已用 {self.allocated_mb}/{self.max_mb}MB)"
            )

        try:
            yield

        finally:
            with self.lock:
                self.allocated_mb -= required_mb
                logger.debug(
                    f"释放内存预算: {required_mb}MB "
                    f"(已用 {self.allocated_mb}/{self.max_mb}MB)"
                )

    def get_available_mb(self) -> float:
        """获取可用预算"""
        with self.lock:
            return self.max_mb - self.allocated_mb

    def reset(self):
        """重置预算"""
        with self.lock:
            self.allocated_mb = 0.0
