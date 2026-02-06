"""
组合退出策略

组合多个退出策略，采用OR逻辑
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position


class CombinedExit(ExitStrategy):
    """
    组合退出策略

    策略逻辑:
    组合多个退出策略，任意一个触发即卖出（OR逻辑）

    适用场景:
    - 多维度风险控制
    - 灵活的退出条件
    - 综合多种策略的优势

    OR逻辑说明:
    - 只要任意一个子策略返回卖出信号，就卖出该股票
    - 例如: (止损 OR 止盈 OR 时间限制)
    - 适合设置多层保护机制

    示例:
        # 组合三种退出策略
        combined = CombinedExit(strategies=[
            ATRStopLossExit(params={'atr_multiplier': 2.0}),      # ATR止损
            FixedStopLossExit(params={'take_profit_pct': 15.0}),  # 固定止盈
            TimeBasedExit(params={'holding_period': 20})          # 时间限制
        ])

        exit_signals = combined.generate_exit_signals(
            positions=positions_dict,
            data=stock_data_dict,
            date=pd.Timestamp('2023-06-01')
        )
        # 返回: 触发任意一个子策略的股票列表

    注意事项:
    - 子策略列表不能为空
    - 子策略按顺序检查，短路求值（找到卖出信号立即返回）
    - 每个股票只会被返回一次（去重）
    """

    def __init__(self, strategies: List[ExitStrategy], params: Dict[str, Any] = None):
        """
        初始化组合退出策略

        参数:
            strategies: 子退出策略列表
            params: 参数字典（可选，用于其他配置）

        异常:
            ValueError: 如果策略列表为空
        """
        if not strategies:
            raise ValueError("组合退出策略至少需要一个子策略")

        self.strategies = strategies
        super().__init__(params=params)

    @property
    def id(self) -> str:
        return "combined"

    @property
    def name(self) -> str:
        """动态生成名称，包含所有子策略"""
        strategy_names = [s.name for s in self.strategies]
        return f"组合退出 ({' + '.join(strategy_names)})"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        """
        组合策略的参数由子策略定义
        这里返回空列表，实际参数在子策略中配置
        """
        return []

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """
        生成退出信号：OR逻辑

        参数:
            positions: 当前持仓字典 {股票代码: Position}
            data: 股票数据字典 {股票代码: OHLCV DataFrame}
            date: 当前日期

        返回:
            需要卖出的股票代码列表
        """
        all_exit_stocks = set()

        logger.debug(
            f"组合退出策略检查: {len(positions)} 个持仓, "
            f"{len(self.strategies)} 个子策略"
        )

        # 依次执行每个子策略
        for i, strategy in enumerate(self.strategies, 1):
            try:
                logger.debug(f"执行子策略 {i}/{len(self.strategies)}: {strategy.name}")

                exit_stocks = strategy.generate_exit_signals(positions, data, date)

                if exit_stocks:
                    logger.info(
                        f"子策略 '{strategy.name}' 触发: "
                        f"{len(exit_stocks)} 只股票 {exit_stocks}"
                    )
                    all_exit_stocks.update(exit_stocks)
                else:
                    logger.debug(f"子策略 '{strategy.name}' 无触发")

            except Exception as e:
                logger.error(
                    f"子策略 '{strategy.name}' 执行失败: {e}",
                    exc_info=True
                )
                # 继续执行其他策略，不因一个策略失败而中断

        result = list(all_exit_stocks)

        if result:
            logger.info(
                f"组合退出策略触发: {len(result)} 只股票需要卖出 {result}"
            )
        else:
            logger.debug("组合退出策略: 无股票触发卖出")

        return result

    def get_strategy_summary(self) -> Dict[str, Any]:
        """
        获取组合策略的摘要信息

        返回:
            包含所有子策略信息的字典
        """
        return {
            "type": "combined",
            "name": self.name,
            "id": self.id,
            "num_strategies": len(self.strategies),
            "strategies": [
                {
                    "name": s.name,
                    "id": s.id,
                    "params": s.params
                }
                for s in self.strategies
            ]
        }

    def __repr__(self) -> str:
        """字符串表示"""
        strategy_names = [s.name for s in self.strategies]
        return f"CombinedExit(strategies=[{', '.join(strategy_names)}])"
