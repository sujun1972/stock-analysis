"""
风险管理模块

提供完整的风险管理工具集，包括：
- VaR计算
- 回撤控制
- 仓位管理
- 综合风险监控
- 压力测试

示例:
    >>> from risk_management import RiskMonitor, VaRCalculator, DrawdownController
    >>>
    >>> # 初始化监控器
    >>> monitor = RiskMonitor({'max_drawdown': 0.15})
    >>>
    >>> # 执行监控
    >>> result = monitor.monitor(portfolio_value, returns, positions, prices)
    >>> print(f"风险等级: {result['overall_risk_level']}")
"""

from .var_calculator import VaRCalculator
from .drawdown_controller import DrawdownController
from .position_sizer import PositionSizer
from .risk_monitor import RiskMonitor
from .stress_test import StressTest

__all__ = [
    'VaRCalculator',
    'DrawdownController',
    'PositionSizer',
    'RiskMonitor',
    'StressTest',
]

__version__ = '1.0.0'
