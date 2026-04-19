"""应收账款风险策略（AR Quality Rotation）

核心逻辑：
    应收账款 / 营收 比率反映"信用销售占比"：
        - 比率快速上升 → 公司为了业绩压货，客户资质可能恶化 → 坏账风险
        - 比率下降 → 现金回款改善 → 盈利质量提升

本策略为"安全区筛选器"：只给 AR 比率改善（下降）的股票正分，
AR 比率上升的股票评分 0（系统层过滤掉）。

评分：
    AR 比率 = bs_accounts_receiv / inc_revenue
    变化 = 当期 AR 比率 - 上期 AR 比率
    score = -变化 × scale_factor（下降越多，分数越高）

    只有 score > 0（即 AR 改善）的股票被选入。
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..base_strategy import BaseStrategy
from .._fundamentals_utils import safe_div as _safe_div


class AccountsReceivableRiskStrategy(BaseStrategy):
    """应收账款改善评分策略。"""

    def __init__(self, name: str, config: Dict[str, Any]):
        default_config = {
            'min_revenue': 1e8,     # 剔除壳公司
            'scale_factor': 100,    # 将 AR 比率变化放大到可读数值
            'max_score': 50.0,      # 避免极端 outlier（小营收分母）主导结果
            'top_n': 30,
            'holding_period': 60,
        }
        default_config.update(config)
        super().__init__(name, default_config)

        self.min_revenue = float(self.config.custom_params.get('min_revenue', 1e8))
        self.scale_factor = float(self.config.custom_params.get('scale_factor', 1000))
        self.max_score = float(self.config.custom_params.get('max_score', 100.0))

        logger.info(
            f"应收账款风险策略参数: min_revenue={self.min_revenue:.0e}, "
            f"scale={self.scale_factor}, max_score={self.max_score}"
        )

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None,
        fundamentals: Optional[pd.DataFrame] = None,
    ) -> pd.Series:
        if fundamentals is None or fundamentals.empty:
            logger.warning("应收账款策略缺少 fundamentals 数据，返回全 0 评分")
            return pd.Series(0.0, index=prices.columns, dtype=float)

        df = fundamentals.sort_values(
            ['ts_code', 'end_date'], ascending=[True, False]
        ).reset_index(drop=True)

        scores_dict: Dict[str, float] = {}
        improvers = 0
        deteriorators = 0
        for ts_code, group in df.groupby('ts_code', sort=False):
            group = group.reset_index(drop=True)
            if len(group) < 2:
                continue
            cur = group.iloc[0]
            prev = group.iloc[1]

            rev_cur = cur.get('inc_revenue')
            rev_prev = prev.get('inc_revenue')
            if (rev_cur is None or np.isnan(rev_cur) or rev_cur < self.min_revenue
                    or rev_prev is None or np.isnan(rev_prev) or rev_prev < self.min_revenue):
                continue

            ar_cur = _safe_div(cur.get('bs_accounts_receiv'), rev_cur)
            ar_prev = _safe_div(prev.get('bs_accounts_receiv'), rev_prev)
            if np.isnan(ar_cur) or np.isnan(ar_prev):
                continue

            ar_change = ar_cur - ar_prev
            if ar_change > 0:
                deteriorators += 1
                continue  # AR 恶化不选

            # AR 改善：放大 + 裁剪
            score = min(self.max_score, -ar_change * self.scale_factor)
            if score > 0:
                scores_dict[ts_code] = score
                improvers += 1

        result = pd.Series(0.0, index=prices.columns, dtype=float)
        for ts, v in scores_dict.items():
            if ts in result.index:
                result.loc[ts] = v

        selected = (result > 0).sum()
        logger.info(
            f"应收账款策略: AR 改善 {improvers} 只，AR 恶化 {deteriorators} 只（剔除），"
            f"入选 {selected} 只"
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
