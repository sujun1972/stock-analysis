"""
特征存储管理器（Feature Storage Manager）

提供特征数据的持久化存储功能：
- 多格式支持：Parquet（推荐）、HDF5、CSV
- 版本管理：支持特征版本控制
- 元数据管理：JSON格式的元数据跟踪
- Scaler管理：保存和加载数据标准化器
- 批量操作：支持批量加载多只股票特征

使用场景：
- 离线特征计算和存储
- 模型训练数据准备
- 特征版本管理和回溯
- 生产环境特征读取
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import warnings

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

warnings.filterwarnings('ignore')


class FeatureStorage:
    """特征存储管理器"""

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

        # 创建目录结构
        self._init_storage_structure()

        # 加载元数据
        self.metadata = self._load_metadata()

    def _init_storage_structure(self):
        """初始化存储目录结构"""
        # 创建主目录
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (self.storage_dir / 'raw').mkdir(exist_ok=True)
        (self.storage_dir / 'technical').mkdir(exist_ok=True)
        (self.storage_dir / 'alpha').mkdir(exist_ok=True)
        (self.storage_dir / 'transformed').mkdir(exist_ok=True)
        (self.storage_dir / 'models').mkdir(exist_ok=True)
        (self.storage_dir / 'scalers').mkdir(exist_ok=True)

    def _load_metadata(self) -> dict:
        """加载元数据"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'stocks': {},
                'feature_versions': {}
            }

    def _save_metadata(self):
        """保存元数据"""
        self.metadata['updated_at'] = datetime.now().isoformat()
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, indent=2, ensure_ascii=False, fp=f)

    # ==================== 特征保存 ====================

    def save_features(
        self,
        df: pd.DataFrame,
        stock_code: str,
        feature_type: str = 'transformed',
        version: str = 'v1',
        metadata: dict = None
    ) -> bool:
        """
        保存特征数据

        参数:
            df: 特征DataFrame
            stock_code: 股票代码
            feature_type: 特征类型 ('raw', 'technical', 'alpha', 'transformed')
            version: 版本号
            metadata: 额外元数据

        返回:
            是否保存成功
        """
        try:
            # 构建保存路径
            subdir = self.storage_dir / feature_type
            subdir.mkdir(exist_ok=True)

            # 文件名
            filename = f"{stock_code}_{version}.{self._get_file_extension()}"
            file_path = subdir / filename

            # 保存数据
            if self.format == 'parquet':
                df.to_parquet(file_path, compression='snappy')
            elif self.format == 'hdf5':
                df.to_hdf(file_path, key='data', mode='w', complevel=9)
            elif self.format == 'csv':
                df.to_csv(file_path, encoding='utf-8-sig')
            else:
                raise ValueError(f"不支持的格式: {self.format}")

            # 更新元数据
            if stock_code not in self.metadata['stocks']:
                self.metadata['stocks'][stock_code] = {}

            self.metadata['stocks'][stock_code][feature_type] = {
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

            self._save_metadata()

            logger.info(f"已保存 {stock_code} 的 {feature_type} 特征 (版本: {version})")
            logger.debug(f"文件: {file_path}, 大小: {len(df)} 行 × {len(df.columns)} 列")

            return True

        except Exception as e:
            logger.error(f"保存特征失败: {e}")
            return False

    def _get_file_extension(self) -> str:
        """获取文件扩展名"""
        extensions = {
            'parquet': 'parquet',
            'hdf5': 'h5',
            'csv': 'csv'
        }
        return extensions.get(self.format, 'parquet')

    # ==================== 特征加载 ====================

    def load_features(
        self,
        stock_code: str,
        feature_type: str = 'transformed',
        version: str = None
    ) -> Optional[pd.DataFrame]:
        """
        加载特征数据

        参数:
            stock_code: 股票代码
            feature_type: 特征类型
            version: 版本号（None表示最新版本）

        返回:
            特征DataFrame，如果不存在返回None
        """
        try:
            # 查找文件
            if version is None:
                # 使用元数据中的版本
                if (stock_code in self.metadata['stocks'] and
                    feature_type in self.metadata['stocks'][stock_code]):
                    version = self.metadata['stocks'][stock_code][feature_type]['version']
                else:
                    logger.warning(f"找不到 {stock_code} 的 {feature_type} 特征")
                    return None

            # 构建文件路径
            subdir = self.storage_dir / feature_type
            filename = f"{stock_code}_{version}.{self._get_file_extension()}"
            file_path = subdir / filename

            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                return None

            # 加载数据
            if self.format == 'parquet':
                df = pd.read_parquet(file_path)
            elif self.format == 'hdf5':
                df = pd.read_hdf(file_path, key='data')
            elif self.format == 'csv':
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            else:
                raise ValueError(f"不支持的格式: {self.format}")

            logger.info(f"已加载 {stock_code} 的 {feature_type} 特征 (版本: {version})")
            logger.debug(f"大小: {len(df)} 行 × {len(df.columns)} 列")

            return df

        except Exception as e:
            logger.error(f"加载特征失败: {e}")
            return None

    def load_multiple_stocks(
        self,
        stock_codes: list,
        feature_type: str = 'transformed',
        version: str = None
    ) -> Dict[str, pd.DataFrame]:
        """
        批量加载多只股票的特征

        参数:
            stock_codes: 股票代码列表
            feature_type: 特征类型
            version: 版本号

        返回:
            {股票代码: 特征DataFrame} 字典
        """
        features_dict = {}

        for stock_code in stock_codes:
            df = self.load_features(stock_code, feature_type, version)
            if df is not None:
                features_dict[stock_code] = df

        logger.info(f"批量加载完成: {len(features_dict)}/{len(stock_codes)} 只股票")

        return features_dict

    # ==================== Scaler管理 ====================

    def save_scaler(
        self,
        scaler: object,
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

            logger.info(f"已保存 Scaler: {scaler_name} (版本: {version})")

            return True

        except Exception as e:
            logger.error(f"保存 Scaler 失败: {e}")
            return False

    def load_scaler(
        self,
        scaler_name: str,
        version: str = 'v1'
    ) -> Optional[object]:
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
                logger.warning(f"Scaler文件不存在: {file_path}")
                return None

            with open(file_path, 'rb') as f:
                scaler = pickle.load(f)

            logger.info(f"已加载 Scaler: {scaler_name} (版本: {version})")

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

    def get_stock_info(self, stock_code: str) -> Optional[dict]:
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
        """
        try:
            if mode == 'replace':
                # 直接替换
                version = self._get_next_version(stock_code, feature_type)
                return self.save_features(new_df, stock_code, feature_type, version)

            elif mode == 'append':
                # 加载旧数据
                old_df = self.load_features(stock_code, feature_type)

                if old_df is None:
                    # 没有旧数据，直接保存
                    return self.save_features(new_df, stock_code, feature_type, 'v1')

                # 合并数据（去重）
                combined_df = pd.concat([old_df, new_df])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                combined_df = combined_df.sort_index()

                # 保存新版本
                version = self._get_next_version(stock_code, feature_type)
                return self.save_features(combined_df, stock_code, feature_type, version)

            else:
                raise ValueError(f"不支持的更新模式: {mode}")

        except Exception as e:
            logger.error(f"更新特征失败: {e}")
            return False

    def _get_next_version(self, stock_code: str, feature_type: str) -> str:
        """获取下一个版本号"""
        if (stock_code in self.metadata['stocks'] and
            feature_type in self.metadata['stocks'][stock_code]):
            current_version = self.metadata['stocks'][stock_code][feature_type]['version']
            # 提取版本号数字
            version_num = int(current_version.replace('v', ''))
            return f"v{version_num + 1}"
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

            else:
                # 删除指定类型
                if feature_type not in self.metadata['stocks'][stock_code]:
                    logger.warning(f"特征类型 {feature_type} 不存在")
                    return False

                self._delete_feature_file(stock_code, feature_type, version)
                del self.metadata['stocks'][stock_code][feature_type]

            self._save_metadata()
            logger.info(f"已删除 {stock_code} 的特征")

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

        subdir = self.storage_dir / feature_type
        filename = f"{stock_code}_{version}.{self._get_file_extension()}"
        file_path = subdir / filename

        if file_path.exists():
            file_path.unlink()

    # ==================== 统计信息 ====================

    def get_statistics(self) -> dict:
        """获取存储统计信息"""
        stats = {
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

        # 计算存储大小
        for subdir in self.storage_dir.iterdir():
            if subdir.is_dir():
                for file in subdir.glob('*'):
                    if file.is_file():
                        stats['storage_size'] += file.stat().st_size

        stats['storage_size_mb'] = stats['storage_size'] / (1024 * 1024)

        return stats

    def print_statistics(self):
        """打印存储统计信息"""
        stats = self.get_statistics()

        logger.info("=" * 60)
        logger.info("特征存储统计信息")
        logger.info("=" * 60)
        logger.info(f"存储目录:       {self.storage_dir}")
        logger.info(f"存储格式:       {self.format}")
        logger.info(f"股票总数:       {stats['total_stocks']}")
        logger.info(f"存储大小:       {stats['storage_size_mb']:.2f} MB")

        if stats['feature_types']:
            logger.info("\n特征类型分布:")
            for ftype, count in stats['feature_types'].items():
                logger.info(f"  {ftype:15s}: {count:4d} 只股票")

        logger.info("=" * 60)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("特征存储管理器测试\n")

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    test_df = pd.DataFrame({
        'close': np.random.uniform(10, 20, 100),
        'MA5': np.random.uniform(10, 20, 100),
        'MA20': np.random.uniform(10, 20, 100),
        'RSI14': np.random.uniform(30, 70, 100),
        'MACD': np.random.uniform(-1, 1, 100)
    }, index=dates)

    # 初始化存储管理器
    storage = FeatureStorage(storage_dir='data/features_test', format='parquet')

    print("1. 保存特征")
    storage.save_features(
        test_df,
        stock_code='000001',
        feature_type='technical',
        version='v1',
        metadata={'description': '测试特征'}
    )

    print("\n2. 加载特征")
    loaded_df = storage.load_features('000001', feature_type='technical')
    print(loaded_df.head())

    print("\n3. 列出所有股票")
    stocks = storage.list_stocks(feature_type='technical')
    print(f"股票列表: {stocks}")

    print("\n4. 获取特征列名")
    columns = storage.get_feature_columns('000001', feature_type='technical')
    print(f"特征列: {columns}")

    print("\n5. 统计信息")
    storage.print_statistics()

    print("✓ 特征存储管理器测试完成")
