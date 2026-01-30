"""
性能指标收集器

提供性能指标收集、计时统计、内存监控和数据库性能监控功能。
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import time
import functools
from collections import defaultdict
import threading
from enum import Enum

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 瞬时值
    HISTOGRAM = "histogram"  # 直方图
    TIMER = "timer"          # 计时器


@dataclass
class PerformanceMetric:
    """性能指标数据结构"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    metric_type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimingMetric:
    """计时指标"""
    operation: str
    duration_ms: float
    start_time: datetime
    end_time: datetime
    success: bool
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """性能指标收集器"""

    def __init__(self, retention_days: int = 7):
        """
        初始化指标收集器

        Args:
            retention_days: 指标保留天数
        """
        self._metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self._timings: List[TimingMetric] = []
        self._lock = threading.Lock()
        self._retention_days = retention_days

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None,
        **metadata
    ) -> None:
        """
        记录性能指标

        Args:
            name: 指标名称
            value: 指标值
            metric_type: 指标类型
            unit: 单位
            tags: 标签字典
            **metadata: 额外元数据
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            metric_type=metric_type,
            tags=tags or {},
            metadata=metadata
        )

        with self._lock:
            self._metrics[name].append(metric)
            self._cleanup_old_metrics()

    def record_timing(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None,
        **context
    ) -> None:
        """
        记录计时信息

        Args:
            operation: 操作名称
            duration_ms: 持续时间(毫秒)
            success: 是否成功
            error: 错误信息
            **context: 上下文信息
        """
        timing = TimingMetric(
            operation=operation,
            duration_ms=duration_ms,
            start_time=datetime.now() - timedelta(milliseconds=duration_ms),
            end_time=datetime.now(),
            success=success,
            error=error,
            context=context
        )

        with self._lock:
            self._timings.append(timing)
            # 清理旧的计时记录
            cutoff = datetime.now() - timedelta(days=self._retention_days)
            self._timings = [t for t in self._timings if t.end_time >= cutoff]

    def timer(self, operation: str, **context):
        """
        计时装饰器

        Args:
            operation: 操作名称
            **context: 上下文信息

        Returns:
            装饰器函数

        Example:
            @metrics.timer("calculate_features")
            def calculate_features(data):
                # 计算逻辑
                pass
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                error = None
                success = True

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error = str(e)
                    raise
                finally:
                    duration_ms = (time.perf_counter() - start) * 1000
                    self.record_timing(
                        operation=operation,
                        duration_ms=duration_ms,
                        success=success,
                        error=error,
                        **context
                    )

            return wrapper
        return decorator

    def get_statistics(
        self,
        name: str,
        window_minutes: int = 60
    ) -> Dict[str, float]:
        """
        获取指标统计信息

        Args:
            name: 指标名称
            window_minutes: 时间窗口(分钟)

        Returns:
            统计信息字典，包含count, min, max, mean, p50, p95, p99
        """
        cutoff = datetime.now() - timedelta(minutes=window_minutes)

        with self._lock:
            recent_metrics = [
                m for m in self._metrics.get(name, [])
                if m.timestamp >= cutoff
            ]

        if not recent_metrics:
            return {}

        values = [m.value for m in recent_metrics]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }

    def get_timing_statistics(
        self,
        operation: str,
        window_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        获取操作计时统计

        Args:
            operation: 操作名称
            window_minutes: 时间窗口(分钟)

        Returns:
            计时统计信息
        """
        cutoff = datetime.now() - timedelta(minutes=window_minutes)

        with self._lock:
            recent_timings = [
                t for t in self._timings
                if t.operation == operation and t.end_time >= cutoff
            ]

        if not recent_timings:
            return {}

        durations = [t.duration_ms for t in recent_timings]
        success_count = sum(1 for t in recent_timings if t.success)

        return {
            "count": len(recent_timings),
            "success_count": success_count,
            "failure_count": len(recent_timings) - success_count,
            "success_rate": success_count / len(recent_timings),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "mean_ms": sum(durations) / len(durations),
            "p50_ms": self._percentile(durations, 50),
            "p95_ms": self._percentile(durations, 95),
            "p99_ms": self._percentile(durations, 99),
        }

    def get_all_metrics(self) -> Dict[str, List[PerformanceMetric]]:
        """
        获取所有指标

        Returns:
            指标字典
        """
        with self._lock:
            return dict(self._metrics)

    def get_all_timings(self) -> List[TimingMetric]:
        """
        获取所有计时记录

        Returns:
            计时记录列表
        """
        with self._lock:
            return list(self._timings)

    def clear_metrics(self) -> None:
        """清空所有指标"""
        with self._lock:
            self._metrics.clear()
            self._timings.clear()

    def _cleanup_old_metrics(self) -> None:
        """清理过期指标"""
        cutoff = datetime.now() - timedelta(days=self._retention_days)

        for name in list(self._metrics.keys()):
            self._metrics[name] = [
                m for m in self._metrics[name]
                if m.timestamp >= cutoff
            ]

            # 如果列表为空，删除该key
            if not self._metrics[name]:
                del self._metrics[name]

    @staticmethod
    def _percentile(values: List[float], p: int) -> float:
        """
        计算百分位数

        Args:
            values: 数值列表
            p: 百分位(0-100)

        Returns:
            百分位数值
        """
        if not values:
            return 0.0

        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * p / 100
        f = int(k)
        c = f + 1

        if c >= len(sorted_values):
            return sorted_values[-1]

        d0 = sorted_values[f] * (c - k)
        d1 = sorted_values[c] * (k - f)
        return d0 + d1


class MemoryMonitor:
    """内存监控器"""

    def __init__(self, metrics_collector: MetricsCollector):
        """
        初始化内存监控器

        Args:
            metrics_collector: 指标收集器实例
        """
        if not PSUTIL_AVAILABLE:
            raise ImportError("psutil is required for MemoryMonitor. Install it with: pip install psutil")

        self.metrics = metrics_collector
        self.process = psutil.Process()

    def collect_memory_metrics(self) -> Dict[str, float]:
        """
        收集内存指标

        Returns:
            内存指标字典
        """
        mem_info = self.process.memory_info()

        # RSS (Resident Set Size) - 实际物理内存
        rss_mb = mem_info.rss / 1024 / 1024
        self.metrics.record_metric(
            "memory_rss_mb",
            rss_mb,
            MetricType.GAUGE,
            unit="MB"
        )

        # VMS (Virtual Memory Size) - 虚拟内存
        vms_mb = mem_info.vms / 1024 / 1024
        self.metrics.record_metric(
            "memory_vms_mb",
            vms_mb,
            MetricType.GAUGE,
            unit="MB"
        )

        # 系统内存
        sys_mem = psutil.virtual_memory()
        self.metrics.record_metric(
            "system_memory_percent",
            sys_mem.percent,
            MetricType.GAUGE,
            unit="%"
        )

        return {
            "rss_mb": rss_mb,
            "vms_mb": vms_mb,
            "system_memory_percent": sys_mem.percent,
        }

    def get_current_memory_usage(self) -> Dict[str, float]:
        """
        获取当前内存使用情况

        Returns:
            内存使用字典
        """
        mem_info = self.process.memory_info()
        sys_mem = psutil.virtual_memory()

        return {
            "process_rss_mb": mem_info.rss / 1024 / 1024,
            "process_vms_mb": mem_info.vms / 1024 / 1024,
            "system_total_mb": sys_mem.total / 1024 / 1024,
            "system_available_mb": sys_mem.available / 1024 / 1024,
            "system_percent": sys_mem.percent,
        }


class DatabaseMetricsCollector:
    """数据库指标收集器"""

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        slow_query_threshold_ms: float = 1000.0
    ):
        """
        初始化数据库指标收集器

        Args:
            metrics_collector: 指标收集器实例
            slow_query_threshold_ms: 慢查询阈值(毫秒)
        """
        self.metrics = metrics_collector
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self._slow_queries: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def track_query(self, query: str, query_type: Optional[str] = None):
        """
        追踪数据库查询装饰器

        Args:
            query: 查询SQL
            query_type: 查询类型(SELECT, INSERT, UPDATE等)

        Returns:
            装饰器函数

        Example:
            @db_metrics.track_query("SELECT * FROM stocks")
            def get_stocks():
                # 查询逻辑
                pass
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()

                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.perf_counter() - start) * 1000

                    # 提取查询类型
                    if query_type is None:
                        detected_type = query.strip().split()[0].upper()
                    else:
                        detected_type = query_type

                    is_slow = duration_ms > self.slow_query_threshold_ms

                    # 记录查询性能
                    self.metrics.record_timing(
                        operation="database_query",
                        duration_ms=duration_ms,
                        query_type=detected_type,
                        is_slow=is_slow
                    )

                    # 记录慢查询
                    if is_slow:
                        self._log_slow_query(query, duration_ms, detected_type)

            return wrapper
        return decorator

    def record_query_metrics(
        self,
        query_type: str,
        duration_ms: float,
        rows_affected: Optional[int] = None
    ) -> None:
        """
        手动记录查询指标

        Args:
            query_type: 查询类型
            duration_ms: 持续时间(毫秒)
            rows_affected: 影响的行数
        """
        is_slow = duration_ms > self.slow_query_threshold_ms

        context = {"query_type": query_type, "is_slow": is_slow}
        if rows_affected is not None:
            context["rows_affected"] = rows_affected

        self.metrics.record_timing(
            operation="database_query",
            duration_ms=duration_ms,
            **context
        )

        # 记录慢查询
        if is_slow:
            self._log_slow_query(f"{query_type} query", duration_ms, query_type)

    def _log_slow_query(
        self,
        query: str,
        duration_ms: float,
        query_type: str
    ) -> None:
        """
        记录慢查询

        Args:
            query: 查询SQL
            duration_ms: 持续时间(毫秒)
            query_type: 查询类型
        """
        slow_query_info = {
            "query": query,
            "duration_ms": duration_ms,
            "query_type": query_type,
            "timestamp": datetime.now(),
        }

        with self._lock:
            self._slow_queries.append(slow_query_info)

            # 只保留最近1000条慢查询
            if len(self._slow_queries) > 1000:
                self._slow_queries = self._slow_queries[-1000:]

    def get_slow_queries(
        self,
        limit: int = 100,
        min_duration_ms: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        获取慢查询列表

        Args:
            limit: 返回数量限制
            min_duration_ms: 最小持续时间筛选

        Returns:
            慢查询列表
        """
        with self._lock:
            queries = list(self._slow_queries)

        if min_duration_ms is not None:
            queries = [q for q in queries if q["duration_ms"] >= min_duration_ms]

        # 按持续时间降序排序
        queries.sort(key=lambda x: x["duration_ms"], reverse=True)

        return queries[:limit]

    def get_query_statistics(
        self,
        window_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        获取查询统计信息

        Args:
            window_minutes: 时间窗口(分钟)

        Returns:
            查询统计信息
        """
        stats = self.metrics.get_timing_statistics(
            "database_query",
            window_minutes
        )

        if not stats:
            return {}

        # 统计慢查询
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        with self._lock:
            recent_slow = [
                q for q in self._slow_queries
                if q["timestamp"] >= cutoff
            ]

        stats["slow_query_count"] = len(recent_slow)
        stats["slow_query_rate"] = (
            len(recent_slow) / stats["count"] if stats["count"] > 0 else 0
        )

        return stats
