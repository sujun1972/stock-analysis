"""
固定持有期退出策略

按照固定的持有天数持仓，到期后自动卖出
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position


class FixedHoldingPeriodExit(ExitStrategy):
    """
    固定持有期退出策略

    策略逻辑:
    持仓达到指定天数后自动卖出

    适用场景:
    - 简单的持有期策略
    - 定期轮换策略
    - 回测和研究

    示例:
        # 持有10天后卖出
        exit_strategy = FixedHoldingPeriodExit(params={
            'holding_period': 10
        })

        exit_signals = exit_strategy.generate_exit_signals(
            positions=positions_dict,
            data=stock_data_dict,
            date=pd.Timestamp('2023-06-01')
        )
        # 返回: ['600000.SH']  (持有期到期的股票)
    """

    @property
    def id(self) -> str:
        return "fixed_holding_period"

    @property
    def name(self) -> str:
        return "固定持有期"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "holding_period",
                "label": "持有天数",
                "type": "int",
                "default": 10,
                "min": 1,
                "max": 252,
                "description": "持仓天数，到期后自动卖出"
            }
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date,
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
        exit_stocks = []

        logger.debug(
            f"固定持有期检查: {len(positions)} 个持仓 "
            f"(持有期={holding_period}天)"
        )

        for stock, position in positions.items():
            # 计算持有天数
            holding_days = position.holding_days

            # 检查是否达到持有期
            if holding_days >= holding_period:
                exit_stocks.append(stock)
                logger.info(
                    f"{stock} 达到持有期: "
                    f"已持有{holding_days}天 >= {holding_period}天, "
                    f"入场价={position.entry_price:.2f}, "
                    f"当前价={position.current_price:.2f}, "
                    f"盈亏={position.unrealized_pnl_pct:.2f}%"
                )
            else:
                logger.debug(
                    f"{stock}: 未达持有期 "
                    f"(已持有{holding_days}天 < {holding_period}天)"
                )

        if exit_stocks:
            logger.info(f"固定持有期: {len(exit_stocks)} 只股票达到持有期")
        else:
            logger.debug(f"固定持有期: 无股票达到持有期")

        return exit_stocks
