"""
交易策略模块

提供多种量化交易策略实现：
- 动量策略 (MomentumStrategy)
- 均值回归策略 (MeanReversionStrategy)
- 多因子策略 (MultiFactorStrategy)
- 策略组合器 (StrategyCombiner)

注意: MLStrategy 已废弃，请使用新的 ml.MLEntry 策略
详情参考: core/docs/planning/ml_system_refactoring_plan.md

使用示例：
    from strategies import MomentumStrategy
    from backtest.backtest_engine import BacktestEngine

    # 创建策略
    strategy = MomentumStrategy(
        name='MOM20',
        config={'lookback_period': 20, 'top_n': 50}
    )

    # 生成信号
    signals = strategy.generate_signals(prices, features)

    # 回测
    engine = BacktestEngine(initial_capital=1000000)
    results = engine.backtest_long_only(signals, prices)
"""

from .base_strategy import BaseStrategy, StrategyConfig
from .signal_generator import SignalGenerator, SignalType
from .momentum_strategy import MomentumStrategy
from .mean_reversion_strategy import MeanReversionStrategy
# MLStrategy 已删除，使用新的 ml.MLEntry 替代
# from .ml_strategy import MLStrategy
from .multi_factor_strategy import MultiFactorStrategy
from .strategy_combiner import StrategyCombiner

__all__ = [
    # 基础类
    'BaseStrategy',
    'StrategyConfig',
    'SignalGenerator',
    'SignalType',

    # 策略实现
    'MomentumStrategy',
    'MeanReversionStrategy',
    # 'MLStrategy',  # 已废弃
    'MultiFactorStrategy',

    # 工具类
    'StrategyCombiner',
]

__version__ = '1.0.0'
