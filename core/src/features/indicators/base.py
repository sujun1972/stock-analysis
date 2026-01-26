"""
技术指标基类和通用工具模块

本模块提供：
1. BaseIndicator 基类 - 所有指标计算器的父类
2. talib 包装器 - 优先使用 TA-Lib，不可用时使用纯 Python 实现
3. HAS_TALIB 标志 - 指示是否安装了 TA-Lib

设计说明：
- 所有指标计算器都继承自 BaseIndicator
- 提供 DataFrame 验证和通用方法
- Fallback 实现确保在没有 TA-Lib 的环境中也能运行
"""

import pandas as pd
import numpy as np
import warnings
from typing import Optional

# 尝试导入talib，如果不存在则使用纯Python实现
try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    warnings.warn("TA-Lib not installed. Using pure Python implementations.")

    # Fallback implementations using pandas
    class talib:
        """Fallback talib implementation using pandas"""
        @staticmethod
        def SMA(data, timeperiod):
            return data.rolling(window=timeperiod).mean()

        @staticmethod
        def EMA(data, timeperiod):
            return data.ewm(span=timeperiod, adjust=False).mean()

        @staticmethod
        def BBANDS(data, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0):
            middle = data.rolling(window=timeperiod).mean()
            std = data.rolling(window=timeperiod).std()
            upper = middle + nbdevup * std
            lower = middle - nbdevdn * std
            return upper, middle, lower

        @staticmethod
        def RSI(data, timeperiod=14):
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=timeperiod).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=timeperiod).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        @staticmethod
        def MACD(data, fastperiod=12, slowperiod=26, signalperiod=9):
            ema_fast = data.ewm(span=fastperiod, adjust=False).mean()
            ema_slow = data.ewm(span=slowperiod, adjust=False).mean()
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=signalperiod, adjust=False).mean()
            hist = macd - signal
            return macd, signal, hist

        @staticmethod
        def STOCH(high, low, close, fastk_period=5, slowk_period=3, slowd_period=3):
            lowest_low = low.rolling(window=fastk_period).min()
            highest_high = high.rolling(window=fastk_period).max()
            fastk = 100 * (close - lowest_low) / (highest_high - lowest_low)
            slowk = fastk.rolling(window=slowk_period).mean()
            slowd = slowk.rolling(window=slowd_period).mean()
            return slowk, slowd

        @staticmethod
        def CCI(high, low, close, timeperiod=14):
            tp = (high + low + close) / 3
            sma = tp.rolling(window=timeperiod).mean()
            mad = tp.rolling(window=timeperiod).apply(lambda x: np.abs(x - x.mean()).mean())
            return (tp - sma) / (0.015 * mad)

        @staticmethod
        def ATR(high, low, close, timeperiod=14):
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(window=timeperiod).mean()

        @staticmethod
        def OBV(close, volume):
            obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
            return obv

        @staticmethod
        def ADX(high, low, close, timeperiod=14):
            # Simplified ADX calculation
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=timeperiod).mean()

            up_move = high - high.shift()
            down_move = low.shift() - low

            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

            plus_di = 100 * pd.Series(plus_dm).rolling(window=timeperiod).mean() / atr
            minus_di = 100 * pd.Series(minus_dm).rolling(window=timeperiod).mean() / atr

            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=timeperiod).mean()
            return adx


warnings.filterwarnings('ignore')


class BaseIndicator:
    """技术指标基类"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化技术指标计算器

        参数:
            df: 价格DataFrame，需包含 open, high, low, close 列
        """
        self.df = df.copy()
        self._validate_dataframe()

    def _validate_dataframe(self):
        """验证DataFrame格式"""
        required_cols = ['open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in self.df.columns]

        if missing_cols:
            raise ValueError(f"DataFrame缺少必需的列: {missing_cols}")

    def get_dataframe(self) -> pd.DataFrame:
        """获取包含所有指标的DataFrame"""
        return self.df
