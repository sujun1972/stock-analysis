"""
统一的异常处理系统

提供类型安全的异常类层次结构，便于错误追踪和处理
"""


class StockAnalysisError(Exception):
    """所有自定义异常的基类"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# ==================== 数据相关异常 ====================

class DataError(StockAnalysisError):
    """数据相关异常基类"""
    pass


class DataNotFoundError(DataError):
    """数据不存在"""
    pass


class DataValidationError(DataError):
    """数据验证失败"""
    pass


class DataSourceError(DataError):
    """数据源错误"""
    pass


class PipelineError(DataError):
    """数据流水线错误"""
    pass


# ==================== 数据库相关异常 ====================

class DatabaseError(StockAnalysisError):
    """数据库相关异常基类"""
    pass


class ConnectionError(DatabaseError):
    """数据库连接错误"""
    pass


class QueryError(DatabaseError):
    """SQL查询错误"""
    pass


# ==================== 特征工程相关异常 ====================

class FeatureError(StockAnalysisError):
    """特征工程相关异常基类"""
    pass


class FeatureComputationError(FeatureError):
    """特征计算错误"""
    pass


class FeatureCacheError(FeatureError):
    """特征缓存错误"""
    pass


# ==================== 模型相关异常 ====================

class ModelError(StockAnalysisError):
    """模型相关异常基类"""
    pass


class ModelTrainingError(ModelError):
    """模型训练错误"""
    pass


class ModelPredictionError(ModelError):
    """模型预测错误"""
    pass


class ModelNotFoundError(ModelError):
    """模型不存在"""
    pass


# ==================== 回测相关异常 ====================

class BacktestError(StockAnalysisError):
    """回测相关异常基类"""
    pass


class StrategyError(BacktestError):
    """策略执行错误"""
    pass


# ==================== 配置相关异常 ====================

class ConfigError(StockAnalysisError):
    """配置相关异常基类"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证错误"""
    pass
