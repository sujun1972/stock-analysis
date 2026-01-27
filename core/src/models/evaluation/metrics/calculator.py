"""
指标计算器
统一封装所有指标计算逻辑
"""
import numpy as np
import pandas as pd
from typing import Dict

from . import (
    calculate_ic,
    calculate_rank_ic,
    calculate_ic_ir,
    calculate_group_returns,
    calculate_long_short_return,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
)


class MetricsCalculator:
    """指标计算器：负责各种量化指标的计算"""

    @staticmethod
    def calculate_ic(
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        method: str = 'pearson'
    ) -> float:
        """
        计算 IC (Information Coefficient)
        衡量预测值与实际收益率的相关性

        Args:
            predictions: 预测值
            actual_returns: 实际收益率
            method: 相关系数方法 ('pearson', 'spearman')

        Returns:
            IC 值
        """
        return calculate_ic(predictions, actual_returns, method)

    @staticmethod
    def calculate_rank_ic(
        predictions: np.ndarray,
        actual_returns: np.ndarray
    ) -> float:
        """
        计算 Rank IC (秩相关系数)
        使用 Spearman 相关系数，对异常值更稳健

        Args:
            predictions: 预测值
            actual_returns: 实际收益率

        Returns:
            Rank IC 值
        """
        return calculate_rank_ic(predictions, actual_returns)

    @staticmethod
    def calculate_ic_ir(ic_series: pd.Series) -> float:
        """
        计算 IC IR (Information Ratio)
        IC 的均值除以 IC 的标准差

        Args:
            ic_series: IC 时间序列

        Returns:
            IC IR 值
        """
        return calculate_ic_ir(ic_series)

    @staticmethod
    def calculate_group_returns(
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        n_groups: int = 5
    ) -> Dict[int, float]:
        """
        计算分组收益率
        将预测值分成 N 组，计算各组的平均收益率

        Args:
            predictions: 预测值
            actual_returns: 实际收益率
            n_groups: 分组数量

        Returns:
            {组号: 平均收益率} 字典
        """
        return calculate_group_returns(predictions, actual_returns, n_groups)

    @staticmethod
    def calculate_long_short_return(
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        top_pct: float = 0.2,
        bottom_pct: float = 0.2
    ) -> Dict[str, float]:
        """
        计算多空组合收益率
        做多预测值最高的 top_pct，做空预测值最低的 bottom_pct

        Args:
            predictions: 预测值
            actual_returns: 实际收益率
            top_pct: 做多比例
            bottom_pct: 做空比例

        Returns:
            {'long': 多头收益, 'short': 空头收益, 'long_short': 多空收益}
        """
        return calculate_long_short_return(predictions, actual_returns, top_pct, bottom_pct)

    @staticmethod
    def calculate_sharpe_ratio(
        returns: np.ndarray,
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252
    ) -> float:
        """
        计算 Sharpe 比率
        (年化收益率 - 无风险利率) / 年化波动率

        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率（年化）
            periods_per_year: 每年期数（日频=252）

        Returns:
            Sharpe 比率
        """
        return calculate_sharpe_ratio(returns, risk_free_rate, periods_per_year)

    @staticmethod
    def calculate_max_drawdown(returns: np.ndarray) -> float:
        """
        计算最大回撤

        Args:
            returns: 收益率序列

        Returns:
            最大回撤（正值）
        """
        return calculate_max_drawdown(returns)

    @staticmethod
    def calculate_win_rate(
        returns: np.ndarray,
        threshold: float = 0.0
    ) -> float:
        """
        计算胜率

        Args:
            returns: 收益率序列
            threshold: 盈利阈值

        Returns:
            胜率（0-1 之间）
        """
        return calculate_win_rate(returns, threshold)
