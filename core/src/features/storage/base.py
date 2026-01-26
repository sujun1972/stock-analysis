"""
存储后端基类和抽象接口

本模块提供：
1. BaseStorageBackend - 所有存储后端的抽象基类
2. StorageMetadata - 存储元数据的数据类
3. 通用的logger配置

设计说明：
- 所有存储后端都继承自 BaseStorageBackend
- 定义统一的保存/加载接口
- 支持多种存储格式的插拔式设计
"""

import pandas as pd
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime

# 尝试导入 loguru，如果不存在则使用简单的后备方案
try:
    from loguru import logger
except ImportError:
    class SimpleLogger:
        @staticmethod
        def debug(msg): pass
        @staticmethod
        def info(msg): print(msg)
        @staticmethod
        def warning(msg): print(f"WARNING: {msg}")
        @staticmethod
        def error(msg): print(f"ERROR: {msg}")
    logger = SimpleLogger()


@dataclass
class FeatureMetadata:
    """特征元数据"""
    stock_code: str
    feature_type: str
    version: str
    file_path: str
    rows: int
    columns: int
    column_names: list
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    saved_at: Optional[str] = None
    custom_metadata: Optional[Dict] = None


class BaseStorageBackend(ABC):
    """存储后端抽象基类"""

    def __init__(self, storage_dir: Path):
        """
        初始化存储后端

        参数:
            storage_dir: 存储根目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def save(
        self,
        df: pd.DataFrame,
        stock_code: str,
        feature_type: str,
        version: str
    ) -> str:
        """
        保存特征数据

        参数:
            df: 特征DataFrame
            stock_code: 股票代码
            feature_type: 特征类型
            version: 版本号

        返回:
            保存的文件路径
        """
        pass

    @abstractmethod
    def load(
        self,
        stock_code: str,
        feature_type: str,
        version: str
    ) -> Optional[pd.DataFrame]:
        """
        加载特征数据

        参数:
            stock_code: 股票代码
            feature_type: 特征类型
            version: 版本号

        返回:
            特征DataFrame，如果不存在返回None
        """
        pass

    @abstractmethod
    def exists(
        self,
        stock_code: str,
        feature_type: str,
        version: str
    ) -> bool:
        """
        检查特征文件是否存在

        参数:
            stock_code: 股票代码
            feature_type: 特征类型
            version: 版本号

        返回:
            文件是否存在
        """
        pass

    @abstractmethod
    def delete(
        self,
        stock_code: str,
        feature_type: str,
        version: str
    ) -> bool:
        """
        删除特征文件

        参数:
            stock_code: 股票代码
            feature_type: 特征类型
            version: 版本号

        返回:
            是否删除成功
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        pass

    def _build_file_path(
        self,
        stock_code: str,
        feature_type: str,
        version: str
    ) -> Path:
        """构建文件路径"""
        subdir = self.storage_dir / feature_type
        subdir.mkdir(exist_ok=True)
        filename = f"{stock_code}_{version}.{self.get_file_extension()}"
        return subdir / filename
