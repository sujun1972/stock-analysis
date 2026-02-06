"""
股票选择器基类

本模块提供股票选择器的抽象基类，所有选股器必须继承此类并实现 select() 方法。

Stock Selector Base Class

This module provides the abstract base class for stock selectors. All selectors
must inherit from this class and implement the select() method.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class SelectorParameter:
    """
    选股器参数定义

    Attributes:
        name: 参数名称（内部标识）
        label: 参数标签（用于UI显示）
        type: 参数类型（'integer', 'float', 'boolean', 'select', 'string'）
        default: 默认值
        min_value: 最小值（仅数值类型）
        max_value: 最大值（仅数值类型）
        options: 可选项列表（仅 select 类型）
        description: 参数描述
    """
    name: str
    label: str
    type: str  # 'integer', 'float', 'boolean', 'select', 'string'
    default: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: Optional[List[Dict[str, str]]] = None
    description: str = ""


class StockSelector(ABC):
    """
    股票选择器基类

    所有选股器必须继承此类并实现 select() 方法

    生命周期：
    1. 初始化时传入参数
    2. select() 方法被回测引擎按 rebalance_freq 频率调用
    3. 返回股票代码列表

    示例：
        class MomentumSelector(StockSelector):
            @property
            def name(self) -> str:
                return "动量选股器"

            @property
            def id(self) -> str:
                return "momentum"

            @classmethod
            def get_parameters(cls) -> List[SelectorParameter]:
                return [
                    SelectorParameter(
                        name="top_n",
                        label="选股数量",
                        type="integer",
                        default=50,
                        min_value=5,
                        max_value=200,
                        description="选择动量最高的前 N 只股票"
                    )
                ]

            def select(self, date, market_data):
                momentum = market_data.pct_change(20)
                top_n = self.params.get("top_n", 50)
                return momentum.loc[date].nlargest(top_n).index.tolist()
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化选股器

        Args:
            params: 参数字典，键为参数名，值为参数值
                   例如: {'top_n': 50, 'lookback_period': 20}

        Raises:
            ValueError: 参数验证失败时抛出
        """
        self.params = params or {}
        self._validate_params()

    @property
    @abstractmethod
    def name(self) -> str:
        """
        选股器名称（用于UI显示）

        Returns:
            选股器名称，例如 "动量选股器"
        """
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """
        选股器ID（唯一标识符）

        Returns:
            选股器ID，例如 "momentum"

        注意：
            ID应该使用小写字母和下划线，不应包含特殊字符
        """
        pass

    @classmethod
    @abstractmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        """
        获取参数定义列表

        Returns:
            参数定义列表，每个参数包含名称、类型、默认值等信息

        示例：
            return [
                SelectorParameter(
                    name="lookback_period",
                    label="动量计算周期（天）",
                    type="integer",
                    default=20,
                    min_value=5,
                    max_value=200,
                    description="计算过去 N 日收益率作为动量指标"
                )
            ]
        """
        pass

    @abstractmethod
    def select(
        self,
        date: pd.Timestamp,
        market_data: pd.DataFrame,
    ) -> List[str]:
        """
        选股逻辑（核心方法）

        Args:
            date: 选股日期
            market_data: 全市场数据
                        DataFrame(index=日期, columns=股票代码, values=收盘价)
                        例如：
                                        600000.SH  000001.SZ  000002.SZ
                        2023-01-01      10.5       15.2       8.3
                        2023-01-02      10.6       15.1       8.4
                        ...

        Returns:
            选出的股票代码列表
            例如：['600000.SH', '000001.SZ', '000002.SZ']

        注意：
        - 返回的股票数量由参数 top_n 控制（如果有该参数）
        - 如果某日数据不足，可以返回空列表或较少股票
        - 必须处理 NaN 值和缺失数据
        - 应该过滤掉停牌、数据异常的股票

        实现示例：
            lookback = self.params.get("lookback_period", 20)
            top_n = self.params.get("top_n", 50)

            # 计算动量
            momentum = market_data.pct_change(lookback)

            # 获取当日动量并排序
            try:
                current_momentum = momentum.loc[date].dropna()
                selected_stocks = current_momentum.nlargest(top_n).index.tolist()
                return selected_stocks
            except KeyError:
                # 日期不存在
                return []
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
        3. 数值参数必须在 min_value 和 max_value 范围内
        """
        param_defs = {p.name: p for p in self.get_parameters()}

        for param_name, param_value in self.params.items():
            if param_name not in param_defs:
                raise ValueError(
                    f"未知参数: {param_name}。"
                    f"支持的参数: {list(param_defs.keys())}"
                )

            param_def = param_defs[param_name]

            # 类型验证
            if param_def.type == "integer" and not isinstance(param_value, int):
                raise ValueError(
                    f"参数 '{param_name}' 必须是整数，当前类型: {type(param_value).__name__}"
                )
            elif param_def.type == "float" and not isinstance(param_value, (int, float)):
                raise ValueError(
                    f"参数 '{param_name}' 必须是浮点数，当前类型: {type(param_value).__name__}"
                )
            elif param_def.type == "boolean" and not isinstance(param_value, bool):
                raise ValueError(
                    f"参数 '{param_name}' 必须是布尔值，当前类型: {type(param_value).__name__}"
                )
            elif param_def.type == "string" and not isinstance(param_value, str):
                raise ValueError(
                    f"参数 '{param_name}' 必须是字符串，当前类型: {type(param_value).__name__}"
                )

            # 范围验证（仅数值类型）
            if param_def.type in ["integer", "float"]:
                if param_def.min_value is not None and param_value < param_def.min_value:
                    raise ValueError(
                        f"参数 '{param_name}' 的值 {param_value} 不能小于 {param_def.min_value}"
                    )
                if param_def.max_value is not None and param_value > param_def.max_value:
                    raise ValueError(
                        f"参数 '{param_name}' 的值 {param_value} 不能大于 {param_def.max_value}"
                    )

            # select 类型的选项验证
            if param_def.type == "select" and param_def.options:
                valid_values = [opt["value"] for opt in param_def.options]
                if param_value not in valid_values:
                    raise ValueError(
                        f"参数 '{param_name}' 的值 '{param_value}' 不在有效选项中。"
                        f"有效选项: {valid_values}"
                    )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.name}(id={self.id}, params={self.params})"
