"""
统一模型训练器
提供统一接口训练和评估不同类型的模型

重构说明:
- 模块化设计: 分离数据准备、训练策略、模型创建逻辑
- 策略模式: 每种模型类型有独立的训练策略
- 工厂模式: 统一的模型创建接口
- 统一日志系统: 使用 loguru 替代 print
- 增强错误处理: 自定义异常类和数据验证
- 配置管理: 使用 dataclass 管理训练参数
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

from .lightgbm_model import LightGBMStockModel
from .ridge_model import RidgeStockModel
from .model_evaluator import ModelEvaluator


# ==================== 异常类 ====================

class TrainingError(Exception):
    """训练过程错误基类"""
    pass


class DataPreparationError(TrainingError):
    """数据准备错误"""
    pass


class ModelCreationError(TrainingError):
    """模型创建错误"""
    pass


class InvalidModelTypeError(TrainingError):
    """无效模型类型错误"""
    pass


# ==================== 配置类 ====================

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
class TrainingConfig:
    """训练配置"""
    model_type: str = 'lightgbm'
    model_params: Dict[str, Any] = field(default_factory=dict)
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
        valid_types = ['lightgbm', 'ridge', 'gru']
        if self.model_type not in valid_types:
            raise ValueError(
                f"不支持的模型类型: {self.model_type}，支持的类型: {valid_types}"
            )



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
        config: TrainingConfig
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

    def create_model(self, model_params: Dict[str, Any]) -> LightGBMStockModel:
        params = {**self.get_default_params(), **model_params}
        return LightGBMStockModel(**params)

    def train(
        self,
        model: LightGBMStockModel,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame],
        y_valid: Optional[pd.Series],
        config: TrainingConfig
    ) -> Dict[str, Any]:
        logger.info("训练 LightGBM 模型...")
        history = model.train(
            X_train, y_train,
            X_valid, y_valid,
            early_stopping_rounds=config.early_stopping_rounds,
            verbose_eval=config.verbose_eval
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
        config: TrainingConfig
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
        config: TrainingConfig
    ) -> Dict[str, Any]:
        logger.info("训练 GRU 模型...")
        history = model.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=config.seq_length,
            batch_size=config.batch_size,
            epochs=config.epochs,
            early_stopping_patience=config.early_stopping_patience
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
    """

    def __init__(self, config: Optional[TrainingConfig] = None):
        """初始化训练器"""
        self.config = config or TrainingConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 创建训练策略
        self.strategy = StrategyFactory.create_strategy(self.config.model_type)

        # 初始化组件
        self.model: Optional[Any] = None
        self.evaluator = ModelEvaluator()
        self.training_history: Dict[str, Any] = {}

        logger.debug(f"初始化 ModelTrainer，模型类型: {self.config.model_type}")

    def prepare_data(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        split_config: Optional[DataSplitConfig] = None
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """准备训练数据"""
        if split_config is None:
            split_config = DataSplitConfig()
        return DataPreparator.prepare_data(df, feature_cols, target_col, split_config)

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None
    ) -> None:
        """
        训练模型

        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_valid: 验证特征
            y_valid: 验证标签
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"开始训练 {self.config.model_type.upper()} 模型")
        logger.info(f"{'='*60}")

        # 对于 GRU 模型，需要设置 input_size
        if self.config.model_type == 'gru':
            if 'input_size' not in self.config.model_params:
                self.config.model_params['input_size'] = len(X_train.columns)
                logger.debug(f"自动设置 GRU input_size: {len(X_train.columns)}")

        # 创建模型
        self.model = self.strategy.create_model(self.config.model_params)
        logger.debug(f"模型创建成功: {type(self.model).__name__}")

        # 训练模型
        self.training_history = self.strategy.train(
            self.model,
            X_train, y_train,
            X_valid, y_valid,
            self.config
        )

        logger.info("训练完成")

    def evaluate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        dataset_name: str = 'test',
        verbose: bool = True
    ) -> Dict[str, float]:
        """
        评估模型

        Args:
            X: 特征
            y: 标签
            dataset_name: 数据集名称
            verbose: 是否打印结果

        Returns:
            评估指标字典
        """
        if self.model is None:
            raise TrainingError("模型未训练，请先调用 train() 方法")

        return ModelEvaluationHelper.evaluate_model(
            self.model,
            self.config.model_type,
            X, y,
            self.evaluator,
            seq_length=self.config.seq_length if self.config.model_type == 'gru' else None,
            dataset_name=dataset_name,
            verbose=verbose
        )

    def save_model(
        self,
        model_name: str,
        save_metrics: bool = True
    ) -> str:
        """
        保存模型

        Args:
            model_name: 模型名称
            save_metrics: 是否保存评估指标

        Returns:
            模型文件路径（字符串）
        """
        if self.model is None:
            raise TrainingError("模型未训练，无法保存")

        logger.info(f"保存模型: {model_name}")

        # 确定模型文件路径
        if self.config.model_type == 'lightgbm':
            model_path = self.output_dir / f"{model_name}.txt"
        elif self.config.model_type == 'gru':
            model_path = self.output_dir / f"{model_name}.pth"
        elif self.config.model_type == 'ridge':
            model_path = self.output_dir / f"{model_name}.pkl"
        else:
            raise InvalidModelTypeError(f"不支持的模型类型: {self.config.model_type}")

        # 保存模型
        self.model.save_model(str(model_path))
        logger.info(f"✓ 模型已保存至: {model_path}")

        # 保存训练配置和指标
        if save_metrics:
            meta_path = self.output_dir / f"{model_name}_meta.json"
            meta_data = {
                'model_type': self.config.model_type,
                'model_params': self.config.model_params,
                'training_history': self.training_history,
                'evaluation_metrics': self.evaluator.get_metrics()
            }

            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ 元数据已保存至: {meta_path}")

        return str(model_path)

    def load_model(self, model_name: str) -> None:
        """
        加载模型

        Args:
            model_name: 模型名称
        """
        logger.info(f"加载模型: {model_name}")

        # 加载元数据
        meta_path = self.output_dir / f"{model_name}_meta.json"
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)

            self.config.model_type = meta_data.get('model_type', self.config.model_type)
            saved_params = meta_data.get('model_params', {})
            self.training_history = meta_data.get('training_history', {})

            # 合并参数：优先使用元数据中的参数
            self.config.model_params = {**self.config.model_params, **saved_params}

            logger.debug(f"加载元数据: model_type={self.config.model_type}")

        # 重新创建策略
        self.strategy = StrategyFactory.create_strategy(self.config.model_type)

        # 加载模型
        if self.config.model_type == 'lightgbm':
            model_path = self.output_dir / f"{model_name}.txt"
            self.model = LightGBMStockModel()
            self.model.load_model(str(model_path))
        elif self.config.model_type == 'gru':
            from .gru_model import GRUStockTrainer
            model_path = self.output_dir / f"{model_name}.pth"

            # 过滤训练专用参数
            gru_model_params = {
                k: v for k, v in self.config.model_params.items()
                if k in ['input_size', 'hidden_size', 'num_layers', 'dropout',
                        'bidirectional', 'learning_rate', 'device']
            }

            self.model = GRUStockTrainer(**gru_model_params)
            self.model.load_model(str(model_path))
        elif self.config.model_type == 'ridge':
            model_path = self.output_dir / f"{model_name}.pkl"
            self.model = RidgeStockModel()
            self.model.load_model(str(model_path))
        else:
            raise InvalidModelTypeError(f"不支持的模型类型: {self.config.model_type}")

        logger.info(f"✓ 模型已加载: {model_path}")


# ==================== 便捷函数 ====================

def train_stock_model(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    model_type: str = 'lightgbm',
    model_params: Optional[Dict[str, Any]] = None,
    train_ratio: float = 0.7,
    valid_ratio: float = 0.15,
    save_path: Optional[str] = None
) -> Tuple[ModelTrainer, Dict[str, float]]:
    """
    便捷函数：训练股票预测模型

    Args:
        df: 数据 DataFrame
        feature_cols: 特征列
        target_col: 目标列
        model_type: 模型类型
        model_params: 模型参数
        train_ratio: 训练集比例
        valid_ratio: 验证集比例
        save_path: 保存路径

    Returns:
        (训练器对象, 测试集评估指标)
    """
    # 创建配置
    training_config = TrainingConfig(
        model_type=model_type,
        model_params=model_params or {}
    )

    split_config = DataSplitConfig(
        train_ratio=train_ratio,
        valid_ratio=valid_ratio
    )

    # 创建训练器
    trainer = ModelTrainer(config=training_config)

    # 准备数据
    X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
        df, feature_cols, target_col, split_config
    )

    # 训练模型
    trainer.train(X_train, y_train, X_valid, y_valid)

    # 评估模型
    test_metrics = trainer.evaluate(X_test, y_test, dataset_name='test')

    # 保存模型
    if save_path:
        trainer.save_model(save_path)

    return trainer, test_metrics


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
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
        config = TrainingConfig(
            model_type='lightgbm',
            model_params={
                'learning_rate': 0.1,
                'n_estimators': 100,
                'num_leaves': 31
            }
        )

        trainer = ModelTrainer(config=config)

        split_config = DataSplitConfig(train_ratio=0.7, valid_ratio=0.15)
        X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
            df, feature_cols, 'target', split_config
        )

        trainer.train(X_train, y_train, X_valid, y_valid)

        # 评估
        test_metrics = trainer.evaluate(X_test, y_test, dataset_name='test')

        # 保存
        trainer.save_model('test_lgb_model')

        logger.success("\n✓ LightGBM 测试完成")

    except Exception as e:
        logger.error(f"\n✗ LightGBM 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # 测试便捷函数
    logger.info("\n" + "="*60)
    logger.info("测试便捷函数")
    logger.info("="*60)

    try:
        trainer, metrics = train_stock_model(
            df,
            feature_cols,
            'target',
            model_type='ridge',
            save_path='test_ridge_model'
        )

        logger.success("\n✓ 便捷函数测试完成")

    except Exception as e:
        logger.error(f"\n✗ 便捷函数测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

    logger.success("\n✓ 所有测试完成")
