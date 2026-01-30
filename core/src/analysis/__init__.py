"""
因子分析和参数优化模块

包含：
- 因子有效性分析（IC、分层回测、相关性）
- 因子组合优化
- 策略参数优化（网格搜索、贝叶斯优化、Walk-Forward）
- 统一因子分析器门面（FactorAnalyzer）⭐ 新增
"""

from .ic_calculator import ICCalculator
from .layering_test import LayeringTest
from .factor_correlation import FactorCorrelation
from .factor_optimizer import FactorOptimizer
from .factor_analyzer import (
    FactorAnalyzer,
    FactorAnalysisReport,
    quick_analyze_factor,
    compare_multiple_factors,
    optimize_factor_combination
)

__all__ = [
    # 原有的单独组件
    'ICCalculator',
    'LayeringTest',
    'FactorCorrelation',
    'FactorOptimizer',

    # 新增：统一门面
    'FactorAnalyzer',
    'FactorAnalysisReport',

    # 便捷函数
    'quick_analyze_factor',
    'compare_multiple_factors',
    'optimize_factor_combination',
]
