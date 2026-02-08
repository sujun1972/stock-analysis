"""
ML模块 - 机器学习工作流核心组件

包含:
- FeatureEngine: 特征工程引擎
- LabelGenerator: 标签生成器
- TrainedModel: 训练好的模型包装类
- TrainingConfig: 训练配置
- MLEntry: ML入场策略 (待实现)
- MLStockRanker: 股票评分工具 (待实现)

对齐文档: core/docs/ml/README.md
版本: v1.1.0
创建时间: 2026-02-08
最后更新: 2026-02-08
"""

from .feature_engine import FeatureEngine
from .label_generator import LabelGenerator, LabelType
from .trained_model import TrainedModel, TrainingConfig

__all__ = [
    'FeatureEngine',
    'LabelGenerator',
    'LabelType',
    'TrainedModel',
    'TrainingConfig',
]

__version__ = '1.1.0'
