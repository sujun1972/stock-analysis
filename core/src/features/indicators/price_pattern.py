"""
价格形态指标模块

提供K线形态分析相关的特征：
- RETURN: 涨跌幅
- AMPLITUDE: 振幅
- UPPER_SHADOW: 上影线长度
- LOWER_SHADOW: 下影线长度
- BODY: K线实体长度
- IS_BULL: 是否为阳线

使用场景：
- 识别K线形态
- 分析价格行为
- 评估市场情绪
- 辅助趋势判断
"""

import pandas as pd
import numpy as np
from .base import BaseIndicator


class PricePatternIndicators(BaseIndicator):
    """价格形态指标计算器"""

    def add_price_patterns(self) -> pd.DataFrame:
        """
        添加价格形态特征

        返回:
            添加价格形态列的DataFrame
        """
        # 涨跌幅
        self.df['RETURN'] = self.df['close'].pct_change() * 100

        # 振幅
        self.df['AMPLITUDE'] = (self.df['high'] - self.df['low']) / self.df['close'].shift(1) * 100

        # 上影线长度（相对于实体）
        self.df['UPPER_SHADOW'] = (
            self.df['high'] - self.df[['open', 'close']].max(axis=1)
        ) / self.df['close'] * 100

        # 下影线长度（相对于实体）
        self.df['LOWER_SHADOW'] = (
            self.df[['open', 'close']].min(axis=1) - self.df['low']
        ) / self.df['close'] * 100

        # 实体长度
        self.df['BODY'] = abs(self.df['close'] - self.df['open']) / self.df['close'] * 100

        # 是否为阳线
        self.df['IS_BULL'] = (self.df['close'] > self.df['open']).astype(int)

        return self.df
