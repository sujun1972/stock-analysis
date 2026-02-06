"""
时间止损退出策略

持仓达到指定天数后强制卖出
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position


class TimeBasedExit(ExitStrategy):
    """
    时间止损退出策略

    策略逻辑:
    持仓天数达到阈值后强制卖出

    适用场景:
    - 固定持仓周期策略
    - 避免长期套牢
    - 定期轮动策略
    - 短线交易策略

    计算方式:
    - 持仓天数 = (当前日期 - 入场日期).days
    - 使用日历天数，不是交易日天数

    示例:
        # 持仓10天后强制卖出
        exit_strategy = TimeBasedExit(params={
            'holding_period': 10
        })

        exit_signals = exit_strategy.generate_exit_signals(
            positions=positions_dict,
            data=stock_data_dict,
            date=pd.Timestamp('2023-06-15')
        )
        # 返回: ['600000.SH']  (持仓超过10天的股票)

        # 配合其他退出策略使用
        combined = CombinedExit(strategies=[
            TimeBasedExit(params={'holding_period': 20}),  # 最长持仓20天
            FixedStopLossExit(params={'stop_loss_pct': -10.0})  # 止损10%
        ])
    """

    @property
    def id(self) -> str:
        return "time_based"

    @property
    def name(self) -> str:
        return "时间止损"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "holding_period",
                "label": "持仓天数",
                "type": "integer",
                "default": 10,
                "min": 1,
                "max": 100,
                "description": "持仓超过此天数后强制卖出"
            },
            {
                "name": "count_trading_days_only",
                "label": "仅计算交易日",
                "type": "boolean",
                "default": False,
                "description": "是否只计算交易日（True）还是包含周末节假日（False）"
            }
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """
        生成退出信号

        参数:
            positions: 当前持仓字典 {股票代码: Position}
            data: 股票数据字典 {股票代码: OHLCV DataFrame}
            date: 当前日期

        返回:
            需要卖出的股票代码列表
        """
        holding_period = self.params.get("holding_period", 10)
        count_trading_days_only = self.params.get("count_trading_days_only", False)

        exit_stocks = []

        logger.debug(
            f"时间止损检查: {len(positions)} 个持仓 "
            f"(持仓期={holding_period}天, "
            f"仅交易日={count_trading_days_only})"
        )

        for stock, position in positions.items():
            if count_trading_days_only:
                # 计算交易日天数
                if stock not in data:
                    logger.debug(f"{stock}: 数据缺失，使用日历天数")
                    holding_days = (date - position.entry_date).days
                else:
                    stock_data = data[stock]
                    # 获取入场日期到当前日期之间的交易日数
                    try:
                        mask = (stock_data.index >= position.entry_date) & (stock_data.index <= date)
                        holding_days = mask.sum()
                    except Exception as e:
                        logger.warning(f"{stock}: 计算交易日失败 - {e}，使用日历天数")
                        holding_days = (date - position.entry_date).days
            else:
                # 计算日历天数
                holding_days = (date - position.entry_date).days

            # 检查是否达到持仓期限
            if holding_days >= holding_period:
                exit_stocks.append(stock)
                logger.info(
                    f"{stock} 达到持仓期限: "
                    f"持仓{holding_days}天 >= {holding_period}天, "
                    f"入场日期={position.entry_date.strftime('%Y-%m-%d')}, "
                    f"当前日期={date.strftime('%Y-%m-%d')}, "
                    f"盈亏={position.unrealized_pnl_pct:.2f}%"
                )
            else:
                logger.debug(
                    f"{stock}: 未达到持仓期限 "
                    f"(持仓{holding_days}天 < {holding_period}天)"
                )

        if exit_stocks:
            logger.info(f"时间止损: {len(exit_stocks)} 只股票触发卖出")
        else:
            logger.debug(f"时间止损: 无股票触发卖出")

        return exit_stocks
