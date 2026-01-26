"""
数据提供者元数据管理模块

定义和管理数据提供者的元数据信息，包括：
- 元数据类定义
- 元数据验证
- 元数据查询接口
"""

from typing import Type, List
from dataclasses import dataclass, field


@dataclass
class ProviderMetadata:
    """
    数据提供者元数据

    使用 dataclass 简化元数据定义，提供：
    - 自动生成 __init__、__repr__、__eq__ 等方法
    - 类型注解
    - 默认值支持
    """

    provider_class: Type['BaseDataProvider']
    """提供者类（必须继承 BaseDataProvider）"""

    description: str = ""
    """描述信息"""

    requires_token: bool = False
    """是否需要 API Token"""

    features: List[str] = field(default_factory=list)
    """支持的特性列表（如 'stock_list', 'daily_data', 'realtime_quotes' 等）"""

    priority: int = 0
    """优先级（数字越大优先级越高）"""

    def __post_init__(self):
        """初始化后验证"""
        # 验证 provider_class
        if not hasattr(self.provider_class, '__name__'):
            raise TypeError(f"provider_class 必须是一个类，当前类型：{type(self.provider_class)}")

        # 确保 features 是列表
        if not isinstance(self.features, list):
            self.features = list(self.features) if self.features else []

    def has_feature(self, feature: str) -> bool:
        """
        检查是否支持指定特性

        Args:
            feature: 特性名称

        Returns:
            bool: 是否支持该特性
        """
        return feature in self.features

    def to_dict(self) -> dict:
        """
        转换为字典格式

        Returns:
            dict: 元数据字典
        """
        return {
            'class': self.provider_class.__name__,
            'description': self.description,
            'requires_token': self.requires_token,
            'features': self.features,
            'priority': self.priority,
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"ProviderMetadata("
            f"class={self.provider_class.__name__}, "
            f"requires_token={self.requires_token}, "
            f"priority={self.priority}, "
            f"features={len(self.features)})"
        )


__all__ = ['ProviderMetadata']
