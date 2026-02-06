"""
入场策略基类

本模块提供入场策略的抽象基类，所有入场策略必须继承此类并实现 generate_entry_signals() 方法。

Entry Strategy Base Class

This module provides the abstract base class for entry strategies. All entry
strategies must inherit from this class and implement the generate_entry_signals() method.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import pandas as pd


class EntryStrategy(ABC):
    """
    入场策略基类

    职责：在候选股票中生成买入信号

    生命周期：
    1. 初始化时传入参数
    2. generate_entry_signals() 被回测引擎每日调用
    3. 返回 {股票代码: 买入权重} 字典

    权重说明：
    - 权重总和应为 1.0（代表 100% 仓位）
    - 权重 0.2 表示分配 20% 仓位给该股票
    - 如果权重总和 > 1.0，回测引擎会自动归一化

    示例：
        class MABreakoutEntry(EntryStrategy):
            @property
            def name(self) -> str:
                return "均线突破入场"

            @property
            def id(self) -> str:
                return "ma_breakout"

            @classmethod
            def get_parameters(cls) -> List[Dict[str, Any]]:
                return [
                    {
                        "name": "short_window",
                        "label": "短期均线周期",
                        "type": "integer",
                        "default": 5,
                        "min": 2,
                        "max": 50,
                        "description": "短期移动平均线周期（天）"
                    }
                ]

            def generate_entry_signals(self, stocks, data, date):
                signals = {}
                for stock in stocks:
                    if self._is_golden_cross(data[stock], date):
                        signals[stock] = 1.0

                # 等权分配
                if signals:
                    weight = 1.0 / len(signals)
                    signals = {stock: weight for stock in signals}

                return signals
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化入场策略

        Args:
            params: 参数字典，键为参数名，值为参数值
                   例如: {'short_window': 5, 'long_window': 20}

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
            策略名称，例如 "均线突破入场"
        """
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """
        策略ID（唯一标识符）

        Returns:
            策略ID，例如 "ma_breakout"

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
                    "name": "short_window",
                    "label": "短期均线周期",
                    "type": "integer",
                    "default": 5,
                    "min": 2,
                    "max": 50,
                    "description": "短期移动平均线周期（天）"
                },
                {
                    "name": "long_window",
                    "label": "长期均线周期",
                    "type": "integer",
                    "default": 20,
                    "min": 5,
                    "max": 200,
                    "description": "长期移动平均线周期（天）"
                }
            ]
        """
        pass

    @abstractmethod
    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """
        生成入场信号（核心方法）

        Args:
            stocks: 候选股票列表（来自选股器）
                   例如：['600000.SH', '000001.SZ', '000002.SZ']

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
            {股票代码: 买入权重} 字典
            例如: {'600000.SH': 0.3, '000001.SZ': 0.2}
            表示给 600000.SH 分配 30% 仓位，给 000001.SZ 分配 20% 仓位

        注意：
        - 只对有买入信号的股票返回权重
        - 如果当日无买入信号，返回空字典 {}
        - 权重可以不归一化，回测引擎会自动处理
        - 权重应该为正数

        实现示例：
            signals = {}

            for stock in stocks:
                if stock not in data:
                    continue

                stock_data = data[stock]

                # 计算技术指标
                ma_short = stock_data['close'].rolling(5).mean()
                ma_long = stock_data['close'].rolling(20).mean()

                try:
                    # 检测金叉
                    if ma_short.loc[date] > ma_long.loc[date]:
                        signals[stock] = 1.0
                except KeyError:
                    continue

            # 等权分配
            if signals:
                weight = 1.0 / len(signals)
                signals = {stock: weight for stock in signals}

            return signals
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
