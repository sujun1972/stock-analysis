"""
三层策略组合器

本模块提供策略组合器，用于将选股器、入场策略、退出策略组合成完整的交易策略。

Strategy Composer

This module provides the strategy composer for combining stock selector, entry
strategy, and exit strategy into a complete trading strategy.
"""

from typing import Any, Dict, List

from .stock_selector import StockSelector
from .entry_strategy import EntryStrategy
from .exit_strategy import ExitStrategy


class StrategyComposer:
    """
    三层策略组合器

    用于将选股器、入场策略、退出策略组合成完整的交易策略

    用法:
        from core.src.strategies.three_layer.selectors import MomentumSelector
        from core.src.strategies.three_layer.entries import ImmediateEntry
        from core.src.strategies.three_layer.exits import FixedStopLossExit

        composer = StrategyComposer(
            selector=MomentumSelector(params={'top_n': 50}),
            entry=ImmediateEntry(),
            exit_strategy=FixedStopLossExit(params={'stop_loss_pct': -5.0}),
            rebalance_freq='W'  # 选股频率：D=日, W=周, M=月
        )

        # 获取元数据
        metadata = composer.get_metadata()

        # 验证策略组合
        validation = composer.validate()

        # 回测
        from core.src.backtest import BacktestEngine

        engine = BacktestEngine()
        result = engine.backtest_three_layer(
            selector=composer.selector,
            entry=composer.entry,
            exit_strategy=composer.exit,
            prices=prices,
            start_date='2023-01-01',
            end_date='2023-12-31',
            rebalance_freq=composer.rebalance_freq
        )

    属性:
        selector: 股票选择器
        entry: 入场策略
        exit: 退出策略
        rebalance_freq: 选股频率（'D'=日, 'W'=周, 'M'=月）
    """

    def __init__(
        self,
        selector: StockSelector,
        entry: EntryStrategy,
        exit_strategy: ExitStrategy,
        rebalance_freq: str = "W",
    ):
        """
        初始化策略组合器

        Args:
            selector: 股票选择器（Layer 1）
            entry: 入场策略（Layer 2）
            exit_strategy: 退出策略（Layer 3）
            rebalance_freq: 选股频率
                          - 'D': 日频（每日选股）
                          - 'W': 周频（每周选股，默认）
                          - 'M': 月频（每月选股）

        Raises:
            TypeError: 如果参数类型不正确
            ValueError: 如果 rebalance_freq 无效
        """
        # 类型验证
        if not isinstance(selector, StockSelector):
            raise TypeError(
                f"selector 必须是 StockSelector 的实例，当前类型: {type(selector).__name__}"
            )
        if not isinstance(entry, EntryStrategy):
            raise TypeError(
                f"entry 必须是 EntryStrategy 的实例，当前类型: {type(entry).__name__}"
            )
        if not isinstance(exit_strategy, ExitStrategy):
            raise TypeError(
                f"exit_strategy 必须是 ExitStrategy 的实例，当前类型: {type(exit_strategy).__name__}"
            )

        # 频率验证
        if rebalance_freq not in ["D", "W", "M"]:
            raise ValueError(
                f"无效的选股频率: {rebalance_freq}。"
                f"有效选项: 'D'(日), 'W'(周), 'M'(月)"
            )

        self.selector = selector
        self.entry = entry
        self.exit = exit_strategy
        self.rebalance_freq = rebalance_freq

    def get_metadata(self) -> Dict[str, Any]:
        """
        获取组合策略完整元数据

        Returns:
            包含选股器、入场策略、退出策略的完整元数据字典

        元数据格式：
            {
                "selector": {
                    "id": "momentum",
                    "name": "动量选股器",
                    "parameters": [
                        {
                            "name": "top_n",
                            "label": "选股数量",
                            "type": "integer",
                            "default": 50,
                            "description": "选择动量最高的前 N 只股票"
                        },
                        ...
                    ]
                },
                "entry": {
                    "id": "immediate",
                    "name": "立即入场",
                    "parameters": [...]
                },
                "exit": {
                    "id": "fixed_stop_loss",
                    "name": "固定止损止盈",
                    "parameters": [...]
                },
                "rebalance_freq": "W"
            }
        """
        # 选股器元数据
        selector_params = []
        for p in self.selector.get_parameters():
            param_dict = {
                "name": p.name,
                "label": p.label,
                "type": p.type,
                "default": p.default,
                "description": p.description,
            }
            if p.min_value is not None:
                param_dict["min_value"] = p.min_value
            if p.max_value is not None:
                param_dict["max_value"] = p.max_value
            if p.options is not None:
                param_dict["options"] = p.options

            selector_params.append(param_dict)

        return {
            "selector": {
                "id": self.selector.id,
                "name": self.selector.name,
                "parameters": selector_params,
                "current_params": self.selector.params,
            },
            "entry": {
                "id": self.entry.id,
                "name": self.entry.name,
                "parameters": self.entry.get_parameters(),
                "current_params": self.entry.params,
            },
            "exit": {
                "id": self.exit.id,
                "name": self.exit.name,
                "parameters": self.exit.get_parameters(),
                "current_params": self.exit.params,
            },
            "rebalance_freq": self.rebalance_freq,
        }

    def validate(self) -> Dict[str, Any]:
        """
        验证策略组合的有效性

        Returns:
            验证结果字典
            {
                "valid": True/False,
                "errors": ["错误信息1", "错误信息2", ...]
            }

        示例：
            validation = composer.validate()
            if validation["valid"]:
                print("策略组合有效")
            else:
                for error in validation["errors"]:
                    print(f"错误: {error}")
        """
        errors = []

        # 验证选股器
        try:
            self.selector._validate_params()
        except ValueError as e:
            errors.append(f"选股器参数错误: {str(e)}")

        # 验证入场策略
        try:
            self.entry._validate_params()
        except ValueError as e:
            errors.append(f"入场策略参数错误: {str(e)}")

        # 验证退出策略
        try:
            self.exit._validate_params()
        except ValueError as e:
            errors.append(f"退出策略参数错误: {str(e)}")

        # 验证选股频率
        if self.rebalance_freq not in ["D", "W", "M"]:
            errors.append(
                f"无效的选股频率: {self.rebalance_freq}。有效选项: 'D', 'W', 'M'"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def get_strategy_combination_id(self) -> str:
        """
        获取策略组合的唯一标识符

        Returns:
            策略组合ID，格式为 "selector_id__entry_id__exit_id__freq"

        示例：
            "momentum__immediate__fixed_stop_loss__W"
        """
        return f"{self.selector.id}__{self.entry.id}__{self.exit.id}__{self.rebalance_freq}"

    def get_strategy_combination_name(self) -> str:
        """
        获取策略组合的可读名称

        Returns:
            策略组合名称

        示例：
            "动量选股器 + 立即入场 + 固定止损止盈 (周频选股)"
        """
        freq_name = {
            "D": "日频",
            "W": "周频",
            "M": "月频"
        }[self.rebalance_freq]

        return f"{self.selector.name} + {self.entry.name} + {self.exit.name} ({freq_name}选股)"

    def get_all_parameters(self) -> Dict[str, Any]:
        """
        获取所有策略的当前参数

        Returns:
            包含所有策略参数的字典

        示例：
            {
                "selector_params": {"top_n": 50, "lookback_period": 20},
                "entry_params": {"short_window": 5, "long_window": 20},
                "exit_params": {"stop_loss_pct": -5.0, "take_profit_pct": 10.0},
                "rebalance_freq": "W"
            }
        """
        return {
            "selector_params": self.selector.params,
            "entry_params": self.entry.params,
            "exit_params": self.exit.params,
            "rebalance_freq": self.rebalance_freq,
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"StrategyComposer(\n"
            f"  selector={self.selector},\n"
            f"  entry={self.entry},\n"
            f"  exit={self.exit},\n"
            f"  rebalance_freq='{self.rebalance_freq}'\n"
            f")"
        )

    def __str__(self) -> str:
        """可读字符串表示"""
        return self.get_strategy_combination_name()
