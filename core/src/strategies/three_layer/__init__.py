"""
三层架构策略模块

Three Layer Architecture Strategy Module

Core v3.0 三层架构：将交易策略分为三个独立的层次

Architecture:
    Layer 1: StockSelector (选股器)
        - 职责：从全市场筛选出候选股票池
        - 频率：周频/月频
        - 示例：MomentumSelector, ValueSelector, ExternalSelector

    Layer 2: EntryStrategy (入场策略)
        - 职责：决定何时买入候选股票
        - 频率：日频
        - 示例：MABreakoutEntry, RSIOversoldEntry, ImmediateEntry

    Layer 3: ExitStrategy (退出策略)
        - 职责：管理持仓，决定何时卖出
        - 频率：日频/实时
        - 示例：ATRStopLossExit, FixedStopLossExit, TimeBasedExit

Usage:
    from core.src.strategies.three_layer import (
        StrategyComposer,
        # 将在后续任务中实现具体的选股器、入场策略、退出策略
    )

    # 组合策略（示例，具体实现将在 T2-T4 完成）
    # composer = StrategyComposer(
    #     selector=MomentumSelector(params={'top_n': 50}),
    #     entry=ImmediateEntry(),
    #     exit_strategy=FixedStopLossExit(params={'stop_loss_pct': -5.0}),
    #     rebalance_freq='W'
    # )

    # 回测
    # from core.src.backtest import BacktestEngine
    # engine = BacktestEngine()
    # result = engine.backtest_three_layer(
    #     selector=composer.selector,
    #     entry=composer.entry,
    #     exit_strategy=composer.exit,
    #     prices=prices,
    #     start_date='2023-01-01',
    #     end_date='2023-12-31'
    # )
"""

# 导入基类
from .base import (
    StockSelector,
    EntryStrategy,
    ExitStrategy,
    StrategyComposer,
    SelectorParameter,
    Position,
)


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
__status__ = "T1 完成 - 基类已实现"
