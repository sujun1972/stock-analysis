"""
计算相关通用函数

该模块提供无外部依赖的计算函数，专注于金融时间序列计算。
所有函数都是纯函数或低耦合函数，可被features、strategies等模块安全引用。

功能分类：
- 收益率计算：简单收益率、对数收益率、累计收益率
- 滚动统计：滚动均值、滚动标准差、滚动相关性
- 技术指标基础：EMA、SMA、动量、波动率
- 统计函数：协方差、相关系数、Beta系数

作者: AI Assistant
日期: 2026-01-31
版本: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Optional, Union, Tuple, Literal

try:
    from ..exceptions import DataValidationError
except ImportError:
    from src.exceptions import DataValidationError


# ==================== 收益率计算函数 ====================


def calculate_returns(
    prices: pd.Series,
    periods: int = 1,
    method: Literal['simple', 'log'] = 'simple'
) -> pd.Series:
    """
    计算收益率

    参数:
        prices: 价格序列
        periods: 计算周期（1表示日收益率，5表示周收益率）
        method: 计算方法
            - 'simple': 简单收益率 (P_t - P_{t-n}) / P_{t-n}
            - 'log': 对数收益率 ln(P_t / P_{t-n})

    返回:
        收益率序列

    示例:
        >>> prices = pd.Series([100, 105, 110, 108])
        >>> returns = calculate_returns(prices, periods=1, method='simple')
        >>> print(returns)
        0         NaN
        1    0.050000
        2    0.047619
        3   -0.018182
        dtype: float64
    """
    if method == 'simple':
        return prices.pct_change(periods)
    elif method == 'log':
        return np.log(prices / prices.shift(periods))
    else:
        raise DataValidationError(
            f"不支持的计算方法: {method}",
            error_code="UNSUPPORTED_CALCULATION_METHOD",
            method=method,
            supported_methods=['simple', 'log']
        )


def calculate_cumulative_returns(
    returns: pd.Series,
    starting_value: float = 1.0
) -> pd.Series:
    """
    计算累计收益率

    参数:
        returns: 周期收益率序列
        starting_value: 起始值（默认1.0）

    返回:
        累计收益率序列

    示例:
        >>> returns = pd.Series([0.05, 0.03, -0.02, 0.01])
        >>> cumulative = calculate_cumulative_returns(returns)
        >>> print(cumulative)
        0    1.050000
        1    1.081500
        2    1.059870
        3    1.070469
        dtype: float64
    """
    return starting_value * (1 + returns).cumprod()


def annualize_returns(
    returns: pd.Series,
    periods_per_year: int = 252
) -> float:
    """
    年化收益率

    参数:
        returns: 周期收益率序列
        periods_per_year: 每年的周期数（252表示交易日，365表示自然日）

    返回:
        年化收益率（浮点数）

    示例:
        >>> returns = pd.Series([0.01, 0.02, -0.01, 0.015])
        >>> annual_return = annualize_returns(returns, periods_per_year=252)
    """
    total_return = (1 + returns).prod() - 1
    n_periods = len(returns)

    if n_periods == 0:
        return 0.0

    annualized = (1 + total_return) ** (periods_per_year / n_periods) - 1
    return annualized


def calculate_excess_returns(
    returns: pd.Series,
    risk_free_rate: Union[float, pd.Series] = 0.0,
    periods_per_year: int = 252
) -> pd.Series:
    """
    计算超额收益率

    参数:
        returns: 收益率序列
        risk_free_rate: 无风险利率（年化）或无风险利率序列
        periods_per_year: 每年的周期数

    返回:
        超额收益率序列

    示例:
        >>> returns = pd.Series([0.01, 0.02, -0.01])
        >>> excess = calculate_excess_returns(returns, risk_free_rate=0.03)
    """
    if isinstance(risk_free_rate, (int, float)):
        # 将年化无风险利率转换为周期利率
        period_rf_rate = risk_free_rate / periods_per_year
        return returns - period_rf_rate
    else:
        # 如果提供了序列，直接相减
        return returns - risk_free_rate


# ==================== 滚动统计函数 ====================


def rolling_mean(
    series: pd.Series,
    window: int,
    min_periods: Optional[int] = None,
    center: bool = False
) -> pd.Series:
    """
    滚动平均（移动平均）

    参数:
        series: 输入序列
        window: 窗口大小
        min_periods: 最小观测数（默认等于window）
        center: 是否居中对齐

    返回:
        滚动平均序列

    示例:
        >>> s = pd.Series([1, 2, 3, 4, 5])
        >>> ma = rolling_mean(s, window=3)
        >>> print(ma)
        0    NaN
        1    NaN
        2    2.0
        3    3.0
        4    4.0
        dtype: float64
    """
    return series.rolling(window=window, min_periods=min_periods, center=center).mean()


def rolling_std(
    series: pd.Series,
    window: int,
    min_periods: Optional[int] = None,
    ddof: int = 1
) -> pd.Series:
    """
    滚动标准差

    参数:
        series: 输入序列
        window: 窗口大小
        min_periods: 最小观测数
        ddof: 自由度修正（1表示样本标准差）

    返回:
        滚动标准差序列
    """
    return series.rolling(window=window, min_periods=min_periods).std(ddof=ddof)


def rolling_var(
    series: pd.Series,
    window: int,
    min_periods: Optional[int] = None,
    ddof: int = 1
) -> pd.Series:
    """
    滚动方差

    参数:
        series: 输入序列
        window: 窗口大小
        min_periods: 最小观测数
        ddof: 自由度修正

    返回:
        滚动方差序列
    """
    return series.rolling(window=window, min_periods=min_periods).var(ddof=ddof)


def rolling_corr(
    series1: pd.Series,
    series2: pd.Series,
    window: int,
    min_periods: Optional[int] = None
) -> pd.Series:
    """
    滚动相关系数

    参数:
        series1: 第一个序列
        series2: 第二个序列
        window: 窗口大小
        min_periods: 最小观测数

    返回:
        滚动相关系数序列

    示例:
        >>> s1 = pd.Series([1, 2, 3, 4, 5])
        >>> s2 = pd.Series([2, 4, 5, 4, 5])
        >>> corr = rolling_corr(s1, s2, window=3)
    """
    return series1.rolling(window=window, min_periods=min_periods).corr(series2)


def rolling_cov(
    series1: pd.Series,
    series2: pd.Series,
    window: int,
    min_periods: Optional[int] = None,
    ddof: int = 1
) -> pd.Series:
    """
    滚动协方差

    参数:
        series1: 第一个序列
        series2: 第二个序列
        window: 窗口大小
        min_periods: 最小观测数
        ddof: 自由度修正

    返回:
        滚动协方差序列
    """
    return series1.rolling(window=window, min_periods=min_periods).cov(series2, ddof=ddof)


def rolling_min(
    series: pd.Series,
    window: int,
    min_periods: Optional[int] = None
) -> pd.Series:
    """
    滚动最小值

    参数:
        series: 输入序列
        window: 窗口大小
        min_periods: 最小观测数

    返回:
        滚动最小值序列
    """
    return series.rolling(window=window, min_periods=min_periods).min()


def rolling_max(
    series: pd.Series,
    window: int,
    min_periods: Optional[int] = None
) -> pd.Series:
    """
    滚动最大值

    参数:
        series: 输入序列
        window: 窗口大小
        min_periods: 最小观测数

    返回:
        滚动最大值序列
    """
    return series.rolling(window=window, min_periods=min_periods).max()


def rolling_sum(
    series: pd.Series,
    window: int,
    min_periods: Optional[int] = None
) -> pd.Series:
    """
    滚动求和

    参数:
        series: 输入序列
        window: 窗���大小
        min_periods: 最小观测数

    返回:
        滚动求和序列
    """
    return series.rolling(window=window, min_periods=min_periods).sum()


# ==================== 指数加权函数 ====================


def exponential_moving_average(
    series: pd.Series,
    span: Optional[int] = None,
    alpha: Optional[float] = None,
    adjust: bool = True,
    min_periods: int = 0
) -> pd.Series:
    """
    指数移动平均（EMA）

    参数:
        series: 输入序列
        span: 窗口大小（与alpha二选一）
        alpha: 平滑因子（0-1之间，与span二选一）
        adjust: 是否使用调整版本
        min_periods: 最小观测数

    返回:
        EMA序列

    示例:
        >>> s = pd.Series([1, 2, 3, 4, 5])
        >>> ema = exponential_moving_average(s, span=3)

    注意:
        span和alpha的关系: alpha = 2 / (span + 1)
    """
    if span is not None:
        return series.ewm(span=span, adjust=adjust, min_periods=min_periods).mean()
    elif alpha is not None:
        return series.ewm(alpha=alpha, adjust=adjust, min_periods=min_periods).mean()
    else:
        raise DataValidationError(
            "必须提供span或alpha参数",
            error_code="MISSING_REQUIRED_PARAMETER",
            required_parameters=['span', 'alpha']
        )


def exponential_weighted_std(
    series: pd.Series,
    span: Optional[int] = None,
    alpha: Optional[float] = None,
    adjust: bool = True,
    min_periods: int = 0
) -> pd.Series:
    """
    指数加权标准差

    参数:
        series: 输入序列
        span: 窗口大小
        alpha: 平滑因子
        adjust: 是否使用调整版本
        min_periods: 最小观测数

    返回:
        指数加权标准差序列
    """
    if span is not None:
        return series.ewm(span=span, adjust=adjust, min_periods=min_periods).std()
    elif alpha is not None:
        return series.ewm(alpha=alpha, adjust=adjust, min_periods=min_periods).std()
    else:
        raise DataValidationError(
            "必须提供span或alpha参数",
            error_code="MISSING_REQUIRED_PARAMETER",
            required_parameters=['span', 'alpha']
        )


# ==================== 技术指标基础函数 ====================


def calculate_momentum(
    prices: pd.Series,
    periods: int = 10
) -> pd.Series:
    """
    计算动量因子

    动量 = 当前价格 - N期前价格

    参数:
        prices: 价格序列
        periods: 回溯周期

    返回:
        动量序列

    示例:
        >>> prices = pd.Series([100, 105, 110, 108, 112])
        >>> momentum = calculate_momentum(prices, periods=2)
    """
    return prices - prices.shift(periods)


def calculate_roc(
    prices: pd.Series,
    periods: int = 10
) -> pd.Series:
    """
    计算变动率（Rate of Change）

    ROC = (当前价格 - N期前价格) / N期前价格 * 100

    参数:
        prices: 价格序列
        periods: 回溯周期

    返回:
        ROC序列（百分比形式）
    """
    return (prices - prices.shift(periods)) / prices.shift(periods) * 100


def calculate_rsi(
    prices: pd.Series,
    periods: int = 14
) -> pd.Series:
    """
    计算相对强弱指标（RSI）

    RSI = 100 - 100 / (1 + RS)
    其中 RS = 平均涨幅 / 平均跌幅

    参数:
        prices: 价格序列
        periods: 计算周期

    返回:
        RSI序列（0-100之间）

    示例:
        >>> prices = pd.Series([100, 105, 103, 108, 110])
        >>> rsi = calculate_rsi(prices, periods=3)
    """
    # 计算价格变化
    delta = prices.diff()

    # 分离涨跌
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    # 计算平均涨跌幅（使用EMA）
    avg_gains = gains.ewm(span=periods, adjust=False, min_periods=periods).mean()
    avg_losses = losses.ewm(span=periods, adjust=False, min_periods=periods).mean()

    # 避免除零
    rs = avg_gains / avg_losses.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_bollinger_bands(
    prices: pd.Series,
    window: int = 20,
    num_std: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算布林带

    参数:
        prices: 价格序列
        window: 移动平均窗口
        num_std: 标准差倍数

    返回:
        (上轨, 中轨, 下轨)

    示例:
        >>> prices = pd.Series([100, 105, 103, 108, 110, 107])
        >>> upper, middle, lower = calculate_bollinger_bands(prices, window=3, num_std=2)
    """
    middle = rolling_mean(prices, window=window)
    std = rolling_std(prices, window=window)

    upper = middle + num_std * std
    lower = middle - num_std * std

    return upper, middle, lower


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    periods: int = 14
) -> pd.Series:
    """
    计算平均真实波动幅度（ATR）

    参数:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        periods: 计算周期

    返回:
        ATR序列

    示例:
        >>> high = pd.Series([105, 108, 110])
        >>> low = pd.Series([100, 103, 105])
        >>> close = pd.Series([103, 106, 108])
        >>> atr = calculate_atr(high, low, close, periods=2)
    """
    # 计算真实波动幅度（TR）
    tr1 = high - low  # 当日高低差
    tr2 = abs(high - close.shift(1))  # 当日高与前收差
    tr3 = abs(low - close.shift(1))  # 当日低与前收差

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # 计算ATR（使用EMA平滑）
    atr = tr.ewm(span=periods, adjust=False, min_periods=periods).mean()

    return atr


# ==================== 统计函数 ====================


def calculate_correlation(
    series1: pd.Series,
    series2: pd.Series,
    method: Literal['pearson', 'kendall', 'spearman'] = 'pearson'
) -> float:
    """
    计算两个序列的相关系数

    参数:
        series1: 第一个序列
        series2: 第二个序列
        method: 相关系数类型
            - 'pearson': 皮尔逊相关系数（线性相关）
            - 'kendall': 肯德尔秩相关系数
            - 'spearman': 斯皮尔曼秩相关系数

    返回:
        相关系数（-1到1之间）
    """
    return series1.corr(series2, method=method)


def calculate_beta(
    stock_returns: pd.Series,
    market_returns: pd.Series,
    window: Optional[int] = None
) -> Union[float, pd.Series]:
    """
    计算Beta系数

    Beta = Cov(股票收益, 市场收益) / Var(市场收益)

    参数:
        stock_returns: 股票收益率序列
        market_returns: 市场收益率序列
        window: 滚动窗口（None表示计算总体Beta）

    返回:
        Beta系数（浮点数或序列）

    示例:
        >>> stock_ret = pd.Series([0.01, 0.02, -0.01, 0.015])
        >>> market_ret = pd.Series([0.008, 0.015, -0.005, 0.01])
        >>> beta = calculate_beta(stock_ret, market_ret)
    """
    if window is None:
        # 计算总体Beta
        covariance = stock_returns.cov(market_returns)
        market_variance = market_returns.var()

        if market_variance == 0:
            return np.nan

        return covariance / market_variance
    else:
        # 计算滚动Beta
        covariance = rolling_cov(stock_returns, market_returns, window=window)
        market_variance = rolling_var(market_returns, window=window)

        return covariance / market_variance.replace(0, np.nan)


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    计算夏普比率

    Sharpe Ratio = (年化收益 - 无风险收益) / 年化波动率

    参数:
        returns: 收益率序列
        risk_free_rate: 无风险利率（年化）
        periods_per_year: 每年的周期数

    返回:
        夏普比率

    示例:
        >>> returns = pd.Series([0.01, 0.02, -0.01, 0.015])
        >>> sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.03)
    """
    excess_returns = calculate_excess_returns(returns, risk_free_rate, periods_per_year)

    # 年化收益
    annual_return = annualize_returns(returns, periods_per_year)

    # 年化波动率
    annual_volatility = returns.std() * np.sqrt(periods_per_year)

    if annual_volatility == 0:
        return np.nan

    return (annual_return - risk_free_rate) / annual_volatility


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    计算索提诺比率

    Sortino Ratio = (年化收益 - 无风险收益) / 下行波动率

    与夏普比率的区别：只考虑负收益的波动性

    参数:
        returns: 收益率序列
        risk_free_rate: 无风险利率（年化）
        periods_per_year: 每年的周期数

    返回:
        索提诺比率
    """
    # 年化收益
    annual_return = annualize_returns(returns, periods_per_year)

    # 下行波动率（只考虑负收益）
    downside_returns = returns[returns < 0]

    if len(downside_returns) == 0:
        return np.nan

    downside_volatility = downside_returns.std() * np.sqrt(periods_per_year)

    if downside_volatility == 0:
        return np.nan

    return (annual_return - risk_free_rate) / downside_volatility


def calculate_max_drawdown(prices: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
    """
    计算最大回撤

    参数:
        prices: 价格序列或净值序列

    返回:
        (最大回撤, 回撤开始日期, 回撤结束日期)

    示例:
        >>> prices = pd.Series([100, 110, 105, 95, 105],
        ...                    index=pd.date_range('2024-01-01', periods=5))
        >>> max_dd, start, end = calculate_max_drawdown(prices)
    """
    # 计算累计最高价
    cumulative_max = prices.cummax()

    # 计算回撤
    drawdown = (prices - cumulative_max) / cumulative_max

    # 找到最大回撤
    max_drawdown = drawdown.min()

    # 找到回撤结束日期（最大回撤发生日）
    end_date = drawdown.idxmin()

    # 找到回撤开始日期（最大回撤之前的最高点）
    start_date = prices[:end_date].idxmax()

    return max_drawdown, start_date, end_date


# ==================== 辅助函数 ====================


def shift_series(
    series: pd.Series,
    periods: int = 1,
    fill_value: Optional[Union[float, int]] = None
) -> pd.Series:
    """
    移位序列

    参数:
        series: 输入序列
        periods: 移位周期（正数向后，负数向前）
        fill_value: 填充值（None表示用NaN填充）

    返回:
        移位后的序列
    """
    return series.shift(periods, fill_value=fill_value)


def diff_series(
    series: pd.Series,
    periods: int = 1
) -> pd.Series:
    """
    计算差分

    参数:
        series: 输入序列
        periods: 差分周期

    返回:
        差分后的序列
    """
    return series.diff(periods)


# ==================== 模块导出 ====================


__all__ = [
    # 收益率计算
    'calculate_returns',
    'calculate_cumulative_returns',
    'annualize_returns',
    'calculate_excess_returns',
    # 滚动统计
    'rolling_mean',
    'rolling_std',
    'rolling_var',
    'rolling_corr',
    'rolling_cov',
    'rolling_min',
    'rolling_max',
    'rolling_sum',
    # 指数加权
    'exponential_moving_average',
    'exponential_weighted_std',
    # 技术指标基础
    'calculate_momentum',
    'calculate_roc',
    'calculate_rsi',
    'calculate_bollinger_bands',
    'calculate_atr',
    # 统计函数
    'calculate_correlation',
    'calculate_beta',
    'calculate_sharpe_ratio',
    'calculate_sortino_ratio',
    'calculate_max_drawdown',
    # 辅助函数
    'shift_series',
    'diff_series',
]
