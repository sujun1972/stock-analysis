"""研发密度策略（R&D Intensity Rotation）

学术背景：
    研发投入被会计准则列入当期费用，但实际具有资本化特征；
    高研发密度公司的长期 Alpha 来自"市场低估无形资产"。

定义：
    研发密度 = inc_rd_exp / inc_revenue

评分：
    score = 当期研发密度 + momentum_weight × 研发密度同比变化

    - 当期密度高 → 科技含量高
    - 同比上升 → 公司持续加码研发 → 未来壁垒变厚
    - 同比下降 → 研发投入缩水（警示信号，降分但不负分）

    不参与评分：inc_rd_exp 为空或 <= 0（非科技公司 / 未披露）
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..base_strategy import BaseStrategy
from .._fundamentals_utils import safe_div as _safe_div


class RDIntensityStrategy(BaseStrategy):
    """研发密度 + 同比变化组合评分。"""

    def __init__(self, name: str, config: Dict[str, Any]):
        default_config = {
            'momentum_weight': 0.3,
            'min_revenue': 1e8,
            'lookback_quarters': 4,  # 4 季度近似 1 年
            'top_n': 30,
            'holding_period': 60,
        }
        default_config.update(config)
        super().__init__(name, default_config)

        self.momentum_weight = float(self.config.custom_params.get('momentum_weight', 0.3))
        self.min_revenue = float(self.config.custom_params.get('min_revenue', 1e8))
        self.lookback_quarters = int(self.config.custom_params.get('lookback_quarters', 4))

        logger.info(
            f"研发密度策略参数: momentum_weight={self.momentum_weight}, "
            f"min_revenue={self.min_revenue:.0e}, lookback_quarters={self.lookback_quarters}"
        )

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None,
        fundamentals: Optional[pd.DataFrame] = None,
    ) -> pd.Series:
        if fundamentals is None or fundamentals.empty:
            logger.warning("研发密度策略缺少 fundamentals 数据，返回全 0 评分")
            return pd.Series(0.0, index=prices.columns, dtype=float)

        df = fundamentals.sort_values(
            ['ts_code', 'end_date'], ascending=[True, False]
        ).reset_index(drop=True)

        scores_dict: Dict[str, float] = {}
        excluded_no_rd = 0
        for ts_code, group in df.groupby('ts_code', sort=False):
            group = group.reset_index(drop=True)
            cur = group.iloc[0]
            rd_cur = cur.get('inc_rd_exp')
            rev_cur = cur.get('inc_revenue')
            if (
                rd_cur is None or np.isnan(rd_cur) or rd_cur <= 0
                or rev_cur is None or np.isnan(rev_cur) or rev_cur < self.min_revenue
            ):
                excluded_no_rd += 1
                continue
            rd_intensity_cur = rd_cur / rev_cur

            # 同比：取 lookback_quarters 期之前（不足则用最老一期）
            yearago_idx = min(self.lookback_quarters, len(group) - 1)
            if yearago_idx == 0:
                rd_mom = 0.0
            else:
                prev = group.iloc[yearago_idx]
                rd_prev_intensity = _safe_div(prev.get('inc_rd_exp'), prev.get('inc_revenue'))
                rd_mom = (rd_intensity_cur - rd_prev_intensity) if not np.isnan(rd_prev_intensity) else 0.0

            score = rd_intensity_cur + self.momentum_weight * rd_mom
            if score > 0:
                scores_dict[ts_code] = float(score)

        result = pd.Series(0.0, index=prices.columns, dtype=float)
        for ts, v in scores_dict.items():
            if ts in result.index:
                result.loc[ts] = v

        selected = (result > 0).sum()
        logger.info(
            f"研发密度策略: 无研发/低营收排除 {excluded_no_rd} 只，有效正值 {len(scores_dict)}，"
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
