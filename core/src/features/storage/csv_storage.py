"""
CSV 格式存储后端

使用 CSV 格式存储特征数据
- 文本格式，易读易调试
- 兼容性最好
- 适合小规模数据和数据交换
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


class CSVStorage(BaseStorage):
    """CSV 格式存储实现"""

    def __init__(self, storage_dir: str, encoding: str = 'utf-8-sig'):
        """
        初始化 CSV 存储后端

        Args:
            storage_dir: 存储根目录
            encoding: 编码格式 ('utf-8-sig', 'utf-8', 'gbk')
        """
        super().__init__(storage_dir)
        self.encoding = encoding
        logger.debug(f"CSV 编码: {encoding}")

    def save(
        self,
        df: pd.DataFrame,
        file_path: Path,
        **kwargs
    ) -> bool:
        """
        保存 DataFrame 为 CSV 格式

        Args:
            df: 要保存的 DataFrame
            file_path: 完整文件路径
            **kwargs: 额外参数（sep, encoding等）

        Returns:
            保存是否成功
        """
        try:
            encoding = kwargs.get('encoding', self.encoding)
            sep = kwargs.get('sep', ',')
            index = kwargs.get('index', True)

            df.to_csv(
                file_path,
                encoding=encoding,
                sep=sep,
                index=index
            )

            file_size = self.get_file_size(file_path)
            logger.info(
                f"CSV 保存成功: {file_path.name}, "
                f"大小: {file_size / 1024:.2f} KB, "
                f"行数: {len(df)}, 列数: {len(df.columns)}"
            )
            return True

        except Exception as e:
            logger.error(f"CSV 保存失败 {file_path}: {e}")
            return False

    def load(
        self,
        file_path: Path,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        从 CSV 文件加载 DataFrame

        Args:
            file_path: 完整文件路径
            **kwargs: 额外参数（sep, encoding等）

        Returns:
            加载的 DataFrame，失败返回 None
        """
        try:
            if not self.file_exists(file_path):
                logger.warning(f"CSV 文件不存在: {file_path}")
                return None

            encoding = kwargs.get('encoding', self.encoding)
            sep = kwargs.get('sep', ',')
            index_col = kwargs.get('index_col', 0)
            parse_dates = kwargs.get('parse_dates', True)

            df = pd.read_csv(
                file_path,
                encoding=encoding,
                sep=sep,
                index_col=index_col,
                parse_dates=parse_dates
            )

            logger.info(
                f"CSV 加载成功: {file_path.name}, "
                f"行数: {len(df)}, 列数: {len(df.columns)}"
            )
            return df

        except Exception as e:
            logger.error(f"CSV 加载失败 {file_path}: {e}")
            return None

    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        return 'csv'
