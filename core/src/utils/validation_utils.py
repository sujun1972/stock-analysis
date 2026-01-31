"""
数据验证通用工具函数

该模块提供数据验证、类型检查、参数验证等功能。
用于确保数据质量和函数参数的正确性。

功能分类：
- 数据框验证：列存在性、数据类型、索引类型
- 参数验证：范围检查、类型检查、枚举值检查
- 股票数据验证：OHLCV数据完整性、价格合理性
- 时间序列验证：日期索引、频率一致性

作者: AI Assistant
日期: 2026-01-31
版本: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import List, Union, Optional, Any, Tuple, Literal
from datetime import datetime


# ==================== DataFrame验证函数 ====================


def validate_columns_exist(
    df: pd.DataFrame,
    required_columns: List[str],
    raise_error: bool = True
) -> Tuple[bool, List[str]]:
    """
    验证DataFrame是否包含必需的列

    参数:
        df: 待验证的DataFrame
        required_columns: 必需的列名列表
        raise_error: 是否在验证失败时抛出异常

    返回:
        (是否通过验证, 缺失的列名列表)

    异常:
        ValueError: 当raise_error=True且存在缺失列时

    示例:
        >>> df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        >>> is_valid, missing = validate_columns_exist(df, ['a', 'b', 'c'], raise_error=False)
        >>> print(missing)
        ['c']
    """
    missing_columns = [col for col in required_columns if col not in df.columns]

    is_valid = len(missing_columns) == 0

    if not is_valid and raise_error:
        raise ValueError(f"缺少必需的列: {missing_columns}")

    return is_valid, missing_columns


def validate_dataframe_not_empty(
    df: pd.DataFrame,
    min_rows: int = 1,
    raise_error: bool = True
) -> bool:
    """
    验证DataFrame不为空

    参数:
        df: 待验证的DataFrame
        min_rows: 最小行数要求
        raise_error: 是否在验证失败时抛出异常

    返回:
        是否通过验证

    异常:
        ValueError: 当raise_error=True且DataFrame为空时
    """
    is_valid = not df.empty and len(df) >= min_rows

    if not is_valid and raise_error:
        raise ValueError(f"DataFrame为空或行数不足（需要至少{min_rows}行，实际{len(df)}行）")

    return is_valid


def validate_no_missing_values(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    threshold: float = 0.0,
    raise_error: bool = True
) -> Tuple[bool, pd.Series]:
    """
    验证DataFrame没有缺失值

    参数:
        df: 待验证的DataFrame
        columns: 要检查的列（None表示全部列）
        threshold: 允许的缺失值比例（0.0表示不允许任何缺失）
        raise_error: 是否在验证失败时抛出异常

    返回:
        (是否通过验证, 各列缺失值比例)

    异常:
        ValueError: 当raise_error=True且存在超过阈值的缺失值时
    """
    if columns is None:
        columns = df.columns.tolist()

    missing_ratio = df[columns].isnull().sum() / len(df)
    invalid_columns = missing_ratio[missing_ratio > threshold]

    is_valid = len(invalid_columns) == 0

    if not is_valid and raise_error:
        raise ValueError(
            f"以下列的缺失值比例超过阈值{threshold}:\n{invalid_columns}"
        )

    return is_valid, missing_ratio


def validate_datetime_index(
    df: pd.DataFrame,
    raise_error: bool = True
) -> bool:
    """
    验证DataFrame的索引是否为DatetimeIndex

    参数:
        df: 待验证的DataFrame
        raise_error: 是否在验证失败时抛出异常

    返回:
        是否通过验证

    异常:
        ValueError: 当raise_error=True且索引不是DatetimeIndex时
    """
    is_valid = isinstance(df.index, pd.DatetimeIndex)

    if not is_valid and raise_error:
        raise ValueError(
            f"DataFrame索引必须是DatetimeIndex，当前类型: {type(df.index).__name__}"
        )

    return is_valid


def validate_sorted_index(
    df: pd.DataFrame,
    ascending: bool = True,
    raise_error: bool = True
) -> bool:
    """
    验证DataFrame的索引是否已排序

    参数:
        df: 待验证的DataFrame
        ascending: 是否要求升序
        raise_error: 是否在验证失败时抛出异常

    返回:
        是否通过验证

    异常:
        ValueError: 当raise_error=True且索引未排序时
    """
    if ascending:
        is_valid = df.index.is_monotonic_increasing
    else:
        is_valid = df.index.is_monotonic_decreasing

    if not is_valid and raise_error:
        order = "升序" if ascending else "降序"
        raise ValueError(f"DataFrame索引必须{order}排列")

    return is_valid


# ==================== 股票数据验证函数 ====================


def validate_ohlcv_data(
    df: pd.DataFrame,
    require_volume: bool = True,
    raise_error: bool = True
) -> Tuple[bool, List[str]]:
    """
    验证OHLCV数据的完整性

    参数:
        df: 待验证的DataFrame
        require_volume: 是否要求包含成交量
        raise_error: 是否在验证失败时抛出异常

    返回:
        (是否通过验证, 错误信息列表)

    异常:
        ValueError: 当raise_error=True且验证失败时
    """
    errors = []

    # 检查必需的列
    required_cols = ['open', 'high', 'low', 'close']
    if require_volume:
        required_cols.append('volume')

    is_valid, missing = validate_columns_exist(df, required_cols, raise_error=False)
    if not is_valid:
        errors.append(f"缺少必需的列: {missing}")

    # 如果缺少列，直接返回
    if not is_valid:
        if raise_error:
            raise ValueError("\n".join(errors))
        return False, errors

    # 验证价格关系：high >= low
    invalid_hl = df['high'] < df['low']
    if invalid_hl.any():
        count = invalid_hl.sum()
        errors.append(f"存在{count}行最高价小于最低价")

    # 验证价格关系：high >= close, high >= open
    invalid_hc = df['high'] < df['close']
    if invalid_hc.any():
        count = invalid_hc.sum()
        errors.append(f"存在{count}行最高价小于收盘价")

    invalid_ho = df['high'] < df['open']
    if invalid_ho.any():
        count = invalid_ho.sum()
        errors.append(f"存在{count}行最高价小于开盘价")

    # 验证价格关系：low <= close, low <= open
    invalid_lc = df['low'] > df['close']
    if invalid_lc.any():
        count = invalid_lc.sum()
        errors.append(f"存在{count}行最低价大于收盘价")

    invalid_lo = df['low'] > df['open']
    if invalid_lo.any():
        count = invalid_lo.sum()
        errors.append(f"存在{count}行最低价大于开盘价")

    # 验证价格为正
    price_cols = ['open', 'high', 'low', 'close']
    for col in price_cols:
        if (df[col] <= 0).any():
            count = (df[col] <= 0).sum()
            errors.append(f"{col}存在{count}个非正值")

    # 验证成交量为非负
    if require_volume and 'volume' in df.columns:
        if (df['volume'] < 0).any():
            count = (df['volume'] < 0).sum()
            errors.append(f"成交量存在{count}个负值")

    is_valid = len(errors) == 0

    if not is_valid and raise_error:
        raise ValueError("OHLCV数据验证失败:\n" + "\n".join(errors))

    return is_valid, errors


def validate_price_range(
    df: pd.DataFrame,
    price_columns: List[str] = ['open', 'high', 'low', 'close'],
    min_price: float = 0.01,
    max_price: float = 10000.0,
    raise_error: bool = True
) -> Tuple[bool, List[str]]:
    """
    验证价格在合理范围内

    参数:
        df: 待验证的DataFrame
        price_columns: 价格列名列表
        min_price: 最小合理价格
        max_price: 最大合理价格
        raise_error: 是否在验证失败时抛出异常

    返回:
        (是否通过验证, 错误信息列表)

    异常:
        ValueError: 当raise_error=True且验证失败时
    """
    errors = []

    for col in price_columns:
        if col not in df.columns:
            continue

        # 检查最小值
        if (df[col] < min_price).any():
            count = (df[col] < min_price).sum()
            min_val = df[col].min()
            errors.append(
                f"{col}存在{count}个异常低价（最小值{min_val:.4f} < {min_price}）"
            )

        # 检查最大值
        if (df[col] > max_price).any():
            count = (df[col] > max_price).sum()
            max_val = df[col].max()
            errors.append(
                f"{col}存在{count}个异常高价（最大值{max_val:.2f} > {max_price}）"
            )

    is_valid = len(errors) == 0

    if not is_valid and raise_error:
        raise ValueError("价格范围验证失败:\n" + "\n".join(errors))

    return is_valid, errors


def validate_daily_return_range(
    prices: pd.Series,
    max_daily_return: float = 0.20,
    raise_error: bool = True
) -> Tuple[bool, pd.Series]:
    """
    验证日收益率在合理范围内（检测异常波动）

    参数:
        prices: 价格序列
        max_daily_return: 最大日收益率（如0.20表示20%）
        raise_error: 是否在验证失败时抛出异常

    返回:
        (是否通过验证, 异常收益率序列)

    异常:
        ValueError: 当raise_error=True且存在异常收益率时
    """
    returns = prices.pct_change()
    abnormal_returns = returns[abs(returns) > max_daily_return]

    is_valid = len(abnormal_returns) == 0

    if not is_valid and raise_error:
        raise ValueError(
            f"存在{len(abnormal_returns)}个异常日收益率（超过±{max_daily_return*100}%）:\n"
            f"{abnormal_returns}"
        )

    return is_valid, abnormal_returns


# ==================== 参数验证函数 ====================


def validate_positive_number(
    value: Union[int, float],
    param_name: str = "参数",
    allow_zero: bool = False,
    raise_error: bool = True
) -> bool:
    """
    验证数值为正数

    参数:
        value: 待验证的值
        param_name: 参数名称（用于错误消息）
        allow_zero: 是否允许零
        raise_error: 是否在验证失败时抛出异常

    返回:
        是否通过验证

    异常:
        ValueError: 当raise_error=True且值不是正数时
    """
    if allow_zero:
        is_valid = value >= 0
        condition = "非负"
    else:
        is_valid = value > 0
        condition = "正"

    if not is_valid and raise_error:
        raise ValueError(f"{param_name}必须是{condition}数，当前值: {value}")

    return is_valid


def validate_range(
    value: Union[int, float],
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    param_name: str = "参数",
    inclusive: Tuple[bool, bool] = (True, True),
    raise_error: bool = True
) -> bool:
    """
    验证数值在指定范围内

    参数:
        value: 待验证的值
        min_value: 最小值（None表示无下限）
        max_value: 最大值（None表示无上限）
        param_name: 参数名称
        inclusive: (是否包含下限, 是否包含上限)
        raise_error: 是否在验证失败时抛出异常

    返回:
        是否通过验证

    异常:
        ValueError: 当raise_error=True且值超出范围时

    示例:
        >>> validate_range(5, min_value=0, max_value=10, param_name="窗口大小")
        True
    """
    is_valid = True
    errors = []

    if min_value is not None:
        if inclusive[0]:
            if value < min_value:
                is_valid = False
                errors.append(f"不能小于{min_value}")
        else:
            if value <= min_value:
                is_valid = False
                errors.append(f"必须大于{min_value}")

    if max_value is not None:
        if inclusive[1]:
            if value > max_value:
                is_valid = False
                errors.append(f"不能大于{max_value}")
        else:
            if value >= max_value:
                is_valid = False
                errors.append(f"必须小于{max_value}")

    if not is_valid and raise_error:
        raise ValueError(f"{param_name}超出范围（当前值: {value}）: {', '.join(errors)}")

    return is_valid


def validate_type(
    value: Any,
    expected_type: Union[type, Tuple[type, ...]],
    param_name: str = "参数",
    raise_error: bool = True
) -> bool:
    """
    验证值的类型

    参数:
        value: 待验证的值
        expected_type: 期望的类型（单个或多个）
        param_name: 参数名称
        raise_error: 是否在验证失败时抛出异常

    返回:
        是否通过验证

    异常:
        TypeError: 当raise_error=True且类型不匹配时

    示例:
        >>> validate_type(5, int, "窗口大小")
        True
        >>> validate_type(5, (int, float), "阈值")
        True
    """
    is_valid = isinstance(value, expected_type)

    if not is_valid and raise_error:
        if isinstance(expected_type, tuple):
            type_names = " 或 ".join(t.__name__ for t in expected_type)
        else:
            type_names = expected_type.__name__

        raise TypeError(
            f"{param_name}类型错误: 期望{type_names}，实际{type(value).__name__}"
        )

    return is_valid


def validate_enum(
    value: Any,
    allowed_values: List[Any],
    param_name: str = "参数",
    raise_error: bool = True
) -> bool:
    """
    验证值在允许的枚举值列表中

    参数:
        value: 待验证的值
        allowed_values: 允许的值列表
        param_name: 参数名称
        raise_error: 是否在验证失败时抛出异常

    返回:
        是否通过验证

    异常:
        ValueError: 当raise_error=True且值不在允许列表中时

    示例:
        >>> validate_enum('linear', ['linear', 'log'], "scale")
        True
    """
    is_valid = value in allowed_values

    if not is_valid and raise_error:
        raise ValueError(
            f"{param_name}的值'{value}'不在允许列表中: {allowed_values}"
        )

    return is_valid


def validate_window_size(
    window: int,
    data_length: int,
    param_name: str = "窗口大小",
    raise_error: bool = True
) -> bool:
    """
    验证窗口大小合理性

    参数:
        window: 窗口大小
        data_length: 数据长度
        param_name: 参数名称
        raise_error: 是否在验证失败时抛出异常

    返回:
        是否通过验证

    异常:
        ValueError: 当raise_error=True且窗口大小不合理时
    """
    is_valid = True
    errors = []

    # 检查窗口为正整数
    if not isinstance(window, int) or window <= 0:
        is_valid = False
        errors.append("必须是正整数")

    # 检查窗口不大于数据长度
    if window > data_length:
        is_valid = False
        errors.append(f"不能大于数据长度{data_length}")

    if not is_valid and raise_error:
        raise ValueError(
            f"{param_name}不合理（当前值: {window}）: {', '.join(errors)}"
        )

    return is_valid


# ==================== 时间序列验证函数 ====================


def validate_date_range(
    start_date: Union[str, datetime, pd.Timestamp],
    end_date: Union[str, datetime, pd.Timestamp],
    raise_error: bool = True
) -> bool:
    """
    验证日期范围的合理性

    参数:
        start_date: 开始日期
        end_date: 结束日期
        raise_error: 是否在验证失败时抛出异常

    返回:
        是否通过验证

    异常:
        ValueError: 当raise_error=True且日期范围不合理时
    """
    # 转换为Timestamp
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    is_valid = start <= end

    if not is_valid and raise_error:
        raise ValueError(
            f"开始日期({start})不能晚于结束日期({end})"
        )

    return is_valid


def validate_frequency_consistency(
    df: pd.DataFrame,
    expected_freq: Optional[str] = None,
    tolerance: float = 0.1,
    raise_error: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    验证时间序列频率的一致性

    参数:
        df: 待验证的DataFrame（需要DatetimeIndex）
        expected_freq: 期望的频率（如 'D', 'B', 'H'），None表示自动推断
        tolerance: 允许的偏差比例
        raise_error: 是否在验证失败时抛出异常

    返回:
        (是否通过验证, 推断的频率)

    异常:
        ValueError: 当raise_error=True且频率不一致时
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        if raise_error:
            raise ValueError("DataFrame索引必须是DatetimeIndex")
        return False, None

    # 推断频率
    inferred_freq = pd.infer_freq(df.index)

    if expected_freq is None:
        # 没有期望频率，检查是否能推断出频率
        is_valid = inferred_freq is not None

        if not is_valid and raise_error:
            raise ValueError("无法推断时间序列的频率，数据可能不规则")

        return is_valid, inferred_freq
    else:
        # 有期望频率，检查是否匹配
        is_valid = inferred_freq == expected_freq

        if not is_valid and raise_error:
            raise ValueError(
                f"时间序列频率不匹配: 期望{expected_freq}，推断为{inferred_freq}"
            )

        return is_valid, inferred_freq


# ==================== 模块导出 ====================


__all__ = [
    # DataFrame验证
    'validate_columns_exist',
    'validate_dataframe_not_empty',
    'validate_no_missing_values',
    'validate_datetime_index',
    'validate_sorted_index',
    # 股票数据验证
    'validate_ohlcv_data',
    'validate_price_range',
    'validate_daily_return_range',
    # 参数验证
    'validate_positive_number',
    'validate_range',
    'validate_type',
    'validate_enum',
    'validate_window_size',
    # 时间序列验证
    'validate_date_range',
    'validate_frequency_consistency',
]
