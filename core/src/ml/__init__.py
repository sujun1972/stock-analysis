"""
ML模块 - 机器学习工作流核心组件

包含:
- FeatureEngine: 特征工程引擎
- LabelGenerator: 标签生成器
- TrainedModel: 训练好的模型包装类
- TrainingConfig: 训练配置
- MLEntry: ML入场策略
- MLStockRanker: 股票评分工具

对齐文档: core/docs/ml/README.md
版本: v1.3.0
创建时间: 2026-02-08
最后更新: 2026-02-08
"""

from .feature_engine import FeatureEngine
from .label_generator import LabelGenerator, LabelType
from .trained_model import TrainedModel, TrainingConfig
from .ml_entry import MLEntry
from .ml_stock_ranker import MLStockRanker, ScoringMethod

__all__ = [
    'FeatureEngine',
    'LabelGenerator',
    'LabelType',
    'TrainedModel',
    'TrainingConfig',
    'MLEntry',
    'MLStockRanker',
    'ScoringMethod',
]

__version__ = '1.3.0'
