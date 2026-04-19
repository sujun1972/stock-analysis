"""存货周转率策略（Inventory Turnover Efficiency）

核心逻辑：
    存货周转率 = 营业收入 / 存货
    高周转率 + 持续提升 = 运营效率好、产品畅销、现金循环快

    - 横截面 level 排名（当期周转率高）
    - 时间序列 change 排名（周转率同比改善）
    - 综合评分：level_rank + change_weight × change_rank

    适用行业：制造业、零售业、消费品（存货敏感）
    不适用：服务业、金融（存货 ≈ 0，系统自动剔除）

评分：
    score = 横截面百分位(周转率水平) + 0.5 × 横截面百分位(周转率变化)
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..base_strategy import BaseStrategy
from .._fundamentals_utils import safe_div as _safe_div


class InventoryTurnoverStrategy(BaseStrategy):
    """存货周转率 + 变化率双因子策略。"""

    def __init__(self, name: str, config: Dict[str, Any]):
        default_config = {
            'change_weight': 0.5,
            'min_inventory': 1e7,  # 剔除服务业（存货 < 1000 万）
            'top_n': 30,
            'holding_period': 60,
        }
        default_config.update(config)
        super().__init__(name, default_config)

        self.change_weight = float(self.config.custom_params.get('change_weight', 0.5))
        self.min_inventory = float(self.config.custom_params.get('min_inventory', 1e7))

        logger.info(
            f"存货周转率策略参数: change_weight={self.change_weight}, "
            f"min_inventory={self.min_inventory:.0e}, top_n={self.config.top_n}"
        )

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None,
        fundamentals: Optional[pd.DataFrame] = None,
    ) -> pd.Series:
        if fundamentals is None or fundamentals.empty:
            logger.warning("存货周转率策略缺少 fundamentals 数据，返回全 0 评分")
            return pd.Series(0.0, index=prices.columns, dtype=float)

        df = fundamentals.sort_values(
            ['ts_code', 'end_date'], ascending=[True, False]
        ).reset_index(drop=True)

        levels: Dict[str, float] = {}
        changes: Dict[str, float] = {}
        for ts_code, group in df.groupby('ts_code', sort=False):
            group = group.reset_index(drop=True)
            if len(group) < 2:
                continue
            cur, prev = group.iloc[0], group.iloc[1]
            inv_cur = cur.get('bs_inventories')
            inv_prev = prev.get('bs_inventories')
            if (inv_cur is None or np.isnan(inv_cur) or inv_cur < self.min_inventory
                    or inv_prev is None or np.isnan(inv_prev) or inv_prev < self.min_inventory):
                continue
            turn_cur = _safe_div(cur.get('inc_revenue'), inv_cur)
            turn_prev = _safe_div(prev.get('inc_revenue'), inv_prev)
            if np.isnan(turn_cur) or np.isnan(turn_prev):
                continue
            levels[ts_code] = turn_cur
            changes[ts_code] = turn_cur - turn_prev

        if len(levels) < 10:
            logger.warning(f"存货周转率策略有效样本不足（{len(levels)} 只），返回全 0")
            return pd.Series(0.0, index=prices.columns, dtype=float)

        level_series = pd.Series(levels)
        change_series = pd.Series(changes)

        # 横截面百分位排名（0-1）
        level_rank = level_series.rank(pct=True)
        change_rank = change_series.rank(pct=True)

        combined = level_rank + self.change_weight * change_rank

        result = pd.Series(0.0, index=prices.columns, dtype=float)
        for ts, v in combined.items():
            if ts in result.index:
                result.loc[ts] = float(v)

        selected = (result > 0).sum()
        logger.info(
            f"存货周转率策略: 有效样本 {len(levels)}，入选 {selected} 只"
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
