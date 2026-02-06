"""
动量选股器

根据股票的历史涨幅（动量指标）进行选股
"""

from typing import List
import numpy as np
import pandas as pd
from loguru import logger

from ..base.stock_selector import SelectorParameter, StockSelector


class MomentumSelector(StockSelector):
    """
    动量选股器

    策略逻辑：
    1. 计算过去 N 日收益率（动量指标）
    2. 选择动量最高的前 M 只股票
    3. 可选：过滤掉负动量（下跌）的股票

    适用场景：
    - 趋势跟踪策略
    - 捕捉强势股
    - 市场上涨期效果较好

    示例：
        selector = MomentumSelector(params={
            'lookback_period': 20,
            'top_n': 50,
            'use_log_return': False,
            'filter_negative': True
        })

        selected_stocks = selector.select(
            date=pd.Timestamp('2023-06-01'),
            market_data=prices_df
        )
    """

    @property
    def id(self) -> str:
        return "momentum"

    @property
    def name(self) -> str:
        return "动量选股器"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="lookback_period",
                label="动量计算周期（天）",
                type="integer",
                default=20,
                min_value=5,
                max_value=200,
                description="计算过去 N 日收益率作为动量指标",
            ),
            SelectorParameter(
                name="top_n",
                label="选股数量",
                type="integer",
                default=50,
                min_value=5,
                max_value=200,
                description="选择动量最高的前 N 只股票",
            ),
            SelectorParameter(
                name="use_log_return",
                label="使用对数收益率",
                type="boolean",
                default=False,
                description="True=对数收益率，False=简单收益率",
            ),
            SelectorParameter(
                name="filter_negative",
                label="过滤负动量",
                type="boolean",
                default=True,
                description="是否过滤掉负动量（下跌）的股票",
            ),
        ]

    def select(self, date: pd.Timestamp, market_data: pd.DataFrame) -> List[str]:
        """
        动量选股逻辑

        参数:
            date: 选股日期
            market_data: 全市场价格数据
                        DataFrame(index=日期, columns=股票代码, values=收盘价)

        返回:
            选出的股票代码列表
        """
        lookback = self.params.get("lookback_period", 20)
        top_n = self.params.get("top_n", 50)
        use_log = self.params.get("use_log_return", False)
        filter_negative = self.params.get("filter_negative", True)

        logger.debug(
            f"动量选股: date={date}, lookback={lookback}, "
            f"top_n={top_n}, use_log={use_log}, filter_negative={filter_negative}"
        )

        # 检查日期是否在数据范围内
        if date not in market_data.index:
            logger.warning(f"日期 {date} 不在数据范围内")
            return []

        # 计算动量
        if use_log:
            # 对数收益率：log(P_t / P_{t-n})
            momentum = np.log(market_data / market_data.shift(lookback))
        else:
            # 简单收益率：(P_t - P_{t-n}) / P_{t-n}
            momentum = market_data.pct_change(lookback)

        # 获取当日动量，删除 NaN 值
        try:
            current_momentum = momentum.loc[date].dropna()
        except KeyError:
            logger.warning(f"日期 {date} 不在数据范围内")
            return []

        if len(current_momentum) == 0:
            logger.warning(f"日期 {date} 没有有效的动量数据")
            return []

        # 过滤负动量
        if filter_negative:
            current_momentum = current_momentum[current_momentum > 0]
            logger.debug(
                f"过滤负动量后剩余 {len(current_momentum)} 只股票"
            )

        if len(current_momentum) == 0:
            logger.warning(f"过滤负动量后没有符合条件的股票")
            return []

        # 选择动量最高的 top_n 只股票
        actual_top_n = min(top_n, len(current_momentum))
        selected_stocks = current_momentum.nlargest(actual_top_n).index.tolist()

        logger.info(
            f"动量选股完成: 共选出 {len(selected_stocks)} 只股票 "
            f"(目标: {top_n})"
        )

        # 打印动量范围
        if len(selected_stocks) > 0:
            momentum_values = current_momentum[selected_stocks]
            logger.debug(
                f"选中股票动量范围: "
                f"{momentum_values.min():.4f} ~ {momentum_values.max():.4f}"
            )

        return selected_stocks
