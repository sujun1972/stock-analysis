"""
三层架构基类模块

Three Layer Architecture Base Module

本模块提供三层架构的核心基类：
- StockSelector: 股票选择器基类（Layer 1）
- EntryStrategy: 入场策略基类（Layer 2）
- ExitStrategy: 退出策略基类（Layer 3）
- StrategyComposer: 策略组合器

所有具体的选股器、入场策略、退出策略都必须继承这些基类并实现相应的抽象方法。

This module provides the core base classes for the three-layer architecture:
- StockSelector: Stock selector base class (Layer 1)
- EntryStrategy: Entry strategy base class (Layer 2)
- ExitStrategy: Exit strategy base class (Layer 3)
- StrategyComposer: Strategy composer

All concrete selectors, entry strategies, and exit strategies must inherit from
these base classes and implement the corresponding abstract methods.
"""

from .stock_selector import StockSelector, SelectorParameter
from .entry_strategy import EntryStrategy
from .exit_strategy import ExitStrategy, Position
from .strategy_composer import StrategyComposer


__all__ = [
    # 基类
    "StockSelector",
    "EntryStrategy",
    "ExitStrategy",
    "StrategyComposer",
    # 数据类
    "SelectorParameter",
    "Position",
]


# 版本信息
__version__ = "3.0.0"
__author__ = "Stock Analysis Team"
__description__ = "三层架构基类 - Core v3.0"
