"""
Backtest module
"""

from .backtest_engine import BacktestEngine
from .performance_analyzer import PerformanceAnalyzer
from .position_manager import PositionManager, Position
from .cost_analyzer import TradingCostAnalyzer, Trade
from .slippage_models import (
    SlippageModel,
    FixedSlippageModel,
    VolumeBasedSlippageModel,
    MarketImpactModel,
    BidAskSpreadModel,
    create_slippage_model
)
from .short_selling import ShortSellingCosts, ShortPosition

__all__ = [
    'BacktestEngine',
    'PerformanceAnalyzer',
    'PositionManager',
    'Position',
    'TradingCostAnalyzer',
    'Trade',
    # Slippage models
    'SlippageModel',
    'FixedSlippageModel',
    'VolumeBasedSlippageModel',
    'MarketImpactModel',
    'BidAskSpreadModel',
    'create_slippage_model',
    # Short selling
    'ShortSellingCosts',
    'ShortPosition',
]
