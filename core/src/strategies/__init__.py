"""
交易策略模块

提供多种量化交易策略实现：
- 动量策略 (MomentumStrategy)
- 均值回归策略 (MeanReversionStrategy)
- 机器学习策略 (MLStrategy)
- 多因子策略 (MultiFactorStrategy)
- 策略组合器 (StrategyCombiner)

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
from .ml_strategy import MLStrategy
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
    'MLStrategy',
    'MultiFactorStrategy',

    # 工具类
    'StrategyCombiner',
]

__version__ = '1.0.0'
