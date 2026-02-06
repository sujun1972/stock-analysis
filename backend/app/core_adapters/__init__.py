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
- ThreeLayerAdapter: 三层架构策略适配器

作者: Backend Team
创建日期: 2026-02-01
版本: 1.0.0
"""

from .backtest_adapter import BacktestAdapter
from .data_adapter import DataAdapter
from .feature_adapter import FeatureAdapter
from .model_adapter import ModelAdapter
from .three_layer_adapter import ThreeLayerAdapter

__all__ = [
    "DataAdapter",
    "FeatureAdapter",
    "BacktestAdapter",
    "ModelAdapter",
    "ThreeLayerAdapter",
]

__version__ = "1.0.0"
