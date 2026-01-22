"""
机器学习模型数据库模型
存储训练任务、模型元数据等
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class MLTrainingTaskCreate(BaseModel):
    """训练任务创建请求"""
    symbol: str
    start_date: str
    end_date: str
    model_type: str  # 'lightgbm' or 'gru'
    target_period: int = 5
    train_ratio: float = 0.7
    valid_ratio: float = 0.15

    # 特征选择
    use_technical_indicators: bool = True
    use_alpha_factors: bool = True
    selected_features: Optional[list[str]] = None

    # 数据处理
    scaler_type: str = 'robust'
    balance_samples: bool = False
    balance_method: str = 'undersample'

    # 模型参数
    model_params: Optional[Dict[str, Any]] = None

    # GRU特定参数
    seq_length: int = 20
    batch_size: int = 64
    epochs: int = 100

    # LightGBM特定参数
    early_stopping_rounds: int = 50


class MLTrainingTaskResponse(BaseModel):
    """训练任务响应"""
    task_id: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 任务配置
    config: Dict[str, Any]

    # 进度信息
    progress: float = 0.0  # 0-100
    current_step: str = ''

    # 训练结果
    metrics: Optional[Dict[str, float]] = None
    model_path: Optional[str] = None
    feature_importance: Optional[Dict[str, float]] = None

    # 错误信息
    error_message: Optional[str] = None


class MLModelMetadata(BaseModel):
    """模型元数据"""
    model_id: str
    task_id: str
    symbol: str
    model_type: str
    target_period: int

    # 性能指标
    test_rmse: float
    test_r2: float
    test_ic: float
    test_rank_ic: float

    # 其他指标
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None

    # 训练信息
    train_samples: int
    valid_samples: int
    test_samples: int
    feature_count: int

    # 文件路径
    model_path: str
    scaler_path: Optional[str] = None

    # 时间戳
    trained_at: datetime

    # 备注
    description: Optional[str] = None


class MLPredictionRequest(BaseModel):
    """预测请求"""
    model_id: str
    symbol: str
    start_date: str
    end_date: str


class MLPredictionResponse(BaseModel):
    """预测响应"""
    predictions: list[Dict[str, Any]]  # [{date, prediction, actual}, ...]
    metrics: Dict[str, float]
