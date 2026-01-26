"""
特征存储管理器（向后兼容导出模块）

此文件保持向后兼容性，从新的模块化结构中导入所有类。
实际实现已经按存储后端拆分到 storage/ 子目录。

新的模块结构：
- storage/base_storage.py: 抽象基类
- storage/parquet_storage.py: Parquet 格式实现
- storage/hdf5_storage.py: HDF5 格式实现
- storage/csv_storage.py: CSV 格式实现
- storage/feature_storage.py: 主接口类
"""

# 从新模块导入所有类，保持向后兼容性
from .storage.base_storage import BaseStorage
from .storage.parquet_storage import ParquetStorage
from .storage.hdf5_storage import HDF5Storage
from .storage.csv_storage import CSVStorage
from .storage.feature_storage import FeatureStorage

# 导出所有类
__all__ = [
    'BaseStorage',
    'ParquetStorage',
    'HDF5Storage',
    'CSVStorage',
    'FeatureStorage'
]
