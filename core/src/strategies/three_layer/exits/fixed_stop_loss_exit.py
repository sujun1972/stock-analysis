"""
固定止损止盈退出策略

设置固定的止损和止盈百分比
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position


class FixedStopLossExit(ExitStrategy):
    """
    固定止损止盈退出策略

    策略逻辑:
    1. 止损: 亏损达到固定百分比时卖出
    2. 止盈: 盈利达到固定百分比时卖出

    适用场景:
    - 严格风险控制
    - 简单明确的退出规则
    - 不依赖市场波动的固定策略

    注意事项:
    - 止损百分比应为负数（如 -5.0 表示亏损5%）
    - 止盈百分比应为正数（如 10.0 表示盈利10%）
    - 可以只设置止损或只设置止盈

    示例:
        # 同时设置止损和止盈
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -5.0,    # 亏损5%止损
            'take_profit_pct': 10.0   # 盈利10%止盈
        })

        # 只设置止损
        exit_strategy = FixedStopLossExit(params={
            'stop_loss_pct': -8.0,
            'take_profit_pct': None   # 不设置止盈
        })

        exit_signals = exit_strategy.generate_exit_signals(
            positions=positions_dict,
            data=stock_data_dict,
            date=pd.Timestamp('2023-06-01')
        )
        # 返回: ['600000.SH']  (触发止损或止盈的股票)
    """

    @property
    def id(self) -> str:
        return "fixed_stop_loss"

    @property
    def name(self) -> str:
        return "固定止损止盈"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "stop_loss_pct",
                "label": "止损百分比",
                "type": "float",
                "default": -5.0,
                "min": -20.0,
                "max": -1.0,
                "description": "亏损达到此百分比时卖出（负数）"
            },
            {
                "name": "take_profit_pct",
                "label": "止盈百分比",
                "type": "float",
                "default": 10.0,
                "min": 1.0,
                "max": 50.0,
                "description": "盈利达到此百分比时卖出（正数）"
            },
            {
                "name": "enable_stop_loss",
                "label": "启用止损",
                "type": "boolean",
                "default": True,
                "description": "是否启用止损功能"
            },
            {
                "name": "enable_take_profit",
                "label": "启用止盈",
                "type": "boolean",
                "default": True,
                "description": "是否启用止盈功能"
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
        stop_loss_pct = self.params.get("stop_loss_pct", -5.0)
        take_profit_pct = self.params.get("take_profit_pct", 10.0)
        enable_stop_loss = self.params.get("enable_stop_loss", True)
        enable_take_profit = self.params.get("enable_take_profit", True)

        exit_stocks = []

        logger.debug(
            f"固定止损止盈检查: {len(positions)} 个持仓 "
            f"(止损={stop_loss_pct if enable_stop_loss else '关闭'}%, "
            f"止盈={take_profit_pct if enable_take_profit else '关闭'}%)"
        )

        for stock, position in positions.items():
            pnl_pct = position.unrealized_pnl_pct

            # 检查止损
            if enable_stop_loss and pnl_pct <= stop_loss_pct:
                exit_stocks.append(stock)
                logger.info(
                    f"{stock} 触发止损: "
                    f"盈亏={pnl_pct:.2f}% <= 止损线{stop_loss_pct:.2f}%, "
                    f"入场价={position.entry_price:.2f}, "
                    f"当前价={position.current_price:.2f}"
                )

            # 检查止盈
            elif enable_take_profit and pnl_pct >= take_profit_pct:
                exit_stocks.append(stock)
                logger.info(
                    f"{stock} 触发止盈: "
                    f"盈亏={pnl_pct:.2f}% >= 止盈线{take_profit_pct:.2f}%, "
                    f"入场价={position.entry_price:.2f}, "
                    f"当前价={position.current_price:.2f}"
                )

            else:
                logger.debug(
                    f"{stock}: 未触发退出 "
                    f"(盈亏={pnl_pct:.2f}%, "
                    f"止损线={stop_loss_pct if enable_stop_loss else '关闭'}%, "
                    f"止盈线={take_profit_pct if enable_take_profit else '关闭'}%)"
                )

        if exit_stocks:
            logger.info(f"固定止损止盈: {len(exit_stocks)} 只股票触发卖出")
        else:
            logger.debug(f"固定止损止盈: 无股票触发卖出")

        return exit_stocks
