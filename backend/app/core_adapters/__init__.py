"""
Core Adapters - 异步适配器层

为 Core 项目的同步方法提供异步包装器，供 FastAPI Backend 使用。

架构说明:
    Backend (FastAPI) --> Adapters (异步) --> Core (同步)

包含的适配器:
- DataAdapter: 数据库访问适配器
- FeatureAdapter: 特征工程适配器
- BacktestAdapter: 回测引擎适配器
- ModelAdapter: 机器学习模型适配器
- ConfigStrategyAdapter: 配置驱动策略适配器 (Core v6.0)
- DynamicStrategyAdapter: 动态代码策略适配器 (Core v6.0)

作者: Backend Team
创建日期: 2026-02-01
版本: 3.0.0
"""

from .backtest_adapter import BacktestAdapter
from .config_strategy_adapter import ConfigStrategyAdapter
from .data_adapter import DataAdapter
from .dynamic_strategy_adapter import DynamicStrategyAdapter
from .feature_adapter import FeatureAdapter
from .model_adapter import ModelAdapter

__all__ = [
    "DataAdapter",
    "FeatureAdapter",
    "BacktestAdapter",
    "ModelAdapter",
    "ConfigStrategyAdapter",
    "DynamicStrategyAdapter",
]

__version__ = "3.0.0"
