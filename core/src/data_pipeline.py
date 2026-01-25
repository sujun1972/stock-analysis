"""
数据流水线编排器 (DataPipeline Orchestrator)

将数据处理流程拆分为多个专职类，DataPipeline作为编排器协调各组件工作
这个设计遵循单一职责原则(SRP)，提高了代码的可维护性和可测试性
"""

import pandas as pd
from typing import Optional, Tuple, List, Union, Dict
from pathlib import Path

from database.db_manager import DatabaseManager, get_database
from data_pipeline.data_loader import DataLoader
from data_pipeline.feature_engineer import FeatureEngineer
from data_pipeline.data_cleaner import DataCleaner
from data_pipeline.data_splitter import DataSplitter
from data_pipeline.feature_cache import FeatureCache
from utils.logger import get_logger
from utils.decorators import timer, validate_args

logger = get_logger(__name__)


class DataPipeline:
    """
    数据流水线编排器

    职责：
    - 编排各数据处理组件
    - 管理流程配置
    - 提供统一的API接口

    组件：
    - DataLoader: 加载原始数据
    - FeatureEngineer: 特征工程
    - DataCleaner: 数据清洗
    - DataSplitter: 数据分割和预处理
    - FeatureCache: 缓存管理
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        target_periods: Union[int, List[int]] = 5,
        scaler_type: str = 'robust',
        cache_features: bool = True,
        cache_dir: str = 'data/pipeline_cache',
        verbose: bool = True
    ):
        """
        初始化数据流水线

        Args:
            db_manager: 数据库管理器实例（None则使用全局单例）
            target_periods: 预测周期（天数），支持单个或多个
            scaler_type: 特征缩放类型 ('standard', 'robust', 'minmax')
            cache_features: 是否缓存计算好的特征
            cache_dir: 缓存目录
            verbose: 是否输出详细日志
        """
        # 配置参数
        self.target_periods = [target_periods] if isinstance(target_periods, int) else target_periods
        self.scaler_type = scaler_type
        self.cache_features = cache_features
        self.verbose = verbose

        # 特征版本号
        self.FEATURE_VERSION = "v2.1"

        # 初始化各组件
        self.data_loader = DataLoader(db_manager or get_database())
        self.feature_engineer = FeatureEngineer(verbose=verbose)
        self.data_cleaner = DataCleaner(verbose=verbose)
        self.data_splitter = DataSplitter(scaler_type=scaler_type, verbose=verbose)
        self.feature_cache = FeatureCache(
            cache_dir=cache_dir,
            feature_version=self.FEATURE_VERSION
        )

        # 状态
        self.feature_names = []
        self.target_name = None

    @timer
    @validate_args(
        symbol=lambda x: isinstance(x, str) and len(x) > 0,
        start_date=lambda x: isinstance(x, str) and len(x) == 8,
        end_date=lambda x: isinstance(x, str) and len(x) == 8
    )
    def get_training_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        target_period: Optional[int] = None,
        use_cache: bool = True,
        force_refresh: bool = False,
        # 缓存键所需参数
        _train_ratio: float = 0.7,
        _valid_ratio: float = 0.15,
        _balance_samples: bool = False,
        _balance_method: str = 'none'
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        获取训练数据（自动化流转）

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            target_period: 预测周期（None则使用初始化时的第一个周期）
            use_cache: 是否使用缓存
            force_refresh: 强制刷新缓存
            _train_ratio: 训练集比例（影响缓存键）
            _valid_ratio: 验证集比例（影响缓存键）
            _balance_samples: 是否平衡样本（影响缓存键）
            _balance_method: 平衡方法（影响缓存键）

        Returns:
            (特征DataFrame, 目标Series)
        """
        self.log(f"\n{'='*60}")
        self.log(f"数据流水线: {symbol} ({start_date} ~ {end_date})")
        self.log(f"{'='*60}")

        # 确定目标周期
        target_period = target_period or self.target_periods[0]
        self.target_name = f'target_{target_period}d_return'

        # 1. 检查缓存
        cache_config = self._build_cache_config(
            target_period, _train_ratio, _valid_ratio, _balance_samples, _balance_method
        )
        cache_file = self.feature_cache.get_cache_path(symbol, start_date, end_date, cache_config)

        if use_cache and not force_refresh and self.cache_features:
            self.log("\n✓ 尝试从缓存加载数据...")
            cached_data = self.feature_cache.load(cache_file, self.target_name, cache_config)
            if cached_data is not None:
                self.log("  ✓ 缓存验证通过，使用缓存数据")
                X, y = cached_data
                self.feature_names = X.columns.tolist()
                return X, y
            else:
                self.log("  ⚠️  缓存验证失败，重新计算特征")

        # 2. 加载原始数据
        self.log("\n[1/5] 加载原始数据...")
        df = self.data_loader.load_data(symbol, start_date, end_date)

        # 3. 特征工程（技术指标、Alpha因子、特征转换、目标标签）
        self.log("\n[2/5] 特征工程...")
        df = self.feature_engineer.compute_all_features(df, target_period)

        # 4. 数据清洗
        self.log("\n[3/5] 数据清洗...")
        df = self.data_cleaner.clean(df, self.target_name)

        # 5. 分离特征和目标
        self.log("\n[4/5] 分离特征和目标...")
        X, y = self._separate_features_target(df)

        # 6. 缓存结果
        if self.cache_features:
            self.log("\n[5/5] 缓存特征...")
            self.feature_cache.save(X, y, cache_file, cache_config, self.target_name)

        self.log(f"\n{'='*60}")
        self.log(f"数据准备完成: {len(X)} 样本, {len(X.columns)} 特征")
        self.log(f"{'='*60}\n")

        logger.info(f"训练数据准备完成: {symbol}, {len(X)} 样本, {len(X.columns)} 特征")

        return X, y

    @timer
    def prepare_for_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        train_ratio: float = 0.7,
        valid_ratio: float = 0.15,
        scale_features: bool = True,
        balance_samples: bool = False,
        balance_method: str = 'undersample',
        balance_threshold: float = 0.0,
        fit_scaler: bool = True
    ) -> Tuple:
        """
        为模型准备数据（缩放、平衡、分割）

        Args:
            X: 特征DataFrame
            y: 目标Series
            train_ratio: 训练集比例
            valid_ratio: 验证集比例
            scale_features: 是否缩放特征
            balance_samples: 是否平衡样本
            balance_method: 平衡方法 ('oversample', 'undersample', 'smote')
            balance_threshold: 分类阈值（收益率>threshold为涨）
            fit_scaler: 是否拟合scaler（True=训练模式，False=推理模式）

        Returns:
            (X_train, y_train, X_valid, y_valid, X_test, y_test)
        """
        self.log(f"\n{'='*60}")
        self.log("为模型准备数据...")
        self.log(f"{'='*60}")

        # 使用 DataSplitter 完成所有预处理
        result = self.data_splitter.split_and_prepare(
            X, y,
            train_ratio=train_ratio,
            valid_ratio=valid_ratio,
            scale_features=scale_features,
            balance_samples=balance_samples,
            balance_method=balance_method,
            balance_threshold=balance_threshold,
            fit_scaler=fit_scaler
        )

        logger.info(f"模型数据准备完成: 训练={len(result[0])}, 验证={len(result[2])}, 测试={len(result[4])}")

        return result

    def _separate_features_target(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """分离特征和目标"""
        # 排除的列（原始价格、成交量等）
        exclude_cols = [
            'open', 'high', 'low', 'close', 'volume', 'amount',
            self.target_name
        ]

        # 特征列
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        self.feature_names = feature_cols

        X = df[feature_cols].copy()
        y = df[self.target_name].copy()

        self.log(f"  特征数量: {len(feature_cols)}")
        self.log(f"  目标变量: {self.target_name}")

        return X, y

    def _build_cache_config(
        self,
        target_period: int,
        train_ratio: float,
        valid_ratio: float,
        balance_samples: bool,
        balance_method: str
    ) -> Dict:
        """构建缓存配置字典"""
        feature_config = {
            'version': self.FEATURE_VERSION,
            'target_period': target_period,
            'scaler_type': self.scaler_type,
            'deprice_ma_periods': [5, 10, 20, 60, 120, 250],
            'deprice_ema_periods': [12, 26, 50],
            'deprice_atr_periods': [14, 28],
        }

        return {
            'scaler_type': self.scaler_type,
            'target_period': target_period,
            'train_ratio': round(train_ratio, 3),
            'valid_ratio': round(valid_ratio, 3),
            'balance_samples': balance_samples,
            'balance_method': balance_method if balance_samples else 'none',
            'feature_config_hash': self.feature_cache.compute_feature_config_hash(feature_config)
        }

    # ==================== 工具方法 ====================

    def get_feature_names(self) -> List[str]:
        """获取特征名列表"""
        return self.feature_names.copy()

    def get_scaler(self) -> Optional[object]:
        """获取scaler对象（用于保存和加载）"""
        return self.data_splitter.get_scaler()

    def set_scaler(self, scaler: object):
        """设置scaler对象（从保存的模型加载）"""
        self.data_splitter.set_scaler(scaler)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.data_cleaner.get_stats()

    def clear_cache(self, symbol: Optional[str] = None):
        """
        清除缓存

        Args:
            symbol: 股票代码（None则清除所有）
        """
        self.feature_cache.clear(symbol)

    def log(self, message: str):
        """输出日志"""
        if self.verbose:
            print(message)


# ==================== 便捷函数 ====================

def create_pipeline(
    target_period: int = 5,
    scaler_type: str = 'robust',
    verbose: bool = True
) -> DataPipeline:
    """
    便捷函数：创建数据流水线

    Args:
        target_period: 预测周期（天数）
        scaler_type: 缩放类型
        verbose: 是否输出日志

    Returns:
        DataPipeline实例
    """
    return DataPipeline(
        target_periods=target_period,
        scaler_type=scaler_type,
        verbose=verbose
    )


def get_full_training_data(
    symbol: str,
    start_date: str,
    end_date: str,
    target_period: int = 5,
    train_ratio: float = 0.7,
    valid_ratio: float = 0.15,
    scale_features: bool = True,
    balance_samples: bool = False,
    balance_method: str = 'undersample',
    scaler_type: str = 'robust'
) -> Tuple:
    """
    便捷函数：一键获取完整训练数据（从数据库到模型就绪）

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        target_period: 预测周期
        train_ratio: 训练集比例
        valid_ratio: 验证集比例
        scale_features: 是否缩放特征
        balance_samples: 是否平衡样本
        balance_method: 平衡方法 ('oversample', 'undersample', 'smote')
        scaler_type: 缩放类型

    Returns:
        (X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline)
    """
    # 创建流水线
    pipeline = DataPipeline(
        target_periods=target_period,
        scaler_type=scaler_type,
        verbose=True
    )

    # 获取数据
    X, y = pipeline.get_training_data(
        symbol, start_date, end_date, target_period,
        _train_ratio=train_ratio,
        _valid_ratio=valid_ratio,
        _balance_samples=balance_samples,
        _balance_method=balance_method if balance_samples else 'none'
    )

    # 准备数据
    X_train, y_train, X_valid, y_valid, X_test, y_test = pipeline.prepare_for_model(
        X, y,
        train_ratio=train_ratio,
        valid_ratio=valid_ratio,
        scale_features=scale_features,
        balance_samples=balance_samples,
        balance_method=balance_method
    )

    return X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline


# ==================== 向后兼容导出 ====================

__all__ = [
    'DataPipeline',
    'create_pipeline',
    'get_full_training_data'
]
