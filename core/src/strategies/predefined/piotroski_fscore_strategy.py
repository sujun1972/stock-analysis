"""Piotroski F-Score 选股策略

基于原始财报三表（income / balancesheet / cashflow）构造 9 因子 F-Score，
是第一个使用 `fundamentals` 参数的参考实现，展示如何从原始表构造
自定义价值/质量因子。

学术背景：
    Piotroski J D. (2000). Value Investing: The Use of Historical Financial
    Statement Information to Separate Winners from Losers from Losers.
    Journal of Accounting Research.

9 项评分标准（每项满足得 1 分，满分 9 分）：
    1. ROA > 0                  —— 盈利能力正（n_income / total_assets）
    2. CFO > 0                  —— 经营现金流正（cf_n_cashflow_act）
    3. ROA 同比改善             —— 盈利能力提升
    4. CFO > 净利润             —— 盈利质量（避免应计盈余操纵）
    5. 长期负债率下降           —— 偿债能力改善
    6. 流动比率上升             —— 短期偿债能力改善
    7. 流通股本未增发           —— 无股权稀释
    8. 毛利率上升               —— 产品竞争力提升
    9. 资产周转率上升           —— 运营效率提升

评分阈值：F >= 7 视为"高质量"股票，输出原始 F-Score 作为评分；
否则评分为 0（系统层过滤）。
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..base_strategy import BaseStrategy
from .._fundamentals_utils import safe_div as _safe_div


class PiotroskiFScoreStrategy(BaseStrategy):
    """Piotroski F-Score 质量选股策略。

    参数：
        min_score: 满足此分数才计入评分结果（默认 7，范围 0-9）
        top_n: 每期最多返回股票数（默认 30）
        holding_period: 持仓天数（默认 60 天，财报季度周期）

    使用场景：
        - 价值 / 质量轮动
        - 熊市防御：高质量公司抗跌
        - 与动量策略组合形成 Quality + Momentum 双因子

    风险提示：
        - 财报数据季度级更新，评分变化缓慢
        - 新股、ST、长期停牌股可能 F-Score 缺失
        - 单因子策略在极端行情可能跑输
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        default_config = {
            'min_score': 7,
            'top_n': 30,
            'holding_period': 60,
        }
        default_config.update(config)
        super().__init__(name, default_config)

        self.min_score = int(self.config.custom_params.get('min_score', 7))
        self.min_score = max(0, min(9, self.min_score))

        logger.info(
            f"Piotroski F-Score 策略参数: min_score={self.min_score}, "
            f"top_n={self.config.top_n}, holding_period={self.config.holding_period}"
        )

    # ------------------------------------------------------------------
    # 必须实现：基类抽象方法
    # ------------------------------------------------------------------

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None,
        fundamentals: Optional[pd.DataFrame] = None,
    ) -> pd.Series:
        """计算全市场 Piotroski F-Score。

        依赖 `fundamentals`（原始财报三表快照，长格式）；
        若缺失，所有股票评分为 0。
        """
        if fundamentals is None or fundamentals.empty:
            logger.warning("Piotroski F-Score 缺少 fundamentals 数据，返回全 0 评分")
            return pd.Series(0.0, index=prices.columns)

        # 按 (ts_code, end_date DESC) 排序，取每只股票最近 2 期
        # fundamentals 进入本函数时已是按 ts_code, end_date DESC 排序（见 fetcher 的 ORDER BY）
        # 但防御性 re-sort
        df = fundamentals.sort_values(
            ['ts_code', 'end_date'], ascending=[True, False]
        ).reset_index(drop=True)

        # 每个 ts_code 取最近 2 期；不足 2 期的股票跳过
        grouped = df.groupby('ts_code', sort=False)
        scores: Dict[str, float] = {}
        details: Dict[str, Dict[str, int]] = {}

        for ts_code, group in grouped:
            if len(group) < 2:
                continue
            cur = group.iloc[0]
            prev = group.iloc[1]

            f1_roa = _safe_div(cur.get('inc_n_income'), cur.get('bs_total_assets'))
            prev_roa = _safe_div(prev.get('inc_n_income'), prev.get('bs_total_assets'))

            f5_ltd_cur = _safe_div(cur.get('bs_lt_borr'), cur.get('bs_total_assets'))
            f5_ltd_prev = _safe_div(prev.get('bs_lt_borr'), prev.get('bs_total_assets'))

            f6_cr_cur = _safe_div(cur.get('bs_total_cur_assets'), cur.get('bs_total_cur_liab'))
            f6_cr_prev = _safe_div(prev.get('bs_total_cur_assets'), prev.get('bs_total_cur_liab'))

            f8_gm_cur = _safe_div(
                (cur.get('inc_revenue') or np.nan) - (cur.get('inc_oper_cost') or np.nan),
                cur.get('inc_revenue'),
            )
            f8_gm_prev = _safe_div(
                (prev.get('inc_revenue') or np.nan) - (prev.get('inc_oper_cost') or np.nan),
                prev.get('inc_revenue'),
            )

            f9_at_cur = _safe_div(cur.get('inc_revenue'), cur.get('bs_total_assets'))
            f9_at_prev = _safe_div(prev.get('inc_revenue'), prev.get('bs_total_assets'))

            # 9 项评分（NaN → 0，视为不满足）
            c1 = 1 if (not np.isnan(f1_roa)) and f1_roa > 0 else 0
            c2 = 1 if (cur.get('cf_n_cashflow_act') or 0) > 0 else 0
            c3 = (
                1 if (not np.isnan(f1_roa)) and (not np.isnan(prev_roa)) and f1_roa > prev_roa
                else 0
            )
            c4 = (
                1 if (cur.get('cf_n_cashflow_act') is not None)
                and (cur.get('inc_n_income') is not None)
                and (cur['cf_n_cashflow_act'] > cur['inc_n_income'])
                else 0
            )
            c5 = (
                1 if (not np.isnan(f5_ltd_cur)) and (not np.isnan(f5_ltd_prev))
                and f5_ltd_cur < f5_ltd_prev
                else 0
            )
            c6 = (
                1 if (not np.isnan(f6_cr_cur)) and (not np.isnan(f6_cr_prev))
                and f6_cr_cur > f6_cr_prev
                else 0
            )
            share_cur = cur.get('bs_total_share')
            share_prev = prev.get('bs_total_share')
            c7 = (
                1 if (share_cur is not None) and (share_prev is not None)
                and not np.isnan(share_cur) and not np.isnan(share_prev)
                and share_cur <= share_prev * 1.001
                else 0
            )
            c8 = (
                1 if (not np.isnan(f8_gm_cur)) and (not np.isnan(f8_gm_prev))
                and f8_gm_cur > f8_gm_prev
                else 0
            )
            c9 = (
                1 if (not np.isnan(f9_at_cur)) and (not np.isnan(f9_at_prev))
                and f9_at_cur > f9_at_prev
                else 0
            )

            f_score = c1 + c2 + c3 + c4 + c5 + c6 + c7 + c8 + c9
            scores[ts_code] = float(f_score) if f_score >= self.min_score else 0.0
            details[ts_code] = {
                'F1_roa_pos': c1, 'F2_cfo_pos': c2, 'F3_roa_up': c3,
                'F4_cfo_vs_ni': c4, 'F5_ltd_down': c5, 'F6_cr_up': c6,
                'F7_no_dilution': c7, 'F8_gm_up': c8, 'F9_asset_turn_up': c9,
                'total': int(f_score),
            }

        # 补齐全市场，其余股票评分 0
        result = pd.Series(0.0, index=prices.columns, dtype=float)
        for ts_code, s in scores.items():
            if ts_code in result.index:
                result.loc[ts_code] = s

        high_quality = sum(1 for v in scores.values() if v >= self.min_score)
        logger.info(
            f"Piotroski F-Score 计算完成: 总覆盖 {len(scores)} 只股票, "
            f"高质量 (F≥{self.min_score}) {high_quality} 只"
        )
        return result

    # ------------------------------------------------------------------
    # 必须实现：基类抽象方法（信号生成）
    # ------------------------------------------------------------------

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """F-Score 策略不直接生成逐日交易信号（季度更新）。返回空信号表。"""
        return pd.DataFrame(0, index=prices.index, columns=prices.columns)
