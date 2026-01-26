"""
HDF5 格式存储后端

使用 HDF5 格式存储特征数据
- 支持大规模数据
- 支持分层存储
- 适合科学计算场景
"""

from pathlib import Path
from typing import Optional
import pandas as pd
from .base_storage import BaseStorage

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


class HDF5Storage(BaseStorage):
    """HDF5 格式存储实现"""

    def __init__(self, storage_dir: str, complevel: int = 9):
        """
        初始化 HDF5 存储后端

        Args:
            storage_dir: 存储根目录
            complevel: 压缩级别 (0-9, 0=不压缩, 9=最大压缩)
        """
        super().__init__(storage_dir)
        self.complevel = complevel
        logger.debug(f"HDF5 压缩级别: {complevel}")

    def save(
        self,
        df: pd.DataFrame,
        file_path: Path,
        **kwargs
    ) -> bool:
        """
        保存 DataFrame 为 HDF5 格式

        Args:
            df: 要保存的 DataFrame
            file_path: 完整文件路径
            **kwargs: 额外参数（key, complevel等）

        Returns:
            保存是否成功
        """
        try:
            key = kwargs.get('key', 'data')
            complevel = kwargs.get('complevel', self.complevel)
            mode = kwargs.get('mode', 'w')

            df.to_hdf(
                file_path,
                key=key,
                mode=mode,
                complevel=complevel,
                format='table'
            )

            file_size = self.get_file_size(file_path)
            logger.info(
                f"HDF5 保存成功: {file_path.name}, "
                f"大小: {file_size / 1024:.2f} KB, "
                f"行数: {len(df)}, 列数: {len(df.columns)}"
            )
            return True

        except Exception as e:
            logger.error(f"HDF5 保存失败 {file_path}: {e}")
            return False

    def load(
        self,
        file_path: Path,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        从 HDF5 文件加载 DataFrame

        Args:
            file_path: 完整文件路径
            **kwargs: 额外参数（key, where等）

        Returns:
            加载的 DataFrame，失败返回 None
        """
        try:
            if not self.file_exists(file_path):
                logger.warning(f"HDF5 文件不存在: {file_path}")
                return None

            key = kwargs.get('key', 'data')
            where = kwargs.get('where', None)
            columns = kwargs.get('columns', None)

            df = pd.read_hdf(
                file_path,
                key=key,
                where=where,
                columns=columns
            )

            logger.info(
                f"HDF5 加载成功: {file_path.name}, "
                f"行数: {len(df)}, 列数: {len(df.columns)}"
            )
            return df

        except Exception as e:
            logger.error(f"HDF5 加载失败 {file_path}: {e}")
            return None

    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        return 'h5'
