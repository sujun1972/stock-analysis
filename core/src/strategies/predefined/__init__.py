"""
预定义策略模块

包含所有预定义的交易策略类：
- 动量策略 (MomentumStrategy)
- 均值回归策略 (MeanReversionStrategy)
- 多因子策略 (MultiFactorStrategy)

这些策略都继承自 BaseStrategy，可直接使用或通过 StrategyFactory 创建
"""

from .momentum_strategy import MomentumStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .multi_factor_strategy import MultiFactorStrategy

__all__ = [
    'MomentumStrategy',
    'MeanReversionStrategy',
    'MultiFactorStrategy',
]
