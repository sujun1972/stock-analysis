"""
股票选择器模块

提供三种基础选股器实现：
- MomentumSelector: 动量选股器
- ValueSelector: 价值选股器（简化版）
- ExternalSelector: 外部选股器（支持 StarRanker 等外部系统）
"""

from .momentum_selector import MomentumSelector
from .value_selector import ValueSelector
from .external_selector import ExternalSelector

__all__ = [
    "MomentumSelector",
    "ValueSelector",
    "ExternalSelector",
]
