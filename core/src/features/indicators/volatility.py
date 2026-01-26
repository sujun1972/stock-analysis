"""
波动率指标模块

提供波动性分析相关的技术指标：
- ATR (Average True Range): 平均真实波幅
- Historical Volatility: 历史波动率（年化标准差）

使用场景：
- 评估市场风险
- 设置止损位
- 调整仓位大小
- 识别市场活跃度
"""

import pandas as pd
import numpy as np
from .base import BaseIndicator, talib


class VolatilityIndicators(BaseIndicator):
    """波动率指标计算器"""

    def add_atr(
        self,
        periods: list = [14, 28]
    ) -> pd.DataFrame:
        """
        添加ATR指标（平均真实波幅）

        参数:
            periods: 周期列表

        返回:
            添加ATR列的DataFrame
        """
        # 支持单个整数或列表
        if isinstance(periods, int):
            periods = [periods]

        for period in periods:
            period = int(period)
            high = pd.to_numeric(self.df['high'], errors='coerce')
            low = pd.to_numeric(self.df['low'], errors='coerce')
            close = pd.to_numeric(self.df['close'], errors='coerce')

            self.df[f'ATR{period}'] = talib.ATR(high, low, close, timeperiod=period)
            # ATR百分比（相对于价格的波动率）
            self.df[f'ATR{period}_PCT'] = self.df[f'ATR{period}'] / close * 100

        return self.df

    def add_volatility(
        self,
        periods: list = [5, 10, 20, 60],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加历史波动率

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加波动率列的DataFrame
        """
        returns = self.df[price_col].pct_change()

        for period in periods:
            self.df[f'VOL{period}'] = returns.rolling(window=period).std() * np.sqrt(252) * 100

        return self.df
