"""
数据流水线包 (Data Pipeline Package)

模块化的数据处理流水线，将原来的单一 DataPipeline 类拆分为多个专职类：
- DataLoader: 数据加载
- FeatureEngineer: 特征工程
- DataCleaner: 数据清洗
- DataSplitter: 数据分割和预处理
- FeatureCache: 缓存管理
- DataPipeline: 流程编排器

配置类已迁移到 config.pipeline 模块,但为了向后兼容仍可从此处导入
"""

from .data_loader import DataLoader
from .feature_engineer import FeatureEngineer
from .data_cleaner import DataCleaner
from .data_splitter import DataSplitter
from .feature_cache import FeatureCache

# 从本地orchestrator模块导入编排器类和辅助函数
# 解决循环导入：data_pipeline <-> pipeline
from .orchestrator import DataPipeline, create_pipeline, get_full_training_data

# 向后兼容：从新位置导入配置类
# 优先从 config.pipeline 导入,保留旧的 pipeline_config 作为备份
try:
    from ..config.pipeline import (
        PipelineConfig,
        DEFAULT_CONFIG,
        QUICK_TRAINING_CONFIG,
        BALANCED_TRAINING_CONFIG,
        LONG_TERM_CONFIG,
        PRODUCTION_CONFIG,
        create_config,
    )
except ImportError:
    # 向后兼容：如果 config.pipeline 不存在,从本地导入
    from .pipeline_config import (
        PipelineConfig,
        DEFAULT_CONFIG,
        QUICK_TRAINING_CONFIG,
        BALANCED_TRAINING_CONFIG,
        LONG_TERM_CONFIG,
        PRODUCTION_CONFIG,
        create_config,
    )

__all__ = [
    'DataLoader',
    'FeatureEngineer',
    'DataCleaner',
    'DataSplitter',
    'FeatureCache',
    'DataPipeline',
    'create_pipeline',
    'get_full_training_data',
    # 配置类
    'PipelineConfig',
    'DEFAULT_CONFIG',
    'QUICK_TRAINING_CONFIG',
    'BALANCED_TRAINING_CONFIG',
    'LONG_TERM_CONFIG',
    'PRODUCTION_CONFIG',
    'create_config',
]
