"""
策略基类
定义策略接口和参数规范
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd


class ParameterType(str, Enum):
    """参数类型枚举"""
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    SELECT = "select"


@dataclass
class StrategyParameter:
    """策略参数定义"""
    name: str                           # 参数名称
    label: str                          # 显示标签
    type: ParameterType                 # 参数类型
    default: Any                        # 默认值
    min_value: Optional[float] = None   # 最小值（数值类型）
    max_value: Optional[float] = None   # 最大值（数值类型）
    step: Optional[float] = None        # 步长（数值类型）
    options: Optional[List[Dict]] = None # 选项列表（选择类型）
    description: str = ""               # 参数说明
    category: str = "general"           # 参数分类


class BaseStrategy(ABC):
    """
    策略基类
    所有策略都需要继承此类并实现 generate_signals 方法
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化策略

        参数:
            params: 策略参数字典
        """
        self.params = params or {}
        self._validate_params()

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """策略描述"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """策略版本"""
        pass

    @classmethod
    @abstractmethod
    def get_parameters(cls) -> List[StrategyParameter]:
        """
        获取策略参数定义

        返回:
            参数定义列表
        """
        pass

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成交易信号

        参数:
            data: 包含OHLCV数据的DataFrame，索引为日期
                 必须包含列: open, high, low, close, volume

        返回:
            交易信号序列 (1=买入, -1=卖出, 0=持有)
        """
        pass

    def _validate_params(self):
        """验证参数有效性"""
        param_defs = {p.name: p for p in self.get_parameters()}

        for param_name, param_value in self.params.items():
            if param_name not in param_defs:
                raise ValueError(f"未知参数: {param_name}")

            param_def = param_defs[param_name]

            # 类型验证
            if param_def.type == ParameterType.INTEGER and not isinstance(param_value, int):
                raise ValueError(f"参数 {param_name} 必须是整数")

            if param_def.type == ParameterType.FLOAT and not isinstance(param_value, (int, float)):
                raise ValueError(f"参数 {param_name} 必须是数值")

            if param_def.type == ParameterType.BOOLEAN and not isinstance(param_value, bool):
                raise ValueError(f"参数 {param_name} 必须是布尔值")

            # 范围验证
            if param_def.type in [ParameterType.INTEGER, ParameterType.FLOAT]:
                if param_def.min_value is not None and param_value < param_def.min_value:
                    raise ValueError(f"参数 {param_name} 不能小于 {param_def.min_value}")
                if param_def.max_value is not None and param_value > param_def.max_value:
                    raise ValueError(f"参数 {param_name} 不能大于 {param_def.max_value}")

    def get_metadata(self) -> Dict[str, Any]:
        """
        获取策略元数据

        返回:
            包含策略信息和参数定义的字典
        """
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'parameters': [
                {
                    'name': p.name,
                    'label': p.label,
                    'type': p.type.value,
                    'default': p.default,
                    'min_value': p.min_value,
                    'max_value': p.max_value,
                    'step': p.step,
                    'options': p.options,
                    'description': p.description,
                    'category': p.category
                }
                for p in self.get_parameters()
            ]
        }

    def calculate_stop_loss(self, data: pd.DataFrame, atr_multiplier: float = 2.0) -> pd.Series:
        """
        计算动态止损价格（基于ATR）

        参数:
            data: 价格数据
            atr_multiplier: ATR倍数

        返回:
            止损价格序列
        """
        if 'ATR' not in data.columns:
            return pd.Series(0, index=data.index)

        return data['close'] - (data['ATR'] * atr_multiplier)

    def calculate_take_profit(self, data: pd.DataFrame, atr_multiplier: float = 3.0) -> pd.Series:
        """
        计算动态止盈价格（基于ATR）

        参数:
            data: 价格数据
            atr_multiplier: ATR倍数

        返回:
            止盈价格序列
        """
        if 'ATR' not in data.columns:
            return pd.Series(float('inf'), index=data.index)

        return data['close'] + (data['ATR'] * atr_multiplier)
