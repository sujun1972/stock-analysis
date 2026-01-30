"""
CLI输出工具

提供美观的终端输出功能，包括彩色输出、表格、面板等
"""

from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# 全局控制台实例
_console: Optional[Console] = None


def create_console(no_color: bool = False, width: Optional[int] = None, force_new: bool = False) -> Console:
    """
    创建或获取全局Console实例

    Args:
        no_color: 是否禁用彩色输出
        width: 终端宽度（None则自动检测）
        force_new: 是否强制创建新实例（用于测试）

    Returns:
        Console实例
    """
    global _console
    if _console is None or force_new:
        console_kwargs = {
            "force_terminal": not no_color,
        }
        if no_color:
            console_kwargs["no_color"] = True
        if width is not None:
            console_kwargs["width"] = width
        new_console = Console(**console_kwargs)
        if force_new:
            return new_console
        _console = new_console
    return _console


def get_console() -> Console:
    """获取全局Console实例"""
    if _console is None:
        return create_console()
    return _console


def print_success(message: str):
    """
    打印成功消息

    Args:
        message: 消息内容
    """
    console = get_console()
    console.print(f"[bold green]✓[/bold green] {message}")


def print_error(message: str):
    """
    打印错误消息

    Args:
        message: 消息内容
    """
    console = get_console()
    console.print(f"[bold red]✗[/bold red] {message}", style="red")


def print_warning(message: str):
    """
    打印警告消息

    Args:
        message: 消息内容
    """
    console = get_console()
    console.print(f"[bold yellow]⚠[/bold yellow] {message}", style="yellow")


def print_info(message: str, bold: bool = False):
    """
    打印信息消息

    Args:
        message: 消息内容
        bold: 是否加粗
    """
    console = get_console()
    if bold:
        console.print(f"[bold]{message}[/bold]")
    else:
        console.print(message)


def print_table(
    data: Dict[str, Any],
    title: Optional[str] = None,
    show_header: bool = True,
    header_style: str = "bold cyan",
):
    """
    打印表格

    Args:
        data: 数据字典 {key: value}
        title: 表格标题
        show_header: 是否显示表头
        header_style: 表头样式
    """
    console = get_console()
    table = Table(title=title, show_header=show_header, header_style=header_style)

    if show_header:
        table.add_column("指标", style="cyan", no_wrap=True)
        table.add_column("值", style="white")

    for key, value in data.items():
        table.add_row(str(key), str(value))

    console.print(table)


def print_summary(
    title: str,
    data: Dict[str, Any],
    border_style: str = "green",
):
    """
    打印汇总面板

    Args:
        title: 面板标题
        data: 数据字典
        border_style: 边框样式
    """
    console = get_console()

    # 构建内容
    lines = []
    for key, value in data.items():
        lines.append(f"{key}: [bold]{value}[/bold]")

    content = "\n".join(lines)
    panel = Panel(content, title=title, border_style=border_style)
    console.print(panel)


def print_divider(char: str = "─", width: Optional[int] = None):
    """
    打印分隔线

    Args:
        char: 分隔符字符
        width: 宽度（None则使用终端宽度）
    """
    console = get_console()
    if width is None:
        width = console.width
    console.print(char * width)


def format_number(value: float, precision: int = 2, suffix: str = "", decimals: Optional[int] = None, use_abbreviation: bool = False) -> str:
    """
    格式化数字

    Args:
        value: 数值
        precision: 小数位数
        suffix: 后缀（如 %）
        decimals: 小数位数（与precision相同，保留向后兼容）
        use_abbreviation: 是否使用K/M缩写（默认False，使用comma分隔）

    Returns:
        格式化后的字符串
    """
    # 支持decimals参数（与precision相同）
    if decimals is not None:
        precision = decimals

    if use_abbreviation:
        # 使用K/M缩写
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.{precision}f}M{suffix}"
        elif abs(value) >= 1_000:
            return f"{value / 1_000:.{precision}f}K{suffix}"
        else:
            return f"{value:.{precision}f}{suffix}"
    else:
        # 使用comma分隔的标准格式
        if value == int(value):
            return f"{int(value):,}{suffix}"
        else:
            return f"{value:,.{precision}f}{suffix}"


def format_percentage(value: float, precision: int = 2, decimals: Optional[int] = None, show_sign: bool = False) -> str:
    """
    格式化百分比

    Args:
        value: 数值（如 0.1234 表示 12.34%）
        precision: 小数位数
        decimals: 小数位数（与precision相同，保留向后兼容）
        show_sign: 是否显示正号

    Returns:
        格式化后的字符串
    """
    # 支持decimals参数（与precision相同）
    if decimals is not None:
        precision = decimals

    percentage = value * 100
    if show_sign and percentage > 0:
        return f"+{percentage:.{precision}f}%"
    return f"{percentage:.{precision}f}%"


def print_results_table(
    results: List[Dict[str, Any]],
    columns: List[str],
    title: Optional[str] = None,
):
    """
    打印结果表格（多行数据）

    Args:
        results: 结果列表
        columns: 列名列表
        title: 表格标题
    """
    console = get_console()
    table = Table(title=title, show_header=True, header_style="bold cyan")

    # 添加列
    for col in columns:
        table.add_column(col, style="white")

    # 添加行
    for row in results:
        values = [str(row.get(col, "")) for col in columns]
        table.add_row(*values)

    console.print(table)
