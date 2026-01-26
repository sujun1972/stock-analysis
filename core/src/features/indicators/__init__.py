"""
技术指标模块 - 模块化设计

本包将技术指标按类型拆分为多个子模块：
- base: 基类和通用工具
- trend: 趋势指标 (MA, EMA, BBANDS)
- momentum: 动量指标 (RSI, MACD, KDJ, CCI)
- volatility: 波动率指标 (ATR, Volatility)
- volume: 成交量指标 (OBV, Volume MA)
- price_pattern: 价格形态指标

使用方式：
1. 直接使用各类型指标计算器：
   from core.src.features.indicators import TrendIndicators, MomentumIndicators

2. 使用聚合类（兼容旧代码）：
   from core.src.features.technical_indicators import TechnicalIndicators
"""

from .base import BaseIndicator, talib, HAS_TALIB
from .trend import TrendIndicators
from .momentum import MomentumIndicators
from .volatility import VolatilityIndicators
from .volume import VolumeIndicators
from .price_pattern import PricePatternIndicators

__all__ = [
    'BaseIndicator',
    'talib',
    'HAS_TALIB',
    'TrendIndicators',
    'MomentumIndicators',
    'VolatilityIndicators',
    'VolumeIndicators',
    'PricePatternIndicators',
]
