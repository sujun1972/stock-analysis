"""自由现金流收益率策略（FCF Yield Proxy）

**重要：本策略使用 FCF / 总资产 作为 FCF 收益率的代理**

真实 FCF Yield = 自由现金流 / 市值。但 `fundamentals` 快照不含市值，
需跨表 JOIN daily_basic。为保持框架纯净，本策略使用 FCF / 总资产 作代理：

    - 同属"高质量 + 低估"因子族
    - 与 ROA 相似但更严格（ROA 用净利，本因子用自由现金流）
    - 避免了会计"应计"导致的虚高

评分逻辑：
    直接输出 FCF / 总资产 比率（仅正值）。99 分位以上裁剪避免极端离群。

**升级路径**：后续若需要真实 FCF Yield，可在策略内注入
`DailyBasicRepository` 查询市值后重算。
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..base_strategy import BaseStrategy


class FCFYieldStrategy(BaseStrategy):
    """FCF / 总资产 收益率排序（FCF Yield 代理）。"""

    def __init__(self, name: str, config: Dict[str, Any]):
        default_config = {
            'min_total_assets': 5e8,
            'top_n': 30,
            'holding_period': 60,
            'outlier_clip_pct': 0.99,
        }
        default_config.update(config)
        super().__init__(name, default_config)

        self.min_total_assets = float(self.config.custom_params.get('min_total_assets', 5e8))
        self.outlier_clip = float(self.config.custom_params.get('outlier_clip_pct', 0.99))

        logger.info(
            f"FCF Yield 策略参数: min_total_assets={self.min_total_assets:.0e}, "
            f"top_n={self.config.top_n}, outlier_clip={self.outlier_clip:.0%}"
        )

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None,
        fundamentals: Optional[pd.DataFrame] = None,
    ) -> pd.Series:
        if fundamentals is None or fundamentals.empty:
            logger.warning("FCF Yield 策略缺少 fundamentals 数据，返回全 0 评分")
            return pd.Series(0.0, index=prices.columns, dtype=float)

        latest = (
            fundamentals.sort_values(['ts_code', 'end_date'], ascending=[True, False])
            .groupby('ts_code', sort=False)
            .head(1)
        )

        scores_dict: Dict[str, float] = {}
        for _, row in latest.iterrows():
            fcf = row.get('cf_free_cashflow')
            ta = row.get('bs_total_assets')
            if fcf is None or ta is None or np.isnan(fcf) or np.isnan(ta):
                continue
            if ta < self.min_total_assets or ta == 0:
                continue
            yield_ratio = fcf / ta
            if yield_ratio <= 0:
                continue
            scores_dict[row['ts_code']] = yield_ratio

        if not scores_dict:
            logger.warning("FCF Yield 策略无正值样本，返回全 0")
            return pd.Series(0.0, index=prices.columns, dtype=float)

        # 99 分位裁剪，避免极端离群（通常是会计异常值）
        s = pd.Series(scores_dict)
        clip_upper = s.quantile(self.outlier_clip)
        s = s.clip(upper=clip_upper)

        result = pd.Series(0.0, index=prices.columns, dtype=float)
        for ts, v in s.items():
            if ts in result.index:
                result.loc[ts] = float(v)

        selected = (result > 0).sum()
        logger.info(
            f"FCF Yield 策略: 有效正值 {len(s)} 只，入选全部 {selected} 只，"
            f"上限裁剪 at {clip_upper:.4f}"
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
