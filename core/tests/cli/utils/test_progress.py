"""
测试CLI进度条工具模块
"""

import pytest
from unittest.mock import patch, MagicMock, call
import time

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.cli.utils.progress import ProgressTracker, create_progress_bar


class TestProgressTracker:
    """测试ProgressTracker类"""

    def test_init(self):
        """测试初始化"""
        tracker = ProgressTracker(total=100, description="测试")
        assert tracker.total == 100
        assert tracker.description == "测试"
        assert tracker.success_count == 0
        assert tracker.fail_count == 0

    def test_init_with_defaults(self):
        """测试默认参数初始化"""
        tracker = ProgressTracker(total=50)
        assert tracker.total == 50
        assert isinstance(tracker.description, str)

    @patch("src.cli.utils.progress.Progress")
    def test_enter_exit(self, mock_progress_class):
        """测试上下文管理器"""
        mock_progress = MagicMock()
        mock_progress_class.return_value = mock_progress

        with ProgressTracker(total=10) as tracker:
            assert isinstance(tracker, ProgressTracker)

        # 验证__enter__和__exit__被调用
        mock_progress.__enter__.assert_called_once()
        mock_progress.__exit__.assert_called_once()

    @patch("src.cli.utils.progress.Progress")
    def test_mark_success(self, mock_progress_class):
        """测试标记成功"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=10) as tracker:
            tracker.mark_success("item1")
            assert tracker.success_count == 1

            tracker.mark_success("item2")
            assert tracker.success_count == 2

    @patch("src.cli.utils.progress.Progress")
    def test_mark_failure(self, mock_progress_class):
        """测试标记失败"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=10) as tracker:
            tracker.mark_failure("item1", "错误信息")
            assert tracker.fail_count == 1

            tracker.mark_failure("item2", "另一个错误")
            assert tracker.fail_count == 2

    @patch("src.cli.utils.progress.Progress")
    def test_mark_mixed(self, mock_progress_class):
        """测试混合标记成功和失败"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=10) as tracker:
            tracker.mark_success("success1")
            tracker.mark_failure("fail1", "错误")
            tracker.mark_success("success2")

            assert tracker.success_count == 2
            assert tracker.fail_count == 1

    @patch("src.cli.utils.progress.Progress")
    def test_update_progress(self, mock_progress_class):
        """测试更新进度"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=10) as tracker:
            tracker.update(5)
            # 验证update被调用
            assert mock_progress.update.called

    @patch("src.cli.utils.progress.Progress")
    def test_get_summary(self, mock_progress_class):
        """测试获取统计摘要"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=10) as tracker:
            tracker.mark_success("s1")
            tracker.mark_success("s2")
            tracker.mark_failure("f1", "error")

            summary = tracker.get_summary()

            assert isinstance(summary, dict)
            assert "总数" in summary
            assert "成功" in summary
            assert "失败" in summary
            assert summary["总数"] == 10
            assert summary["成功"] == 2
            assert summary["失败"] == 1

    @patch("src.cli.utils.progress.Progress")
    def test_success_rate_calculation(self, mock_progress_class):
        """测试成功率计算"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=10) as tracker:
            tracker.mark_success("s1")
            tracker.mark_success("s2")
            tracker.mark_success("s3")

            summary = tracker.get_summary()
            # 3/10 = 30%
            assert "30" in str(summary.get("成功率", ""))

    @patch("src.cli.utils.progress.Progress")
    def test_all_success(self, mock_progress_class):
        """测试全部成功的情况"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=5) as tracker:
            for i in range(5):
                tracker.mark_success(f"item{i}")

            summary = tracker.get_summary()
            assert summary["成功"] == 5
            assert summary["失败"] == 0
            assert "100" in str(summary.get("成功率", ""))

    @patch("src.cli.utils.progress.Progress")
    def test_all_failure(self, mock_progress_class):
        """测试全部失败的情况"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=5) as tracker:
            for i in range(5):
                tracker.mark_failure(f"item{i}", "error")

            summary = tracker.get_summary()
            assert summary["成功"] == 0
            assert summary["失败"] == 5
            assert "0" in str(summary.get("成功率", ""))


class TestCreateProgressBar:
    """测试create_progress_bar函数"""

    @patch("src.cli.utils.progress.Progress")
    def test_create_progress_bar(self, mock_progress_class):
        """测试创建进度条"""
        mock_progress = MagicMock()
        # 让__enter__返回mock_progress本身
        mock_progress.__enter__.return_value = mock_progress
        mock_progress_class.return_value = mock_progress

        with create_progress_bar() as progress:
            assert progress is mock_progress

        # 验证__enter__和__exit__被调用
        mock_progress.__enter__.assert_called_once()
        mock_progress.__exit__.assert_called_once()

    @patch("src.cli.utils.progress.Progress")
    def test_create_progress_bar_with_task(self, mock_progress_class):
        """测试创建进度条并添加任务"""
        mock_progress = MagicMock()
        mock_task_id = "task_123"
        # 让__enter__返回mock_progress本身
        mock_progress.__enter__.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task_id
        mock_progress_class.return_value = mock_progress

        with create_progress_bar() as progress:
            task = progress.add_task("[cyan]测试任务", total=100)
            assert task == mock_task_id

        mock_progress.add_task.assert_called_once()


class TestProgressTrackerEdgeCases:
    """测试边界情况"""

    @patch("src.cli.utils.progress.Progress")
    def test_zero_total(self, mock_progress_class):
        """测试总数为0的情况"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=0) as tracker:
            summary = tracker.get_summary()
            assert summary["总数"] == 0

    @patch("src.cli.utils.progress.Progress")
    def test_exceed_total(self, mock_progress_class):
        """测试超过总数的情况"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=3) as tracker:
            # 标记超过总数
            for i in range(5):
                tracker.mark_success(f"item{i}")

            assert tracker.success_count == 5  # 仍然记录所有

    @patch("src.cli.utils.progress.Progress")
    def test_empty_description(self, mock_progress_class):
        """测试空描述"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=10, description="") as tracker:
            tracker.mark_success("item1")
            assert tracker.success_count == 1

    @patch("src.cli.utils.progress.Progress")
    def test_unicode_items(self, mock_progress_class):
        """测试Unicode项目名称"""
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = mock_task

        with ProgressTracker(total=3) as tracker:
            tracker.mark_success("中文项目")
            tracker.mark_failure("测试项目", "中文错误信息")
            assert tracker.success_count == 1
            assert tracker.fail_count == 1


class TestIntegration:
    """集成测试"""

    def test_real_progress_tracker(self):
        """测试实际的进度跟踪（无mock）"""
        # 这个测试不使用mock，测试实际功能
        try:
            with ProgressTracker(total=5, description="实际测试") as tracker:
                tracker.mark_success("task1")
                tracker.mark_success("task2")
                tracker.mark_failure("task3", "error")

                summary = tracker.get_summary()
                assert summary["成功"] == 2
                assert summary["失败"] == 1
        except Exception as e:
            pytest.fail(f"实际进度跟踪失败: {e}")

    def test_real_progress_bar(self):
        """测试实际的进度条（无mock）"""
        try:
            with create_progress_bar() as progress:
                task = progress.add_task("[cyan]测试", total=10)
                for i in range(10):
                    progress.update(task, advance=1)
        except Exception as e:
            pytest.fail(f"实际进度条失败: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
