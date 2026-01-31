"""
统一API模块

提供标准化的高层API接口，所有API使用统一的Response返回格式。

该模块封装了各个子系统的功能，提供一致的错误处理和返回格式。

Modules:
    - feature_api: 特征计算相关API
    - (future) backtest_api: 回测相关API
    - (future) model_api: 模型训练相关API

Examples:
    >>> from src.api.feature_api import calculate_alpha_factors
    >>> from src.api import calculate_alpha_factors  # 也可以从这里导入
    >>>
    >>> response = calculate_alpha_factors(data)
    >>> if response.is_success():
    ...     features = response.data
"""

from src.api.feature_api import (
    calculate_alpha_factors,
    calculate_technical_indicators,
    validate_feature_data
)

__all__ = [
    'calculate_alpha_factors',
    'calculate_technical_indicators',
    'validate_feature_data',
]
