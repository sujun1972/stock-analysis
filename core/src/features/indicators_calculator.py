"""
技术指标计算器

提供各种技术指标的计算方法，所有方法都是纯函数，便于测试和复用。

作者: Stock Analysis Team
更新: 2026-01-27
"""

import pandas as pd
import numpy as np
from typing import Tuple


def safe_divide(numerator: pd.Series, denominator: pd.Series, fill_value: float = 0.0) -> pd.Series:
    """
    安全除法，处理除零情况

    Args:
        numerator: 分子
        denominator: 分母
        fill_value: 除零时的填充值

    Returns:
        计算结果
    """
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = numerator / denominator
        result = result.replace([np.inf, -np.inf], fill_value)
        result = result.fillna(fill_value)
    return result


# ==================== 技术指标计算函数 ====================

def calculate_rsi(series: pd.Series, period: int) -> pd.Series:
    """
    计算RSI (相对强弱指标)

    Args:
        series: 价格序列
        period: 计算周期

    Returns:
        RSI 值序列
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    # 使用安全除法避免除零
    rs = safe_divide(gain, loss, fill_value=0)
    rsi = 100 - safe_divide(100, (1 + rs), fill_value=50)

    return rsi


def calculate_macd(series: pd.Series, fast: int, slow: int, signal: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算MACD指标

    Args:
        series: 价格序列
        fast: 快线周期
        slow: 慢线周期
        signal: 信号线周期

    Returns:
        (MACD, Signal, Histogram) 三个序列的元组
    """
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, signal_line, hist


def calculate_kdj(df: pd.DataFrame, n: int, m1: int, m2: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算KDJ指标

    Args:
        df: 包含 high, low, close 的 DataFrame
        n: RSV 计算周期
        m1: K 值平滑参数
        m2: D 值平滑参数

    Returns:
        (K, D, J) 三个序列的元组
    """
    low_list = df['low'].rolling(window=n).min()
    high_list = df['high'].rolling(window=n).max()

    # 使用安全除法计算 RSV
    rsv = safe_divide(df['close'] - low_list, high_list - low_list, fill_value=0) * 100

    k = rsv.ewm(com=m1 - 1, adjust=False).mean()
    d = k.ewm(com=m2 - 1, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def calculate_boll(series: pd.Series, period: int, std_num: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算布林带

    Args:
        series: 价格序列
        period: 计算周期
        std_num: 标准差倍数

    Returns:
        (Upper, Middle, Lower) 三个序列的元组
    """
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = middle + std_num * std
    lower = middle - std_num * std
    return upper, middle, lower


def calculate_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """
    计算ATR (平均真实波幅)

    Args:
        df: 包含 high, low, close 的 DataFrame
        period: 计算周期

    Returns:
        ATR 值序列
    """
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """
    计算OBV (能量潮)

    Args:
        df: 包含 close, volume 的 DataFrame

    Returns:
        OBV 值序列
    """
    obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    return obv


def calculate_cci(df: pd.DataFrame, period: int) -> pd.Series:
    """
    计算CCI (商品通道指标)

    Args:
        df: 包含 high, low, close 的 DataFrame
        period: 计算周期

    Returns:
        CCI 值序列
    """
    tp = (df['high'] + df['low'] + df['close']) / 3
    ma = tp.rolling(window=period).mean()
    md = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())

    # 使用安全除法
    cci = safe_divide(tp - ma, 0.015 * md, fill_value=0)
    return cci


# ==================== 导出 ====================

__all__ = [
    'safe_divide',
    'calculate_rsi',
    'calculate_macd',
    'calculate_kdj',
    'calculate_boll',
    'calculate_atr',
    'calculate_obv',
    'calculate_cci',
]
