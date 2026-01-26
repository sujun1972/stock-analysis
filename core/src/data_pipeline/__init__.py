"""
数据流水线包 (Data Pipeline Package)

模块化的数据处理流水线，将原来的单一 DataPipeline 类拆分为多个专职类：
- DataLoader: 数据加载
- FeatureEngineer: 特征工程
- DataCleaner: 数据清洗
- DataSplitter: 数据分割和预处理
- FeatureCache: 缓存管理
- DataPipeline: 流程编排器
"""

from .data_loader import DataLoader
from .feature_engineer import FeatureEngineer
from .data_cleaner import DataCleaner
from .data_splitter import DataSplitter
from .feature_cache import FeatureCache

# 处理模块/包命名冲突：
# - data_pipeline/ 包（本目录）包含模块化组件（DataLoader, FeatureEngineer 等）
# - data_pipeline.py 文件（父目录）包含编排器类 DataPipeline
# 使用 importlib 动态加载兄弟模块，避免循环导入和命名冲突
import sys
from pathlib import Path
import importlib.util

_module_path = Path(__file__).parent.parent / 'data_pipeline.py'
_spec = importlib.util.spec_from_file_location("_data_pipeline_module", _module_path)
_data_pipeline_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_data_pipeline_module)

# 从兄弟模块导出主类和辅助函数
DataPipeline = _data_pipeline_module.DataPipeline
create_pipeline = _data_pipeline_module.create_pipeline
get_full_training_data = _data_pipeline_module.get_full_training_data

__all__ = [
    'DataLoader',
    'FeatureEngineer',
    'DataCleaner',
    'DataSplitter',
    'FeatureCache',
    'DataPipeline',
    'create_pipeline',
    'get_full_training_data',
]
