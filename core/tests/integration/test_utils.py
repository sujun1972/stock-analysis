"""
Integration 测试工具函数

提供统一的 Response 对象处理工具，用于适配代码重构后的 Response 封装模式。
"""

import pandas as pd
from typing import Any, Dict, Tuple, Optional


def unwrap_response(response: Any) -> Any:
    """
    从 Response 对象中提取数据

    Args:
        response: Response 对象或原始数据

    Returns:
        解包后的数据，如果为 None 则返回空 DataFrame

    Examples:
        >>> result = unwrap_response(api.get_data())
        >>> # 自动处理 Response 对象并返回实际数据
    """
    if hasattr(response, 'data'):
        data = response.data
        if data is None:
            return pd.DataFrame()
        return data
    return response if response is not None else pd.DataFrame()


def unwrap_prepare_data(response: Any) -> Tuple:
    """
    从 prepare_data 的 Response 中提取训练数据

    Args:
        response: prepare_data 方法返回的 Response 对象或数据元组

    Returns:
        (X_train, y_train, X_valid, y_valid, X_test, y_test) 数据元组

    Examples:
        >>> X_train, y_train, X_valid, y_valid, X_test, y_test = unwrap_prepare_data(
        ...     trainer.prepare_data(df, features, target)
        ... )
    """
    if hasattr(response, 'data'):
        data = response.data
        return (
            data['X_train'], data['y_train'],
            data['X_valid'], data['y_valid'],
            data['X_test'], data['y_test']
        )
    # 如果已经是元组，直接返回
    return response


def unwrap_model_result(response: Any) -> Tuple[Any, Dict]:
    """
    从模型训练结果中提取模型和指标

    Args:
        response: train_stock_model 等方法返回的 Response 对象

    Returns:
        (trainer/model, metrics) 元组

    Examples:
        >>> trainer, metrics = unwrap_model_result(
        ...     train_stock_model(df, features, target)
        ... )
    """
    if hasattr(response, 'data'):
        result = response.data
        trainer = result.get('trainer') or result.get('model')
        metrics = result.get('metrics') or result.get('test_metrics')
        return trainer, metrics
    # 如果已经是元组，直接返回
    return response


def unwrap_save_path(response: Any) -> str:
    """
    从保存操作的 Response 中提取文件路径

    Args:
        response: save_model 等方法返回的 Response 对象

    Returns:
        文件路径字符串

    Examples:
        >>> model_path = unwrap_save_path(trainer.save_model('my_model'))
    """
    if hasattr(response, 'data'):
        data = response.data
        # 可能是字典 {'model_path': ..., 'metadata_path': ...} 或直接是路径字符串
        if isinstance(data, dict):
            return data.get('model_path') or data.get('path')
        return data
    return response


def safe_unwrap(response: Any, default: Any = None) -> Any:
    """
    安全地解包 Response 对象，失败时返回默认值

    Args:
        response: Response 对象或原始数据
        default: 失败时返回的默认值

    Returns:
        解包后的数据或默认值
    """
    try:
        return unwrap_response(response)
    except Exception:
        return default
