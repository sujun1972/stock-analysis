"""
数据流水线编排器 (DataPipeline Orchestrator) - 重构优化版

将数据处理流程拆分为多个专职类，DataPipeline作为编排器协调各组件工作
这个设计遵循单一职责原则(SRP)，提高了代码的可维护性和可测试性

重构改进：
1. 提取配置处理逻辑到 _resolve_config 方法，减少重复代码
2. 集中管理特征配置常量，避免硬编码
3. 改进错误处理和数据验证
4. 统一日志记录方式
5. 完善类型注解
6. 优化缓存配置构建逻辑
"""

import pandas as pd
from typing import Optional, Tuple, List, Union, Dict, Any

from src.database.db_manager import DatabaseManager, get_database
from src.data_pipeline.data_loader import DataLoader
from src.data_pipeline.feature_engineer import FeatureEngineer
from src.data_pipeline.data_cleaner import DataCleaner
from src.data_pipeline.data_splitter import DataSplitter
from src.data_pipeline.feature_cache import FeatureCache
from src.data_pipeline.pipeline_config import (
    PipelineConfig,
    DEFAULT_CONFIG,
    BALANCED_TRAINING_CONFIG,
    QUICK_TRAINING_CONFIG,
    LONG_TERM_CONFIG,
    PRODUCTION_CONFIG,
    create_config
)
from src.utils.logger import get_logger
from src.utils.decorators import timer, validate_args
from src.exceptions import PipelineError, DataValidationError

logger = get_logger(__name__)


# ==================== 特征配置常量 ====================

FEATURE_CONFIG = {
    'deprice_ma_periods': [5, 10, 20, 60, 120, 250],
    'deprice_ema_periods': [12, 26, 50],
    'deprice_atr_periods': [14, 28],
}
"""特征计算配置（集中管理，避免硬编码）"""


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

    # 特征版本号（修改版本号以强制重新计算特征）
    # v2.2: 修复目标变量计算公式，避免数据泄露
    #       使用 (close.shift(-N) / close - 1) 替代错误的 pct_change(N).shift(-N)
    FEATURE_VERSION = "v2.2"

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
        self.feature_names: List[str] = []
        self.target_name: Optional[str] = None

    def _resolve_config(
        self,
        config: Optional[PipelineConfig],
        **legacy_params: Any
    ) -> PipelineConfig:
        """
        解析配置参数（支持向后兼容）

        Args:
            config: 新式配置对象
            **legacy_params: 旧式参数（向后兼容）

        Returns:
            解析后的配置对象
        """
        # 如果没有提供配置，从旧参数创建
        if config is None:
            # 提取旧参数并设置默认值
            return PipelineConfig(
                target_period=legacy_params.get('target_period') or self.target_periods[0],
                train_ratio=legacy_params.get('train_ratio') or 0.7,
                valid_ratio=legacy_params.get('valid_ratio') or 0.15,
                balance_samples=legacy_params.get('balance_samples') or False,
                balance_method=legacy_params.get('balance_method') or 'none',
                balance_threshold=legacy_params.get('balance_threshold') or 0.0,
                scale_features=legacy_params.get('scale_features', True),
                use_cache=legacy_params.get('use_cache', True),
                force_refresh=legacy_params.get('force_refresh') or False,
                scaler_type=legacy_params.get('scaler_type') or self.scaler_type
            )

        # 如果提供了配置，检查是否有旧参数覆盖
        overrides = {}
        param_mapping = {
            'target_period': 'target_period',
            'train_ratio': 'train_ratio',
            'valid_ratio': 'valid_ratio',
            'use_cache': 'use_cache',
            'force_refresh': 'force_refresh',
            'scale_features': 'scale_features',
            'balance_samples': 'balance_samples',
            'balance_method': 'balance_method',
            'balance_threshold': 'balance_threshold'
        }

        for legacy_key, config_key in param_mapping.items():
            if legacy_key in legacy_params and legacy_params[legacy_key] is not None:
                overrides[config_key] = legacy_params[legacy_key]

        # 如果有覆盖参数，创建新配置
        if overrides:
            return config.copy(**overrides)

        return config

    def _build_cache_config(self, config: PipelineConfig) -> Dict[str, Any]:
        """
        构建缓存配置字典

        Args:
            config: 流水线配置对象

        Returns:
            缓存配置字典
        """
        feature_config = {
            'version': self.FEATURE_VERSION,
            'target_period': config.target_period,
            'scaler_type': config.scaler_type,
            **FEATURE_CONFIG  # 使用集中管理的特征配置
        }

        return {
            'scaler_type': config.scaler_type,
            'target_period': config.target_period,
            'train_ratio': round(config.train_ratio, 3),
            'valid_ratio': round(config.valid_ratio, 3),
            'balance_samples': config.balance_samples,
            'balance_method': config.balance_method if config.balance_samples else 'none',
            'feature_config_hash': self.feature_cache.compute_feature_config_hash(feature_config)
        }

    def _validate_data(self, X: pd.DataFrame, y: pd.Series, context: str) -> None:
        """
        验证数据有效性

        Args:
            X: 特征DataFrame
            y: 目标Series
            context: 上下文信息（用于错误消息）

        Raises:
            DataValidationError: 数据验证失败
        """
        if X.empty or y.empty:
            raise DataValidationError(f"{context}: 数据为空")

        if len(X) != len(y):
            raise DataValidationError(
                f"{context}: 特征和目标长度不匹配 (X={len(X)}, y={len(y)})"
            )

        if X.isnull().any().any():
            null_counts = X.isnull().sum()
            null_cols = null_counts[null_counts > 0]
            raise DataValidationError(
                f"{context}: 特征中存在空值\n{null_cols}"
            )

        if y.isnull().any():
            raise DataValidationError(f"{context}: 目标中存在空值 ({y.isnull().sum()} 个)")

    def _log_pipeline_start(self, symbol: str, start_date: str, end_date: str, config: PipelineConfig) -> None:
        """记录流水线开始日志"""
        self._log(f"\n{'='*60}")
        self._log(f"数据流水线: {symbol} ({start_date} ~ {end_date})")
        self._log(f"配置: target_period={config.target_period}, balance={config.balance_samples}")
        self._log(f"{'='*60}")

    def _log_pipeline_end(self, X: pd.DataFrame) -> None:
        """记录流水线结束日志"""
        self._log(f"\n{'='*60}")
        self._log(f"数据准备完成: {len(X)} 样本, {len(X.columns)} 特征")
        self._log(f"{'='*60}\n")

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
        config: Optional[PipelineConfig] = None,
        # 向后兼容的参数（已废弃，建议使用 config）
        target_period: Optional[int] = None,
        use_cache: Optional[bool] = None,
        force_refresh: Optional[bool] = None,
        _train_ratio: Optional[float] = None,
        _valid_ratio: Optional[float] = None,
        _balance_samples: Optional[bool] = None,
        _balance_method: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        获取训练数据（自动化流转）

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            config: 流水线配置对象（推荐使用）

            # 以下参数已废弃，建议使用 config 对象
            target_period: 预测周期（废弃，请使用 config.target_period）
            use_cache: 是否使用缓存（废弃，请使用 config.use_cache）
            force_refresh: 强制刷新缓存（废弃，请使用 config.force_refresh）
            _train_ratio: 训练集比例（废弃，请使用 config.train_ratio）
            _valid_ratio: 验证集比例（废弃，请使用 config.valid_ratio）
            _balance_samples: 是否平衡样本（废弃，请使用 config.balance_samples）
            _balance_method: 平衡方法（废弃，请使用 config.balance_method）

        Returns:
            (特征DataFrame, 目标Series)

        Raises:
            PipelineError: 流水线执行失败
            DataValidationError: 数据验证失败

        Example:
            >>> # 推荐用法
            >>> config = PipelineConfig(target_period=5, balance_samples=True)
            >>> X, y = pipeline.get_training_data('000001', '20200101', '20231231', config)
            >>>
            >>> # 或使用默认配置
            >>> X, y = pipeline.get_training_data('000001', '20200101', '20231231')
        """
        try:
            # 使用辅助方法解析配置（支持向后兼容）
            config = self._resolve_config(
                config,
                target_period=target_period,
                train_ratio=_train_ratio,
                valid_ratio=_valid_ratio,
                balance_samples=_balance_samples,
                balance_method=_balance_method,
                use_cache=use_cache,
                force_refresh=force_refresh
            )

            self._log_pipeline_start(symbol, start_date, end_date, config)

            # 确定目标名称
            self.target_name = f'target_{config.target_period}d_return'

            # 1. 检查缓存
            cache_config = self._build_cache_config(config)
            cache_file = self.feature_cache.get_cache_path(symbol, start_date, end_date, cache_config)

            if config.use_cache and not config.force_refresh and self.cache_features:
                self._log("\n✓ 尝试从缓存加载数据...")
                cached_data = self.feature_cache.load(cache_file, self.target_name, cache_config)
                if cached_data is not None:
                    self._log("  ✓ 缓存验证通过，使用缓存数据")
                    X, y = cached_data
                    self.feature_names = X.columns.tolist()
                    self._validate_data(X, y, "缓存数据")
                    return X, y
                else:
                    self._log("  ⚠️  缓存验证失败，重新计算特征")

            # 2. 加载原始数据
            self._log("\n[1/5] 加载原始数据...")
            df = self.data_loader.load_data(symbol, start_date, end_date)
            if df.empty:
                raise PipelineError(f"未能加载数据: {symbol} ({start_date} ~ {end_date})")

            # 3. 特征工程（技术指标、Alpha因子、特征转换、目标标签）
            self._log("\n[2/5] 特征工程...")
            df = self.feature_engineer.compute_all_features(df, config.target_period)

            # 4. 数据清洗
            self._log("\n[3/5] 数据清洗...")
            df = self.data_cleaner.clean(df, self.target_name)

            # 5. 分离特征和目标
            self._log("\n[4/5] 分离特征和目标...")
            X, y = self._separate_features_target(df)

            # 6. 验证数据
            self._validate_data(X, y, "处理后的数据")

            # 7. 缓存结果
            if self.cache_features:
                self._log("\n[5/5] 缓存特征...")
                self.feature_cache.save(X, y, cache_file, cache_config, self.target_name)

            self._log_pipeline_end(X)
            logger.info(f"训练数据准备完成: {symbol}, {len(X)} 样本, {len(X.columns)} 特征")

            return X, y

        except Exception as e:
            error_msg = f"数据流水线执行失败: {symbol} ({start_date} ~ {end_date}): {str(e)}"
            logger.error(error_msg)
            raise PipelineError(error_msg) from e

    @timer
    def prepare_for_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        config: Optional[PipelineConfig] = None,
        fit_scaler: bool = True,
        # 向后兼容的参数（已废弃）
        train_ratio: Optional[float] = None,
        valid_ratio: Optional[float] = None,
        scale_features: Optional[bool] = None,
        balance_samples: Optional[bool] = None,
        balance_method: Optional[str] = None,
        balance_threshold: Optional[float] = None
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """
        为模型准备数据（缩放、平衡、分割）

        Args:
            X: 特征DataFrame
            y: 目标Series
            config: 流水线配置对象（推荐使用）
            fit_scaler: 是否拟合scaler（True=训练模式，False=推理模式）

            # 以下参数已废弃，建议使用 config 对象
            train_ratio: 训练集比例（废弃）
            valid_ratio: 验证集比例（废弃）
            scale_features: 是否缩放特征（废弃）
            balance_samples: 是否平衡样本（废弃）
            balance_method: 平衡方法（废弃）
            balance_threshold: 分类阈值（废弃）

        Returns:
            (X_train, y_train, X_valid, y_valid, X_test, y_test)

        Raises:
            PipelineError: 数据准备失败
            DataValidationError: 数据验证失败

        Example:
            >>> # 推荐用法
            >>> config = PipelineConfig(balance_samples=True, balance_method='smote')
            >>> result = pipeline.prepare_for_model(X, y, config)
        """
        try:
            # 验证输入数据
            self._validate_data(X, y, "输入数据")

            # 使用辅助方法解析配置（支持向后兼容）
            config = self._resolve_config(
                config,
                train_ratio=train_ratio,
                valid_ratio=valid_ratio,
                scale_features=scale_features,
                balance_samples=balance_samples,
                balance_method=balance_method,
                balance_threshold=balance_threshold
            )

            self._log(f"\n{'='*60}")
            self._log("为模型准备数据...")
            self._log(f"配置: scale={config.scale_features}, balance={config.balance_samples}")
            self._log(f"{'='*60}")

            # 使用 DataSplitter 完成所有预处理
            result = self.data_splitter.split_and_prepare(
                X, y,
                train_ratio=config.train_ratio,
                valid_ratio=config.valid_ratio,
                scale_features=config.scale_features,
                balance_samples=config.balance_samples,
                balance_method=config.balance_method,
                balance_threshold=config.balance_threshold,
                fit_scaler=fit_scaler
            )

            logger.info(f"模型数据准备完成: 训练={len(result[0])}, 验证={len(result[2])}, 测试={len(result[4])}")

            return result

        except Exception as e:
            error_msg = f"模型数据准备失败: {str(e)}"
            logger.error(error_msg)
            raise PipelineError(error_msg) from e

    def _separate_features_target(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        分离特征和目标

        Args:
            df: 包含特征和目标的DataFrame

        Returns:
            (特征DataFrame, 目标Series)
        """
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

        self._log(f"  特征数量: {len(feature_cols)}")
        self._log(f"  目标变量: {self.target_name}")

        return X, y

    # ==================== 工具方法 ====================

    def get_feature_names(self) -> List[str]:
        """获取特征名列表"""
        return self.feature_names.copy()

    def get_scaler(self) -> Optional[object]:
        """获取scaler对象（用于保存和加载）"""
        return self.data_splitter.get_scaler()

    def set_scaler(self, scaler: object) -> None:
        """设置scaler对象（从保存的模型加载）"""
        self.data_splitter.set_scaler(scaler)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.data_cleaner.get_stats()

    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        清除缓存

        Args:
            symbol: 股票代码（None则清除所有）
        """
        self.feature_cache.clear(symbol)
        logger.info(f"缓存已清除: {symbol or '全部'}")

    def _log(self, message: str) -> None:
        """输出日志"""
        if self.verbose:
            logger.info(message)


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
    config: Optional[PipelineConfig] = None,
    # 向后兼容的参数（已废弃）
    target_period: int = 5,
    train_ratio: float = 0.7,
    valid_ratio: float = 0.15,
    scale_features: bool = True,
    balance_samples: bool = False,
    balance_method: str = 'undersample',
    scaler_type: str = 'robust'
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, DataPipeline]:
    """
    便捷函数：一键获取完整训练数据（从数据库到模型就绪）

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        config: 流水线配置对象（推荐使用）

        # 以下参数已废弃，建议使用 config 对象
        target_period: 预测周期（废弃）
        train_ratio: 训练集比例（废弃）
        valid_ratio: 验证集比例（废弃）
        scale_features: 是否缩放特征（废弃）
        balance_samples: 是否平衡样本（废弃）
        balance_method: 平衡方法（废弃）
        scaler_type: 缩放类型（废弃）

    Returns:
        (X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline)

    Example:
        >>> # 推荐用法
        >>> from data_pipeline.pipeline_config import BALANCED_TRAINING_CONFIG
        >>> result = get_full_training_data('000001', '20200101', '20231231', BALANCED_TRAINING_CONFIG)
        >>>
        >>> # 或自定义配置
        >>> config = PipelineConfig(target_period=10, balance_samples=True)
        >>> result = get_full_training_data('000001', '20200101', '20231231', config)
    """
    # 处理配置参数（支持向后兼容）
    if config is None:
        config = PipelineConfig(
            target_period=target_period,
            train_ratio=train_ratio,
            valid_ratio=valid_ratio,
            scale_features=scale_features,
            balance_samples=balance_samples,
            balance_method=balance_method,
            scaler_type=scaler_type
        )

    # 创建流水线
    pipeline = DataPipeline(
        target_periods=config.target_period,
        scaler_type=config.scaler_type,
        verbose=True
    )

    # 获取数据
    X, y = pipeline.get_training_data(symbol, start_date, end_date, config)

    # 准备数据
    X_train, y_train, X_valid, y_valid, X_test, y_test = pipeline.prepare_for_model(X, y, config)

    return X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline


# ==================== 向后兼容导出 ====================

__all__ = [
    'DataPipeline',
    'PipelineConfig',
    'DEFAULT_CONFIG',
    'BALANCED_TRAINING_CONFIG',
    'QUICK_TRAINING_CONFIG',
    'LONG_TERM_CONFIG',
    'PRODUCTION_CONFIG',
    'create_pipeline',
    'get_full_training_data',
    'create_config',
    'FEATURE_CONFIG'
]
