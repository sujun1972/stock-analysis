"""
动量因子计算器

包含:
- MomentumFactorCalculator: 计算动量、相对强度、RSI、加速度等因子
"""

import pandas as pd
import numpy as np
from typing import List
from loguru import logger
import time

from .base import BaseFactorCalculator, FactorConfig
from src.utils.response import Response
from src.exceptions import FeatureCalculationError


class MomentumFactorCalculator(BaseFactorCalculator):
    """动量因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

    def add_momentum_factors(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加动量因子（价格动量）

        参数:
            periods: 周期列表，默认使用配置值
            price_col: 价格列名

        返回:
            添加动量因子的DataFrame
        """
        if periods is None:
            periods = FactorConfig.DEFAULT_SHORT_PERIODS + FactorConfig.DEFAULT_LONG_PERIODS

        logger.debug(f"计算动量因子，周期: {periods}")

        for period in periods:
            try:
                # 简单收益率动量
                self.df[f'MOM{period}'] = self.df[price_col].pct_change(period, fill_method=None) * 100

                # 对数收益率动量
                self.df[f'MOM_LOG{period}'] = (
                    np.log(self.df[price_col] / self.df[price_col].shift(period)) * 100
                )

            except Exception as e:
                logger.error(f"计算动量因子 MOM{period} 失败: {e}")

        return self.df

    def add_relative_strength(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加相对强度因子（价格相对于均线的位置）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加相对强度因子的DataFrame
        """
        if periods is None:
            periods = FactorConfig.DEFAULT_MEDIUM_PERIODS

        logger.debug(f"计算相对强度因子，周期: {periods}")

        for period in periods:
            try:
                ma = self.df[price_col].rolling(window=period).mean()
                # 价格相对于均线的偏离度
                self.df[f'RS{period}'] = self._safe_divide(
                    self.df[price_col] - ma, ma
                ) * 100

            except Exception as e:
                logger.error(f"计算相对强度因子 RS{period} 失败: {e}")

        return self.df

    def add_rsi(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加RSI相对强弱指标

        参数:
            periods: 周期列表，默认[14, 28]
            price_col: 价格列名

        返回:
            添加RSI列的DataFrame
        """
        if periods is None:
            periods = [14, 28]

        logger.debug(f"计算RSI因子，周期: {periods}")

        for period in periods:
            try:
                # 计算价格变化
                delta = self.df[price_col].diff()

                # 分离涨跌
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)

                # 计算平均涨跌幅
                avg_gain = gain.rolling(window=period, min_periods=period).mean()
                avg_loss = loss.rolling(window=period, min_periods=period).mean()

                # 计算RS和RSI
                rs = self._safe_divide(avg_gain, avg_loss)
                self.df[f'RSI{period}'] = 100 - (100 / (1 + rs))

            except Exception as e:
                logger.error(f"计算RSI{period}因子失败: {e}")

        return self.df

    def add_acceleration(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加加速度因子（动量的变化率）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加加速度因子的DataFrame
        """
        if periods is None:
            periods = FactorConfig.DEFAULT_SHORT_PERIODS

        logger.debug(f"计算加速度因子，周期: {periods}")

        for period in periods:
            try:
                momentum = self.df[price_col].pct_change(period)
                # 动量的变化（加速度）
                self.df[f'ACC{period}'] = momentum - momentum.shift(period)

            except Exception as e:
                logger.error(f"计算加速度因子 ACC{period} 失败: {e}")

        return self.df

    def calculate_all(self) -> Response:
        """
        计算所有动量类因子

        返回:
            Response对象，包含计算结果和元信息
        """
        try:
            start_time = time.time()
            initial_cols = len(self.df.columns)

            # 计算各类动量因子
            self.add_momentum_factors()
            self.add_relative_strength()
            self.add_acceleration()

            # 计算新增因子数量
            n_factors_added = len(self.df.columns) - initial_cols
            elapsed = time.time() - start_time

            return Response.success(
                data=self.df,
                message=f"动量因子计算完成",
                n_factors=n_factors_added,
                total_columns=len(self.df.columns),
                elapsed_time=f"{elapsed:.3f}s"
            )
        except Exception as e:
            logger.error(f"动量因子计算失败: {e}")
            return Response.error(
                error=f"动量因子计算失败: {str(e)}",
                error_code="MOMENTUM_CALCULATION_ERROR",
                exception_type=type(e).__name__
            )
