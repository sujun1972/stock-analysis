"""
价值选股器（简化版）

基于价格波动率和反转效应进行选股
"""

from typing import List
import numpy as np
import pandas as pd
from loguru import logger

from ..base.stock_selector import SelectorParameter, StockSelector


class ValueSelector(StockSelector):
    """
    价值选股器（简化版）

    策略逻辑：
    由于缺少基本面数据（市盈率、市净率等），本选股器采用技术指标模拟价值选股：
    1. 计算过去 N 日的价格波动率（标准差）
    2. 计算过去 M 日的收益率（反转指标）
    3. 选择低波动率 + 负收益（超卖）的股票
    4. 这些股票可能被过度抛售，具有反转潜力

    适用场景：
    - 逆向投资策略
    - 寻找被低估的股票
    - 市场震荡期效果较好

    注意：
    这是技术指标版本的"价值选股"，不是真正的基本面价值投资
    如需真正的价值选股，需要接入财务数据

    示例：
        selector = ValueSelector(params={
            'volatility_period': 20,
            'return_period': 20,
            'top_n': 50,
            'select_low_volatility': True,
            'select_negative_return': True
        })

        selected_stocks = selector.select(
            date=pd.Timestamp('2023-06-01'),
            market_data=prices_df
        )
    """

    @property
    def id(self) -> str:
        return "value"

    @property
    def name(self) -> str:
        return "价值选股器（简化版）"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="volatility_period",
                label="波动率计算周期（天）",
                type="integer",
                default=20,
                min_value=5,
                max_value=100,
                description="计算过去 N 日收益率的标准差作为波动率",
            ),
            SelectorParameter(
                name="return_period",
                label="收益率计算周期（天）",
                type="integer",
                default=20,
                min_value=5,
                max_value=200,
                description="计算过去 N 日收益率作为反转指标",
            ),
            SelectorParameter(
                name="top_n",
                label="选股数量",
                type="integer",
                default=50,
                min_value=5,
                max_value=200,
                description="最多选择 N 只股票",
            ),
            SelectorParameter(
                name="select_low_volatility",
                label="选择低波动率股票",
                type="boolean",
                default=True,
                description="True=选择低波动率股票，False=选择高波动率股票",
            ),
            SelectorParameter(
                name="select_negative_return",
                label="选择负收益股票",
                type="boolean",
                default=True,
                description="True=选择近期下跌的股票（反转策略），False=选择上涨的股票",
            ),
            SelectorParameter(
                name="volatility_weight",
                label="波动率权重",
                type="float",
                default=0.5,
                min_value=0.0,
                max_value=1.0,
                description="波动率在综合得分中的权重（0-1），收益率权重为 1-此值",
            ),
        ]

    def select(self, date: pd.Timestamp, market_data: pd.DataFrame) -> List[str]:
        """
        价值选股逻辑

        参数:
            date: 选股日期
            market_data: 全市场价格数据
                        DataFrame(index=日期, columns=股票代码, values=收盘价)

        返回:
            选出的股票代码列表
        """
        volatility_period = self.params.get("volatility_period", 20)
        return_period = self.params.get("return_period", 20)
        top_n = self.params.get("top_n", 50)
        select_low_vol = self.params.get("select_low_volatility", True)
        select_negative = self.params.get("select_negative_return", True)
        vol_weight = self.params.get("volatility_weight", 0.5)
        ret_weight = 1.0 - vol_weight

        logger.debug(
            f"价值选股: date={date}, vol_period={volatility_period}, "
            f"ret_period={return_period}, top_n={top_n}"
        )

        # 检查日期是否在数据范围内
        if date not in market_data.index:
            logger.warning(f"日期 {date} 不在数据范围内")
            return []

        # 1. 计算日收益率
        daily_returns = market_data.pct_change()

        # 2. 计算波动率（滚动标准差）
        volatility = daily_returns.rolling(window=volatility_period).std()

        # 3. 计算累计收益率
        cumulative_return = market_data.pct_change(return_period)

        # 4. 获取当日数据
        try:
            current_volatility = volatility.loc[date].dropna()
            current_return = cumulative_return.loc[date].dropna()
        except KeyError:
            logger.warning(f"日期 {date} 不在数据范围内")
            return []

        # 5. 找到两个指标都有数据的股票
        common_stocks = current_volatility.index.intersection(current_return.index)
        if len(common_stocks) == 0:
            logger.warning(f"日期 {date} 没有有效的价值数据")
            return []

        current_volatility = current_volatility[common_stocks]
        current_return = current_return[common_stocks]

        # 6. 标准化指标（Z-score normalization）
        vol_mean = current_volatility.mean()
        vol_std = current_volatility.std()
        ret_mean = current_return.mean()
        ret_std = current_return.std()

        if vol_std > 0:
            vol_scores = (current_volatility - vol_mean) / vol_std
        else:
            vol_scores = pd.Series(0, index=current_volatility.index)

        if ret_std > 0:
            ret_scores = (current_return - ret_mean) / ret_std
        else:
            ret_scores = pd.Series(0, index=current_return.index)

        # 7. 根据策略调整得分方向
        if select_low_vol:
            # 低波动率得分高，所以取负值
            vol_scores = -vol_scores
        # else: 高波动率得分高，保持正值

        if select_negative:
            # 负收益（下跌）得分高，所以取负值
            ret_scores = -ret_scores
        # else: 正收益（上涨）得分高，保持正值

        # 8. 计算综合得分
        composite_score = vol_weight * vol_scores + ret_weight * ret_scores

        # 9. 选择得分最高的 top_n 只股票
        actual_top_n = min(top_n, len(composite_score))
        selected_stocks = composite_score.nlargest(actual_top_n).index.tolist()

        logger.info(
            f"价值选股完成: 共选出 {len(selected_stocks)} 只股票 "
            f"(目标: {top_n})"
        )

        # 打印统计信息
        if len(selected_stocks) > 0:
            selected_vol = current_volatility[selected_stocks]
            selected_ret = current_return[selected_stocks]
            logger.debug(
                f"选中股票波动率范围: "
                f"{selected_vol.min():.4f} ~ {selected_vol.max():.4f}"
            )
            logger.debug(
                f"选中股票收益率范围: "
                f"{selected_ret.min():.4f} ~ {selected_ret.max():.4f}"
            )

        return selected_stocks
