"""
Performance monitoring system for strategy loading and execution.

Tracks timing, resource usage, and system health metrics.
"""

import time
import psutil
import threading
from typing import Dict, Any, Optional, List, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from loguru import logger


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation."""

    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None

    # Resource usage
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0

    # Operation metadata
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finalize(self, success: bool = True, error: Optional[str] = None):
        """Finalize metrics when operation completes."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error

        # Capture final resource usage
        process = psutil.Process()
        self.cpu_percent = process.cpu_percent()
        mem_info = process.memory_info()
        self.memory_mb = mem_info.rss / 1024 / 1024
        self.memory_percent = process.memory_percent()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class PerformanceMonitor:
    """
    Performance monitoring system.

    Monitors and tracks performance metrics for:
    - Strategy loading (config/dynamic)
    - Strategy execution
    - Cache operations
    - Database queries

    Features:
    - Real-time monitoring
    - Historical metrics storage
    - Statistical analysis
    - Performance alerts
    """

    def __init__(
        self,
        enable_alerts: bool = True,
        slow_threshold_ms: float = 1000.0,
        memory_threshold_mb: float = 500.0
    ):
        """
        Initialize performance monitor.

        Args:
            enable_alerts: Enable performance alerts
            slow_threshold_ms: Threshold for slow operation alerts (ms)
            memory_threshold_mb: Threshold for high memory usage alerts (MB)
        """
        self.enable_alerts = enable_alerts
        self.slow_threshold_ms = slow_threshold_ms
        self.memory_threshold_mb = memory_threshold_mb

        # Metrics storage
        self._metrics_history: List[PerformanceMetrics] = []
        self._current_metrics: Dict[str, PerformanceMetrics] = {}
        self._lock = threading.Lock()

        # Statistics cache
        self._stats_cache: Dict[str, Any] = {}
        self._stats_cache_time: Optional[float] = None
        self._stats_cache_ttl = 60.0  # 60 seconds

        logger.info(f"Performance monitor initialized: alerts={enable_alerts}")

    @contextmanager
    def monitor(self, operation: str, **metadata):
        """
        Context manager for monitoring an operation.

        Usage:
            with monitor.monitor('load_strategy', strategy_id=123):
                strategy = loader.load_strategy(123)

        Args:
            operation: Operation name
            **metadata: Additional metadata to store
        """
        # Create metrics object
        metrics = PerformanceMetrics(
            operation=operation,
            start_time=time.time(),
            metadata=metadata
        )

        # Store current metrics
        thread_id = threading.get_ident()
        key = f"{thread_id}_{operation}"

        with self._lock:
            self._current_metrics[key] = metrics

        try:
            yield metrics

            # Operation succeeded
            metrics.finalize(success=True)

        except Exception as e:
            # Operation failed
            metrics.finalize(success=False, error=str(e))
            raise

        finally:
            # Save to history
            with self._lock:
                self._metrics_history.append(metrics)
                self._current_metrics.pop(key, None)

            # Check for alerts
            if self.enable_alerts:
                self._check_alerts(metrics)

            # Log metrics
            self._log_metrics(metrics)

    def _check_alerts(self, metrics: PerformanceMetrics):
        """Check if metrics exceed thresholds and log alerts."""
        alerts = []

        # Check duration
        if metrics.duration_ms and metrics.duration_ms > self.slow_threshold_ms:
            alerts.append(
                f"Slow operation: {metrics.operation} took {metrics.duration_ms:.2f}ms "
                f"(threshold: {self.slow_threshold_ms}ms)"
            )

        # Check memory
        if metrics.memory_mb > self.memory_threshold_mb:
            alerts.append(
                f"High memory usage: {metrics.operation} used {metrics.memory_mb:.2f}MB "
                f"(threshold: {self.memory_threshold_mb}MB)"
            )

        # Check failure
        if not metrics.success:
            alerts.append(
                f"Operation failed: {metrics.operation} - {metrics.error}"
            )

        # Log alerts
        for alert in alerts:
            logger.warning(f"⚠️ PERFORMANCE ALERT: {alert}")

    def _log_metrics(self, metrics: PerformanceMetrics):
        """Log metrics for an operation."""
        status = "✅" if metrics.success else "❌"

        logger.info(
            f"{status} {metrics.operation}: "
            f"duration={metrics.duration_ms:.2f}ms, "
            f"memory={metrics.memory_mb:.1f}MB, "
            f"cpu={metrics.cpu_percent:.1f}%"
        )

    def get_statistics(
        self,
        operation: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get performance statistics.

        Args:
            operation: Filter by operation name (None = all operations)
            use_cache: Use cached statistics if available

        Returns:
            Dictionary with statistics:
            - count: Number of operations
            - success_rate: Success rate (0-1)
            - avg_duration_ms: Average duration
            - p50_duration_ms: Median duration
            - p95_duration_ms: 95th percentile duration
            - p99_duration_ms: 99th percentile duration
            - avg_memory_mb: Average memory usage
            - total_errors: Total number of errors
        """
        # Check cache
        cache_key = operation or "all"
        if use_cache and self._is_cache_valid():
            if cache_key in self._stats_cache:
                return self._stats_cache[cache_key]

        # Filter metrics
        with self._lock:
            if operation:
                metrics_list = [
                    m for m in self._metrics_history
                    if m.operation == operation
                ]
            else:
                metrics_list = list(self._metrics_history)

        if not metrics_list:
            return {
                'count': 0,
                'success_rate': 0.0,
                'avg_duration_ms': 0.0,
                'p50_duration_ms': 0.0,
                'p95_duration_ms': 0.0,
                'p99_duration_ms': 0.0,
                'avg_memory_mb': 0.0,
                'total_errors': 0,
            }

        # Calculate statistics
        durations = sorted([m.duration_ms for m in metrics_list if m.duration_ms])
        memories = [m.memory_mb for m in metrics_list]
        successes = sum(1 for m in metrics_list if m.success)

        stats = {
            'count': len(metrics_list),
            'success_rate': successes / len(metrics_list) if metrics_list else 0.0,
            'avg_duration_ms': sum(durations) / len(durations) if durations else 0.0,
            'p50_duration_ms': self._percentile(durations, 0.50),
            'p95_duration_ms': self._percentile(durations, 0.95),
            'p99_duration_ms': self._percentile(durations, 0.99),
            'avg_memory_mb': sum(memories) / len(memories) if memories else 0.0,
            'total_errors': len(metrics_list) - successes,
        }

        # Update cache
        self._stats_cache[cache_key] = stats
        self._stats_cache_time = time.time()

        return stats

    def get_recent_metrics(
        self,
        operation: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent performance metrics.

        Args:
            operation: Filter by operation name
            limit: Maximum number of metrics to return

        Returns:
            List of metrics dictionaries
        """
        with self._lock:
            if operation:
                metrics_list = [
                    m for m in self._metrics_history
                    if m.operation == operation
                ]
            else:
                metrics_list = list(self._metrics_history)

        # Return most recent
        recent = metrics_list[-limit:] if len(metrics_list) > limit else metrics_list
        return [m.to_dict() for m in recent]

    def get_summary(self) -> Dict[str, Any]:
        """
        Get overall performance summary.

        Returns:
            Dictionary with summary statistics for all operations
        """
        with self._lock:
            total_operations = len(self._metrics_history)

            if total_operations == 0:
                return {
                    'total_operations': 0,
                    'operations_by_type': {},
                    'overall_success_rate': 0.0,
                    'total_errors': 0,
                }

            # Group by operation type
            operations_by_type = {}
            for metrics in self._metrics_history:
                op = metrics.operation
                if op not in operations_by_type:
                    operations_by_type[op] = {
                        'count': 0,
                        'successes': 0,
                        'failures': 0,
                    }

                operations_by_type[op]['count'] += 1
                if metrics.success:
                    operations_by_type[op]['successes'] += 1
                else:
                    operations_by_type[op]['failures'] += 1

            # Calculate overall success rate
            total_successes = sum(
                1 for m in self._metrics_history if m.success
            )
            overall_success_rate = total_successes / total_operations

            return {
                'total_operations': total_operations,
                'operations_by_type': operations_by_type,
                'overall_success_rate': overall_success_rate,
                'total_errors': total_operations - total_successes,
            }

    def clear_history(self, operation: Optional[str] = None):
        """
        Clear metrics history.

        Args:
            operation: Clear only this operation (None = clear all)
        """
        with self._lock:
            if operation:
                self._metrics_history = [
                    m for m in self._metrics_history
                    if m.operation != operation
                ]
            else:
                self._metrics_history.clear()

        # Clear cache
        self._stats_cache.clear()
        self._stats_cache_time = None

        logger.info(f"Cleared metrics history: operation={operation or 'all'}")

    def _percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int(len(sorted_data) * p)
        if index >= len(sorted_data):
            index = len(sorted_data) - 1

        return sorted_data[index]

    def _is_cache_valid(self) -> bool:
        """Check if statistics cache is still valid."""
        if self._stats_cache_time is None:
            return False

        elapsed = time.time() - self._stats_cache_time
        return elapsed < self._stats_cache_ttl


# Global singleton instance
_monitor = None
_monitor_lock = threading.Lock()


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _monitor

    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = PerformanceMonitor()

    return _monitor
