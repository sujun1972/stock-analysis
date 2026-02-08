"""
Models module
"""

# 基础模型（可选导入lightgbm）
try:
    from .lightgbm_model import LightGBMStockModel, train_lightgbm_model
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

from .ridge_model import RidgeStockModel
from .model_evaluator import ModelEvaluator, evaluate_model
from .model_trainer import ModelTrainer, ModelTrainerConfig, DataSplitConfig
from .training_pipeline import TrainingPipeline, train_stock_model
from .model_validator import (
    TimeSeriesCrossValidator,
    ModelStabilityTester,
    OverfittingDetector,
    cross_validate_model
)
from .hyperparameter_tuner import (
    GridSearchTuner,
    RandomSearchTuner,
    tune_hyperparameters
)
from .comparison_evaluator import ComparisonEvaluator

# 集成模块
from .ensemble import (
    WeightedAverageEnsemble,
    VotingEnsemble,
    StackingEnsemble,
    create_ensemble
)

# 模型注册表
from .model_registry import ModelRegistry, ModelMetadata

# GRU模型（可选导入PyTorch）
try:
    from .gru_model import GRUStockModel, GRUStockTrainer
    GRU_AVAILABLE = True
except ImportError:
    GRU_AVAILABLE = False

__all__ = [
    # 基础模型
    'RidgeStockModel',

    # 评估
    'ModelEvaluator',
    'evaluate_model',
    'ComparisonEvaluator',

    # 训练
    'ModelTrainer',
    'ModelTrainerConfig',
    'DataSplitConfig',
    'TrainingPipeline',
    'train_stock_model',

    # 验证
    'TimeSeriesCrossValidator',
    'ModelStabilityTester',
    'OverfittingDetector',
    'cross_validate_model',

    # 超参数调优
    'GridSearchTuner',
    'RandomSearchTuner',
    'tune_hyperparameters',

    # 集成
    'WeightedAverageEnsemble',
    'VotingEnsemble',
    'StackingEnsemble',
    'create_ensemble',

    # 模型注册表
    'ModelRegistry',
    'ModelMetadata',
]

if LIGHTGBM_AVAILABLE:
    __all__.extend(['LightGBMStockModel', 'train_lightgbm_model'])

if GRU_AVAILABLE:
    __all__.extend(['GRUStockModel', 'GRUStockTrainer'])
