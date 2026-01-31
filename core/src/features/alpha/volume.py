"""
成交量因子计算器

包含:
- VolumeFactorCalculator: 计算成交量变化率、量价相关性等因子
"""

import pandas as pd
from typing import List
from loguru import logger
import time

from .base import BaseFactorCalculator, FactorConfig
from src.utils.response import Response


class VolumeFactorCalculator(BaseFactorCalculator):
    """成交量因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

        vol_col = self._get_volume_column()
        if vol_col is None:
            logger.warning("找不到成交量列，部分功能将不可用")

    def add_volume_factors(
        self,
        periods: List[int] = None,
        volume_col: str = None
    ) -> pd.DataFrame:
        """
        添加成交量因子

        参数:
            periods: 周期列表
            volume_col: 成交量列名（自动检测）

        返回:
            添加成交量因子的DataFrame
        """
        if volume_col is None:
            volume_col = self._get_volume_column()

        if volume_col is None or volume_col not in self.df.columns:
            logger.warning(f"找不到成交量列'{volume_col}'，跳过成交量因子")
            return self.df

        if periods is None:
            periods = FactorConfig.DEFAULT_SHORT_PERIODS

        logger.debug(f"计算成交量因子，周期: {periods}")

        for period in periods:
            try:
                # 成交量变化率
                self.df[f'VOLUME_CHG{period}'] = (
                    self.df[volume_col].pct_change(period) * 100
                )

                # 成交量相对强度
                vol_ma = self.df[volume_col].rolling(window=period).mean()
                self.df[f'VOLUME_RATIO{period}'] = self._safe_divide(
                    self.df[volume_col], vol_ma
                )

                # 成交量标准化（Z-score）
                vol_std = self.df[volume_col].rolling(window=period).std()
                self.df[f'VOLUME_ZSCORE{period}'] = self._safe_divide(
                    self.df[volume_col] - vol_ma, vol_std
                )

            except Exception as e:
                logger.error(f"计算成交量因子 VOLUME{period} 失败: {e}")

        return self.df

    def add_price_volume_correlation(
        self,
        periods: List[int] = None,
        price_col: str = 'close',
        volume_col: str = None
    ) -> pd.DataFrame:
        """
        添加价量相关性因子

        计算两种价量相关性指标:
        1. PV_CORR: 价格变化率与成交量变化率的相关性（量价同步性）
        2. PV_ABS_CORR: 价格变化率与成交量绝对值的相关性（原有逻辑）

        参数:
            periods: 周期列表
            price_col: 价格列名
            volume_col: 成交量列名

        返回:
            添加价量相关性因子的DataFrame

        注意:
            - PV_CORR更符合量价关系的经济学含义（涨跌同步性）
            - PV_ABS_CORR可用于检测价格变化与成交量活跃度的关系
        """
        if volume_col is None:
            volume_col = self._get_volume_column()

        if volume_col is None or volume_col not in self.df.columns:
            logger.warning(f"找不到成交量列'{volume_col}'，跳过价量相关性因子")
            return self.df

        if periods is None:
            periods = FactorConfig.DEFAULT_MEDIUM_PERIODS

        logger.debug(f"计算价量相关性因子，周期: {periods}")

        price_ret = self._calculate_returns(price_col)
        volume_ret = self.df[volume_col].pct_change()

        for period in periods:
            try:
                # 1. 价格变化率与成交量变化率的相关性（推荐使用）
                self.df[f'PV_CORR{period}'] = (
                    price_ret.rolling(window=period).corr(volume_ret)
                )

                # 2. 价格变化率与成交量绝对值的相关性（保留用于对比）
                self.df[f'PV_ABS_CORR{period}'] = (
                    price_ret.rolling(window=period).corr(self.df[volume_col])
                )

            except Exception as e:
                logger.error(f"计算价量相关性 PV_CORR{period} 失败: {e}")

        return self.df

    def calculate_all(self) -> Response:
        """
        计算所有成交量类因子

        返回:
            Response对象，包含计算结果和元信息
        """
        try:
            start_time = time.time()
            initial_cols = len(self.df.columns)

            # 计算各类成交量因子
            self.add_volume_factors()
            self.add_price_volume_correlation()

            # 计算新增因子数量
            n_factors_added = len(self.df.columns) - initial_cols
            elapsed = time.time() - start_time

            return Response.success(
                data=self.df,
                message=f"成交量因子计算完成",
                n_factors=n_factors_added,
                total_columns=len(self.df.columns),
                elapsed_time=f"{elapsed:.3f}s"
            )
        except Exception as e:
            logger.error(f"成交量因子计算失败: {e}")
            return Response.error(
                error=f"成交量因子计算失败: {str(e)}",
                error_code="VOLUME_CALCULATION_ERROR",
                exception_type=type(e).__name__
            )
