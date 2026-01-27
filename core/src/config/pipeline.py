#!/usr/bin/env python3
"""
数据流水线配置类

使用 dataclass 和 Pydantic 提供类型安全和验证
"""

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class PipelineConfig:
    """
    数据流水线配置

    使用配置类替代长参数列表，提供：
    - 类型提示和验证
    - 默认值管理
    - 配置的可序列化
    - 更好的IDE支持
    """

    # 目标设置
    target_period: int = 5
    """预测周期（天数）"""

    # 数据分割比例
    train_ratio: float = 0.7
    """训练集比例"""

    valid_ratio: float = 0.15
    """验证集比例"""

    # 样本平衡
    balance_samples: bool = False
    """是否平衡样本"""

    balance_method: Literal['oversample', 'undersample', 'smote', 'none'] = 'none'
    """平衡方法"""

    balance_threshold: float = 0.0
    """分类阈值（收益率>threshold为涨）"""

    # 特征缩放
    scale_features: bool = True
    """是否缩放特征"""

    scaler_type: Literal['standard', 'robust', 'minmax'] = 'robust'
    """缩放类型"""

    # 缓存设置
    use_cache: bool = True
    """是否使用缓存"""

    force_refresh: bool = False
    """强制刷新缓存"""

    def __post_init__(self):
        """初始化后验证"""
        # 验证比例
        if not 0 < self.train_ratio < 1:
            raise ValueError(f"train_ratio must be in (0, 1), got {self.train_ratio}")

        if not 0 < self.valid_ratio < 1:
            raise ValueError(f"valid_ratio must be in (0, 1), got {self.valid_ratio}")

        # 使用小的 epsilon 来处理浮点数精度问题
        test_ratio = 1 - self.train_ratio - self.valid_ratio
        if test_ratio < 0.001:  # 至少需要 0.1% 的测试集
            raise ValueError(
                f"train_ratio + valid_ratio must be < 1 (need at least 0.001 for test set), "
                f"got {self.train_ratio} + {self.valid_ratio} = {self.train_ratio + self.valid_ratio}"
            )

        # 验证目标周期
        if self.target_period < 1:
            raise ValueError(f"target_period must be >= 1, got {self.target_period}")

        # 验证平衡方法
        if self.balance_samples and self.balance_method == 'none':
            # 自动设置默认平衡方法
            self.balance_method = 'undersample'

    def to_dict(self) -> dict:
        """转换为字典（用于缓存键）"""
        return {
            'target_period': self.target_period,
            'train_ratio': round(self.train_ratio, 3),
            'valid_ratio': round(self.valid_ratio, 3),
            'balance_samples': self.balance_samples,
            'balance_method': self.balance_method,
            'scaler_type': self.scaler_type,
        }

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'PipelineConfig':
        """从字典创建配置"""
        return cls(**config_dict)

    def copy(self, **kwargs) -> 'PipelineConfig':
        """复制配置并修改部分参数"""
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return self.from_dict(config_dict)


# 预定义的常用配置

DEFAULT_CONFIG = PipelineConfig()
"""默认配置"""

QUICK_TRAINING_CONFIG = PipelineConfig(
    target_period=3,
    train_ratio=0.7,
    valid_ratio=0.15,
    balance_samples=False,
    use_cache=True
)
"""快速训练配置（短期预测）"""

BALANCED_TRAINING_CONFIG = PipelineConfig(
    target_period=5,
    train_ratio=0.7,
    valid_ratio=0.15,
    balance_samples=True,
    balance_method='undersample',
    use_cache=True
)
"""平衡训练配置（适用于不平衡数据）"""

LONG_TERM_CONFIG = PipelineConfig(
    target_period=20,
    train_ratio=0.8,
    valid_ratio=0.1,
    balance_samples=False,
    use_cache=True
)
"""长期预测配置"""

PRODUCTION_CONFIG = PipelineConfig(
    target_period=5,
    train_ratio=0.7,
    valid_ratio=0.15,
    balance_samples=True,
    balance_method='smote',
    scale_features=True,
    scaler_type='robust',
    use_cache=True,
    force_refresh=False
)
"""生产环境配置"""


# 便捷函数

def create_config(
    target_period: int = 5,
    train_ratio: float = 0.7,
    balance_samples: bool = False,
    **kwargs
) -> PipelineConfig:
    """
    便捷函数：创建配置

    Args:
        target_period: 预测周期
        train_ratio: 训练集比例
        balance_samples: 是否平衡样本
        **kwargs: 其他配置参数

    Returns:
        PipelineConfig实例
    """
    return PipelineConfig(
        target_period=target_period,
        train_ratio=train_ratio,
        balance_samples=balance_samples,
        **kwargs
    )
