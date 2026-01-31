"""
流动性因子计算器

包含:
- LiquidityFactorCalculator: 计算Amihud非流动性指标等因子
"""

import pandas as pd
from typing import List
from loguru import logger
import time

from .base import BaseFactorCalculator
from src.utils.response import Response


class LiquidityFactorCalculator(BaseFactorCalculator):
    """流动性因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

    def add_liquidity_factors(
        self,
        periods: List[int] = None,
        volume_col: str = None
    ) -> pd.DataFrame:
        """
        添加流动性因子（Amihud非流动性指标）

        参数:
            periods: 周期列表
            volume_col: 成交量列名

        返回:
            添加流动性因子的DataFrame
        """
        if volume_col is None:
            volume_col = self._get_volume_column()

        if volume_col is None or volume_col not in self.df.columns:
            logger.warning(f"找不到成交量列'{volume_col}'，跳过流动性因子")
            return self.df

        if periods is None:
            periods = [20]

        logger.debug(f"计算流动性因子，周期: {periods}")

        # 日收益率绝对值
        returns = self.df['close'].pct_change().abs()

        for period in periods:
            try:
                # Amihud非流动性 = |收益率| / 成交量
                amihud = self._safe_divide(returns, self.df[volume_col])
                self.df[f'ILLIQUIDITY{period}'] = (
                    amihud.rolling(window=period).mean() * 1e6  # 放大倍数
                )

            except Exception as e:
                logger.error(f"计算流动性因子 ILLIQUIDITY{period} 失败: {e}")

        return self.df

    def calculate_all(self) -> Response:
        """
        计算所有流动性类因子

        返回:
            Response对象，包含计算结果和元信息
        """
        try:
            start_time = time.time()
            initial_cols = len(self.df.columns)

            # 计算流动性因子
            self.add_liquidity_factors()

            # 计算新增因子数量
            n_factors_added = len(self.df.columns) - initial_cols
            elapsed = time.time() - start_time

            return Response.success(
                data=self.df,
                message=f"流动性因子计算完成",
                n_factors=n_factors_added,
                total_columns=len(self.df.columns),
                elapsed_time=f"{elapsed:.3f}s"
            )
        except Exception as e:
            logger.error(f"流动性因子计算失败: {e}")
            return Response.error(
                error=f"流动性因子计算失败: {str(e)}",
                error_code="LIQUIDITY_CALCULATION_ERROR",
                exception_type=type(e).__name__
            )
