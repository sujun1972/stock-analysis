"""
测试性能指标收集器
"""

import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.monitoring.metrics_collector import (
    MetricsCollector,
    MemoryMonitor,
    DatabaseMetricsCollector,
    MetricType,
    PerformanceMetric,
    TimingMetric,
)


class TestMetricsCollector:
    """测试MetricsCollector"""

    def setup_method(self):
        """设置测试"""
        self.collector = MetricsCollector(retention_days=7)

    def test_init(self):
        """测试初始化"""
        assert self.collector._retention_days == 7
        assert len(self.collector._metrics) == 0
        assert len(self.collector._timings) == 0

    def test_record_metric(self):
        """测试记录指标"""
        self.collector.record_metric(
            name="test_counter",
            value=100,
            metric_type=MetricType.COUNTER,
            unit="requests",
            tags={"service": "test"}
        )

        metrics = self.collector.get_all_metrics()
        assert "test_counter" in metrics
        assert len(metrics["test_counter"]) == 1

        metric = metrics["test_counter"][0]
        assert metric.name == "test_counter"
        assert metric.value == 100
        assert metric.unit == "requests"
        assert metric.metric_type == MetricType.COUNTER
        assert metric.tags["service"] == "test"

    def test_record_multiple_metrics(self):
        """测试记录多个指标"""
        for i in range(5):
            self.collector.record_metric(
                name="test_gauge",
                value=i * 10,
                metric_type=MetricType.GAUGE
            )

        metrics = self.collector.get_all_metrics()
        assert len(metrics["test_gauge"]) == 5

    def test_record_timing(self):
        """测试记录计时"""
        self.collector.record_timing(
            operation="test_operation",
            duration_ms=100.5,
            success=True
        )

        timings = self.collector.get_all_timings()
        assert len(timings) == 1

        timing = timings[0]
        assert timing.operation == "test_operation"
        assert timing.duration_ms == 100.5
        assert timing.success is True
        assert timing.error is None

    def test_record_timing_with_error(self):
        """测试记录失败的计时"""
        self.collector.record_timing(
            operation="failed_operation",
            duration_ms=50.0,
            success=False,
            error="Test error"
        )

        timings = self.collector.get_all_timings()
        assert len(timings) == 1

        timing = timings[0]
        assert timing.success is False
        assert timing.error == "Test error"

    def test_timer_decorator_success(self):
        """测试计时装饰器(成功)"""
        @self.collector.timer("decorated_operation")
        def test_func(x, y):
            time.sleep(0.01)  # 10ms
            return x + y

        result = test_func(1, 2)
        assert result == 3

        timings = self.collector.get_all_timings()
        assert len(timings) == 1

        timing = timings[0]
        assert timing.operation == "decorated_operation"
        assert timing.duration_ms >= 10  # 至少10ms
        assert timing.success is True

    def test_timer_decorator_failure(self):
        """测试计时装饰器(失败)"""
        @self.collector.timer("failing_operation")
        def failing_func():
            time.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

        timings = self.collector.get_all_timings()
        assert len(timings) == 1

        timing = timings[0]
        assert timing.operation == "failing_operation"
        assert timing.success is False
        assert "Test error" in timing.error

    def test_get_statistics(self):
        """测试获取统计信息"""
        # 记录多个指标
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for value in values:
            self.collector.record_metric(
                name="test_metric",
                value=value,
                metric_type=MetricType.GAUGE
            )

        stats = self.collector.get_statistics("test_metric")

        assert stats["count"] == 10
        assert stats["min"] == 10
        assert stats["max"] == 100
        assert stats["mean"] == 55
        assert stats["p50"] > 40 and stats["p50"] < 60
        assert stats["p95"] > 90
        assert stats["p99"] > 90

    def test_get_statistics_empty(self):
        """测试获取空指标的统计"""
        stats = self.collector.get_statistics("nonexistent_metric")
        assert stats == {}

    def test_get_timing_statistics(self):
        """测试获取计时统计"""
        # 记录多个计时
        for i in range(10):
            self.collector.record_timing(
                operation="test_op",
                duration_ms=100 + i * 10,
                success=i % 2 == 0  # 偶数成功
            )

        stats = self.collector.get_timing_statistics("test_op")

        assert stats["count"] == 10
        assert stats["success_count"] == 5
        assert stats["failure_count"] == 5
        assert stats["success_rate"] == 0.5
        assert stats["min_ms"] == 100
        assert stats["max_ms"] == 190

    def test_clear_metrics(self):
        """测试清空指标"""
        self.collector.record_metric("test", 100, MetricType.COUNTER)
        self.collector.record_timing("test_op", 50)

        assert len(self.collector.get_all_metrics()) > 0
        assert len(self.collector.get_all_timings()) > 0

        self.collector.clear_metrics()

        assert len(self.collector.get_all_metrics()) == 0
        assert len(self.collector.get_all_timings()) == 0

    def test_percentile_calculation(self):
        """测试百分位数计算"""
        values = list(range(1, 101))  # 1到100

        p50 = MetricsCollector._percentile(values, 50)
        assert 49 <= p50 <= 51

        p95 = MetricsCollector._percentile(values, 95)
        assert 94 <= p95 <= 96

        p99 = MetricsCollector._percentile(values, 99)
        assert 98 <= p99 <= 100

    def test_percentile_edge_cases(self):
        """测试百分位数边缘情况"""
        # 空列表
        assert MetricsCollector._percentile([], 50) == 0.0

        # 单个值
        assert MetricsCollector._percentile([42], 50) == 42

        # 两个值
        values = [10, 20]
        p50 = MetricsCollector._percentile(values, 50)
        assert 10 <= p50 <= 20


class TestMemoryMonitor:
    """测试MemoryMonitor"""

    def setup_method(self):
        """设置测试"""
        self.collector = MetricsCollector()

    def test_init(self):
        """测试初始化"""
        try:
            monitor = MemoryMonitor(self.collector)
            assert monitor.metrics == self.collector
            assert monitor.process is not None
        except ImportError:
            pytest.skip("psutil not available")

    def test_collect_memory_metrics(self):
        """测试收集内存指标"""
        try:
            monitor = MemoryMonitor(self.collector)
            memory_data = monitor.collect_memory_metrics()

            assert "rss_mb" in memory_data
            assert "vms_mb" in memory_data
            assert "system_memory_percent" in memory_data

            assert memory_data["rss_mb"] > 0
            assert memory_data["vms_mb"] > 0
            assert 0 <= memory_data["system_memory_percent"] <= 100

            # 检查指标是否被记录
            metrics = self.collector.get_all_metrics()
            assert "memory_rss_mb" in metrics
            assert "memory_vms_mb" in metrics
            assert "system_memory_percent" in metrics

        except ImportError:
            pytest.skip("psutil not available")

    def test_get_current_memory_usage(self):
        """测试获取当前内存使用"""
        try:
            monitor = MemoryMonitor(self.collector)
            usage = monitor.get_current_memory_usage()

            assert "process_rss_mb" in usage
            assert "process_vms_mb" in usage
            assert "system_total_mb" in usage
            assert "system_available_mb" in usage
            assert "system_percent" in usage

            assert usage["process_rss_mb"] > 0
            assert usage["system_total_mb"] > 0

        except ImportError:
            pytest.skip("psutil not available")


class TestDatabaseMetricsCollector:
    """测试DatabaseMetricsCollector"""

    def setup_method(self):
        """设置测试"""
        self.collector = MetricsCollector()
        self.db_metrics = DatabaseMetricsCollector(self.collector)

    def test_init(self):
        """测试初始化"""
        assert self.db_metrics.metrics == self.collector
        assert self.db_metrics.slow_query_threshold_ms == 1000.0

    def test_init_custom_threshold(self):
        """测试自定义慢查询阈值"""
        db_metrics = DatabaseMetricsCollector(self.collector, slow_query_threshold_ms=500.0)
        assert db_metrics.slow_query_threshold_ms == 500.0

    def test_track_query_decorator(self):
        """测试查询追踪装饰器"""
        @self.db_metrics.track_query("SELECT * FROM stocks")
        def mock_query():
            time.sleep(0.01)  # 10ms
            return "result"

        result = mock_query()
        assert result == "result"

        timings = self.collector.get_all_timings()
        assert len(timings) == 1

        timing = timings[0]
        assert timing.operation == "database_query"
        assert timing.duration_ms >= 10

    def test_record_query_metrics(self):
        """测试记录查询指标"""
        self.db_metrics.record_query_metrics(
            query_type="SELECT",
            duration_ms=50.0,
            rows_affected=100
        )

        timings = self.collector.get_all_timings()
        assert len(timings) == 1

        timing = timings[0]
        assert timing.operation == "database_query"
        assert timing.context["query_type"] == "SELECT"
        assert timing.context["rows_affected"] == 100

    def test_slow_query_detection(self):
        """测试慢查询检测"""
        # 快查询
        self.db_metrics.record_query_metrics("SELECT", duration_ms=100.0)

        # 慢查询
        self.db_metrics.record_query_metrics("SELECT", duration_ms=2000.0)

        timings = self.collector.get_all_timings()
        assert len(timings) == 2

        # 检查慢查询标记
        slow_timing = [t for t in timings if t.duration_ms == 2000.0][0]
        assert slow_timing.context["is_slow"] is True

        fast_timing = [t for t in timings if t.duration_ms == 100.0][0]
        assert fast_timing.context["is_slow"] is False

    def test_get_slow_queries(self):
        """测试获取慢查询列表"""
        # 记录一些慢查询
        self.db_metrics.record_query_metrics("SELECT", duration_ms=1500.0)
        self.db_metrics.record_query_metrics("UPDATE", duration_ms=2000.0)
        self.db_metrics.record_query_metrics("INSERT", duration_ms=800.0)

        slow_queries = self.db_metrics.get_slow_queries()

        # 应该只有2个慢查询(>1000ms)
        assert len(slow_queries) == 2

        # 按持续时间降序
        assert slow_queries[0]["duration_ms"] == 2000.0
        assert slow_queries[1]["duration_ms"] == 1500.0

    def test_get_slow_queries_with_filter(self):
        """测试获取慢查询(带过滤)"""
        self.db_metrics.record_query_metrics("SELECT", duration_ms=1200.0)
        self.db_metrics.record_query_metrics("UPDATE", duration_ms=1800.0)

        # 只获取超过1500ms的
        slow_queries = self.db_metrics.get_slow_queries(min_duration_ms=1500.0)

        assert len(slow_queries) == 1
        assert slow_queries[0]["duration_ms"] == 1800.0

    def test_get_query_statistics(self):
        """测试获取查询统计"""
        # 记录多个查询
        for i in range(10):
            self.db_metrics.record_query_metrics(
                "SELECT",
                duration_ms=1000 + i * 100
            )

        stats = self.db_metrics.get_query_statistics()

        assert stats["count"] == 10
        assert stats["slow_query_count"] >= 0
        assert "slow_query_rate" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
