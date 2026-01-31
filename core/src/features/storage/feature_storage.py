"""
特征存储管理器（Feature Storage Manager）

提供特征数据的持久化存储功能：
- 多格式支持：Parquet（推荐）、HDF5、CSV
- 版本管理：支持特征版本控制
- 元数据管理：JSON格式的元数据跟踪
- Scaler管理：保存和加载数据标准化器
- 批量操作：支持批量加载多只股票特征

重构说明：
- 使用策略模式将不同存储格式拆分为独立的后端
- BaseStorage: 抽象基类
- ParquetStorage, HDF5Storage, CSVStorage: 具体实现
- FeatureStorage: 主接口类，负责元数据和业务逻辑
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import json
import re
import threading
from datetime import datetime
from typing import Optional, Dict, List, Any, Type
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

from .base_storage import BaseStorage
from .parquet_storage import ParquetStorage
from .hdf5_storage import HDF5Storage
from .csv_storage import CSVStorage

from src.utils.logger import logger
from src.utils.response import Response
from src.exceptions import FeatureStorageError

warnings.filterwarnings('ignore')


class FeatureStorage:
    """特征存储管理器（主接口类）"""

    # 存储后端映射
    STORAGE_BACKENDS: Dict[str, Type[BaseStorage]] = {
        'parquet': ParquetStorage,
        'hdf5': HDF5Storage,
        'csv': CSVStorage
    }

    def __init__(
        self,
        storage_dir: str = 'data/features',
        format: str = 'parquet'
    ):
        """
        初始化特征存储管理器

        参数:
            storage_dir: 特征存储目录
            format: 存储格式 ('parquet', 'hdf5', 'csv')
        """
        self.storage_dir = Path(storage_dir)
        self.format = format
        self.metadata_file = self.storage_dir / 'metadata.json'

        # 元数据线程锁（保证并发安全）
        self._metadata_lock = threading.RLock()

        # 创建目录结构
        self._init_storage_structure()

        # 初始化存储后端
        self.backend = self._create_backend(format)

        # 加载元数据
        self.metadata = self._load_metadata()

        logger.info(
            f"FeatureStorage 初始化完成: "
            f"目录={self.storage_dir}, 格式={format}, "
            f"后端={self.backend.__class__.__name__}"
        )

    def _create_backend(self, format: str) -> BaseStorage:
        """
        创建存储后端（工厂方法）

        参数:
            format: 存储格式

        返回:
            存储后端实例
        """
        if format not in self.STORAGE_BACKENDS:
            logger.error(f"不支持的存储格式: {format}")
            raise ValueError(
                f"不支持的格式: {format}. "
                f"支持的格式: {list(self.STORAGE_BACKENDS.keys())}"
            )

        backend_class = self.STORAGE_BACKENDS[format]
        return backend_class(storage_dir=str(self.storage_dir))

    def _init_storage_structure(self):
        """初始化存储目录结构"""
        # 创建主目录
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        subdirs = ['raw', 'technical', 'alpha', 'transformed', 'models', 'scalers']
        for subdir in subdirs:
            (self.storage_dir / subdir).mkdir(exist_ok=True)

        logger.debug(f"存储目录结构初始化完成: {self.storage_dir}")

    def _load_metadata(self) -> Dict[str, Any]:
        """
        加载元数据（线程安全）

        Returns:
            元数据字典
        """
        with self._metadata_lock:
            if self.metadata_file.exists():
                try:
                    with open(self.metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    logger.debug(f"元数据加载成功: {len(metadata.get('stocks', {}))} 只股票")
                    return metadata
                except json.JSONDecodeError as e:
                    logger.error(f"元数据 JSON 解析失败: {e}")
                    return self._create_empty_metadata()
                except Exception as e:
                    logger.error(f"元数据加载失败: {e}")
                    return self._create_empty_metadata()
            else:
                logger.debug("元数据文件不存在，创建新的元数据")
                return self._create_empty_metadata()

    def _create_empty_metadata(self) -> dict:
        """创建空元数据结构"""
        return {
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'stocks': {},
            'feature_versions': {}
        }

    def _save_metadata(self) -> bool:
        """
        保存元数据（线程安全）

        Returns:
            是否保存成功
        """
        with self._metadata_lock:
            try:
                self.metadata['updated_at'] = datetime.now().isoformat()

                # 先写入临时文件，然后原子性重命名（避免写入过程中崩溃导致文件损坏）
                temp_file = self.metadata_file.with_suffix('.json.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, indent=2, ensure_ascii=False, fp=f)

                # 原子性重命名
                temp_file.replace(self.metadata_file)

                logger.debug("元数据保存成功")
                return True
            except Exception as e:
                logger.error(f"元数据保存失败: {e}")
                return False

    # ==================== 特征保存 ====================

    def save_features(
        self,
        df: pd.DataFrame,
        stock_code: str,
        feature_type: str = 'transformed',
        version: str = 'v1',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Response:
        """
        保存特征数据

        参数:
            df: 特征DataFrame
            stock_code: 股票代码
            feature_type: 特征类型 ('raw', 'technical', 'alpha', 'transformed')
            version: 版本号
            metadata: 额外元数据

        返回:
            Response对象，包含保存结果和元信息
        """
        try:
            # 验证输入
            if df.empty:
                logger.warning(f"保存失败: DataFrame 为空 (股票={stock_code}, 类型={feature_type})")
                return Response.error(
                    error="DataFrame 为空，无法保存",
                    error_code="EMPTY_DATAFRAME_ERROR",
                    stock_code=stock_code,
                    feature_type=feature_type
                )

            # 构建文件路径
            file_path = self.backend.build_file_path(stock_code, feature_type, version)

            # 使用后端保存数据
            success = self.backend.save(df, file_path)

            if not success:
                logger.error(f"后端保存失败: 股票={stock_code}, 类型={feature_type}")
                return Response.error(
                    error="后端保存失败",
                    error_code="BACKEND_SAVE_ERROR",
                    stock_code=stock_code,
                    feature_type=feature_type,
                    file_path=str(file_path)
                )

            # 更新元数据
            if stock_code not in self.metadata['stocks']:
                self.metadata['stocks'][stock_code] = {}

            feature_metadata = {
                'version': version,
                'file_path': str(file_path),
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': df.columns.tolist(),
                'date_range': {
                    'start': str(df.index.min()) if isinstance(df.index, pd.DatetimeIndex) else None,
                    'end': str(df.index.max()) if isinstance(df.index, pd.DatetimeIndex) else None
                },
                'saved_at': datetime.now().isoformat(),
                'metadata': metadata or {}
            }

            self.metadata['stocks'][stock_code][feature_type] = feature_metadata

            metadata_saved = self._save_metadata()
            if not metadata_saved:
                logger.warning(
                    f"元数据保存失败，但特征文件已保存: "
                    f"股票={stock_code}, 类型={feature_type}"
                )

            logger.info(
                f"特征保存成功: 股票={stock_code}, 类型={feature_type}, "
                f"版本={version}, 行数={len(df)}, 列数={len(df.columns)}"
            )

            return Response.success(
                data={'file_path': str(file_path)},
                message=f"特征保存成功",
                stock_code=stock_code,
                feature_type=feature_type,
                version=version,
                rows=len(df),
                columns=len(df.columns),
                metadata_saved=metadata_saved
            )

        except (IOError, OSError) as e:
            logger.error(f"文件系统错误: {e} (股票={stock_code}, 类型={feature_type})")
            return Response.error(
                error=f"文件系统错误: {str(e)}",
                error_code="FILE_SYSTEM_ERROR",
                stock_code=stock_code,
                feature_type=feature_type
            )
        except Exception as e:
            logger.error(
                f"保存特征失败: {e} (股票={stock_code}, 类型={feature_type})",
                exc_info=True
            )
            return Response.error(
                error=f"保存特征失败: {str(e)}",
                error_code="FEATURE_SAVE_ERROR",
                stock_code=stock_code,
                feature_type=feature_type,
                exception_type=type(e).__name__
            )

    # ==================== 特征加载 ====================

    def load_features(
        self,
        stock_code: str,
        feature_type: str = 'transformed',
        version: str = None
    ) -> Response:
        """
        加载特征数据

        参数:
            stock_code: 股票代码
            feature_type: 特征类型
            version: 版本号（None表示最新版本）

        返回:
            Response对象，包含加载结果和元信息
        """
        try:
            # 查找版本
            if version is None:
                # 使用元数据中的版本
                if (stock_code in self.metadata['stocks'] and
                    feature_type in self.metadata['stocks'][stock_code]):
                    version = self.metadata['stocks'][stock_code][feature_type]['version']
                else:
                    logger.warning(f"找不到特征: 股票={stock_code}, 类型={feature_type}")
                    return Response.error(
                        error=f"找不到特征",
                        error_code="FEATURE_NOT_FOUND",
                        stock_code=stock_code,
                        feature_type=feature_type
                    )

            # 构建文件路径
            file_path = self.backend.build_file_path(stock_code, feature_type, version)

            # 使用后端加载数据
            df = self.backend.load(file_path)

            if df is None:
                logger.warning(f"加载失败，返回None: 股票={stock_code}, 类型={feature_type}")
                return Response.error(
                    error="加载失败，后端返回None",
                    error_code="BACKEND_LOAD_ERROR",
                    stock_code=stock_code,
                    feature_type=feature_type,
                    version=version,
                    file_path=str(file_path)
                )

            logger.info(
                f"特征加载成功: 股票={stock_code}, 类型={feature_type}, "
                f"版本={version}, 行数={len(df)}, 列数={len(df.columns)}"
            )

            # 准备日期范围信息
            date_range = None
            if isinstance(df.index, pd.DatetimeIndex):
                date_range = {
                    'start': str(df.index.min()),
                    'end': str(df.index.max())
                }

            return Response.success(
                data=df,
                message="特征加载成功",
                stock_code=stock_code,
                feature_type=feature_type,
                version=version,
                rows=len(df),
                columns=len(df.columns),
                date_range=date_range,
                file_path=str(file_path)
            )

        except FileNotFoundError as e:
            logger.warning(
                f"特征文件不存在: 股票={stock_code}, 类型={feature_type}, "
                f"版本={version}"
            )
            return Response.error(
                error=f"特征文件不存在",
                error_code="FILE_NOT_FOUND",
                stock_code=stock_code,
                feature_type=feature_type,
                version=version
            )
        except (IOError, OSError) as e:
            logger.error(
                f"文件系统错误: {e} (股票={stock_code}, 类型={feature_type})"
            )
            return Response.error(
                error=f"文件系统错误: {str(e)}",
                error_code="FILE_SYSTEM_ERROR",
                stock_code=stock_code,
                feature_type=feature_type,
                version=version
            )
        except Exception as e:
            logger.error(
                f"加载特征失败: {e} (股票={stock_code}, 类型={feature_type})",
                exc_info=True
            )
            return Response.error(
                error=f"加载特征失败: {str(e)}",
                error_code="FEATURE_LOAD_ERROR",
                stock_code=stock_code,
                feature_type=feature_type,
                version=version,
                exception_type=type(e).__name__
            )

    def load_multiple_stocks(
        self,
        stock_codes: List[str],
        feature_type: str = 'transformed',
        version: Optional[str] = None,
        parallel: bool = True,
        max_workers: int = 4
    ) -> Dict[str, pd.DataFrame]:
        """
        批量加载多只股票的特征

        参数:
            stock_codes: 股票代码列表
            feature_type: 特征类型
            version: 版本号
            parallel: 是否使用并发加载（默认开启）
            max_workers: 最大并发线程数

        返回:
            {股票代码: 特征DataFrame} 字典
        """
        features_dict = {}

        logger.info(
            f"批量加载开始: {len(stock_codes)} 只股票, 类型={feature_type}, "
            f"并发={parallel}"
        )

        if parallel and len(stock_codes) > 1:
            # 并发加载
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_stock = {
                    executor.submit(
                        self.load_features, stock_code, feature_type, version
                    ): stock_code
                    for stock_code in stock_codes
                }

                for future in as_completed(future_to_stock):
                    stock_code = future_to_stock[future]
                    try:
                        df = future.result()
                        if df is not None:
                            features_dict[stock_code] = df
                    except Exception as e:
                        logger.error(f"并发加载失败: 股票={stock_code}, 错误={e}")
        else:
            # 串行加载
            for stock_code in stock_codes:
                df = self.load_features(stock_code, feature_type, version)
                if df is not None:
                    features_dict[stock_code] = df

        logger.info(
            f"批量加载完成: 成功 {len(features_dict)}/{len(stock_codes)} 只股票"
        )

        return features_dict

    # ==================== Scaler管理 ====================

    def save_scaler(
        self,
        scaler: Any,
        scaler_name: str,
        version: str = 'v1'
    ) -> bool:
        """
        保存Scaler对象（用于模型推理时的特征标准化）

        参数:
            scaler: Scaler对象（StandardScaler, RobustScaler等）
            scaler_name: Scaler名称
            version: 版本号

        返回:
            是否保存成功
        """
        try:
            scaler_dir = self.storage_dir / 'scalers'
            scaler_dir.mkdir(exist_ok=True)

            file_path = scaler_dir / f"{scaler_name}_{version}.pkl"

            with open(file_path, 'wb') as f:
                pickle.dump(scaler, f)

            logger.info(f"Scaler 保存成功: {scaler_name}, 版本={version}")

            return True

        except Exception as e:
            logger.error(f"保存 Scaler 失败: {e}")
            return False

    def load_scaler(
        self,
        scaler_name: str,
        version: str = 'v1'
    ) -> Optional[Any]:
        """
        加载Scaler对象

        参数:
            scaler_name: Scaler名称
            version: 版本号

        返回:
            Scaler对象，如果不存在返回None
        """
        try:
            scaler_dir = self.storage_dir / 'scalers'
            file_path = scaler_dir / f"{scaler_name}_{version}.pkl"

            if not file_path.exists():
                logger.warning(f"Scaler 文件不存在: {file_path}")
                return None

            with open(file_path, 'rb') as f:
                scaler = pickle.load(f)

            logger.info(f"Scaler 加载成功: {scaler_name}, 版本={version}")

            return scaler

        except Exception as e:
            logger.error(f"加载 Scaler 失败: {e}")
            return None

    # ==================== 特征列表管理 ====================

    def list_stocks(self, feature_type: str = None) -> List[str]:
        """
        列出所有已保存特征的股票代码

        参数:
            feature_type: 特征类型（None表示所有类型）

        返回:
            股票代码列表
        """
        stock_codes = []

        for stock_code, features in self.metadata['stocks'].items():
            if feature_type is None:
                stock_codes.append(stock_code)
            elif feature_type in features:
                stock_codes.append(stock_code)

        return sorted(stock_codes)

    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票的特征信息

        参数:
            stock_code: 股票代码

        返回:
            股票特征信息字典
        """
        return self.metadata['stocks'].get(stock_code)

    def get_feature_columns(
        self,
        stock_code: str,
        feature_type: str = 'transformed'
    ) -> Optional[List[str]]:
        """
        获取特征列名列表

        参数:
            stock_code: 股票代码
            feature_type: 特征类型

        返回:
            特征列名列表
        """
        if (stock_code in self.metadata['stocks'] and
            feature_type in self.metadata['stocks'][stock_code]):
            return self.metadata['stocks'][stock_code][feature_type]['column_names']
        else:
            return None

    # ==================== 特征更新 ====================

    def update_features(
        self,
        stock_code: str,
        new_df: pd.DataFrame,
        feature_type: str = 'transformed',
        mode: str = 'append'
    ) -> bool:
        """
        更新特征数据

        参数:
            stock_code: 股票代码
            new_df: 新数据DataFrame
            feature_type: 特征类型
            mode: 更新模式 ('append', 'replace')

        返回:
            是否更新成功

        注意:
            本方法返回bool，但内部调用save_features和load_features返回Response对象，
            需要通过.is_success()检查成功状态，通过.data访问数据
        """
        try:
            if mode == 'replace':
                # 直接替换
                version = self._get_next_version(stock_code, feature_type)
                response = self.save_features(new_df, stock_code, feature_type, version)
                return response.is_success()

            elif mode == 'append':
                # 加载旧数据（load_features返回Response对象）
                response = self.load_features(stock_code, feature_type)

                if not response.is_success():
                    # 没有旧数据，直接保存
                    response = self.save_features(new_df, stock_code, feature_type, 'v1')
                    return response.is_success()

                # 从Response中提取DataFrame
                old_df = response.data

                # 合并数据（去重）
                combined_df = pd.concat([old_df, new_df])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                combined_df = combined_df.sort_index()

                # 保存新版本（save_features返回Response对象）
                version = self._get_next_version(stock_code, feature_type)
                response = self.save_features(combined_df, stock_code, feature_type, version)
                return response.is_success()

            else:
                raise ValueError(f"不支持的更新模式: {mode}")

        except Exception as e:
            logger.error(f"更新特征失败: {e}")
            return False

    def _get_next_version(self, stock_code: str, feature_type: str) -> str:
        """
        获取下一个版本号

        支持的版本格式: v1, v2, v3, ... 或 1, 2, 3, ...
        如果版本格式不规范，默认返回 v1

        Args:
            stock_code: 股票代码
            feature_type: 特征类型

        Returns:
            下一个版本号字符串
        """
        if (stock_code in self.metadata['stocks'] and
            feature_type in self.metadata['stocks'][stock_code]):
            current_version = self.metadata['stocks'][stock_code][feature_type]['version']

            # 使用正则表达式提取版本号
            match = re.match(r'v?(\d+)', current_version)
            if match:
                version_num = int(match.group(1))
                return f"v{version_num + 1}"
            else:
                logger.warning(
                    f"版本格式不规范: {current_version}, 重置为 v1 "
                    f"(股票={stock_code}, 类型={feature_type})"
                )
                return 'v1'
        else:
            return 'v1'

    # ==================== 特征删除 ====================

    def delete_features(
        self,
        stock_code: str,
        feature_type: str = None,
        version: str = None
    ) -> bool:
        """
        删除特征数据

        参数:
            stock_code: 股票代码
            feature_type: 特征类型（None表示删除所有类型）
            version: 版本号（None表示删除所有版本）

        返回:
            是否删除成功
        """
        try:
            if stock_code not in self.metadata['stocks']:
                logger.warning(f"股票 {stock_code} 不存在")
                return False

            if feature_type is None:
                # 删除该股票的所有特征类型
                for ftype in list(self.metadata['stocks'][stock_code].keys()):
                    self._delete_feature_file(stock_code, ftype)
                del self.metadata['stocks'][stock_code]
                logger.info(f"已删除股票 {stock_code} 的所有特征")

            else:
                # 删除指定类型
                if feature_type not in self.metadata['stocks'][stock_code]:
                    logger.warning(f"特征类型 {feature_type} 不存在")
                    return False

                self._delete_feature_file(stock_code, feature_type, version)
                del self.metadata['stocks'][stock_code][feature_type]
                logger.info(f"已删除股票 {stock_code} 的 {feature_type} 特征")

            self._save_metadata()

            return True

        except Exception as e:
            logger.error(f"删除特征失败: {e}")
            return False

    def _delete_feature_file(
        self,
        stock_code: str,
        feature_type: str,
        version: str = None
    ):
        """删除特征文件"""
        if version is None:
            version = self.metadata['stocks'][stock_code][feature_type]['version']

        file_path = self.backend.build_file_path(stock_code, feature_type, version)
        self.backend.delete_file(file_path)

    # ==================== 统计信息 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取存储统计信息

        Returns:
            包含统计信息的字典:
            - total_stocks: 股票总数
            - feature_types: 各类型特征数量
            - storage_size: 存储大小（字节）
            - storage_size_mb: 存储大小（MB）
        """
        stats: Dict[str, Any] = {
            'total_stocks': len(self.metadata['stocks']),
            'feature_types': {},
            'storage_size': 0
        }

        # 统计各类型特征数量
        for stock_code, features in self.metadata['stocks'].items():
            for feature_type in features.keys():
                if feature_type not in stats['feature_types']:
                    stats['feature_types'][feature_type] = 0
                stats['feature_types'][feature_type] += 1

        # 计算存储大小（安全处理文件访问错误）
        try:
            for subdir in self.storage_dir.iterdir():
                if subdir.is_dir():
                    for file in subdir.glob('*'):
                        if file.is_file():
                            try:
                                stats['storage_size'] += file.stat().st_size
                            except (OSError, IOError) as e:
                                logger.warning(f"无法获取文件大小: {file}, 错误: {e}")
        except Exception as e:
            logger.error(f"计算存储大小失败: {e}")

        stats['storage_size_mb'] = round(stats['storage_size'] / (1024 * 1024), 2)

        return stats

    def print_statistics(self):
        """打印存储统计信息"""
        stats = self.get_statistics()

        logger.info("=" * 60)
        logger.info("特征存储统计信息")
        logger.info("=" * 60)
        logger.info(f"存储目录:       {self.storage_dir}")
        logger.info(f"存储格式:       {self.format}")
        logger.info(f"存储后端:       {self.backend.__class__.__name__}")
        logger.info(f"股票总数:       {stats['total_stocks']}")
        logger.info(f"存储大小:       {stats['storage_size_mb']:.2f} MB")

        if stats['feature_types']:
            logger.info("\n特征类型分布:")
            for ftype, count in stats['feature_types'].items():
                logger.info(f"  {ftype:15s}: {count:4d} 只股票")

        logger.info("=" * 60)
