"""Sloan 应计策略（Accruals Anomaly）

学术背景：
    Sloan R G. (1996). Do Stock Prices Fully Reflect Information in Accruals
    and Cash Flows About Future Earnings? The Accounting Review.

核心观察：
    净利润 = 经营现金流 + 应计利润。市场往往把应计部分（accruals）当作真利润，
    但研究证明低应计（盈利质量高）的股票长期跑赢高应计（盈利质量差）。

应计比率 = (净利润 - 经营现金流) / 总资产

    - 值越小（甚至为负） → 盈利质量越高 → 未来回报预期更好
    - 值越大 → 盈利被"应收款 / 存货增长"虚增 → 未来回报预期更差

评分逻辑：
    横截面按应计比率升序 rank，最低 top_pct 的股票归入"低应计组"，
    评分 = 归一化到 (0, 1] 的排名，其余股票评分 0。
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..base_strategy import BaseStrategy
from .._fundamentals_utils import safe_div as _safe_div


class SloanAccrualsStrategy(BaseStrategy):
    """Sloan 应计异常选股：低应计 = 高盈利质量 = 高预期收益。"""

    def __init__(self, name: str, config: Dict[str, Any]):
        default_config = {
            'min_total_assets': 5e8,  # 剔除微盘股（总资产 < 5 亿），分母过小噪声大
            'top_pct': 0.3,            # 最低应计比率的 30% 股票入选
            'top_n': 30,
            'holding_period': 60,
        }
        default_config.update(config)
        super().__init__(name, default_config)

        self.min_total_assets = float(self.config.custom_params.get('min_total_assets', 5e8))
        self.top_pct = float(self.config.custom_params.get('top_pct', 0.3))
        self.top_pct = max(0.05, min(1.0, self.top_pct))

        logger.info(
            f"Sloan 应计策略参数: min_total_assets={self.min_total_assets:.0e}, "
            f"top_pct={self.top_pct:.0%}, top_n={self.config.top_n}"
        )

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None,
        fundamentals: Optional[pd.DataFrame] = None,
    ) -> pd.Series:
        if fundamentals is None or fundamentals.empty:
            logger.warning("Sloan 策略缺少 fundamentals 数据，返回全 0 评分")
            return pd.Series(0.0, index=prices.columns, dtype=float)

        # 每只股票取最新一期
        latest = (
            fundamentals.sort_values(['ts_code', 'end_date'], ascending=[True, False])
            .groupby('ts_code', sort=False)
            .head(1)
            .copy()
        )

        # 计算应计比率
        accruals = []
        for _, row in latest.iterrows():
            ts_code = row['ts_code']
            total_assets = row.get('bs_total_assets')
            if total_assets is None or np.isnan(total_assets) or total_assets < self.min_total_assets:
                continue
            ratio = _safe_div(
                (row.get('inc_n_income') or np.nan) - (row.get('cf_n_cashflow_act') or np.nan),
                total_assets,
            )
            if np.isnan(ratio):
                continue
            accruals.append((ts_code, ratio))

        if len(accruals) < 10:
            logger.warning(f"Sloan 策略有效样本不足（{len(accruals)} 只），返回全 0")
            return pd.Series(0.0, index=prices.columns, dtype=float)

        accrual_series = pd.Series({ts: v for ts, v in accruals})
        # 升序排名（最低应计 = rank 1）
        ranks = accrual_series.rank(method='first', ascending=True)
        cutoff = max(1, int(len(accrual_series) * self.top_pct))
        # 归一化评分：最低应计得 1.0，cutoff 位得 1/cutoff，cutoff 之外得 0
        scores_dict = {
            ts: (cutoff - ranks[ts] + 1) / cutoff if ranks[ts] <= cutoff else 0.0
            for ts in accrual_series.index
        }

        result = pd.Series(0.0, index=prices.columns, dtype=float)
        for ts, s in scores_dict.items():
            if ts in result.index:
                result.loc[ts] = s

        selected = (result > 0).sum()
        logger.info(
            f"Sloan 应计策略: 有效样本 {len(accruals)}，入选 {selected} 只（top_{self.top_pct:.0%}）"
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
