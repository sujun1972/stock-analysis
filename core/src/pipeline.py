"""
向后兼容模块：重新导出 DataPipeline 相关类和函数

这个模块作为向后兼容层存在，实际实现已迁移到 src.data_pipeline.orchestrator
用于避免循环导入：data_pipeline <-> pipeline

推荐使用：
    from src.data_pipeline import DataPipeline, create_pipeline, get_full_training_data

旧代码仍可使用：
    from src.pipeline import DataPipeline, create_pipeline, get_full_training_data
"""

# 从新位置重新导出所有内容
from src.data_pipeline.orchestrator import (
    DataPipeline,
    create_pipeline,
    get_full_training_data,
)
from src.data_pipeline.pipeline_config import (
    PipelineConfig,
    DEFAULT_CONFIG,
    BALANCED_TRAINING_CONFIG,
    QUICK_TRAINING_CONFIG,
    LONG_TERM_CONFIG,
    PRODUCTION_CONFIG,
    create_config
)
# 为了向后兼容，也导出子组件类（测试可能会用到）
from src.data_pipeline.data_loader import DataLoader
from src.data_pipeline.feature_engineer import FeatureEngineer
from src.data_pipeline.data_cleaner import DataCleaner
from src.data_pipeline.data_splitter import DataSplitter
from src.data_pipeline.feature_cache import FeatureCache

# 向后兼容导出
__all__ = [
    # 主要类和函数
    'DataPipeline',
    'create_pipeline',
    'get_full_training_data',
    # 配置类
    'PipelineConfig',
    'DEFAULT_CONFIG',
    'BALANCED_TRAINING_CONFIG',
    'QUICK_TRAINING_CONFIG',
    'LONG_TERM_CONFIG',
    'PRODUCTION_CONFIG',
    'create_config',
    # 子组件类（向后兼容）
    'DataLoader',
    'FeatureEngineer',
    'DataCleaner',
    'DataSplitter',
    'FeatureCache',
]


# 保留旧的类定义注释，供文档参考
"""
原 DataPipeline 类已迁移到 src.data_pipeline.orchestrator 模块

这样做是为了解决循环导入问题：
- 之前: src.data_pipeline.__init__ -> src.pipeline -> src.data_pipeline.data_loader (循环！)
- 现在: src.data_pipeline.__init__ -> src.data_pipeline.orchestrator (无循环)

迁移说明：
- 所有功能保持不变
- API完全兼容
- 请优先使用 from src.data_pipeline import DataPipeline
"""
