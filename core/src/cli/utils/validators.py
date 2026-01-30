"""
CLI参数验证器

提供命令行参数的验证功能
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path
import click


def validate_stock_symbol(symbol: str) -> str:
    """
    验证股票代码格式

    Args:
        symbol: 股票代码

    Returns:
        验证后的股票代码

    Raises:
        click.BadParameter: 如果格式无效
    """
    # 去除空格
    symbol = symbol.strip()

    # A股代码格式：6位数字
    if not re.match(r"^\d{6}$", symbol):
        raise click.BadParameter(
            f"无效的股票代码: {symbol}，A股代码应为6位数字（如: 000001, 600000）"
        )

    return symbol


def validate_date_range(
    start: Optional[datetime],
    end: Optional[datetime],
    max_days: int = 3650,
    allow_none: bool = True,
    allow_future: bool = True
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    验证日期范围

    Args:
        start: 开始日期
        end: 结束日期
        max_days: 最大天数限制
        allow_none: 是否允许None值
        allow_future: 是否允许未来日期

    Returns:
        (开始日期, 结束日期)元组

    Raises:
        click.BadParameter: 如果日期范围无效
    """
    # 允许None值的情况
    if allow_none:
        if start is None and end is None:
            return None, None
        if start is None:
            return None, end
        if end is None:
            return start, None
    else:
        if start is None or end is None:
            raise click.BadParameter("开始日期和结束日期都必须指定")

    # 检查开始日期必须早于或等于结束日期
    if start > end:
        raise click.BadParameter("开始日期必须早于或等于结束日期")

    # 检查日期范围不能太长
    if max_days > 0:
        days_diff = (end - start).days
        if days_diff > max_days:
            raise click.BadParameter(f"日期范围不能超过 {max_days} 天（约 {max_days // 365} 年）")

    # 检查日期不能是未来
    if not allow_future:
        now = datetime.now()
        if end > now:
            raise click.BadParameter("结束日期不能是未来日期")

    return start, end


def validate_positive_int(value: int, name: str = "参数") -> int:
    """
    验证正整数

    Args:
        value: 数值
        name: 参数名称

    Returns:
        验证后的数值

    Raises:
        click.BadParameter: 如果不是正整数
    """
    if value <= 0:
        raise click.BadParameter(f"{name}必须是正整数")
    return value


def validate_percentage(value: float, name: str = "参数") -> float:
    """
    验证百分比（0-100）

    Args:
        value: 数值
        name: 参数名称

    Returns:
        验证后的数值

    Raises:
        click.BadParameter: 如果不在范围内
    """
    if not 0 <= value <= 100:
        raise click.BadParameter(f"{name}必须在0-100之间")
    return value


def validate_path(
    path_str: str, must_exist: bool = True, is_dir: Optional[bool] = None
) -> Path:
    """
    验证路径

    Args:
        path_str: 路径字符串
        must_exist: 路径是否必须存在
        is_dir: 是否为目录（None=不检查，True=必须是目录，False=必须是文件）

    Returns:
        验证后的Path对象

    Raises:
        click.BadParameter: 如果路径无效
    """
    path = Path(path_str)

    # 检查路径是否存在
    if must_exist and not path.exists():
        raise click.BadParameter(f"路径不存在: {path_str}")

    # 如果路径存在，检查类型
    if path.exists():
        if is_dir is True and not path.is_dir():
            raise click.BadParameter(f"期望目录但得到文件: {path_str}")
        if is_dir is False and not path.is_file():
            raise click.BadParameter(f"期望文件但得到目录: {path_str}")

    return path


class StockSymbolType(click.ParamType):
    """自定义股票代码参数类型"""

    name = "STOCK_SYMBOL"

    def convert(self, value, param, ctx):
        """
        转换和验证股票代码

        Args:
            value: 输入值
            param: 参数对象
            ctx: 上下文

        Returns:
            验证后的股票代码
        """
        try:
            return validate_stock_symbol(value)
        except click.BadParameter as e:
            self.fail(str(e), param, ctx)


class DateRangeType(click.ParamType):
    """自定义日期范围参数类型"""

    name = "DATE_RANGE"

    def __init__(self, max_days: int = 3650, allow_future: bool = True):
        """
        初始化日期范围类型

        Args:
            max_days: 最大天数限制
            allow_future: 是否允许未来日期
        """
        self.max_days = max_days
        self.allow_future = allow_future

    def convert(self, value, param, ctx):
        """
        转换和验证日期范围

        Args:
            value: 输入值（格式: YYYY-MM-DD:YYYY-MM-DD 或 YYYY-MM-DD）
            param: 参数对象
            ctx: 上下文

        Returns:
            (开始日期, 结束日期)元组
        """
        try:
            # 支持单个日期或日期范围
            if ":" in value:
                start_str, end_str = value.split(":", 1)
                start = datetime.strptime(start_str.strip(), "%Y-%m-%d")
                end = datetime.strptime(end_str.strip(), "%Y-%m-%d")
            else:
                # 单个日期，开始和结束相同
                date = datetime.strptime(value.strip(), "%Y-%m-%d")
                start = end = date

            return validate_date_range(start, end, self.max_days,
                                      allow_none=False, allow_future=self.allow_future)
        except ValueError as e:
            self.fail(f"日期格式错误: {e}", param, ctx)
        except click.BadParameter as e:
            self.fail(str(e), param, ctx)


class SymbolListType(click.ParamType):
    """自定义股票代码列表参数类型"""

    name = "SYMBOL_LIST"

    def convert(self, value, param, ctx):
        """
        转换和验证股票代码列表

        Args:
            value: 输入值（逗号分隔的股票代码）
            param: 参数对象
            ctx: 上下文

        Returns:
            股票代码列表
        """
        if value.lower() == "all":
            return "all"

        symbols = [s.strip() for s in value.split(",") if s.strip()]

        if not symbols:
            self.fail("至少需要指定一个股票代码", param, ctx)

        # 验证每个代码
        validated_symbols = []
        for symbol in symbols:
            try:
                validated_symbols.append(validate_stock_symbol(symbol))
            except click.BadParameter as e:
                self.fail(str(e), param, ctx)

        return validated_symbols
