"""
特征缓存管理器 (FeatureCache)

负责特征数据的缓存存储、验证和加载
"""

import pandas as pd
import json
import hashlib
from pathlib import Path
from typing import Optional, Tuple, Dict
from exceptions import FeatureCacheError
from utils.logger import get_logger

logger = get_logger(__name__)


class FeatureCache:
    """
    特征缓存管理器

    职责：
    - 生成缓存键和文件路径
    - 保存特征到缓存
    - 验证缓存有效性
    - 从缓存加载特征
    - 清除缓存
    """

    def __init__(
        self,
        cache_dir: str = 'data/pipeline_cache',
        feature_version: str = 'v2.0'
    ):
        """
        初始化特征缓存管理器

        Args:
            cache_dir: 缓存目录
            feature_version: 特征版本号
        """
        self.cache_dir = Path(cache_dir)
        self.feature_version = feature_version
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        config: Dict
    ) -> Path:
        """
        生成缓存文件路径

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            config: 配置字典（包含所有影响数据的参数）

        Returns:
            缓存文件路径
        """
        # 添加版本号到配置
        config['version'] = self.feature_version

        # 计算配置哈希
        config_str = json.dumps(config, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:12]

        # 生成文件名
        filename = f"{symbol}_{start_date}_{end_date}_{config_hash}.parquet"
        return self.cache_dir / filename

    def save(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cache_file: Path,
        config: Dict,
        target_name: str
    ):
        """
        保存特征到缓存

        Args:
            X: 特征DataFrame
            y: 目标Series
            cache_file: 缓存文件路径
            config: 配置字典
            target_name: 目标列名
        """
        try:
            # 合并X和y
            df_cache = X.copy()
            df_cache[target_name] = y

            # 保存为Parquet格式
            df_cache.to_parquet(cache_file, compression='gzip')

            # 保存元数据
            metadata = {
                'version': self.feature_version,
                'config': config,
                'feature_count': len(X.columns),
                'feature_names': X.columns.tolist(),
                'sample_count': len(X),
                'target_name': target_name,
                'created_at': pd.Timestamp.now().isoformat()
            }

            metadata_file = self._get_metadata_path(cache_file)
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"缓存已保存: {cache_file.name} ({len(X)} 样本, {len(X.columns)} 特征)")

        except Exception as e:
            logger.error(f"缓存保存失败: {e}")
            raise FeatureCacheError(f"缓存保存失败: {e}")

    def load(
        self,
        cache_file: Path,
        target_name: str,
        config: Dict
    ) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
        """
        从缓存加载特征

        Args:
            cache_file: 缓存文件路径
            target_name: 目标列名
            config: 当前配置（用于验证）

        Returns:
            (X, y) 或 None（如果缓存无效）
        """
        # 验证缓存
        if not self._validate(cache_file, config):
            # 删除无效缓存
            self._delete_cache_files(cache_file)
            return None

        try:
            df_cache = pd.read_parquet(cache_file)

            X = df_cache.drop(columns=[target_name])
            y = df_cache[target_name]

            logger.info(f"缓存加载成功: {cache_file.name} ({len(X)} 样本, {len(X.columns)} 特征)")

            return X, y

        except Exception as e:
            logger.error(f"缓存加载失败: {e}")
            self._delete_cache_files(cache_file)
            return None

    def _validate(self, cache_file: Path, config: Dict) -> bool:
        """
        验证缓存是否有效

        Args:
            cache_file: 缓存文件路径
            config: 当前配置

        Returns:
            是否有效
        """
        metadata_file = self._get_metadata_path(cache_file)

        if not cache_file.exists() or not metadata_file.exists():
            logger.debug(f"缓存文件不存在: {cache_file.name}")
            return False

        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # 检查版本号
            if metadata.get('version') != self.feature_version:
                logger.debug(
                    f"特征版本不匹配: 缓存={metadata.get('version')}, "
                    f"当前={self.feature_version}"
                )
                return False

            # 检查关键配置
            cached_config = metadata.get('config', {})
            for key in ['scaler_type', 'target_period', 'feature_config_hash']:
                if cached_config.get(key) != config.get(key):
                    logger.debug(f"配置不匹配 ({key}): 缓存={cached_config.get(key)}, 当前={config.get(key)}")
                    return False

            logger.debug(f"缓存验证通过: {cache_file.name}")
            return True

        except Exception as e:
            logger.error(f"缓存验证失败: {e}")
            return False

    def clear(self, symbol: Optional[str] = None):
        """
        清除缓存

        Args:
            symbol: 股票代码（None则清除所有）
        """
        if symbol:
            pattern = f"{symbol}_*.parquet"
        else:
            pattern = "*.parquet"

        cache_files = list(self.cache_dir.glob(pattern))
        metadata_files = list(self.cache_dir.glob(f"{pattern[:-8]}.meta.json"))

        for file in cache_files + metadata_files:
            file.unlink()

        logger.info(f"已清除 {len(cache_files)} 个缓存文件")

    def _get_metadata_path(self, cache_file: Path) -> Path:
        """获取缓存元数据文件路径"""
        return cache_file.with_suffix('.meta.json')

    def _delete_cache_files(self, cache_file: Path):
        """删除缓存文件和元数据"""
        if cache_file.exists():
            cache_file.unlink()

        metadata_file = self._get_metadata_path(cache_file)
        if metadata_file.exists():
            metadata_file.unlink()

    def compute_feature_config_hash(self, config: Dict) -> str:
        """
        计算特征配置的哈希值

        Args:
            config: 特征配置字典

        Returns:
            MD5哈希值（前8位）
        """
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]
