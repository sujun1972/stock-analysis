"""
趋势指标模块

提供趋势分析相关的技术指标：
- MA (Simple Moving Average): 简单移动平均线
- EMA (Exponential Moving Average): 指数移动平均线
- Bollinger Bands: 布林带，包含上轨、中轨、下轨以及衍生指标

使用场景：
- 判断市场趋势方向
- 识别支撑和阻力位
- 评估价格波动区间
"""

import pandas as pd
import numpy as np
from .base import BaseIndicator, talib


class TrendIndicators(BaseIndicator):
    """趋势指标计算器"""

    def add_ma(
        self,
        periods: list = [5, 10, 20, 60, 120, 250],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加移动平均线（MA）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加MA列的DataFrame
        """
        for period in periods:
            # 确保period是整数，并将数据转换为数值类型
            period = int(period)
            price_series = pd.to_numeric(self.df[price_col], errors='coerce')
            self.df[f'MA{period}'] = talib.SMA(price_series, timeperiod=period)

        return self.df

    def add_ema(
        self,
        periods: list = [12, 26, 50],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加指数移动平均线（EMA）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加EMA列的DataFrame
        """
        for period in periods:
            self.df[f'EMA{period}'] = talib.EMA(self.df[price_col], timeperiod=period)

        return self.df

    def add_bollinger_bands(
        self,
        period: int = 20,
        nbdevup: float = 2.0,
        nbdevdn: float = 2.0,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加布林带（Bollinger Bands）

        参数:
            period: 周期
            nbdevup: 上轨标准差倍数
            nbdevdn: 下轨标准差倍数
            price_col: 价格列名

        返回:
            添加布林带列的DataFrame
        """
        upper, middle, lower = talib.BBANDS(
            self.df[price_col],
            timeperiod=period,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn,
            matype=0
        )

        self.df['BOLL_UPPER'] = upper
        self.df['BOLL_MIDDLE'] = middle
        self.df['BOLL_LOWER'] = lower

        # 布林带宽度（波动率指标）
        self.df['BOLL_WIDTH'] = (upper - lower) / middle

        # 价格在布林带中的位置 (0-1之间)
        self.df['BOLL_POS'] = (self.df[price_col] - lower) / (upper - lower)

        return self.df
