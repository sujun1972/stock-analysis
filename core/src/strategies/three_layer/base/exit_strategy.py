"""
退出策略基类

本模块提供退出策略的抽象基类，所有退出策略必须继承此类并实现 generate_exit_signals() 方法。

Exit Strategy Base Class

This module provides the abstract base class for exit strategies. All exit
strategies must inherit from this class and implement the generate_exit_signals() method.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class Position:
    """
    持仓信息

    Attributes:
        stock_code: 股票代码，例如 '600000.SH'
        entry_date: 入场日期
        entry_price: 入场价格
        shares: 持仓数量（股）
        current_price: 当前价格
        unrealized_pnl: 浮动盈亏（绝对值）
        unrealized_pnl_pct: 浮动盈亏百分比
    """
    stock_code: str
    entry_date: pd.Timestamp
    entry_price: float
    shares: int
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class ExitStrategy(ABC):
    """
    退出策略基类

    职责：管理持仓，决定何时卖出

    生命周期：
    1. 初始化时传入参数
    2. generate_exit_signals() 被回测引擎每日调用
    3. 返回需要卖出的股票代码列表

    示例：
        class FixedStopLossExit(ExitStrategy):
            @property
            def name(self) -> str:
                return "固定止损止盈"

            @property
            def id(self) -> str:
                return "fixed_stop_loss"

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
                    }
                ]

            def generate_exit_signals(self, positions, data, date):
                exit_stocks = []
                stop_loss_pct = self.params.get("stop_loss_pct", -5.0)

                for stock, position in positions.items():
                    if position.unrealized_pnl_pct <= stop_loss_pct:
                        exit_stocks.append(stock)

                return exit_stocks
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化退出策略

        Args:
            params: 参数字典，键为参数名，值为参数值
                   例如: {'stop_loss_pct': -5.0, 'take_profit_pct': 10.0}

        Raises:
            ValueError: 参数验证失败时抛出
        """
        self.params = params or {}
        self._validate_params()

    @property
    @abstractmethod
    def name(self) -> str:
        """
        策略名称（用于UI显示）

        Returns:
            策略名称，例如 "固定止损止盈"
        """
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """
        策略ID（唯一标识符）

        Returns:
            策略ID，例如 "fixed_stop_loss"

        注意：
            ID应该使用小写字母和下划线，不应包含特殊字符
        """
        pass

    @classmethod
    @abstractmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        """
        获取参数定义列表

        Returns:
            参数定义列表，每个参数包含名称、类型、默认值等信息

        示例：
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
                }
            ]
        """
        pass

    @abstractmethod
    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """
        生成退出信号（核心方法）

        Args:
            positions: 当前持仓字典，格式为 {股票代码: Position}
                      例如：
                      {
                          '600000.SH': Position(
                              stock_code='600000.SH',
                              entry_date=Timestamp('2023-01-01'),
                              entry_price=10.5,
                              shares=1000,
                              current_price=11.0,
                              unrealized_pnl=500.0,
                              unrealized_pnl_pct=4.76
                          ),
                          '000001.SZ': ...
                      }

            data: 股票数据字典，格式为 {股票代码: OHLCV DataFrame}
                 DataFrame 必须包含列: open, high, low, close, volume
                 例如：
                 {
                     '600000.SH': DataFrame(
                         index=日期,
                         columns=['open', 'high', 'low', 'close', 'volume']
                     ),
                     '000001.SZ': ...
                 }

            date: 当前日期

        Returns:
            需要卖出的股票代码列表
            例如: ['600000.SH', '000001.SZ']

        注意：
        - 只返回需要卖出的股票代码
        - 如果当日无卖出信号，返回空列表 []
        - 回测引擎会以当日收盘价执行卖出
        - 必须处理数据缺失等异常情况

        实现示例：
            exit_stocks = []
            stop_loss_pct = self.params.get("stop_loss_pct", -5.0)
            take_profit_pct = self.params.get("take_profit_pct", 10.0)

            for stock, position in positions.items():
                pnl_pct = position.unrealized_pnl_pct

                # 触发止损
                if pnl_pct <= stop_loss_pct:
                    exit_stocks.append(stock)
                    logger.info(f"{stock} 触发止损: {pnl_pct:.2f}%")

                # 触发止盈
                elif pnl_pct >= take_profit_pct:
                    exit_stocks.append(stock)
                    logger.info(f"{stock} 触发止盈: {pnl_pct:.2f}%")

            return exit_stocks
        """
        pass

    def _validate_params(self):
        """
        验证参数有效性

        Raises:
            ValueError: 参数验证失败时抛出

        验证规则：
        1. 参数名必须在 get_parameters() 中定义
        2. 参数类型必须匹配
        3. 数值参数必须在 min 和 max 范围内
        """
        param_defs = {p["name"]: p for p in self.get_parameters()}

        for param_name, param_value in self.params.items():
            if param_name not in param_defs:
                raise ValueError(
                    f"未知参数: {param_name}。"
                    f"支持的参数: {list(param_defs.keys())}"
                )

            param_def = param_defs[param_name]

            # 类型验证
            if param_def["type"] == "integer" and not isinstance(param_value, int):
                raise ValueError(
                    f"参数 '{param_name}' 必须是整数，当前类型: {type(param_value).__name__}"
                )
            elif param_def["type"] == "float" and not isinstance(param_value, (int, float)):
                raise ValueError(
                    f"参数 '{param_name}' 必须是浮点数，当前类型: {type(param_value).__name__}"
                )
            elif param_def["type"] == "boolean" and not isinstance(param_value, bool):
                raise ValueError(
                    f"参数 '{param_name}' 必须是布尔值，当前类型: {type(param_value).__name__}"
                )
            elif param_def["type"] == "string" and not isinstance(param_value, str):
                raise ValueError(
                    f"参数 '{param_name}' 必须是字符串，当前类型: {type(param_value).__name__}"
                )

            # 范围验证（仅数值类型）
            if param_def["type"] in ["integer", "float"]:
                if "min" in param_def and param_value < param_def["min"]:
                    raise ValueError(
                        f"参数 '{param_name}' 的值 {param_value} 不能小于 {param_def['min']}"
                    )
                if "max" in param_def and param_value > param_def["max"]:
                    raise ValueError(
                        f"参数 '{param_name}' 的值 {param_value} 不能大于 {param_def['max']}"
                    )

            # select 类型的选项验证
            if param_def["type"] == "select" and "options" in param_def:
                valid_values = [opt["value"] for opt in param_def["options"]]
                if param_value not in valid_values:
                    raise ValueError(
                        f"参数 '{param_name}' 的值 '{param_value}' 不在有效选项中。"
                        f"有效选项: {valid_values}"
                    )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.name}(id={self.id}, params={self.params})"
