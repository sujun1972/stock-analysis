"""
成交量指标模块

提供成交量分析相关的技术指标：
- OBV (On-Balance Volume): 能量潮指标
- Volume MA: 成交量移动平均线

使用场景：
- 确认价格趋势
- 识别资金流向
- 判断趋势可靠性
- 预警趋势反转
"""

import pandas as pd
import numpy as np
from .base import BaseIndicator, talib

# 尝试导入 loguru，如果不存在则使用简单的后备方案
try:
    from loguru import logger
except ImportError:
    class SimpleLogger:
        @staticmethod
        def warning(msg): logger.warning(f"WARNING: {msg}")
    logger = SimpleLogger()


class VolumeIndicators(BaseIndicator):
    """成交量指标计算器"""

    def add_obv(
        self,
        price_col: str = 'close',
        volume_col: str = 'volume'
    ) -> pd.DataFrame:
        """
        添加OBV指标（能量潮）

        参数:
            price_col: 价格列名
            volume_col: 成交量列名

        返回:
            添加OBV列的DataFrame
        """
        if volume_col not in self.df.columns:
            logger.warning(f"列'{volume_col}'不存在，跳过OBV计算")
            return self.df

        self.df['OBV'] = talib.OBV(self.df[price_col], self.df[volume_col])

        return self.df

    def add_volume_ma(
        self,
        periods: list = [5, 10, 20],
        volume_col: str = 'volume'
    ) -> pd.DataFrame:
        """
        添加成交量移动平均线

        参数:
            periods: 周期列表
            volume_col: 成交量列名

        返回:
            添加成交量MA列的DataFrame
        """
        if volume_col not in self.df.columns:
            logger.warning(f"列'{volume_col}'不存在，跳过成交量MA计算")
            return self.df

        for period in periods:
            self.df[f'VOL_MA{period}'] = talib.SMA(self.df[volume_col], timeperiod=period)

        return self.df
