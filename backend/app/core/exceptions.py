"""
Backend 业务异常类

提供结构化的业务异常，支持 error_code 和 context。
与 FastAPI、ApiResponse 完美集成。

使用示例:
    >>> raise DataQueryError(
    ...     "股票数据不存在",
    ...     error_code="STOCK_NOT_FOUND",
    ...     stock_code="000001",
    ...     date_range="2024-01-01至2024-12-31"
    ... )

异常层次结构:
    BackendError (基类)
    ├── DataQueryError - 数据查询失败
    ├── StrategyExecutionError - 策略执行失败
    ├── ValidationError - 数据验证失败
    ├── CalculationError - 计算错误
    ├── DatabaseError - 数据库错误
    └── ExternalAPIError - 外部 API 错误
"""

from typing import Any, Dict, Optional


class BackendError(Exception):
    """
    Backend 业务异常基类

    所有业务异常都应继承此类，支持 error_code 和 context。

    Attributes:
        message: 错误消息（人类可读）
        error_code: 错误代码（大写下划线命名，便于监控和分类）
        context: 错误上下文（字典，包含所有额外信息）

    Examples:
        >>> raise BackendError(
        ...     "操作失败",
        ...     error_code="OPERATION_FAILED",
        ...     user_id=123,
        ...     operation="delete"
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        **context: Any
    ):
        """
        初始化业务异常

        Args:
            message: 错误消息
            error_code: 错误代码（可选，默认为类名转大写下划线）
            **context: 错误上下文（任意关键字参数）
        """
        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.context = context
        super().__init__(message)

    def _generate_error_code(self) -> str:
        """
        从类名生成默认错误代码

        Returns:
            大写下划线格式的错误代码

        Examples:
            DataQueryError -> DATA_QUERY_ERROR
            ValidationError -> VALIDATION_ERROR
        """
        import re
        class_name = self.__class__.__name__
        # 移除 Error 后缀
        if class_name.endswith('Error'):
            class_name = class_name[:-5]
        # 转换驼峰为下划线
        code = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        code = re.sub('([a-z0-9])([A-Z])', r'\1_\2', code)
        return code.upper()

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            包含 message、error_code 和 context 的字典
        """
        return {
            "message": self.message,
            "error_code": self.error_code,
            **self.context
        }

    def __str__(self) -> str:
        """字符串表示"""
        if self.context:
            return f"[{self.error_code}] {self.message} | Context: {self.context}"
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """开发者友好的表示"""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"context={self.context!r})"
        )


# ==================== 数据相关异常 ====================


class DataQueryError(BackendError):
    """
    数据查询失败

    用于数据库查询、数据获取失败等场景。

    Examples:
        >>> raise DataQueryError(
        ...     "股票数据不存在",
        ...     error_code="STOCK_NOT_FOUND",
        ...     stock_code="000001",
        ...     table="stock_daily"
        ... )
    """
    pass


class DataNotFoundError(DataQueryError):
    """
    数据不存在（404 场景）

    继承自 DataQueryError，用于资源不存在的情况。

    Examples:
        >>> raise DataNotFoundError(
        ...     "股票不存在",
        ...     error_code="STOCK_NOT_FOUND",
        ...     stock_code="000001"
        ... )
    """
    pass


class InsufficientDataError(DataQueryError):
    """
    数据不足

    用于数据量不满足计算要求的场景。

    Examples:
        >>> raise InsufficientDataError(
        ...     "数据点不足，无法计算MA20",
        ...     error_code="INSUFFICIENT_DATA",
        ...     required_points=20,
        ...     actual_points=10
        ... )
    """
    pass


# ==================== 验证相关异常 ====================


class ValidationError(BackendError):
    """
    数据验证失败

    用于参数验证、数据格式验证等场景。

    Examples:
        >>> raise ValidationError(
        ...     "股票代码格式不正确",
        ...     error_code="INVALID_STOCK_CODE",
        ...     stock_code="ABC123",
        ...     expected_format="6位数字"
        ... )
    """
    pass


# ==================== 策略相关异常 ====================


class StrategyExecutionError(BackendError):
    """
    策略执行失败

    用于策略运行、信号生成失败等场景。

    Examples:
        >>> raise StrategyExecutionError(
        ...     "策略执行失败",
        ...     error_code="STRATEGY_FAILED",
        ...     strategy_name="动量策略",
        ...     reason="信号生成异常"
        ... )
    """
    pass


class SignalGenerationError(StrategyExecutionError):
    """
    信号生成失败

    继承自 StrategyExecutionError。

    Examples:
        >>> raise SignalGenerationError(
        ...     "买入信号生成失败",
        ...     error_code="SIGNAL_GENERATION_FAILED",
        ...     signal_type="buy",
        ...     stock_code="000001"
        ... )
    """
    pass


# ==================== 回测相关异常 ====================


class BacktestError(BackendError):
    """
    回测相关错误

    用于回测执行、性能分析失败等场景。

    Examples:
        >>> raise BacktestError(
        ...     "回测执行失败",
        ...     error_code="BACKTEST_FAILED",
        ...     strategy="动量策略",
        ...     reason="数据不足"
        ... )
    """
    pass


class BacktestExecutionError(BacktestError):
    """
    回测执行失败

    继承自 BacktestError。

    Examples:
        >>> raise BacktestExecutionError(
        ...     "回测引擎执行失败",
        ...     error_code="BACKTEST_ENGINE_ERROR",
        ...     error_message="内存不足"
        ... )
    """
    pass


# ==================== 计算相关异常 ====================


class CalculationError(BackendError):
    """
    计算错误

    用于数值计算、指标计算失败等场景。

    Examples:
        >>> raise CalculationError(
        ...     "夏普比率计算失败",
        ...     error_code="CALCULATION_FAILED",
        ...     indicator="sharpe_ratio",
        ...     reason="收益率标准差为零"
        ... )
    """
    pass


class FeatureCalculationError(CalculationError):
    """
    特征计算失败

    继承自 CalculationError。

    Examples:
        >>> raise FeatureCalculationError(
        ...     "技术指标计算失败",
        ...     error_code="FEATURE_CALCULATION_FAILED",
        ...     feature_name="MA_20",
        ...     reason="数据点不足"
        ... )
    """
    pass


# ==================== 数据库相关异常 ====================


class DatabaseError(BackendError):
    """
    数据库错误

    用于数据库连接、事务、查询失败等场景。

    Examples:
        >>> raise DatabaseError(
        ...     "数据库连接失败",
        ...     error_code="DB_CONNECTION_FAILED",
        ...     host="localhost",
        ...     port=5432,
        ...     database="stock_analysis"
        ... )
    """
    pass


class DatabaseConnectionError(DatabaseError):
    """
    数据库连接失败

    继承自 DatabaseError。

    Examples:
        >>> raise DatabaseConnectionError(
        ...     "无法连接到 TimescaleDB",
        ...     error_code="DB_CONNECTION_TIMEOUT",
        ...     host="localhost",
        ...     timeout=30
        ... )
    """
    pass


class QueryError(DatabaseError):
    """
    SQL 查询错误

    继承自 DatabaseError。

    Examples:
        >>> raise QueryError(
        ...     "SQL 查询失败",
        ...     error_code="SQL_QUERY_ERROR",
        ...     table="stock_daily",
        ...     error_message="语法错误"
        ... )
    """
    pass


# ==================== 外部 API 相关异常 ====================


class ExternalAPIError(BackendError):
    """
    外部 API 调用失败

    用于调用外部数据源、第三方服务失败等场景。

    Examples:
        >>> raise ExternalAPIError(
        ...     "AkShare API 调用失败",
        ...     error_code="API_REQUEST_FAILED",
        ...     api_name="akshare",
        ...     endpoint="/stock/hist",
        ...     status_code=500
        ... )
    """
    pass


class APIRateLimitError(ExternalAPIError):
    """
    API 频率限制

    继承自 ExternalAPIError。

    Attributes:
        retry_after: 建议重试的秒数

    Examples:
        >>> raise APIRateLimitError(
        ...     "API 调用频率超限",
        ...     error_code="RATE_LIMIT_EXCEEDED",
        ...     api_name="akshare",
        ...     retry_after=60
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        retry_after: int = 60,
        **context: Any
    ):
        """
        初始化频率限制异常

        Args:
            message: 错误消息
            error_code: 错误代码
            retry_after: 建议重试的秒数
            **context: 其他上下文
        """
        context['retry_after'] = retry_after
        super().__init__(message, error_code=error_code, **context)

    @property
    def retry_after(self) -> int:
        """向后兼容属性"""
        return self.context.get('retry_after', 60)


class APITimeoutError(ExternalAPIError):
    """
    API 请求超时

    继承自 ExternalAPIError。

    Examples:
        >>> raise APITimeoutError(
        ...     "API 请求超时",
        ...     error_code="API_TIMEOUT",
        ...     api_name="akshare",
        ...     timeout=30
        ... )
    """
    pass


# ==================== 配置相关异常 ====================


class ConfigError(BackendError):
    """
    配置错误

    用于配置文件、环境变量、参数配置错误等场景。

    Examples:
        >>> raise ConfigError(
        ...     "配置文件格式错误",
        ...     error_code="INVALID_CONFIG",
        ...     config_file="config.yaml",
        ...     reason="缺少必需字段 database.host"
        ... )
    """
    pass


class ConfigValidationError(ConfigError):
    """
    配置验证失败

    继承自 ConfigError。

    Examples:
        >>> raise ConfigValidationError(
        ...     "数据库配置无效",
        ...     error_code="INVALID_DB_CONFIG",
        ...     field="port",
        ...     expected="1-65535",
        ...     actual=0
        ... )
    """
    pass


# ==================== 权限相关异常 ====================


class PermissionError(BackendError):
    """
    权限不足

    用于访问控制、权限验证失败等场景。

    Examples:
        >>> raise PermissionError(
        ...     "无权限访问该资源",
        ...     error_code="PERMISSION_DENIED",
        ...     user_id=123,
        ...     resource="admin_panel",
        ...     required_role="admin"
        ... )
    """
    pass


# ==================== 便捷函数 ====================


def raise_data_query_error(message: str, **context) -> None:
    """快捷抛出数据查询异常"""
    raise DataQueryError(message, **context)


def raise_validation_error(message: str, **context) -> None:
    """快捷抛出验证异常"""
    raise ValidationError(message, **context)


def raise_strategy_error(message: str, **context) -> None:
    """快捷抛出策略异常"""
    raise StrategyExecutionError(message, **context)


def raise_database_error(message: str, **context) -> None:
    """快捷抛出数据库异常"""
    raise DatabaseError(message, **context)


def raise_api_error(message: str, **context) -> None:
    """快捷抛出 API 异常"""
    raise ExternalAPIError(message, **context)


# ==================== 异常类型映射 ====================

# 用于根据场景快速选择异常类型
EXCEPTION_MAP = {
    # 数据相关
    'data_query': DataQueryError,
    'data_not_found': DataNotFoundError,
    'insufficient_data': InsufficientDataError,

    # 验证相关
    'validation': ValidationError,

    # 策略相关
    'strategy': StrategyExecutionError,
    'signal': SignalGenerationError,

    # 回测相关
    'backtest': BacktestError,
    'backtest_execution': BacktestExecutionError,

    # 计算相关
    'calculation': CalculationError,
    'feature': FeatureCalculationError,

    # 数据库相关
    'database': DatabaseError,
    'db_connection': DatabaseConnectionError,
    'query': QueryError,

    # API 相关
    'api': ExternalAPIError,
    'rate_limit': APIRateLimitError,
    'timeout': APITimeoutError,

    # 配置相关
    'config': ConfigError,
    'config_validation': ConfigValidationError,

    # 权限相关
    'permission': PermissionError,
}


def get_exception_class(exception_type: str):
    """
    根据异常类型字符串获取异常类

    Args:
        exception_type: 异常类型（如 'data_query', 'validation'）

    Returns:
        对应的异常类

    Raises:
        KeyError: 如果异常类型不存在

    Examples:
        >>> cls = get_exception_class('data_query')
        >>> raise cls("数据查询失败", stock_code="000001")
    """
    return EXCEPTION_MAP[exception_type]
