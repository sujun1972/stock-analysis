"""
波动率因子计算器

包含:
- VolatilityFactorCalculator: 计算历史波动率、Parkinson波动率等因子
"""

import pandas as pd
import numpy as np
from typing import List
from loguru import logger
import time

from .base import BaseFactorCalculator, FactorConfig
from src.utils.response import Response


class VolatilityFactorCalculator(BaseFactorCalculator):
    """波动率因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

    def add_volatility_factors(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加波动率因子

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加波动率因子的DataFrame
        """
        if periods is None:
            periods = FactorConfig.DEFAULT_SHORT_PERIODS + [60]

        logger.debug(f"计算波动率因子，周期: {periods}")

        returns = self._calculate_returns(price_col)

        for period in periods:
            try:
                # 历史波动率（年化）
                self.df[f'VOLATILITY{period}'] = (
                    returns.rolling(window=period).std() *
                    np.sqrt(FactorConfig.ANNUAL_TRADING_DAYS) * 100
                )

                # 波动率偏度（衡量极端波动）
                self.df[f'VOLSKEW{period}'] = returns.rolling(window=period).skew()

            except Exception as e:
                logger.error(f"计算波动率因子 VOLATILITY{period} 失败: {e}")

        return self.df

    def add_high_low_volatility(
        self,
        periods: List[int] = None
    ) -> pd.DataFrame:
        """
        添加高低价波动率因子（Parkinson波动率）

        参数:
            periods: 周期列表

        返回:
            添加高低价波动率因子的DataFrame
        """
        if 'high' not in self.df.columns or 'low' not in self.df.columns:
            logger.warning("找不到'high'或'low'列，跳过高低价波动率因子")
            return self.df

        if periods is None:
            periods = [10, 20]

        logger.debug(f"计算Parkinson波动率因子，周期: {periods}")

        for period in periods:
            try:
                # Parkinson波动率（基于高低价）
                hl_ratio = np.log(self._safe_divide(self.df['high'], self.df['low'])) ** 2
                self.df[f'PARKINSON_VOL{period}'] = (
                    np.sqrt(hl_ratio.rolling(window=period).mean() / (4 * np.log(2))) *
                    np.sqrt(FactorConfig.ANNUAL_TRADING_DAYS) * 100
                )

            except Exception as e:
                logger.error(f"计算Parkinson波动率 PARKINSON_VOL{period} 失败: {e}")

        return self.df

    def calculate_all(self) -> Response:
        """
        计算所有波动率类因子

        返回:
            Response对象，包含计算结果和元信息
        """
        try:
            start_time = time.time()
            initial_cols = len(self.df.columns)

            # 计算各类波动率因子
            self.add_volatility_factors()
            self.add_high_low_volatility()

            # 计算新增因子数量
            n_factors_added = len(self.df.columns) - initial_cols
            elapsed = time.time() - start_time

            return Response.success(
                data=self.df,
                message=f"波动率因子计算完成",
                n_factors=n_factors_added,
                total_columns=len(self.df.columns),
                elapsed_time=f"{elapsed:.3f}s"
            )
        except Exception as e:
            logger.error(f"波动率因子计算失败: {e}")
            return Response.error(
                error=f"波动率因子计算失败: {str(e)}",
                error_code="VOLATILITY_CALCULATION_ERROR",
                exception_type=type(e).__name__
            )
