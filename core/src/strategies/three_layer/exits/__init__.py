"""
退出策略模块

提供多种退出策略实现:
- ATRStopLossExit: ATR动态止损
- FixedStopLossExit: 固定止损止盈
- TimeBasedExit: 时间止损
- CombinedExit: 组合退出策略
"""

from .atr_stop_loss_exit import ATRStopLossExit
from .fixed_stop_loss_exit import FixedStopLossExit
from .time_based_exit import TimeBasedExit
from .combined_exit import CombinedExit

__all__ = [
    'ATRStopLossExit',
    'FixedStopLossExit',
    'TimeBasedExit',
    'CombinedExit',
]
