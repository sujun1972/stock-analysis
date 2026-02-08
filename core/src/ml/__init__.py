"""
ML模块 - 机器学习工作流核心组件

包含:
- FeatureEngine: 特征工程引擎
- LabelGenerator: 标签生成器
- TrainedModel: 训练好的模型包装类
- MLEntry: ML入场策略
- MLStockRanker: 股票评分工具

对齐文档: core/docs/ml/README.md
版本: v1.0.0
创建时间: 2026-02-08
"""

from .feature_engine import FeatureEngine

__all__ = [
    'FeatureEngine',
]

__version__ = '1.0.0'
