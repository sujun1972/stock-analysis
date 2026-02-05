"""
机器学习模型数据库模型
存储训练任务、模型元数据等
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class MLTrainingTaskCreate(BaseModel):
    """训练任务创建请求"""

    # 支持单股票或多股票池化训练
    symbol: Optional[str] = None  # 单股票（向后兼容）
    symbols: Optional[list[str]] = None  # 多股票列表（新增）

    start_date: str
    end_date: str
    model_type: str  # 'lightgbm', 'ridge', or 'gru'
    target_period: int = 5
    train_ratio: float = 0.7
    valid_ratio: float = 0.15

    # 池化训练配置（新增）
    enable_pooled_training: bool = False  # 是否启用池化训练
    enable_ridge_baseline: bool = True  # 是否启用Ridge基准对比

    # 特征选择
    use_technical_indicators: bool = True
    use_alpha_factors: bool = True
    selected_features: Optional[list[str]] = None

    # 数据处理
    scaler_type: str = "robust"
    balance_samples: bool = False
    balance_method: str = "undersample"

    # 模型参数
    model_params: Optional[Dict[str, Any]] = None
    ridge_params: Optional[Dict[str, Any]] = None  # Ridge参数（新增）

    # GRU特定参数
    seq_length: int = 20
    batch_size: int = 64
    epochs: int = 100

    # LightGBM特定参数
    early_stopping_rounds: int = 50

    def get_symbol_list(self) -> list[str]:
        """获取股票列表（统一接口）"""
        if self.symbols:
            return self.symbols
        elif self.symbol:
            return [self.symbol]
        else:
            raise ValueError("必须提供symbol或symbols")


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
    current_step: str = ""

    # 训练结果
    metrics: Optional[Dict[str, float]] = None
    model_path: Optional[str] = None
    feature_importance: Optional[Dict[str, float]] = None
    training_history: Optional[Dict[str, list]] = None  # GRU模型的训练历史曲线

    # 池化训练结果（新增）
    has_baseline: bool = False  # 是否包含Ridge基准对比
    baseline_metrics: Optional[Dict[str, float]] = None  # Ridge指标
    comparison_result: Optional[Dict[str, Any]] = None  # 对比结果
    recommendation: Optional[str] = None  # 推荐模型 ('ridge' or 'lightgbm')
    total_samples: Optional[int] = None  # 池化后总样本数
    successful_symbols: Optional[list[str]] = None  # 成功加载的股票

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

    model_id: Optional[str] = None  # 兼容旧版：模型名称
    experiment_id: Optional[int] = None  # 新版：实验ID（experiments表主键）
    symbol: str
    start_date: str
    end_date: str


class MLPredictionResponse(BaseModel):
    """预测响应"""

    predictions: list[Dict[str, Any]]  # [{date, prediction, actual}, ...]
    metrics: Dict[str, float]
