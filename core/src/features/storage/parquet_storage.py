"""
Parquet 格式存储后端

使用 Parquet 格式存储特征数据（推荐格式）
- 高性能读写
- 优秀的压缩率
- 支持列式存储
"""

from pathlib import Path
from typing import Optional, Any
import pandas as pd
from .base_storage import BaseStorage

from src.utils.logger import logger


class ParquetStorage(BaseStorage):
    """Parquet 格式存储实现"""

    def __init__(self, storage_dir: str, compression: str = 'snappy'):
        """
        初始化 Parquet 存储后端

        Args:
            storage_dir: 存储根目录
            compression: 压缩算法 ('snappy', 'gzip', 'brotli', 'lz4', 'zstd')
        """
        super().__init__(storage_dir)
        self.compression = compression
        logger.debug(f"Parquet 压缩算法: {compression}")

    def save(
        self,
        df: pd.DataFrame,
        file_path: Path,
        **kwargs: Any
    ) -> bool:
        """
        保存 DataFrame 为 Parquet 格式

        Args:
            df: 要保存的 DataFrame
            file_path: 完整文件路径
            **kwargs: 额外参数（compression, engine等）

        Returns:
            保存是否成功
        """
        try:
            compression = kwargs.get('compression', self.compression)
            engine = kwargs.get('engine', 'auto')

            df.to_parquet(
                file_path,
                compression=compression,
                engine=engine,
                index=True
            )

            file_size = self.get_file_size(file_path)
            logger.info(
                f"Parquet 保存成功: {file_path.name}, "
                f"大小: {file_size / 1024:.2f} KB, "
                f"行数: {len(df)}, 列数: {len(df.columns)}"
            )
            return True

        except Exception as e:
            logger.error(f"Parquet 保存失败 {file_path}: {e}")
            return False

    def load(
        self,
        file_path: Path,
        **kwargs: Any
    ) -> Optional[pd.DataFrame]:
        """
        从 Parquet 文件加载 DataFrame

        Args:
            file_path: 完整文件路径
            **kwargs: 额外参数（columns, engine等）

        Returns:
            加载的 DataFrame，失败返回 None
        """
        try:
            if not self.file_exists(file_path):
                logger.warning(f"Parquet 文件不存在: {file_path}")
                return None

            engine = kwargs.get('engine', 'auto')
            columns = kwargs.get('columns', None)

            df = pd.read_parquet(
                file_path,
                engine=engine,
                columns=columns
            )

            logger.info(
                f"Parquet 加载成功: {file_path.name}, "
                f"行数: {len(df)}, 列数: {len(df.columns)}"
            )
            return df

        except Exception as e:
            logger.error(f"Parquet 加载失败 {file_path}: {e}")
            return None

    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        return 'parquet'
