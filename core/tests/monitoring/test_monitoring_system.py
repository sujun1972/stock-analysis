"""
测试统一监控系统集成
"""

import pytest
import time
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.monitoring.monitoring_system import (
    MonitoringSystem,
    get_global_monitoring,
    initialize_global_monitoring,
    shutdown_global_monitoring
)
from src.monitoring.metrics_collector import MetricType


class TestMonitoringSystem:
    """测试MonitoringSystem"""

    def setup_method(self):
        """设置测试"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.monitoring = MonitoringSystem(
            log_dir=self.temp_dir,
            service_name="test-service",
            db_manager=None,
            enable_background_monitoring=False  # 测试时禁用后台监控
        )

    def teardown_method(self):
        """清理测试"""
        if hasattr(self, 'monitoring'):
            self.monitoring.stop_background_monitoring()

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_init(self):
        """测试初始化"""
        assert self.monitoring.service_name == "test-service"
        assert self.monitoring.log_dir == self.temp_dir
        assert self.monitoring.metrics is not None
        assert self.monitoring.logger is not None
        assert self.monitoring.error_tracker is not None
        assert self.monitoring.log_query is not None

    def test_components_integration(self):
        """测试组件集成"""
        # 各组件应该可用
        assert hasattr(self.monitoring, 'metrics')
        assert hasattr(self.monitoring, 'logger')
        assert hasattr(self.monitoring, 'error_tracker')
        assert hasattr(self.monitoring, 'db_metrics')

    def test_track_operation_success(self):
        """测试追踪操作(成功)"""
        def test_func(x, y):
            time.sleep(0.01)
            return x + y

        result = self.monitoring.track_operation(
            "test_operation",
            test_func,
            1, 2
        )

        assert result == 3

        # 检查计时记录
        timings = self.monitoring.metrics.get_all_timings()
        assert len(timings) == 1
        assert timings[0].operation == "test_operation"
        assert timings[0].success is True

    def test_track_operation_failure(self):
        """测试追踪操作(失败)"""
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            self.monitoring.track_operation(
                "failing_operation",
                failing_func
            )

        # 检查错误被追踪
        error_summary = self.monitoring.error_tracker.get_error_summary()
        assert error_summary["total_errors"] == 1

    def test_get_system_status(self):
        """测试获取系统状态"""
        # 先生成一些数据
        self.monitoring.metrics.record_metric("test", 100, MetricType.COUNTER)

        try:
            raise ValueError("Test error")
        except ValueError as e:
            self.monitoring.error_tracker.track_error(e)

        status = self.monitoring.get_system_status()

        assert "timestamp" in status
        assert "service" in status
        assert status["service"] == "test-service"
        assert "errors" in status
        assert "metrics_count" in status

    def test_get_performance_report(self):
        """测试获取性能报告"""
        # 记录一些性能数据
        for i in range(5):
            self.monitoring.metrics.record_timing(
                "test_op",
                duration_ms=100 + i * 10,
                success=True
            )

        report = self.monitoring.get_performance_report(
            operation="test_op",
            window_minutes=60
        )

        assert report["operation"] == "test_op"
        assert "statistics" in report
        assert report["statistics"]["count"] == 5

    def test_get_performance_report_all_operations(self):
        """测试获取所有操作的性能报告"""
        # 记录多个操作
        self.monitoring.metrics.record_timing("op1", 100, True)
        self.monitoring.metrics.record_timing("op2", 200, True)
        self.monitoring.metrics.record_timing("op1", 150, True)

        report = self.monitoring.get_performance_report()

        assert "operations" in report
        assert "op1" in report["operations"]
        assert "op2" in report["operations"]

    def test_get_error_report(self):
        """测试获取错误报告"""
        # 创建一些错误
        for i in range(3):
            try:
                raise ValueError(f"Error {i}")
            except ValueError as e:
                self.monitoring.error_tracker.track_error(e)

        report = self.monitoring.get_error_report(
            window_hours=24,
            include_top_errors=True
        )

        assert "statistics" in report
        assert "top_errors" in report
        assert report["statistics"]["total_errors"] == 3

    def test_cleanup_old_data(self):
        """测试清理旧数据"""
        # 创建一些数据
        self.monitoring.metrics.record_metric("test", 100, MetricType.COUNTER)

        try:
            raise ValueError("Test error")
        except ValueError as e:
            self.monitoring.error_tracker.track_error(e)

        cleanup_stats = self.monitoring.cleanup_old_data(days_to_keep=30)

        assert "errors_cleared" in cleanup_stats
        assert "metrics_remaining" in cleanup_stats

    def test_background_monitoring_start_stop(self):
        """测试后台监控启动和停止"""
        monitoring = MonitoringSystem(
            log_dir=self.temp_dir / "bg_test",
            enable_background_monitoring=True,
            monitoring_interval_seconds=1
        )

        # 等待一小段时间
        time.sleep(0.5)

        # 检查监控线程是否运行
        assert monitoring._monitoring_thread is not None
        assert monitoring._monitoring_thread.is_alive()

        # 停止监控
        monitoring.stop_background_monitoring()

        # 线程应该停止
        time.sleep(0.2)
        assert not monitoring._monitoring_thread.is_alive() or monitoring._stop_monitoring.is_set()

    def test_context_manager(self):
        """测试上下文管理器"""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            with MonitoringSystem(
                log_dir=temp_dir,
                enable_background_monitoring=False
            ) as monitoring:
                assert monitoring is not None
                monitoring.metrics.record_metric("test", 100, MetricType.COUNTER)

            # 退出后后台监控应该停止
            # (虽然我们禁用了后台监控，但测试逻辑)
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def test_context_manager_with_exception(self):
        """测试上下文管理器处理异常"""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            with MonitoringSystem(
                log_dir=temp_dir,
                enable_background_monitoring=False
            ) as monitoring:
                try:
                    raise ValueError("Test exception")
                except ValueError:
                    pass  # 在with块内捕获

            # 监控系统应该记录了错误
            # 注意：这里错误被内部捕获了，不会传播
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)


class TestGlobalMonitoring:
    """测试全局监控系统"""

    def teardown_method(self):
        """清理"""
        shutdown_global_monitoring()

    def test_initialize_global_monitoring(self):
        """测试初始化全局监控"""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            monitoring = initialize_global_monitoring(
                log_dir=temp_dir,
                service_name="global-test",
                enable_background_monitoring=False
            )

            assert monitoring is not None
            assert get_global_monitoring() == monitoring

        finally:
            shutdown_global_monitoring()
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def test_get_global_monitoring_before_init(self):
        """测试初始化前获取全局监控"""
        shutdown_global_monitoring()  # 确保清理
        assert get_global_monitoring() is None

    def test_shutdown_global_monitoring(self):
        """测试关闭全局监控"""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            initialize_global_monitoring(
                log_dir=temp_dir,
                enable_background_monitoring=False
            )

            assert get_global_monitoring() is not None

            shutdown_global_monitoring()

            assert get_global_monitoring() is None

        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def test_reinitialize_global_monitoring(self):
        """测试重新初始化全局监控"""
        temp_dir1 = Path(tempfile.mkdtemp())
        temp_dir2 = Path(tempfile.mkdtemp())

        try:
            # 第一次初始化
            monitoring1 = initialize_global_monitoring(
                log_dir=temp_dir1,
                service_name="service1",
                enable_background_monitoring=False
            )

            # 第二次初始化应该替换第一个
            monitoring2 = initialize_global_monitoring(
                log_dir=temp_dir2,
                service_name="service2",
                enable_background_monitoring=False
            )

            assert monitoring1 != monitoring2
            assert get_global_monitoring() == monitoring2
            assert monitoring2.service_name == "service2"

        finally:
            shutdown_global_monitoring()
            for dir_path in [temp_dir1, temp_dir2]:
                if dir_path.exists():
                    shutil.rmtree(dir_path)


class TestMonitoringSystemWithMemory:
    """测试带内存监控的监控系统"""

    def setup_method(self):
        """设置测试"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """清理测试"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_memory_monitoring_available(self):
        """测试内存监控可用性"""
        try:
            monitoring = MonitoringSystem(
                log_dir=self.temp_dir,
                enable_background_monitoring=False
            )

            if monitoring._memory_monitor_available:
                assert monitoring.memory_monitor is not None

                # 测试收集内存指标
                memory_data = monitoring.memory_monitor.collect_memory_metrics()
                assert "rss_mb" in memory_data

        except ImportError:
            pytest.skip("psutil not available")

    def test_system_health_logging(self):
        """测试系统健康日志"""
        monitoring = MonitoringSystem(
            log_dir=self.temp_dir,
            enable_background_monitoring=False
        )

        # 手动触发健康检查
        monitoring._log_system_health()

        # 这应该不会抛出异常
        time.sleep(0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
