"""
反转因子计算器

包含:
- ReversalFactorCalculator: 计算短期反转、Z-score、隔夜反转等因子
"""

import pandas as pd
from typing import List
from loguru import logger
import time

from .base import BaseFactorCalculator, FactorConfig
from src.utils.response import Response


class ReversalFactorCalculator(BaseFactorCalculator):
    """反转因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

    def add_reversal_factors(
        self,
        short_periods: List[int] = None,
        long_periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加反转因子（短期反转效应）

        参数:
            short_periods: 短期周期列表
            long_periods: 长期周期列表
            price_col: 价格列名

        返回:
            添加反转因子的DataFrame
        """
        if short_periods is None:
            short_periods = [1, 3, 5]
        if long_periods is None:
            long_periods = FactorConfig.DEFAULT_MEDIUM_PERIODS

        logger.debug(f"计算反转因子，短期周期: {short_periods}, 长期周期: {long_periods}")

        # 短期反转（负向动量）
        for period in short_periods:
            try:
                self.df[f'REV{period}'] = -self.df[price_col].pct_change(period, fill_method=None) * 100
            except Exception as e:
                logger.error(f"计算短期反转因子 REV{period} 失败: {e}")

        # 长期反转（均值回归）
        for period in long_periods:
            try:
                ma = self.df[price_col].rolling(window=period).mean()
                std = self.df[price_col].rolling(window=period).std()
                # Z-score（标准化偏离度）
                self.df[f'ZSCORE{period}'] = self._safe_divide(ma - self.df[price_col], std)
            except Exception as e:
                logger.error(f"计算Z-score因子 ZSCORE{period} 失败: {e}")

        return self.df

    def add_overnight_reversal(self) -> pd.DataFrame:
        """
        添加隔夜反转因子（开盘价相对于前收盘的跳空）

        返回:
            添加隔夜反转因子的DataFrame
        """
        if 'open' not in self.df.columns:
            logger.warning("找不到'open'列，跳过隔夜反转因子")
            return self.df

        logger.debug("计算隔夜反转因子")

        try:
            # 隔夜收益率（开盘-前收盘）
            self.df['OVERNIGHT_RET'] = self._safe_divide(
                self.df['open'] - self.df['close'].shift(1),
                self.df['close'].shift(1)
            ) * 100

            # 日内收益率（收盘-开盘）
            self.df['INTRADAY_RET'] = self._safe_divide(
                self.df['close'] - self.df['open'],
                self.df['open']
            ) * 100

            # 隔夜反转强度（隔夜收益的负值）
            self.df['OVERNIGHT_REV'] = -self.df['OVERNIGHT_RET']

        except Exception as e:
            logger.error(f"计算隔夜反转因子失败: {e}")

        return self.df

    def calculate_all(self) -> Response:
        """
        计算所有反转类因子

        返回:
            Response对象，包含计算结果和元信息
        """
        try:
            start_time = time.time()
            initial_cols = len(self.df.columns)

            # 计算各类反转因子
            self.add_reversal_factors()
            self.add_overnight_reversal()

            # 计算新增因子数量
            n_factors_added = len(self.df.columns) - initial_cols
            elapsed = time.time() - start_time

            return Response.success(
                data=self.df,
                message=f"反转因子计算完成",
                n_factors=n_factors_added,
                total_columns=len(self.df.columns),
                elapsed_time=f"{elapsed:.3f}s"
            )
        except Exception as e:
            logger.error(f"反转因子计算失败: {e}")
            return Response.error(
                error=f"反转因子计算失败: {str(e)}",
                error_code="REVERSAL_CALCULATION_ERROR",
                exception_type=type(e).__name__
            )
