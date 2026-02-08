"""
统一模型训练器（核心模块）
提供统一接口训练和评估不同类型的模型

重构说明 (TD-005):
- 模块化设计: 分离数据准备、训练策略、模型创建逻辑
- 策略模式: 每种模型类型有独立的训练策略
- 工厂模式: 统一的模型创建接口
- 统一日志系统: 使用 loguru 替代 print
- 增强错误处理: 自定义异常类和数据验证
- 配置管理: 使用 ml.TrainingConfig (Phase 2 对齐)

配套模块:
- training_pipeline.py: 端到端训练流程管理
- model_validator.py: 模型验证（交叉验证、稳定性测试）
- hyperparameter_tuner.py: 超参数调优（网格搜索、随机搜索）

Phase 2 更新 (2026-02-08):
- 使用 src.ml.TrainingConfig 替代本地 TrainingConfig
- 添加 ModelTrainerConfig 管理训练器特定参数
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from loguru import logger
import json
import warnings

warnings.filterwarnings('ignore')

# 可选导入 LightGBM（如果未安装则跳过）
try:
    from .lightgbm_model import LightGBMStockModel
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    LightGBMStockModel = None

from .ridge_model import RidgeStockModel
from .model_evaluator import ModelEvaluator

# 导入 ML 模块的 TrainingConfig
from src.ml.trained_model import TrainingConfig


# ==================== 异常类 ====================

# 导入统一异常系统
from src.exceptions import ModelTrainingError as BaseModelTrainingError

class TrainingError(BaseModelTrainingError):
    """训练过程错误基类（迁移到统一异常系统）

    该异常类现在继承自统一异常系统的ModelTrainingError。
    支持错误代码和上下文信息。

    Examples:
        >>> raise TrainingError(
        ...     "模型训练失败",
        ...     error_code="TRAINING_FAILED",
        ...     model_type="LightGBM",
        ...     n_samples=1000,
        ...     n_features=125,
        ...     reason="数据包含NaN值"
        ... )
    """
    pass


class DataPreparationError(TrainingError):
    """数据准备错误（迁移到统一异常系统）

    该异常类继承自TrainingError，用于数据准备阶段的错误。

    Examples:
        >>> raise DataPreparationError(
        ...     "特征列不存在",
        ...     error_code="MISSING_FEATURES",
        ...     required_features=['open', 'high', 'low', 'close'],
        ...     missing_features=['volume']
        ... )
    """
    pass


class ModelCreationError(TrainingError):
    """模型创建错误（迁移到统一异常系统）

    当模型创建或初始化失败时抛出。

    Examples:
        >>> raise ModelCreationError(
        ...     "模型创建失败",
        ...     error_code="MODEL_INIT_ERROR",
        ...     model_type="LightGBM",
        ...     model_params=params,
        ...     reason="参数配置错误"
        ... )
    """
    pass


class InvalidModelTypeError(TrainingError):
    """无效模型类型错误（迁移到统一异常系统）

    当指定的模型类型不被支持时抛出。

    Examples:
        >>> raise InvalidModelTypeError(
        ...     "不支持的模型类型",
        ...     error_code="UNSUPPORTED_MODEL_TYPE",
        ...     requested_type="xgboost",
        ...     supported_types=["lightgbm", "ridge", "gru"]
        ... )
    """
    pass


# ==================== 配置类 ====================

# TrainingConfig 已从 src.ml.trained_model 导入

@dataclass
class DataSplitConfig:
    """数据分割配置"""
    train_ratio: float = 0.7
    valid_ratio: float = 0.15
    remove_nan: bool = True

    def __post_init__(self):
        """验证配置参数"""
        if not 0 < self.train_ratio < 1:
            raise ValueError(f"train_ratio 必须在 (0, 1) 之间，当前值: {self.train_ratio}")
        if not 0 < self.valid_ratio < 1:
            raise ValueError(f"valid_ratio 必须在 (0, 1) 之间，当前值: {self.valid_ratio}")
        if self.train_ratio + self.valid_ratio >= 1.0:
            raise ValueError(
                f"train_ratio + valid_ratio 必须小于 1.0，"
                f"当前值: {self.train_ratio + self.valid_ratio}"
            )


@dataclass
class ModelTrainerConfig:
    """
    模型训练器配置 (训练器特定参数)

    该配置管理训练过程的参数，与 ml.TrainingConfig 配合使用:
    - ml.TrainingConfig: 模型配置 (model_type, hyperparameters, feature_groups, etc.)
    - ModelTrainerConfig: 训练器配置 (output_dir, early_stopping, batch_size, etc.)

    Attributes:
        output_dir: 模型保存目录
        early_stopping_rounds: LightGBM早停轮数
        verbose_eval: LightGBM日志输出频率
        seq_length: GRU序列长度
        batch_size: GRU批次大小
        epochs: GRU训练轮数
        early_stopping_patience: GRU早停耐心值
    """
    output_dir: str = 'data/models/saved'

    # LightGBM 特定参数
    early_stopping_rounds: int = 50
    verbose_eval: int = 50

    # GRU 特定参数
    seq_length: int = 20
    batch_size: int = 64
    epochs: int = 100
    early_stopping_patience: int = 10

    def __post_init__(self):
        """验证配置参数"""
        if self.early_stopping_rounds < 0:
            raise ValueError(f"early_stopping_rounds must be non-negative, got {self.early_stopping_rounds}")
        if self.seq_length <= 0:
            raise ValueError(f"seq_length must be positive, got {self.seq_length}")
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {self.batch_size}")
        if self.epochs <= 0:
            raise ValueError(f"epochs must be positive, got {self.epochs}")



# ==================== 数据准备器 ====================

class DataPreparator:
    """数据准备器: 负责数据验证、清洗和分割"""

    @staticmethod
    def validate_data(
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str
    ) -> None:
        """
        验证数据有效性

        Args:
            df: 数据 DataFrame
            feature_cols: 特征列名列表
            target_col: 目标列名

        Raises:
            DataPreparationError: 数据验证失败
        """
        # 检查 DataFrame 是否为空
        if df is None or len(df) == 0:
            raise DataPreparationError("输入 DataFrame 为空")

        # 检查特征列是否存在
        missing_features = [col for col in feature_cols if col not in df.columns]
        if missing_features:
            raise DataPreparationError(
                f"以下特征列不存在: {missing_features}"
            )

        # 检查目标列是否存在
        if target_col not in df.columns:
            raise DataPreparationError(f"目标列 '{target_col}' 不存在")

        # 检查数据类型
        for col in feature_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise DataPreparationError(f"特征列 '{col}' 不是数值类型")

        if not pd.api.types.is_numeric_dtype(df[target_col]):
            raise DataPreparationError(f"目标列 '{target_col}' 不是数值类型")

        logger.debug(f"数据验证通过: {len(df)} 行 × {len(feature_cols)} 特征")

    @staticmethod
    def prepare_data(
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        config: DataSplitConfig
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """
        准备训练数据

        Args:
            df: 完整数据 DataFrame
            feature_cols: 特征列名列表
            target_col: 目标列名
            config: 数据分割配置

        Returns:
            (X_train, y_train, X_valid, y_valid, X_test, y_test)

        Raises:
            DataPreparationError: 数据准备失败
        """
        logger.info("开始准备数据...")

        # 验证数据
        DataPreparator.validate_data(df, feature_cols, target_col)

        logger.info(f"原始数据: {len(df)} 行 × {len(df.columns)} 列")

        # 提取特征和目标
        X = df[feature_cols].copy()
        y = df[target_col].copy()

        # 移除 NaN
        if config.remove_nan:
            valid_mask = ~(X.isna().any(axis=1) | y.isna())
            X = X[valid_mask]
            y = y[valid_mask]
            logger.info(f"移除 NaN 后: {len(X)} 行")

        # 检查数据量
        if len(X) < 10:
            raise DataPreparationError(f"数据量不足: {len(X)} < 10")

        # 时间序列分割（不打乱顺序）
        n_samples = len(X)
        train_end = int(n_samples * config.train_ratio)
        valid_end = int(n_samples * (config.train_ratio + config.valid_ratio))

        X_train = X.iloc[:train_end]
        y_train = y.iloc[:train_end]

        X_valid = X.iloc[train_end:valid_end]
        y_valid = y.iloc[train_end:valid_end]

        X_test = X.iloc[valid_end:]
        y_test = y.iloc[valid_end:]

        logger.info("\n数据分割:")
        logger.info(f"  训练集: {len(X_train)} 样本 ({len(X_train)/n_samples*100:.1f}%)")
        logger.info(f"  验证集: {len(X_valid)} 样本 ({len(X_valid)/n_samples*100:.1f}%)")
        logger.info(f"  测试集: {len(X_test)} 样本 ({len(X_test)/n_samples*100:.1f}%)")
        logger.info(f"  特征数: {len(feature_cols)}")

        return X_train, y_train, X_valid, y_valid, X_test, y_test


# ==================== 训练策略（策略模式）====================

class TrainingStrategy(ABC):
    """训练策略抽象基类"""

    @abstractmethod
    def create_model(self, model_params: Dict[str, Any]) -> Any:
        """创建模型实例"""
        pass

    @abstractmethod
    def train(
        self,
        model: Any,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame],
        y_valid: Optional[pd.Series],
        trainer_config: ModelTrainerConfig
    ) -> Dict[str, Any]:
        """训练模型"""
        pass

    @abstractmethod
    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        pass


class LightGBMTrainingStrategy(TrainingStrategy):
    """LightGBM 训练策略"""

    def get_default_params(self) -> Dict[str, Any]:
        return {
            'objective': 'regression',
            'metric': 'rmse',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'n_estimators': 500,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'verbose': -1
        }

    def create_model(self, model_params: Dict[str, Any]):
        if not LIGHTGBM_AVAILABLE:
            raise ModelCreationError(
                "LightGBM 模型需要 lightgbm: pip install lightgbm",
                error_code="LIGHTGBM_NOT_INSTALLED"
            )
        params = {**self.get_default_params(), **model_params}
        return LightGBMStockModel(**params)

    def train(
        self,
        model: Any,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame],
        y_valid: Optional[pd.Series],
        trainer_config: ModelTrainerConfig
    ) -> Dict[str, Any]:
        logger.info("训练 LightGBM 模型...")
        history = model.train(
            X_train, y_train,
            X_valid, y_valid,
            early_stopping_rounds=trainer_config.early_stopping_rounds,
            verbose_eval=trainer_config.verbose_eval
        )
        return history


class RidgeTrainingStrategy(TrainingStrategy):
    """Ridge 训练策略"""

    def get_default_params(self) -> Dict[str, Any]:
        return {
            'alpha': 1.0,
            'fit_intercept': True,
            'random_state': 42
        }

    def create_model(self, model_params: Dict[str, Any]) -> RidgeStockModel:
        params = {**self.get_default_params(), **model_params}
        return RidgeStockModel(**params)

    def train(
        self,
        model: RidgeStockModel,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame],
        y_valid: Optional[pd.Series],
        trainer_config: ModelTrainerConfig
    ) -> Dict[str, Any]:
        logger.info("训练 Ridge 模型...")
        history = model.train(X_train, y_train, X_valid, y_valid)
        return history


class GRUTrainingStrategy(TrainingStrategy):
    """GRU 训练策略"""

    def get_default_params(self) -> Dict[str, Any]:
        return {
            'hidden_size': 64,
            'num_layers': 2,
            'dropout': 0.2,
            'learning_rate': 0.001
        }

    def create_model(self, model_params: Dict[str, Any]) -> Any:
        try:
            from .gru_model import GRUStockTrainer
        except ImportError:
            raise ModelCreationError("GRU 模型需要 PyTorch: pip install torch")

        if 'input_size' not in model_params:
            raise ModelCreationError("GRU 模型缺少必需参数 'input_size'")

        params = {**self.get_default_params(), **model_params}
        return GRUStockTrainer(**params)

    def train(
        self,
        model: Any,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame],
        y_valid: Optional[pd.Series],
        trainer_config: ModelTrainerConfig
    ) -> Dict[str, Any]:
        logger.info("训练 GRU 模型...")
        history = model.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=trainer_config.seq_length,
            batch_size=trainer_config.batch_size,
            epochs=trainer_config.epochs,
            early_stopping_patience=trainer_config.early_stopping_patience
        )
        return history


# ==================== 策略工厂 ====================

class StrategyFactory:
    """训练策略工厂"""

    _strategies = {
        'lightgbm': LightGBMTrainingStrategy,
        'ridge': RidgeTrainingStrategy,
        'gru': GRUTrainingStrategy
    }

    @classmethod
    def create_strategy(cls, model_type: str) -> TrainingStrategy:
        """创建训练策略"""
        if model_type not in cls._strategies:
            raise InvalidModelTypeError(
                f"不支持的模型类型: {model_type}，"
                f"支持的类型: {list(cls._strategies.keys())}"
            )
        strategy_class = cls._strategies[model_type]
        return strategy_class()

    @classmethod
    def register_strategy(cls, model_type: str, strategy_class: type) -> None:
        """注册新的训练策略"""
        cls._strategies[model_type] = strategy_class
        logger.info(f"注册训练策略: {model_type} -> {strategy_class.__name__}")


# ==================== 模型评估辅助类 ====================

class ModelEvaluationHelper:
    """模型评估辅助类: 处理不同模型类型的评估逻辑"""

    @staticmethod
    def evaluate_model(
        model: Any,
        model_type: str,
        X: pd.DataFrame,
        y: pd.Series,
        evaluator: ModelEvaluator,
        seq_length: Optional[int] = None,
        dataset_name: str = 'test',
        verbose: bool = True
    ) -> Dict[str, float]:
        """评估模型（处理不同模型类型的差异）"""
        logger.info(f"评估 {dataset_name} 集...")

        # 预测
        predictions = model.predict(X)

        # 对齐标签（处理 GRU 模型的特殊情况）
        if model_type == 'gru':
            if seq_length is None:
                raise ValueError("GRU 模型评估需要提供 seq_length 参数")
            y_actual = y.values[seq_length:]
            if len(predictions) != len(y_actual):
                raise ValueError(
                    f"GRU 预测结果与标签形状不匹配: "
                    f"predictions={len(predictions)}, y_actual={len(y_actual)}"
                )
        else:
            y_actual = y.values

        # 计算评估指标
        metrics = evaluator.evaluate_regression(
            predictions,
            y_actual,
            verbose=verbose
        )
        return metrics


# ==================== 主训练器 ====================

class ModelTrainer:
    """
    统一模型训练器

    重构后的主训练器作为协调者，使用策略模式处理不同模型的训练逻辑

    Phase 2 更新:
    - 使用 ml.TrainingConfig (模型配置)
    - 使用 ModelTrainerConfig (训练器配置)
    """

    def __init__(
        self,
        training_config: Optional[TrainingConfig] = None,
        trainer_config: Optional[ModelTrainerConfig] = None
    ):
        """
        初始化训练器

        Args:
            training_config: ML训练配置 (来自 src.ml.trained_model)
            trainer_config: 训练器配置 (本地配置)
        """
        self.training_config = training_config or TrainingConfig()
        self.trainer_config = trainer_config or ModelTrainerConfig()

        self.output_dir = Path(self.trainer_config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 创建训练策略
        self.strategy = StrategyFactory.create_strategy(self.training_config.model_type)

        # 初始化组件
        self.model: Optional[Any] = None
        self.evaluator = ModelEvaluator()
        self.training_history: Dict[str, Any] = {}

        logger.debug(f"初始化 ModelTrainer，模型类型: {self.training_config.model_type}")

    def prepare_data(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        split_config: Optional[DataSplitConfig] = None
    ):
        """准备训练数据

        Args:
            df: 完整数据 DataFrame
            feature_cols: 特征列名列表
            target_col: 目标列名
            split_config: 数据分割配置

        Returns:
            Response对象，成功时data包含:
            {
                'X_train': 训练特征,
                'y_train': 训练标签,
                'X_valid': 验证特征,
                'y_valid': 验证标签,
                'X_test': 测试特征,
                'y_test': 测试标签
            }
        """
        from src.utils.response import Response

        try:
            if split_config is None:
                split_config = DataSplitConfig()

            X_train, y_train, X_valid, y_valid, X_test, y_test = DataPreparator.prepare_data(
                df, feature_cols, target_col, split_config
            )

            return Response.success(
                data={
                    'X_train': X_train,
                    'y_train': y_train,
                    'X_valid': X_valid,
                    'y_valid': y_valid,
                    'X_test': X_test,
                    'y_test': y_test
                },
                message="数据准备完成",
                n_samples=len(df),
                n_features=len(feature_cols),
                n_train=len(X_train),
                n_valid=len(X_valid),
                n_test=len(X_test)
            )
        except DataPreparationError as e:
            return Response.error(
                error=str(e),
                error_code=e.error_code if hasattr(e, 'error_code') else "DATA_PREPARATION_ERROR"
            )
        except Exception as e:
            return Response.error(
                error=f"数据准备失败: {str(e)}",
                error_code="DATA_PREPARATION_ERROR"
            )

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None
    ):
        """
        训练模型

        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_valid: 验证特征
            y_valid: 验证标签

        Returns:
            Response对象，成功时data包含:
            {
                'model': 训练好的模型,
                'training_history': 训练历史
            }
        """
        from src.utils.response import Response
        import time

        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"开始训练 {self.training_config.model_type.upper()} 模型")
            logger.info(f"{'='*60}")

            start_time = time.time()

            # 准备模型参数 (从 hyperparameters 获取)
            model_params = self.training_config.hyperparameters or {}

            # 对于 GRU 模型，需要设置 input_size
            if self.training_config.model_type == 'gru':
                if 'input_size' not in model_params:
                    model_params['input_size'] = len(X_train.columns)
                    logger.debug(f"自动设置 GRU input_size: {len(X_train.columns)}")

            # 创建模型
            self.model = self.strategy.create_model(model_params)
            logger.debug(f"模型创建成功: {type(self.model).__name__}")

            # 训练模型
            self.training_history = self.strategy.train(
                self.model,
                X_train, y_train,
                X_valid, y_valid,
                self.trainer_config
            )

            elapsed_time = time.time() - start_time

            logger.info("训练完成")

            return Response.success(
                data={
                    'model': self.model,
                    'training_history': self.training_history
                },
                message=f"{self.training_config.model_type.upper()} 模型训练完成",
                model_type=self.training_config.model_type,
                n_samples=len(X_train),
                n_features=len(X_train.columns),
                elapsed_time=f"{elapsed_time:.2f}s"
            )

        except ModelCreationError as e:
            return Response.error(
                error=str(e),
                error_code=e.error_code if hasattr(e, 'error_code') else "MODEL_CREATION_ERROR",
                model_type=self.training_config.model_type
            )
        except TrainingError as e:
            return Response.error(
                error=str(e),
                error_code=e.error_code if hasattr(e, 'error_code') else "TRAINING_ERROR",
                model_type=self.training_config.model_type
            )
        except Exception as e:
            logger.exception(f"训练过程发生异常: {e}")
            return Response.error(
                error=f"模型训练失败: {str(e)}",
                error_code="TRAINING_ERROR",
                model_type=self.training_config.model_type
            )

    def evaluate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        dataset_name: str = 'test',
        verbose: bool = True
    ):
        """
        评估模型

        Args:
            X: 特征
            y: 标签
            dataset_name: 数据集名称
            verbose: 是否打印结果

        Returns:
            Response对象，成功时data包含评估指标字典
        """
        from src.utils.response import Response
        import time

        try:
            if self.model is None:
                return Response.error(
                    error="模型未训练",
                    error_code="MODEL_NOT_TRAINED",
                    message="请先调用 train() 方法"
                )

            start_time = time.time()

            metrics = ModelEvaluationHelper.evaluate_model(
                self.model,
                self.training_config.model_type,
                X, y,
                self.evaluator,
                seq_length=self.trainer_config.seq_length if self.training_config.model_type == 'gru' else None,
                dataset_name=dataset_name,
                verbose=verbose
            )

            elapsed_time = time.time() - start_time

            return Response.success(
                data=metrics,
                message=f"{dataset_name} 集评估完成",
                dataset_name=dataset_name,
                model_type=self.training_config.model_type,
                n_samples=len(X),
                elapsed_time=f"{elapsed_time:.2f}s"
            )

        except Exception as e:
            logger.exception(f"评估过程发生异常: {e}")
            return Response.error(
                error=f"模型评估失败: {str(e)}",
                error_code="EVALUATION_ERROR",
                dataset_name=dataset_name,
                model_type=self.training_config.model_type
            )

    def save_model(
        self,
        model_name: str,
        save_metrics: bool = True
    ):
        """
        保存模型

        Args:
            model_name: 模型名称
            save_metrics: 是否保存评估指标

        Returns:
            Response对象，成功时data包含:
            {
                'model_path': 模型文件路径,
                'meta_path': 元数据文件路径（如果save_metrics=True）
            }
        """
        from src.utils.response import Response
        import time

        try:
            if self.model is None:
                return Response.error(
                    error="模型未训练，无法保存",
                    error_code="MODEL_NOT_TRAINED",
                    model_name=model_name
                )

            start_time = time.time()
            logger.info(f"保存模型: {model_name}")

            # 确定模型文件路径
            if self.training_config.model_type == 'lightgbm':
                model_path = self.output_dir / f"{model_name}.txt"
            elif self.training_config.model_type == 'gru':
                model_path = self.output_dir / f"{model_name}.pth"
            elif self.training_config.model_type == 'ridge':
                model_path = self.output_dir / f"{model_name}.pkl"
            else:
                return Response.error(
                    error=f"不支持的模型类型: {self.training_config.model_type}",
                    error_code="UNSUPPORTED_MODEL_TYPE",
                    model_type=self.training_config.model_type,
                    model_name=model_name
                )

            # 保存模型
            self.model.save_model(str(model_path))
            logger.info(f"✓ 模型已保存至: {model_path}")

            meta_path = None
            # 保存训练配置和指标
            if save_metrics:
                meta_path = self.output_dir / f"{model_name}_meta.json"
                meta_data = {
                    'model_type': self.training_config.model_type,
                    'hyperparameters': self.training_config.hyperparameters,
                    'training_config': {
                        'train_start_date': self.training_config.train_start_date,
                        'train_end_date': self.training_config.train_end_date,
                        'validation_split': self.training_config.validation_split,
                        'forward_window': self.training_config.forward_window,
                        'feature_groups': self.training_config.feature_groups
                    },
                    'training_history': self.training_history,
                    'evaluation_metrics': self.evaluator.get_metrics()
                }

                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(meta_data, f, indent=2, ensure_ascii=False)

                logger.info(f"✓ 元数据已保存至: {meta_path}")

            elapsed_time = time.time() - start_time

            return Response.success(
                data={
                    'model_path': str(model_path),
                    'meta_path': str(meta_path) if meta_path else None
                },
                message="模型保存成功",
                model_name=model_name,
                model_type=self.training_config.model_type,
                elapsed_time=f"{elapsed_time:.2f}s"
            )

        except Exception as e:
            logger.exception(f"保存模型时发生异常: {e}")
            return Response.error(
                error=f"保存模型失败: {str(e)}",
                error_code="MODEL_SAVE_ERROR",
                model_name=model_name,
                model_type=self.training_config.model_type
            )

    def load_model(self, model_name: str):
        """
        加载模型

        Args:
            model_name: 模型名称

        Returns:
            Response对象，成功时data包含:
            {
                'model': 加载的模型,
                'model_type': 模型类型,
                'training_history': 训练历史,
                'model_params': 模型参数
            }
        """
        from src.utils.response import Response
        import time

        try:
            start_time = time.time()
            logger.info(f"加载模型: {model_name}")

            # 加载元数据
            meta_path = self.output_dir / f"{model_name}_meta.json"
            meta_data = {}
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)

                # 更新配置
                self.training_config.model_type = meta_data.get('model_type', self.training_config.model_type)
                saved_hyperparams = meta_data.get('hyperparameters', {})
                self.training_history = meta_data.get('training_history', {})

                # 合并超参数：优先使用元数据中的参数
                if self.training_config.hyperparameters is None:
                    self.training_config.hyperparameters = {}
                self.training_config.hyperparameters = {**self.training_config.hyperparameters, **saved_hyperparams}

                # 加载训练配置信息
                if 'training_config' in meta_data:
                    tc = meta_data['training_config']
                    self.training_config.train_start_date = tc.get('train_start_date', self.training_config.train_start_date)
                    self.training_config.train_end_date = tc.get('train_end_date', self.training_config.train_end_date)
                    self.training_config.validation_split = tc.get('validation_split', self.training_config.validation_split)
                    self.training_config.forward_window = tc.get('forward_window', self.training_config.forward_window)
                    self.training_config.feature_groups = tc.get('feature_groups', self.training_config.feature_groups)

                logger.debug(f"加载元数据: model_type={self.training_config.model_type}")
            else:
                logger.warning(f"元数据文件不存在: {meta_path}")

            # 重新创建策略
            self.strategy = StrategyFactory.create_strategy(self.training_config.model_type)

            # 加载模型
            if self.training_config.model_type == 'lightgbm':
                if not LIGHTGBM_AVAILABLE:
                    return Response.error(
                        error="LightGBM 模型需要 lightgbm: pip install lightgbm",
                        error_code="LIGHTGBM_NOT_INSTALLED",
                        model_name=model_name
                    )
                model_path = self.output_dir / f"{model_name}.txt"
                self.model = LightGBMStockModel()
                self.model.load_model(str(model_path))
            elif self.training_config.model_type == 'gru':
                from .gru_model import GRUStockTrainer
                model_path = self.output_dir / f"{model_name}.pth"

                # 过滤训练专用参数
                hyperparams = self.training_config.hyperparameters or {}
                gru_model_params = {
                    k: v for k, v in hyperparams.items()
                    if k in ['input_size', 'hidden_size', 'num_layers', 'dropout',
                            'bidirectional', 'learning_rate', 'device']
                }

                self.model = GRUStockTrainer(**gru_model_params)
                self.model.load_model(str(model_path))
            elif self.training_config.model_type == 'ridge':
                model_path = self.output_dir / f"{model_name}.pkl"
                self.model = RidgeStockModel()
                self.model.load_model(str(model_path))
            else:
                return Response.error(
                    error=f"不支持的模型类型: {self.training_config.model_type}",
                    error_code="UNSUPPORTED_MODEL_TYPE",
                    model_type=self.training_config.model_type,
                    model_name=model_name
                )

            elapsed_time = time.time() - start_time
            logger.info(f"✓ 模型已加载: {model_path}")

            return Response.success(
                data={
                    'model': self.model,
                    'model_type': self.training_config.model_type,
                    'training_history': self.training_history,
                    'hyperparameters': self.training_config.hyperparameters,
                    'training_config': self.training_config
                },
                message="模型加载成功",
                model_name=model_name,
                model_path=str(model_path),
                elapsed_time=f"{elapsed_time:.2f}s"
            )

        except FileNotFoundError as e:
            return Response.error(
                error=f"模型文件不存在: {str(e)}",
                error_code="MODEL_FILE_NOT_FOUND",
                model_name=model_name
            )
        except Exception as e:
            logger.exception(f"加载模型时发生异常: {e}")
            return Response.error(
                error=f"加载模型失败: {str(e)}",
                error_code="MODEL_LOAD_ERROR",
                model_name=model_name
            )


# ==================== 注意 ====================
# 便捷函数已迁移到 training_pipeline.py 模块
# 请使用: from src.models.training_pipeline import train_stock_model

# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: logger.info(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}",
        level="INFO"
    )

    logger.info("\n" + "="*60)
    logger.info("模型训练器测试")
    logger.info("="*60 + "\n")

    # 创建测试数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 20

    dates = pd.date_range('2020-01-01', periods=n_samples, freq='D')

    # 模拟特征
    features = {}
    for i in range(n_features):
        features[f'feature_{i}'] = np.random.randn(n_samples)

    # 模拟目标（未来5日收益率）
    target = (
        features['feature_0'] * 0.5 +
        features['feature_1'] * 0.3 +
        np.random.randn(n_samples) * 0.02
    )

    df = pd.DataFrame(features, index=dates)
    df['target'] = target

    logger.info("测试数据:")
    logger.info(f"  样本数: {len(df)}")
    logger.info(f"  特征数: {n_features}")
    logger.info(df.head())

    # 准备特征列表
    feature_cols = [f'feature_{i}' for i in range(n_features)]

    # 测试 LightGBM
    logger.info("\n" + "="*60)
    logger.info("测试 LightGBM 模型")
    logger.info("="*60)

    try:
        # 创建训练配置 (使用 ml.TrainingConfig)
        training_config = TrainingConfig(
            model_type='lightgbm',
            hyperparameters={
                'learning_rate': 0.1,
                'n_estimators': 100,
                'num_leaves': 31
            },
            train_start_date='2020-01-01',
            train_end_date='2023-12-31',
            validation_split=0.15,
            forward_window=5,
            feature_groups=['all']
        )

        # 创建训练器配置
        trainer_config = ModelTrainerConfig(
            output_dir='data/models/saved',
            early_stopping_rounds=50,
            verbose_eval=50
        )

        trainer = ModelTrainer(
            training_config=training_config,
            trainer_config=trainer_config
        )

        split_config = DataSplitConfig(train_ratio=0.7, valid_ratio=0.15)
        prep_result = trainer.prepare_data(df, feature_cols, 'target', split_config)

        if prep_result.success:
            data = prep_result.data
            X_train = data['X_train']
            y_train = data['y_train']
            X_valid = data['X_valid']
            y_valid = data['y_valid']
            X_test = data['X_test']
            y_test = data['y_test']

            train_result = trainer.train(X_train, y_train, X_valid, y_valid)

            # 评估
            test_result = trainer.evaluate(X_test, y_test, dataset_name='test')

            # 保存
            save_result = trainer.save_model('test_lgb_model')

            logger.success("\n✓ LightGBM 测试完成")
        else:
            logger.error(f"\n✗ 数据准备失败: {prep_result.error}")

    except Exception as e:
        logger.error(f"\n✗ LightGBM 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

    logger.success("\n✓ 所有测试完成")
    logger.info("\n提示: 便捷函数已迁移到 training_pipeline.py 模块")
