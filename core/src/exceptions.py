"""
统一的异常处理系统

提供类型安全的异常类层次结构，便于错误追踪和处理

该模块定义了整个stock-analysis项目的异常类体系:
- 所有异常继承自StockAnalysisError基类
- 支持错误代码(error_code)用于机器可读的错误分类
- 支持上下文信息(context)用于调试和日志记录
- 支持结构化输出(to_dict)用于API返回

Examples:
    >>> # 基本使用
    >>> raise DataValidationError(
    ...     "股票代码不能为空",
    ...     error_code="EMPTY_STOCK_CODE",
    ...     stock_code="",
    ...     field="stock_code"
    ... )

    >>> # 异常捕获和结构化输出
    >>> try:
    ...     provider.get_daily_data("")
    ... except DataValidationError as e:
    ...     error_dict = e.to_dict()
    ...     logger.error(error_dict)
"""
from typing import Dict, Any, Optional


class StockAnalysisError(Exception):
    """所有自定义异常的基类

    所有项目中的自定义异常都应该继承此类，提供统一的错误处理接口。

    Attributes:
        message: 人类可读的错误消息
        error_code: 机器可读的错误代码，默认为类名
        context: 额外的上下文信息字典，用于调试和日志

    Examples:
        >>> # 创建基础异常
        >>> error = StockAnalysisError(
        ...     message="操作失败",
        ...     error_code="OPERATION_FAILED",
        ...     operation="calculate_features",
        ...     stock_code="000001"
        ... )
        >>> print(error)
        操作失败 (error_code=OPERATION_FAILED, operation=calculate_features, stock_code=000001)

        >>> # 结构化输出
        >>> error.to_dict()
        {
            'error_type': 'StockAnalysisError',
            'error_code': 'OPERATION_FAILED',
            'message': '操作失败',
            'context': {'operation': 'calculate_features', 'stock_code': '000001'}
        }
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        **context
    ):
        """初始化异常

        Args:
            message: 错误消息
            error_code: 错误代码，如果为None则使用类名
            **context: 任意额外的上下文信息
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context
        # 向后兼容:保留details属性
        self.details = context
        super().__init__(self.message)

    def __str__(self) -> str:
        """字符串表示，包含错误代码和上下文"""
        parts = [self.message]

        # 添加错误代码
        if self.error_code != self.__class__.__name__:
            parts.append(f"error_code={self.error_code}")

        # 添加上下文信息
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            if self.error_code != self.__class__.__name__:
                parts.append(context_str)
            else:
                parts.append(f"({context_str})")

        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2 and not parts[1].startswith("("):
            return f"{parts[0]} ({parts[1]})"
        else:
            return f"{parts[0]} ({', '.join(parts[1:])})"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化和日志记录

        Returns:
            包含错误信息的字典:
            - error_type: 异常类名
            - error_code: 错误代码
            - message: 错误消息
            - context: 上下文信息字典

        Examples:
            >>> error = DataNotFoundError(
            ...     "股票数据不存在",
            ...     error_code="STOCK_NOT_FOUND",
            ...     stock_code="999999"
            ... )
            >>> error.to_dict()
            {
                'error_type': 'DataNotFoundError',
                'error_code': 'STOCK_NOT_FOUND',
                'message': '股票数据不存在',
                'context': {'stock_code': '999999'}
            }
        """
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'context': self.context
        }


# ==================== 数据相关异常 ====================

class DataError(StockAnalysisError):
    """数据相关异常基类

    所有与数据获取、处理、验证相关的异常都应继承此类。
    """
    pass


class DataNotFoundError(DataError):
    """数据不存在异常

    当请求的数据在数据源、数据库或缓存中不存在时抛出。

    Examples:
        >>> raise DataNotFoundError(
        ...     "股票数据不存在",
        ...     error_code="STOCK_NOT_FOUND",
        ...     stock_code="999999",
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-31"
        ... )
    """
    pass


class DataValidationError(DataError):
    """数据验证失败异常

    当数据不符合预期格式、范围或约束条件时抛出。

    Examples:
        >>> raise DataValidationError(
        ...     "股票代码格式不正确",
        ...     error_code="INVALID_STOCK_CODE",
        ...     stock_code="ABC",
        ...     expected_format="6位数字"
        ... )
    """
    pass


class DataProviderError(DataError):
    """数据提供者异常

    当数据源API调用失败、超时或返回错误时抛出。

    Examples:
        >>> raise DataProviderError(
        ...     "AkShare API调用失败",
        ...     error_code="AKSHARE_API_ERROR",
        ...     provider="akshare",
        ...     api_endpoint="stock_zh_a_hist",
        ...     status_code=500
        ... )
    """
    pass


class DataSourceError(DataError):
    """数据源错误(向后兼容别名)"""
    pass


class PipelineError(DataError):
    """数据流水线错误

    当数据处理流水线执行失败时抛出。

    Examples:
        >>> raise PipelineError(
        ...     "数据清洗步骤失败",
        ...     error_code="PIPELINE_STEP_FAILED",
        ...     step="data_cleaning",
        ...     stage=3
        ... )
    """
    pass


class InsufficientDataError(DataError):
    """数据不足异常

    当数据量不足以完成计算或分析时抛出。

    Examples:
        >>> raise InsufficientDataError(
        ...     "数据点不足，无法计算MA20",
        ...     error_code="INSUFFICIENT_DATA_FOR_INDICATOR",
        ...     required_points=20,
        ...     actual_points=10,
        ...     indicator="MA20"
        ... )
    """
    pass


# ==================== 数据库相关异常 ====================

class DatabaseError(StockAnalysisError):
    """数据库相关异常基类

    所有与数据库操作相关的异常都应继承此类。
    """
    pass


class DatabaseConnectionError(DatabaseError):
    """数据库连接错误

    当无法建立数据库连接或连接中断时抛出。

    Examples:
        >>> raise DatabaseConnectionError(
        ...     "无法连接到TimescaleDB",
        ...     error_code="DB_CONNECTION_FAILED",
        ...     host="localhost",
        ...     port=5432,
        ...     database="stock_analysis"
        ... )
    """
    pass


# 向后兼容别名
ConnectionError = DatabaseConnectionError


class QueryError(DatabaseError):
    """SQL查询错误

    当SQL查询执行失败时抛出。

    Examples:
        >>> raise QueryError(
        ...     "SQL查询执行失败",
        ...     error_code="SQL_EXECUTION_ERROR",
        ...     query="SELECT * FROM stock_data",
        ...     error_message="syntax error"
        ... )
    """
    pass


# ==================== 特征工程相关异常 ====================

class FeatureError(StockAnalysisError):
    """特征工程相关异常基类

    所有与特征计算、存储、加载相关的异常都应继承此类。
    """
    pass


class FeatureCalculationError(FeatureError):
    """特征计算错误

    当特征计算过程中发生错误时抛出。

    Examples:
        >>> raise FeatureCalculationError(
        ...     "Alpha因子计算失败",
        ...     error_code="ALPHA_CALCULATION_ERROR",
        ...     factor_name="MOM_20",
        ...     stock_code="000001",
        ...     reason="数据包含NaN值"
        ... )
    """
    pass


# 向后兼容别名
FeatureComputationError = FeatureCalculationError


class FeatureStorageError(FeatureError):
    """特征存储错误

    当特征保存到存储系统失败时抛出。

    Examples:
        >>> raise FeatureStorageError(
        ...     "特征保存失败",
        ...     error_code="FEATURE_SAVE_ERROR",
        ...     file_path="/data/features/000001.parquet",
        ...     format="parquet"
        ... )
    """
    pass


class FeatureCacheError(FeatureError):
    """特征缓存错误

    当特征缓存操作失败时抛出。

    Examples:
        >>> raise FeatureCacheError(
        ...     "特征缓存读取失败",
        ...     error_code="CACHE_READ_ERROR",
        ...     cache_key="features_000001_20240101_20241231"
        ... )
    """
    pass


# ==================== 模型相关异常 ====================

class ModelError(StockAnalysisError):
    """模型相关异常基类

    所有与机器学习模型相关的异常都应继承此类。
    """
    pass


class ModelTrainingError(ModelError):
    """模型训练错误

    当模型训练过程中发生错误时抛出。

    Examples:
        >>> raise ModelTrainingError(
        ...     "LightGBM训练失败",
        ...     error_code="TRAINING_FAILED",
        ...     model_type="LightGBM",
        ...     n_samples=1000,
        ...     n_features=125,
        ...     reason="数据包含无穷值"
        ... )
    """
    pass


class ModelPredictionError(ModelError):
    """模型预测错误

    当模型预测过程中发生错误时抛出。

    Examples:
        >>> raise ModelPredictionError(
        ...     "模型预测失败",
        ...     error_code="PREDICTION_FAILED",
        ...     model_name="lgb_model_v1",
        ...     input_shape=(100, 125),
        ...     reason="特征维度不匹配"
        ... )
    """
    pass


class ModelNotFoundError(ModelError):
    """模型不存在异常

    当请求的模型文件或注册模型不存在时抛出。

    Examples:
        >>> raise ModelNotFoundError(
        ...     "模型文件不存在",
        ...     error_code="MODEL_FILE_NOT_FOUND",
        ...     model_path="/models/lgb_model_v1.pkl",
        ...     model_name="lgb_model_v1"
        ... )
    """
    pass


class ModelValidationError(ModelError):
    """模型验证错误

    当模型验证失败时抛出。

    Examples:
        >>> raise ModelValidationError(
        ...     "模型性能不达标",
        ...     error_code="MODEL_PERFORMANCE_LOW",
        ...     metric="sharpe_ratio",
        ...     actual_value=0.5,
        ...     threshold=1.0
        ... )
    """
    pass


# ==================== 分析相关异常 ====================

class AnalysisError(StockAnalysisError):
    """分析相关异常基类

    所有与因子分析、IC计算、回测分析相关的异常都应继承此类。

    Examples:
        >>> raise AnalysisError(
        ...     "IC分析失败",
        ...     error_code="IC_ANALYSIS_ERROR",
        ...     factor_name="MOM_20",
        ...     reason="数据不足"
        ... )
    """
    pass


# ==================== 网络相关异常 ====================

class NetworkError(StockAnalysisError):
    """网络相关异常基类

    所有与网络请求、API调用相关的异常都应继承此类。

    Examples:
        >>> raise NetworkError(
        ...     "API请求超时",
        ...     error_code="API_TIMEOUT",
        ...     url="https://api.example.com/stock",
        ...     timeout=30
        ... )
    """
    pass


# ==================== 策略和回测相关异常 ====================

class StrategyError(StockAnalysisError):
    """策略相关异常基类

    所有与交易策略相关的异常都应继承此类。
    """
    pass


class SignalGenerationError(StrategyError):
    """信号生成错误

    当策略信号生成失败时抛出。

    Examples:
        >>> raise SignalGenerationError(
        ...     "动量策略信号生成失败",
        ...     error_code="SIGNAL_GEN_ERROR",
        ...     strategy_name="MomentumStrategy",
        ...     stock_code="000001",
        ...     reason="特征值全为NaN"
        ... )
    """
    pass


class BacktestError(StockAnalysisError):
    """回测相关异常基类

    所有与策略回测相关的异常都应继承此类。
    """
    pass


class BacktestExecutionError(BacktestError):
    """回测执行错误

    当回测执行过程中发生错误时抛出。

    Examples:
        >>> raise BacktestExecutionError(
        ...     "回测执行失败",
        ...     error_code="BACKTEST_EXEC_ERROR",
        ...     strategy="MomentumStrategy",
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-31",
        ...     reason="信号数据缺失"
        ... )
    """
    pass


# ==================== 配置相关异常 ====================

class ConfigError(StockAnalysisError):
    """配置相关异常基类

    所有与配置管理相关的异常都应继承此类。
    """
    pass


class ConfigValidationError(ConfigError):
    """配置验证错误

    当配置参数验证失败时抛出。

    Examples:
        >>> raise ConfigValidationError(
        ...     "配置参数无效",
        ...     error_code="INVALID_CONFIG_VALUE",
        ...     param_name="initial_capital",
        ...     param_value=-1000,
        ...     constraint="必须为正数"
        ... )
    """
    pass


class ConfigFileNotFoundError(ConfigError):
    """配置文件不存在异常

    当配置文件路径不存在时抛出。

    Examples:
        >>> raise ConfigFileNotFoundError(
        ...     "配置文件不存在",
        ...     error_code="CONFIG_FILE_NOT_FOUND",
        ...     file_path="/config/settings.yaml"
        ... )
    """
    pass


# ==================== 风险管理相关异常 ====================

class RiskManagementError(StockAnalysisError):
    """风险管理相关异常基类

    所有与风险控制相关的异常都应继承此类。
    """
    pass


class RiskLimitExceededError(RiskManagementError):
    """风险限制超出异常

    当交易或持仓超出风险限制时抛出。

    Examples:
        >>> raise RiskLimitExceededError(
        ...     "单股持仓超过风险限制",
        ...     error_code="POSITION_LIMIT_EXCEEDED",
        ...     stock_code="000001",
        ...     current_position=0.25,
        ...     limit=0.20
        ... )
    """
    pass


class DrawdownExceededError(RiskManagementError):
    """回撤超限异常

    当账户回撤超过预设阈值时抛出。

    Examples:
        >>> raise DrawdownExceededError(
        ...     "最大回撤超过阈值",
        ...     error_code="MAX_DRAWDOWN_EXCEEDED",
        ...     current_drawdown=0.25,
        ...     threshold=0.20
        ... )
    """
    pass


# ==================== 导出列表 ====================

__all__ = [
    # 基础异常
    'StockAnalysisError',

    # 数据相关异常
    'DataError',
    'DataNotFoundError',
    'DataValidationError',
    'DataProviderError',
    'DataSourceError',  # 向后兼容
    'PipelineError',
    'InsufficientDataError',

    # 数据库相关异常
    'DatabaseError',
    'DatabaseConnectionError',
    'ConnectionError',  # 向后兼容
    'QueryError',

    # 特征工程相关异常
    'FeatureError',
    'FeatureCalculationError',
    'FeatureComputationError',  # 向后兼容
    'FeatureStorageError',
    'FeatureCacheError',

    # 模型相关异常
    'ModelError',
    'ModelTrainingError',
    'ModelPredictionError',
    'ModelNotFoundError',
    'ModelValidationError',

    # 分析相关异常
    'AnalysisError',

    # 网络相关异常
    'NetworkError',

    # 策略和回测相关异常
    'StrategyError',
    'SignalGenerationError',
    'BacktestError',
    'BacktestExecutionError',

    # 配置相关异常
    'ConfigError',
    'ConfigValidationError',
    'ConfigFileNotFoundError',

    # 风险管理相关异常
    'RiskManagementError',
    'RiskLimitExceededError',
    'DrawdownExceededError',
]
