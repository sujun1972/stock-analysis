"""
风险指标计算模块
包含 Sharpe 比率、最大回撤、胜率等
"""
import numpy as np

from ..decorators import safe_compute


@safe_compute("Sharpe 比率")
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
    # 移除 NaN 和 Inf
    returns = returns[~np.isnan(returns) & ~np.isinf(returns)]

    if len(returns) < 2:
        return np.nan

    # 年化收益率
    mean_return = np.mean(returns) * periods_per_year

    # 年化波动率
    std_return = np.std(returns, ddof=1) * np.sqrt(periods_per_year)

    if std_return == 0:
        return np.nan

    sharpe = (mean_return - risk_free_rate) / std_return

    return float(sharpe)


@safe_compute("最大回撤")
def calculate_max_drawdown(returns: np.ndarray) -> float:
    """
    计算最大回撤

    Args:
        returns: 收益率序列

    Returns:
        最大回撤（正值）
    """
    # 移除 NaN
    returns = returns[~np.isnan(returns) & ~np.isinf(returns)]

    if len(returns) == 0:
        return np.nan

    # 累计收益
    cum_returns = (1 + returns).cumprod()

    # 历史最高点
    running_max = np.maximum.accumulate(cum_returns)

    # 回撤
    drawdown = (cum_returns - running_max) / running_max

    # 最大回撤
    max_dd = -drawdown.min()

    return float(max_dd)


@safe_compute("胜率")
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
    returns = returns[~np.isnan(returns) & ~np.isinf(returns)]

    if len(returns) == 0:
        return np.nan

    win_rate = np.mean(returns > threshold)

    return float(win_rate)
