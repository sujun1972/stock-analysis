"""高质量 + 高动量组合策略（Quality × Momentum）

核心逻辑：
    Quality + Momentum 是学术界广泛验证的长效因子组合：
        - Quality：盈利能力 + 现金流 + 毛利率（3 分制轻量 F-Score）
        - Momentum：20 日价格动量（横截面百分位排名）

    筛选：Quality >= threshold（默认 2/3）
    评分：Quality × MomentumRank（高质量放大高动量）

    这是首个同时使用 `prices` 和 `fundamentals` 的策略，
    展示两类数据如何协同构造复合因子。

评分：
    score = quality_score(0-3) × momentum_rank(0-1)
    if quality_score < threshold: score = 0
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..base_strategy import BaseStrategy
from .._fundamentals_utils import safe_div as _safe_div


class QualityMomentumStrategy(BaseStrategy):
    """Quality(3-factor lite) × Momentum(20d) 组合策略。"""

    def __init__(self, name: str, config: Dict[str, Any]):
        default_config = {
            'quality_threshold': 2,     # 3 个质量因子中至少满足几个
            'momentum_lookback': 20,
            'gross_margin_floor': 0.10, # 毛利率 > 10% 视为合格
            'top_n': 30,
            'holding_period': 20,
        }
        default_config.update(config)
        super().__init__(name, default_config)

        self.quality_threshold = int(self.config.custom_params.get('quality_threshold', 2))
        self.quality_threshold = max(0, min(3, self.quality_threshold))
        self.momentum_lookback = int(self.config.custom_params.get('momentum_lookback', 20))
        self.gross_margin_floor = float(self.config.custom_params.get('gross_margin_floor', 0.10))

        logger.info(
            f"Quality × Momentum 策略参数: quality_threshold={self.quality_threshold}/3, "
            f"momentum_lookback={self.momentum_lookback}, "
            f"gross_margin_floor={self.gross_margin_floor:.0%}"
        )

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None,
        fundamentals: Optional[pd.DataFrame] = None,
    ) -> pd.Series:
        if fundamentals is None or fundamentals.empty:
            logger.warning("Quality × Momentum 策略缺少 fundamentals，返回全 0 评分")
            return pd.Series(0.0, index=prices.columns, dtype=float)

        # Part A: 计算动量（prices 侧）
        actual_lookback = self.momentum_lookback
        if prices.shape[0] < self.momentum_lookback + 1:
            fallback = max(5, prices.shape[0] - 1)
            logger.warning(
                f"prices 行数不足（{prices.shape[0]}），momentum_lookback 降级为 {fallback}"
            )
            actual_lookback = fallback
        momentum = prices.pct_change(actual_lookback).iloc[-1]  # Series indexed by ts_code
        # 横截面百分位排名（0-1，越大动量越强）
        mom_rank = momentum.rank(pct=True)

        # Part B: 计算质量评分（fundamentals 侧）
        latest = (
            fundamentals.sort_values(['ts_code', 'end_date'], ascending=[True, False])
            .groupby('ts_code', sort=False)
            .head(1)
        )
        quality_dict: Dict[str, int] = {}
        for _, row in latest.iterrows():
            ts_code = row['ts_code']
            q1 = 1 if _safe_div(row.get('inc_n_income'), row.get('bs_total_assets')) and (
                _safe_div(row.get('inc_n_income'), row.get('bs_total_assets')) > 0
            ) else 0
            cfo = row.get('cf_n_cashflow_act')
            q2 = 1 if (cfo is not None and not np.isnan(cfo) and cfo > 0) else 0
            gm = _safe_div(
                (row.get('inc_revenue') or np.nan) - (row.get('inc_oper_cost') or np.nan),
                row.get('inc_revenue'),
            )
            q3 = 1 if (not np.isnan(gm) and gm > self.gross_margin_floor) else 0
            quality_dict[ts_code] = q1 + q2 + q3

        # Part C: 合成评分
        result = pd.Series(0.0, index=prices.columns, dtype=float)
        quality_qualified = 0
        for ts_code in prices.columns:
            q = quality_dict.get(ts_code, 0)
            if q < self.quality_threshold:
                continue
            quality_qualified += 1
            m = mom_rank.get(ts_code)
            if m is None or np.isnan(m):
                continue
            result.loc[ts_code] = float(q) * float(m)

        selected = (result > 0).sum()
        logger.info(
            f"Quality × Momentum 策略: 质量达标 {quality_qualified} 只 "
            f"(≥{self.quality_threshold}/3)，入选 {selected} 只"
        )
        return result

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs,
    ) -> pd.DataFrame:
        return pd.DataFrame(0, index=prices.index, columns=prices.columns)
