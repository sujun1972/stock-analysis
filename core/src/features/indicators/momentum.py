"""
动量指标模块

提供动量分析相关的技术指标：
- RSI (Relative Strength Index): 相对强弱指数
- MACD (Moving Average Convergence Divergence): 指数平滑异同移动平均线
- KDJ: 随机指标，包含 K、D、J 三个值
- CCI (Commodity Channel Index): 商品通道指标

使用场景：
- 判断超买超卖状态
- 识别趋势转折点
- 评估价格动量强度
"""

import pandas as pd
import numpy as np
from .base import BaseIndicator, talib


class MomentumIndicators(BaseIndicator):
    """动量指标计算器"""

    def add_rsi(
        self,
        periods: list = [6, 12, 24],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加相对强弱指数（RSI）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加RSI列的DataFrame
        """
        for period in periods:
            self.df[f'RSI{period}'] = talib.RSI(self.df[price_col], timeperiod=period)

        return self.df

    def add_macd(
        self,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加MACD指标

        参数:
            fastperiod: 快线周期
            slowperiod: 慢线周期
            signalperiod: 信号线周期
            price_col: 价格列名

        返回:
            添加MACD列的DataFrame
        """
        macd, signal, hist = talib.MACD(
            self.df[price_col],
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod
        )

        self.df['MACD'] = macd
        self.df['MACD_SIGNAL'] = signal
        self.df['MACD_HIST'] = hist

        return self.df

    def add_kdj(
        self,
        fastk_period: int = 9,
        slowk_period: int = 3,
        slowd_period: int = 3
    ) -> pd.DataFrame:
        """
        添加KDJ指标（随机指标）

        参数:
            fastk_period: K线周期
            slowk_period: K线平滑周期
            slowd_period: D线周期

        返回:
            添加KDJ列的DataFrame

        注意:
            移除了slowk_matype和slowd_matype参数，因为某些版本的TA-Lib不支持
        """
        # 调用STOCH计算随机指标（KDJ的K和D值）
        slowk, slowd = talib.STOCH(
            self.df['high'],
            self.df['low'],
            self.df['close'],
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowd_period=slowd_period
        )

        self.df['KDJ_K'] = slowk
        self.df['KDJ_D'] = slowd
        self.df['KDJ_J'] = 3 * slowk - 2 * slowd  # J = 3K - 2D

        return self.df

    def add_cci(
        self,
        periods: list = [14, 28]
    ) -> pd.DataFrame:
        """
        添加CCI指标（商品通道指标）

        参数:
            periods: 周期列表

        返回:
            添加CCI列的DataFrame
        """
        # 支持单个整数或列表
        if isinstance(periods, int):
            periods = [periods]

        for period in periods:
            period = int(period)
            high = pd.to_numeric(self.df['high'], errors='coerce')
            low = pd.to_numeric(self.df['low'], errors='coerce')
            close = pd.to_numeric(self.df['close'], errors='coerce')

            self.df[f'CCI{period}'] = talib.CCI(high, low, close, timeperiod=period)

        return self.df
