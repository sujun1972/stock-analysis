"""
Models module
"""

from .lightgbm_model import LightGBMStockModel, train_lightgbm_model
from .model_evaluator import ModelEvaluator, evaluate_model
from .model_trainer import ModelTrainer, train_stock_model

try:
    from .gru_model import GRUStockModel, GRUStockTrainer
    GRU_AVAILABLE = True
except ImportError:
    GRU_AVAILABLE = False

__all__ = [
    'LightGBMStockModel',
    'train_lightgbm_model',
    'ModelEvaluator',
    'evaluate_model',
    'ModelTrainer',
    'train_stock_model',
]

if GRU_AVAILABLE:
    __all__.extend(['GRUStockModel', 'GRUStockTrainer'])
