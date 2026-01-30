"""
CLI进度条工具

提供进度显示和追踪功能
"""

from typing import Optional, Any
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from .output import get_console


def create_progress_bar(show_time: bool = True) -> Progress:
    """
    创建进度条

    Args:
        show_time: 是否显示时间信息

    Returns:
        Progress实例
    """
    columns = [
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
    ]

    if show_time:
        columns.extend(
            [
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            ]
        )

    return Progress(*columns, console=get_console())


class ProgressTracker:
    """
    进度追踪器

    用于追踪任务进度和状态
    """

    def __init__(self, total: int, description: str = "处理中...", show_time: bool = True):
        """
        初始化进度追踪器

        Args:
            total: 总任务数
            description: 任务描述
            show_time: 是否显示时间
        """
        self.total = total
        self.description = description
        self.show_time = show_time
        self.progress: Optional[Progress] = None
        self.task_id: Optional[Any] = None
        self.current = 0
        self.success_count = 0
        self.fail_count = 0

    def __enter__(self):
        """上下文管理器入口"""
        self.progress = create_progress_bar(self.show_time)
        self.progress.__enter__()
        self.task_id = self.progress.add_task(self.description, total=self.total)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        if self.progress:
            self.progress.__exit__(exc_type, exc_val, exc_tb)
        return False

    def update(self, advance: int = 1, description: Optional[str] = None):
        """
        更新进度

        Args:
            advance: 前进步数
            description: 新的描述（可选）
        """
        if self.progress and self.task_id is not None:
            self.current += advance
            kwargs = {"advance": advance}
            if description:
                kwargs["description"] = description
            self.progress.update(self.task_id, **kwargs)

    def mark_success(self, item: str = ""):
        """
        标记成功

        Args:
            item: 项目名称
        """
        self.success_count += 1
        desc = f"[green]{item} 完成[/green]" if item else "[green]完成[/green]"
        self.update(1, desc)

    def mark_failure(self, item: str = "", error: str = ""):
        """
        标记失败

        Args:
            item: 项目名称
            error: 错误信息
        """
        self.fail_count += 1
        desc = f"[red]{item} 失败[/red]" if item else "[red]失败[/red]"
        if error:
            desc += f" ({error})"
        self.update(1, desc)

    def get_summary(self) -> dict:
        """
        获取汇总信息

        Returns:
            汇总字典
        """
        return {
            "总数": self.total,
            "成功": self.success_count,
            "失败": self.fail_count,
            "成功率": f"{self.success_count / self.total * 100:.1f}%"
            if self.total > 0
            else "N/A",
        }
