"""
统一监控系统

集成性能监控、日志记录和错误追踪功能。
"""

import time
import threading
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from .metrics_collector import MetricsCollector, MemoryMonitor, DatabaseMetricsCollector, MetricType
from .structured_logger import StructuredLogger, LogQueryEngine
from .error_tracker import ErrorTracker


class MonitoringSystem:
    """统一监控系统"""

    def __init__(
        self,
        log_dir: Path,
        service_name: str = "stock-analysis",
        db_manager=None,
        enable_background_monitoring: bool = True,
        monitoring_interval_seconds: int = 60
    ):
        """
        初始化监控系统

        Args:
            log_dir: 日志目录
            service_name: 服务名称
            db_manager: 数据库管理器(可选)
            enable_background_monitoring: 是否启用后台监控
            monitoring_interval_seconds: 后台监控间隔(秒)
        """
        self.service_name = service_name
        self.log_dir = Path(log_dir)
        self.db_manager = db_manager

        # 初始化各个组件
        self.metrics = MetricsCollector()
        self.logger = StructuredLogger(self.log_dir, service_name)
        self.error_tracker = ErrorTracker(db_manager)
        self.log_query = LogQueryEngine(self.log_dir)

        # 初始化内存监控(如果可用)
        try:
            self.memory_monitor = MemoryMonitor(self.metrics)
            self._memory_monitor_available = True
        except ImportError:
            self.memory_monitor = None
            self._memory_monitor_available = False
            self.logger.log_operation(
                "Memory monitoring disabled (psutil not installed)",
                level="WARNING"
            )

        # 初始化数据库监控
        self.db_metrics = DatabaseMetricsCollector(self.metrics)

        # 后台监控线程
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._monitoring_interval = monitoring_interval_seconds

        if enable_background_monitoring:
            self.start_background_monitoring()

        # 记录系统启动
        self.logger.log_operation(
            "Monitoring system initialized",
            level="INFO",
            service=service_name,
            memory_monitor_available=self._memory_monitor_available
        )

    def start_background_monitoring(self) -> None:
        """启动后台监控"""
        if self._monitoring_thread is not None and self._monitoring_thread.is_alive():
            return

        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="MonitoringThread"
        )
        self._monitoring_thread.start()

        self.logger.log_operation(
            "Background monitoring started",
            level="INFO",
            interval_seconds=self._monitoring_interval
        )

    def stop_background_monitoring(self) -> None:
        """停止后台监控"""
        if self._monitoring_thread is None:
            return

        self._stop_monitoring.set()
        self._monitoring_thread.join(timeout=5)

        self.logger.log_operation(
            "Background monitoring stopped",
            level="INFO"
        )

    def _monitoring_loop(self) -> None:
        """监控循环"""
        while not self._stop_monitoring.is_set():
            try:
                # 收集内存指标
                if self._memory_monitor_available:
                    self.memory_monitor.collect_memory_metrics()

                # 记录系统健康状态
                self._log_system_health()

            except Exception as e:
                self.error_tracker.track_error(
                    e,
                    severity=ErrorTracker.SEVERITY_WARNING,
                    module="monitoring_system",
                    function="_monitoring_loop"
                )

            # 等待下一次监控
            self._stop_monitoring.wait(self._monitoring_interval)

    def _log_system_health(self) -> None:
        """记录系统健康状态"""
        health_data = {}

        # 内存使用情况
        if self._memory_monitor_available:
            memory_usage = self.memory_monitor.get_current_memory_usage()
            health_data["memory"] = memory_usage

        # 错误统计
        error_stats = self.error_tracker.get_error_statistics(window_hours=1)
        health_data["errors_last_hour"] = error_stats.get("total_errors", 0)

        self.logger.log_operation(
            "System health check",
            level="DEBUG",
            **health_data
        )

    def track_operation(
        self,
        operation_name: str,
        func,
        *args,
        log_performance: bool = True,
        track_errors: bool = True,
        **kwargs
    ) -> Any:
        """
        追踪操作执行

        Args:
            operation_name: 操作名称
            func: 要执行的函数
            *args: 函数参数
            log_performance: 是否记录性能日志
            track_errors: 是否追踪错误
            **kwargs: 函数关键字参数

        Returns:
            函数返回值
        """
        start_time = time.perf_counter()
        error_occurred = None

        try:
            result = func(*args, **kwargs)

            # 记录成功
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.metrics.record_timing(
                operation=operation_name,
                duration_ms=duration_ms,
                success=True
            )

            if log_performance:
                self.logger.log_performance(
                    operation=operation_name,
                    duration_ms=duration_ms
                )

            return result

        except Exception as e:
            error_occurred = e
            duration_ms = (time.perf_counter() - start_time) * 1000

            # 记录失败
            self.metrics.record_timing(
                operation=operation_name,
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )

            if track_errors:
                self.error_tracker.track_error(
                    e,
                    severity=ErrorTracker.SEVERITY_ERROR,
                    operation=operation_name
                )

            self.logger.log_error(e, context={"operation": operation_name})

            raise

    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态概览

        Returns:
            系统状态信息
        """
        status = {
            "timestamp": datetime.now().isoformat(),
            "service": self.service_name,
        }

        # 内存状态
        if self._memory_monitor_available:
            status["memory"] = self.memory_monitor.get_current_memory_usage()

        # 错误统计
        error_summary = self.error_tracker.get_error_summary()
        status["errors"] = error_summary

        # 性能指标统计
        all_metrics = self.metrics.get_all_metrics()
        status["metrics_count"] = sum(len(v) for v in all_metrics.values())

        # 计时统计
        all_timings = self.metrics.get_all_timings()
        status["timing_records_count"] = len(all_timings)

        return status

    def get_performance_report(
        self,
        operation: Optional[str] = None,
        window_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        获取性能报告

        Args:
            operation: 操作名称(可选)
            window_minutes: 时间窗口(分钟)

        Returns:
            性能报告
        """
        if operation:
            timing_stats = self.metrics.get_timing_statistics(
                operation,
                window_minutes
            )
            return {
                "operation": operation,
                "window_minutes": window_minutes,
                "statistics": timing_stats
            }
        else:
            # 获取所有操作的统计
            all_timings = self.metrics.get_all_timings()
            operations = set(t.operation for t in all_timings)

            report = {
                "window_minutes": window_minutes,
                "operations": {}
            }

            for op in operations:
                stats = self.metrics.get_timing_statistics(op, window_minutes)
                if stats:
                    report["operations"][op] = stats

            return report

    def get_error_report(
        self,
        window_hours: int = 24,
        include_top_errors: bool = True,
        top_errors_limit: int = 10
    ) -> Dict[str, Any]:
        """
        获取错误报告

        Args:
            window_hours: 时间窗口(小时)
            include_top_errors: 是否包含高频错误
            top_errors_limit: 高频错误数量限制

        Returns:
            错误报告
        """
        report = {
            "window_hours": window_hours,
            "statistics": self.error_tracker.get_error_statistics(window_hours)
        }

        if include_top_errors:
            report["top_errors"] = self.error_tracker.get_top_errors(
                limit=top_errors_limit,
                window_hours=window_hours
            )

        return report

    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """
        清理旧数据

        Args:
            days_to_keep: 保留天数

        Returns:
            清理统计信息
        """
        cleanup_stats = {}

        # 清理错误记录
        errors_cleared = self.error_tracker.clear_old_errors(days_to_keep)
        cleanup_stats["errors_cleared"] = errors_cleared

        # 清理指标(重置保留期限)
        self.metrics._retention_days = days_to_keep
        self.metrics._cleanup_old_metrics()

        all_metrics = self.metrics.get_all_metrics()
        cleanup_stats["metrics_remaining"] = sum(len(v) for v in all_metrics.values())

        self.logger.log_operation(
            "Old data cleanup completed",
            level="INFO",
            days_to_keep=days_to_keep,
            **cleanup_stats
        )

        return cleanup_stats

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_background_monitoring()

        if exc_type is not None:
            self.error_tracker.track_error(
                exc_val,
                severity=ErrorTracker.SEVERITY_ERROR,
                module="monitoring_system",
                function="__exit__"
            )
            self.logger.log_error(exc_val)

        return False


# 全局监控系统实例(可选)
_global_monitoring: Optional[MonitoringSystem] = None


def get_global_monitoring() -> Optional[MonitoringSystem]:
    """
    获取全局监控系统实例

    Returns:
        全局监控系统实例
    """
    return _global_monitoring


def initialize_global_monitoring(
    log_dir: Path,
    service_name: str = "stock-analysis",
    db_manager=None,
    **kwargs
) -> MonitoringSystem:
    """
    初始化全局监控系统

    Args:
        log_dir: 日志目录
        service_name: 服务名称
        db_manager: 数据库管理器
        **kwargs: 其他参数

    Returns:
        监控系统实例
    """
    global _global_monitoring

    if _global_monitoring is not None:
        _global_monitoring.stop_background_monitoring()

    _global_monitoring = MonitoringSystem(
        log_dir=log_dir,
        service_name=service_name,
        db_manager=db_manager,
        **kwargs
    )

    return _global_monitoring


def shutdown_global_monitoring() -> None:
    """关闭全局监控系统"""
    global _global_monitoring

    if _global_monitoring is not None:
        _global_monitoring.stop_background_monitoring()
        _global_monitoring = None
