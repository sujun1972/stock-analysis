"""
数据清理工具模块
提供用于清理和规范化数据的通用函数
"""

import math
from typing import Any

import numpy as np


def sanitize_float_values(data: Any) -> Any:
    """
    递归清理数据中的无效浮点数值（NaN, Inf, -Inf）
    将无效值转换为 None 以便 JSON 序列化

    此函数用于处理机器学习模型输出中可能出现的特殊浮点值，
    这些值无法被 JSON 序列化，会导致 API 响应失败。

    Args:
        data: 待清理的数据，支持 dict, list, float, int, numpy类型等

    Returns:
        清理后的数据，无效浮点数被替换为 None

    Examples:
        >>> sanitize_float_values({"a": float('nan'), "b": 1.5})
        {"a": None, "b": 1.5}

        >>> sanitize_float_values([1.0, float('inf'), 2.0])
        [1.0, None, 2.0]
    """
    if isinstance(data, dict):
        return {k: sanitize_float_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_float_values(item) for item in data]
    elif isinstance(data, float):
        if np.isnan(data) or np.isinf(data):
            return None
        return data
    elif isinstance(data, (np.floating, np.integer)):
        value = float(data)
        if np.isnan(value) or np.isinf(value):
            return None
        return value
    else:
        return data


def clean_value(val: Any) -> Any:
    """
    清理单个值，将 NaN/Infinity 替换为 None

    用于清理从数据库或 pandas DataFrame 中读取的单个值，
    确保值可以被 JSON 序列化。

    Args:
        val: 待清理的值

    Returns:
        清理后的值，无效值被替换为 None

    Examples:
        >>> clean_value(float('nan'))
        None

        >>> clean_value(1.5)
        1.5

        >>> clean_value(None)
        None
    """
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
    return val


def clean_dict_values(data: dict) -> dict:
    """
    清理字典中的所有值

    Args:
        data: 待清理的字典

    Returns:
        清理后的字典

    Examples:
        >>> clean_dict_values({"a": float('nan'), "b": 1.5, "c": None})
        {"a": None, "b": 1.5, "c": None}
    """
    return {k: clean_value(v) for k, v in data.items()}


def clean_records(records: list[dict]) -> list[dict]:
    """
    清理记录列表（字典列表）中的所有值

    Args:
        records: 待清理的记录列表

    Returns:
        清理后的记录列表

    Examples:
        >>> records = [{"a": float('nan'), "b": 1.5}, {"a": 2.0, "b": float('inf')}]
        >>> clean_records(records)
        [{"a": None, "b": 1.5}, {"a": 2.0, "b": None}]
    """
    return [clean_dict_values(record) for record in records]
