"""
特征存储基础抽象类

定义所有存储后端必须实现的接口
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import pandas as pd

# 尝试导入 loguru，如果不存在则使用简单的后备方案
try:
    from utils.logger import logger
except ImportError:
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


class BaseStorage(ABC):
    """特征存储抽象基类"""

    def __init__(self, storage_dir: str):
        """
        初始化存储后端

        Args:
            storage_dir: 存储根目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"初始化存储后端: {self.__class__.__name__}, 目录: {self.storage_dir}")

    @abstractmethod
    def save(
        self,
        df: pd.DataFrame,
        file_path: Path,
        **kwargs
    ) -> bool:
        """
        保存DataFrame到文件

        Args:
            df: 要保存的DataFrame
            file_path: 完整文件路径
            **kwargs: 额外参数

        Returns:
            保存是否成功
        """
        pass

    @abstractmethod
    def load(
        self,
        file_path: Path,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        从文件加载DataFrame

        Args:
            file_path: 完整文件路径
            **kwargs: 额外参数

        Returns:
            加载的DataFrame，失败返回None
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """
        获取文件扩展名

        Returns:
            文件扩展名（不含点）
        """
        pass

    def build_file_path(
        self,
        stock_code: str,
        feature_type: str,
        version: str
    ) -> Path:
        """
        构建文件完整路径

        Args:
            stock_code: 股票代码
            feature_type: 特征类型
            version: 版本号

        Returns:
            完整文件路径
        """
        subdir = self.storage_dir / feature_type
        subdir.mkdir(exist_ok=True)
        filename = f"{stock_code}_{version}.{self.get_file_extension()}"
        return subdir / filename

    def file_exists(self, file_path: Path) -> bool:
        """
        检查文件是否存在

        Args:
            file_path: 文件路径

        Returns:
            文件是否存在
        """
        return file_path.exists()

    def delete_file(self, file_path: Path) -> bool:
        """
        删除文件

        Args:
            file_path: 文件路径

        Returns:
            删除是否成功
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"已删除文件: {file_path}")
                return True
            else:
                logger.warning(f"文件不存在: {file_path}")
                return False
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False

    def get_file_size(self, file_path: Path) -> int:
        """
        获取文件大小（字节）

        Args:
            file_path: 文件路径

        Returns:
            文件大小
        """
        if file_path.exists():
            return file_path.stat().st_size
        return 0
