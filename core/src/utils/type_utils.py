#!/usr/bin/env python3
"""
类型转换工具模块

提供安全的类型转换函数，处理 NaN、None、Inf 等特殊值
"""

import pandas as pd
import numpy as np
from typing import Any, Optional, Union


# ==================== 标量转换函数 ====================

def safe_float(val: Any, default: float = 0.0) -> float:
    """
    安全转换为 float，处理 NaN、None、Inf 等特殊值

    Args:
        val: 待转换的值
        default: 转换失败时的默认值

    Returns:
        float: 转换后的值或默认值

    Example:
        >>> safe_float(3.14)
        3.14
        >>> safe_float(None)
        0.0
        >>> safe_float(np.nan)
        0.0
        >>> safe_float("invalid", default=-1.0)
        -1.0
    """
    if pd.isna(val) or val is None:
        return default

    # 处理无穷值
    if isinstance(val, (float, np.floating)) and np.isinf(val):
        return default

    try:
        result = float(val)
        # 再次检查转换后的值是否为无穷
        if np.isinf(result):
            return default
        return result
    except (ValueError, TypeError, OverflowError):
        return default


def safe_int(val: Any, default: int = 0) -> int:
    """
    安全转换为 int，处理 NaN、None、Inf 等特殊值

    Args:
        val: 待转换的值
        default: 转换失败时的默认值

    Returns:
        int: 转换后的值或默认值

    Example:
        >>> safe_int(42)
        42
        >>> safe_int(3.14)
        3
        >>> safe_int(None)
        0
        >>> safe_int(np.nan)
        0
    """
    if pd.isna(val) or val is None:
        return default

    # 处理无穷值
    if isinstance(val, (float, np.floating)) and np.isinf(val):
        return default

    try:
        # 先转为 float 再转为 int，避免字符串 "3.14" 转换失败
        result = float(val)
        if np.isinf(result):
            return default
        return int(result)
    except (ValueError, TypeError, OverflowError):
        return default


def safe_str(val: Any, default: str = '') -> str:
    """
    安全转换为 str，处理 NaN、None 等特殊值

    Args:
        val: 待转换的值
        default: 转换失败时的默认值

    Returns:
        str: 转换后的值或默认值

    Example:
        >>> safe_str("hello")
        'hello'
        >>> safe_str(None)
        ''
        >>> safe_str(np.nan)
        ''
    """
    if pd.isna(val) or val is None:
        return default

    try:
        return str(val).strip()
    except (ValueError, TypeError):
        return default


# ==================== Series 向量化转换函数 ====================

def safe_float_series(series: pd.Series, default: float = 0.0) -> np.ndarray:
    """
    向量化的 safe_float，将 Series 转换为 float 数组

    处理 NaN、None、Inf 等特殊值，替换为默认值

    Args:
        series: pandas Series
        default: 默认值

    Returns:
        np.ndarray: float 数组

    Example:
        >>> s = pd.Series([1.0, np.nan, 3.0, None, np.inf])
        >>> safe_float_series(s)
        array([1., 0., 3., 0., 0.])
    """
    return series.fillna(default).replace([np.inf, -np.inf], default).astype(float).values


def safe_int_series(series: pd.Series, default: int = 0) -> np.ndarray:
    """
    向量化的 safe_int，将 Series 转换为 int 数组

    处理 NaN、None、Inf 等特殊值，替换为默认值

    Args:
        series: pandas Series
        default: 默认值

    Returns:
        np.ndarray: int 数组

    Example:
        >>> s = pd.Series([1.5, np.nan, 3.9, None])
        >>> safe_int_series(s)
        array([1, 0, 3, 0])
    """
    return series.fillna(default).replace([np.inf, -np.inf], default).astype(int).values


def safe_float_or_none(series: pd.Series) -> list:
    """
    将 Series 转换为 float 列表，NaN 转为 None

    用于数据库插入时保留 NULL 值

    Args:
        series: pandas Series

    Returns:
        list: float 或 None 的列表

    Example:
        >>> s = pd.Series([1.0, np.nan, 3.0])
        >>> safe_float_or_none(s)
        [1.0, None, 3.0]
    """
    return series.replace({pd.NA: None, np.nan: None}).astype(object).where(pd.notna(series), None).tolist()


def safe_float_or_zero(series: pd.Series) -> np.ndarray:
    """
    将 Series 转换为 float 数组，NaN 转为 0.0

    Args:
        series: pandas Series

    Returns:
        np.ndarray: float 数组

    Example:
        >>> s = pd.Series([1.0, np.nan, 3.0])
        >>> safe_float_or_zero(s)
        array([1., 0., 3.])
    """
    return safe_float_series(series, default=0.0)


def safe_int_or_zero(series: pd.Series) -> np.ndarray:
    """
    将 Series 转换为 int 数组，NaN 转为 0

    Args:
        series: pandas Series

    Returns:
        np.ndarray: int 数组

    Example:
        >>> s = pd.Series([1, np.nan, 3])
        >>> safe_int_or_zero(s)
        array([1, 0, 3])
    """
    return safe_int_series(series, default=0)


# ==================== 类型检查函数 ====================

def is_numeric(val: Any) -> bool:
    """
    检查值是否为数字类型（不包括 NaN 和 Inf）

    Args:
        val: 待检查的值

    Returns:
        bool: 是否为有效数字

    Example:
        >>> is_numeric(3.14)
        True
        >>> is_numeric(np.nan)
        False
        >>> is_numeric(np.inf)
        False
        >>> is_numeric("42")
        False
    """
    if pd.isna(val) or val is None:
        return False

    if isinstance(val, (int, float, np.integer, np.floating)):
        return not np.isinf(val)

    return False


def is_valid_string(val: Any) -> bool:
    """
    检查值是否为有效字符串（非空、非 NaN、非 None）

    Args:
        val: 待检查的值

    Returns:
        bool: 是否为有效字符串

    Example:
        >>> is_valid_string("hello")
        True
        >>> is_valid_string("")
        False
        >>> is_valid_string(None)
        False
    """
    if pd.isna(val) or val is None:
        return False

    if isinstance(val, str):
        return len(val.strip()) > 0

    return False


# ==================== 导出 ====================

__all__ = [
    # 标量转换
    'safe_float',
    'safe_int',
    'safe_str',
    # Series 向量化转换
    'safe_float_series',
    'safe_int_series',
    'safe_float_or_none',
    'safe_float_or_zero',
    'safe_int_or_zero',
    # 类型检查
    'is_numeric',
    'is_valid_string',
]
