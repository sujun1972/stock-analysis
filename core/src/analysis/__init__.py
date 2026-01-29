"""
因子分析和参数优化模块

包含：
- 因子有效性分析（IC、分层回测、相关性）
- 因子组合优化
- 策略参数优化（网格搜索、贝叶斯优化、Walk-Forward）
"""

from .ic_calculator import ICCalculator
from .layering_test import LayeringTest
from .factor_correlation import FactorCorrelation
from .factor_optimizer import FactorOptimizer

__all__ = [
    'ICCalculator',
    'LayeringTest',
    'FactorCorrelation',
    'FactorOptimizer',
]
