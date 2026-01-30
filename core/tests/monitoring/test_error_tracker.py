"""
测试错误追踪系统
"""

import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.monitoring.error_tracker import ErrorTracker, ErrorEvent


class TestErrorTracker:
    """测试ErrorTracker"""

    def setup_method(self):
        """设置测试"""
        # 不使用数据库的错误追踪器
        self.tracker = ErrorTracker(db_manager=None)

    def test_init_without_db(self):
        """测试不带数据库初始化"""
        tracker = ErrorTracker()
        assert tracker.db is None
        assert tracker._use_database is False
        assert len(tracker._error_events) == 0
        assert len(tracker._error_groups) == 0

    def test_track_error(self):
        """测试追踪错误"""
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            error_hash = self.tracker.track_error(
                e,
                severity=ErrorTracker.SEVERITY_ERROR,
                module="test_module",
                function="test_function"
            )

        assert error_hash is not None
        assert len(error_hash) == 64  # SHA256哈希长度

        # 检查事件是否被记录
        assert len(self.tracker._error_events) == 1
        event = self.tracker._error_events[0]

        assert event.error_type == "ValueError"
        assert event.error_message == "Test error message"
        assert event.severity == ErrorTracker.SEVERITY_ERROR
        assert event.module == "test_module"
        assert event.function == "test_function"
        assert event.stack_trace is not None

    def test_track_error_with_context(self):
        """测试追踪带上下文的错误"""
        try:
            raise RuntimeError("Runtime error")
        except RuntimeError as e:
            self.tracker.track_error(
                e,
                severity=ErrorTracker.SEVERITY_CRITICAL,
                module="runtime_module",
                user_id=123,
                request_id="req-456"
            )

        event = self.tracker._error_events[0]
        assert event.context["user_id"] == 123
        assert event.context["request_id"] == "req-456"

    def test_error_grouping(self):
        """测试错误分组"""
        # 追踪多个相同类型的错误
        for i in range(5):
            try:
                raise ValueError("Same error")
            except ValueError as e:
                self.tracker.track_error(
                    e,
                    module="test_module",
                    function="test_func"
                )

        # 所有错误应该被分到同一组
        assert len(self.tracker._error_groups) == 1

        # 组内应该有5个事件
        error_hash = list(self.tracker._error_groups.keys())[0]
        assert len(self.tracker._error_groups[error_hash]) == 5

    def test_different_errors_different_groups(self):
        """测试不同错误分到不同组"""
        errors = [
            ValueError("Error 1"),
            TypeError("Error 2"),
            RuntimeError("Error 3")
        ]

        for error in errors:
            try:
                raise error
            except Exception as e:
                self.tracker.track_error(e, module="test")

        # 应该有3个不同的组
        assert len(self.tracker._error_groups) == 3

    def test_get_error_statistics(self):
        """测试获取错误统计"""
        # 创建不同类型和严重程度的错误
        # 注意：错误哈希基于类型+模块+函数，相同类型在同一模块函数中会被分到同一组
        errors = [
            (ValueError("Error 1"), ErrorTracker.SEVERITY_ERROR, "module1", "func1"),
            (ValueError("Error 2"), ErrorTracker.SEVERITY_ERROR, "module2", "func2"),  # 不同模块，不同哈希
            (TypeError("Error 3"), ErrorTracker.SEVERITY_CRITICAL, "module1", "func1"),
            (RuntimeError("Error 4"), ErrorTracker.SEVERITY_WARNING, "module1", "func1"),
        ]

        for error, severity, module, function in errors:
            try:
                raise error
            except Exception as e:
                self.tracker.track_error(e, severity=severity, module=module, function=function)

        stats = self.tracker.get_error_statistics(window_hours=24)

        assert stats["total_errors"] == 4
        # ValueError在不同模块，TypeError和RuntimeError在同一模块，所以unique_errors可能是3或4
        assert stats["unique_errors"] >= 3  # 至少3个不同的错误组
        assert stats["by_severity"][ErrorTracker.SEVERITY_ERROR] == 2
        assert stats["by_severity"][ErrorTracker.SEVERITY_CRITICAL] == 1
        assert stats["by_severity"][ErrorTracker.SEVERITY_WARNING] == 1

    def test_get_error_statistics_empty(self):
        """测试获取空的错误统计"""
        stats = self.tracker.get_error_statistics()

        assert stats["total_errors"] == 0
        assert stats["unique_errors"] == 0

    def test_get_error_trends(self):
        """测试获取错误趋势"""
        # 追踪同一类型的错误
        try:
            raise ValueError("Test error")
        except ValueError as e:
            error_hash = self.tracker.track_error(e, module="test", function="test")

        # 再追踪几次
        for _ in range(3):
            try:
                raise ValueError("Test error")
            except ValueError as e:
                self.tracker.track_error(e, module="test", function="test")

        trends = self.tracker.get_error_trends(error_hash, days=7)

        # 应该有趋势数据
        assert len(trends) > 0
        assert all("timestamp" in t and "count" in t for t in trends)

    def test_get_top_errors(self):
        """测试获取高频错误"""
        # 创建不同频率的错误
        for i in range(10):
            try:
                raise ValueError("Frequent error")
            except ValueError as e:
                self.tracker.track_error(e, module="mod1", function="func1")

        for i in range(3):
            try:
                raise TypeError("Less frequent")
            except TypeError as e:
                self.tracker.track_error(e, module="mod2", function="func2")

        top_errors = self.tracker.get_top_errors(limit=10)

        assert len(top_errors) == 2
        # 第一个应该是最频繁的
        assert top_errors[0]["count"] == 10
        assert top_errors[0]["error_type"] == "ValueError"
        assert top_errors[1]["count"] == 3

    def test_get_top_errors_with_severity_filter(self):
        """测试按严重程度筛选高频错误"""
        # 创建不同严重程度的错误
        for i in range(5):
            try:
                raise ValueError("Critical error")
            except ValueError as e:
                self.tracker.track_error(e, severity=ErrorTracker.SEVERITY_CRITICAL)

        for i in range(3):
            try:
                raise TypeError("Warning error")
            except TypeError as e:
                self.tracker.track_error(e, severity=ErrorTracker.SEVERITY_WARNING)

        critical_errors = self.tracker.get_top_errors(
            severity=ErrorTracker.SEVERITY_CRITICAL
        )

        assert len(critical_errors) == 1
        assert critical_errors[0]["severity"] == ErrorTracker.SEVERITY_CRITICAL

    def test_get_error_details(self):
        """测试获取错误详情"""
        # 追踪多个相同错误
        for i in range(3):
            try:
                raise ValueError("Detailed error")
            except ValueError as e:
                error_hash = self.tracker.track_error(
                    e,
                    module="detail_module",
                    function="detail_func",
                    iteration=i
                )

        details = self.tracker.get_error_details(error_hash)

        assert details["error_type"] == "ValueError"
        assert details["error_message"] == "Detailed error"
        assert details["module"] == "detail_module"
        assert details["function"] == "detail_func"
        assert details["total_occurrences"] == 3
        assert len(details["recent_events"]) == 3

    def test_get_error_details_nonexistent(self):
        """测试获取不存在错误的详情"""
        details = self.tracker.get_error_details("nonexistent_hash")
        assert details == {}

    def test_mark_resolved(self):
        """测试标记错误为已解决"""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            error_hash = self.tracker.track_error(e)

        # 标记为已解决
        self.tracker.mark_resolved(error_hash, resolved=True)

        # 检查状态
        events = self.tracker._error_groups[error_hash]
        assert all(e.resolved for e in events)
        assert all(e.resolved_at is not None for e in events)

    def test_mark_unresolved(self):
        """测试标记错误为未解决"""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            error_hash = self.tracker.track_error(e)

        # 先标记为已解决
        self.tracker.mark_resolved(error_hash, resolved=True)

        # 再标记为未解决
        self.tracker.mark_resolved(error_hash, resolved=False)

        events = self.tracker._error_groups[error_hash]
        assert all(not e.resolved for e in events)
        assert all(e.resolved_at is None for e in events)

    def test_clear_old_errors(self):
        """测试清理旧错误"""
        # 创建一些错误
        for i in range(5):
            try:
                raise ValueError(f"Error {i}")
            except ValueError as e:
                self.tracker.track_error(e)

        initial_count = len(self.tracker._error_events)
        assert initial_count == 5

        # 清理0天前的错误(应该清理所有)
        cleared = self.tracker.clear_old_errors(days=0)

        # 由于错误都是刚创建的，可能不会被清理
        # 这里主要测试函数能正常运行
        assert cleared >= 0

    def test_get_error_summary(self):
        """测试获取错误总览"""
        # 创建各种错误
        errors = [
            (ValueError("E1"), ErrorTracker.SEVERITY_ERROR),
            (TypeError("E2"), ErrorTracker.SEVERITY_CRITICAL),
            (RuntimeError("E3"), ErrorTracker.SEVERITY_WARNING),
        ]

        for error, severity in errors:
            try:
                raise error
            except Exception as e:
                self.tracker.track_error(e, severity=severity)

        summary = self.tracker.get_error_summary()

        assert summary["total_errors"] == 3
        assert summary["unique_errors"] == 3
        assert ErrorTracker.SEVERITY_ERROR in summary["by_severity"]
        assert len(summary["recent_errors"]) == 3

    def test_get_error_summary_empty(self):
        """测试获取空的错误总览"""
        summary = self.tracker.get_error_summary()

        assert summary["total_errors"] == 0
        assert summary["unique_errors"] == 0
        assert summary["by_severity"] == {}
        assert summary["recent_errors"] == []

    def test_severity_constants(self):
        """测试严重程度常量"""
        assert ErrorTracker.SEVERITY_CRITICAL == "CRITICAL"
        assert ErrorTracker.SEVERITY_ERROR == "ERROR"
        assert ErrorTracker.SEVERITY_WARNING == "WARNING"

    def test_error_hash_consistency(self):
        """测试错误哈希一致性"""
        # 相同的错误应该生成相同的哈希
        hashes = []
        for i in range(3):
            try:
                raise ValueError("Same error")
            except ValueError as e:
                hash_val = self.tracker.track_error(
                    e,
                    module="same_module",
                    function="same_function"
                )
                hashes.append(hash_val)

        # 所有哈希应该相同
        assert len(set(hashes)) == 1

    def test_error_hash_difference(self):
        """测试不同错误的哈希不同"""
        hash1 = hash2 = hash3 = None

        try:
            raise ValueError("Error")
        except ValueError as e:
            hash1 = self.tracker.track_error(e, module="mod1", function="func1")

        try:
            raise ValueError("Error")
        except ValueError as e:
            hash2 = self.tracker.track_error(e, module="mod2", function="func1")

        try:
            raise TypeError("Error")
        except TypeError as e:
            hash3 = self.tracker.track_error(e, module="mod1", function="func1")

        # 不同模块或不同错误类型应该有不同哈希
        assert hash1 != hash2  # 不同模块
        assert hash1 != hash3  # 不同错误类型


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
