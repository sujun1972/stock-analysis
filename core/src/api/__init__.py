"""
统一API模块

提供标准化的高层API接口，所有API使用统一的Response返回格式。

该模块封装了各个子系统的功能，提供一致的错误处理和返回格式。

Modules:
    - feature_api: 特征计算相关API
    - data_api: 数据加载、验证和清洗API (新增)
    - (future) backtest_api: 回测相关API
    - (future) model_api: 模型训练相关API

Examples:
    >>> # 特征计算API
    >>> from src.api.feature_api import calculate_alpha_factors
    >>> from src.api import calculate_alpha_factors  # 也可以从这里导入
    >>>
    >>> response = calculate_alpha_factors(data)
    >>> if response.is_success():
    ...     features = response.data
    >>>
    >>> # 数据管理API
    >>> from src.api.data_api import load_stock_data, validate_stock_data, clean_stock_data
    >>>
    >>> # 加载数据
    >>> response = load_stock_data('000001', '20240101', '20241231')
    >>> if response.is_success():
    ...     data = response.data
    ...     print(f"加载了 {response.metadata['n_records']} 条记录")
"""

from src.api.feature_api import (
    calculate_alpha_factors,
    calculate_technical_indicators,
    validate_feature_data
)

from src.api.data_api import (
    load_stock_data,
    validate_stock_data,
    clean_stock_data
)

__all__ = [
    # Feature API
    'calculate_alpha_factors',
    'calculate_technical_indicators',
    'validate_feature_data',
    # Data API (新增)
    'load_stock_data',
    'validate_stock_data',
    'clean_stock_data',
]
