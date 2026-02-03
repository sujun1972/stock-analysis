"""
全局异常处理器
统一处理所有自定义异常，返回一致的 API 响应格式
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.exceptions import (
    BackendError,
    DataQueryError,
    DataNotFoundError,
    InsufficientDataError,
    ValidationError,
    StrategyExecutionError,
    SignalGenerationError,
    BacktestError,
    BacktestExecutionError,
    CalculationError,
    FeatureCalculationError,
    DatabaseError,
    DatabaseConnectionError,
    QueryError,
    ExternalAPIError,
    APIRateLimitError,
    APITimeoutError,
    ConfigError,
    ConfigValidationError,
    DataSyncError,
    SyncTaskError,
    PermissionError,
)
from app.models.api_response import ApiResponse


# ==================== 数据相关异常处理器 ====================


async def data_not_found_handler(request: Request, exc: DataNotFoundError) -> JSONResponse:
    """处理数据不存在异常 (404)"""
    logger.warning(f"数据不存在: {exc.message}", extra=exc.context)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ApiResponse.not_found(
            message=exc.message,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


async def data_query_error_handler(request: Request, exc: DataQueryError) -> JSONResponse:
    """处理数据查询异常 (400)"""
    logger.warning(f"数据查询失败: {exc.message}", extra=exc.context)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ApiResponse.error(
            message=exc.message,
            code=400,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


async def insufficient_data_handler(request: Request, exc: InsufficientDataError) -> JSONResponse:
    """处理数据不足异常 (400)"""
    logger.warning(f"数据不足: {exc.message}", extra=exc.context)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ApiResponse.error(
            message=exc.message,
            code=400,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


# ==================== 验证相关异常处理器 ====================


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """处理验证异常 (400)"""
    logger.warning(f"验证失败: {exc.message}", extra=exc.context)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ApiResponse.error(
            message=exc.message,
            code=400,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


# ==================== 策略相关异常处理器 ====================


async def strategy_execution_error_handler(request: Request, exc: StrategyExecutionError) -> JSONResponse:
    """处理策略执行异常 (500)"""
    logger.error(f"策略执行失败: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message=exc.message,
            code=500,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


async def signal_generation_error_handler(request: Request, exc: SignalGenerationError) -> JSONResponse:
    """处理信号生成异常 (500)"""
    logger.error(f"信号生成失败: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message=exc.message,
            code=500,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


# ==================== 回测相关异常处理器 ====================


async def backtest_error_handler(request: Request, exc: BacktestError) -> JSONResponse:
    """处理回测异常 (500)"""
    logger.error(f"回测失败: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message=exc.message,
            code=500,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


# ==================== 计算相关异常处理器 ====================


async def calculation_error_handler(request: Request, exc: CalculationError) -> JSONResponse:
    """处理计算异常 (500)"""
    logger.error(f"计算失败: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message=exc.message,
            code=500,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


async def feature_calculation_error_handler(request: Request, exc: FeatureCalculationError) -> JSONResponse:
    """处理特征计算异常 (500)"""
    logger.error(f"特征计算失败: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message=exc.message,
            code=500,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


# ==================== 数据库相关异常处理器 ====================


async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """处理数据库异常 (500)"""
    logger.error(f"数据库错误: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message="数据库操作失败",
            code=500,
            data={"error_code": exc.error_code}
        ).to_dict()
    )


async def database_connection_error_handler(request: Request, exc: DatabaseConnectionError) -> JSONResponse:
    """处理数据库连接异常 (503)"""
    logger.error(f"数据库连接失败: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ApiResponse.error(
            message="数据库连接失败，请稍后重试",
            code=503,
            data={"error_code": exc.error_code}
        ).to_dict()
    )


async def query_error_handler(request: Request, exc: QueryError) -> JSONResponse:
    """处理 SQL 查询异常 (500)"""
    logger.error(f"SQL 查询失败: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message="数据查询失败",
            code=500,
            data={"error_code": exc.error_code}
        ).to_dict()
    )


# ==================== 外部 API 相关异常处理器 ====================


async def external_api_error_handler(request: Request, exc: ExternalAPIError) -> JSONResponse:
    """处理外部 API 异常 (502)"""
    logger.error(f"外部 API 调用失败: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ApiResponse.error(
            message=exc.message,
            code=502,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


async def api_rate_limit_error_handler(request: Request, exc: APIRateLimitError) -> JSONResponse:
    """处理 API 频率限制异常 (429)"""
    logger.warning(f"API 频率限制: {exc.message}", extra=exc.context)
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ApiResponse.error(
            message=exc.message,
            code=429,
            data={"error_code": exc.error_code, "retry_after": exc.retry_after, **exc.context}
        ).to_dict()
    )
    response.headers["Retry-After"] = str(exc.retry_after)
    return response


async def api_timeout_error_handler(request: Request, exc: APITimeoutError) -> JSONResponse:
    """处理 API 超时异常 (504)"""
    logger.error(f"API 请求超时: {exc.message}", extra=exc.context)
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content=ApiResponse.error(
            message=exc.message,
            code=504,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


# ==================== 配置相关异常处理器 ====================


async def config_error_handler(request: Request, exc: ConfigError) -> JSONResponse:
    """处理配置异常 (500)"""
    logger.error(f"配置错误: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message=exc.message,
            code=500,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


# ==================== 数据同步相关异常处理器 ====================


async def data_sync_error_handler(request: Request, exc: DataSyncError) -> JSONResponse:
    """处理数据同步异常 (500)"""
    logger.error(f"数据同步失败: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message=exc.message,
            code=500,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


# ==================== 权限相关异常处理器 ====================


async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
    """处理权限异常 (403)"""
    logger.warning(f"权限不足: {exc.message}", extra=exc.context)
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=ApiResponse.error(
            message=exc.message,
            code=403,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


# ==================== 基类异常处理器 ====================


async def backend_error_handler(request: Request, exc: BackendError) -> JSONResponse:
    """处理所有 BackendError 基类异常 (500)"""
    logger.error(f"业务异常: {exc.message}", extra=exc.context, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message=exc.message,
            code=500,
            data={"error_code": exc.error_code, **exc.context}
        ).to_dict()
    )


# ==================== 注册所有异常处理器 ====================


def register_exception_handlers(app):
    """
    注册所有全局异常处理器

    Args:
        app: FastAPI 应用实例

    使用:
        >>> from app.main import app
        >>> register_exception_handlers(app)
    """
    # 数据相关 - 从具体到抽象的顺序注册
    app.add_exception_handler(DataNotFoundError, data_not_found_handler)
    app.add_exception_handler(InsufficientDataError, insufficient_data_handler)
    app.add_exception_handler(DataQueryError, data_query_error_handler)

    # 验证相关
    app.add_exception_handler(ValidationError, validation_error_handler)

    # 策略相关
    app.add_exception_handler(SignalGenerationError, signal_generation_error_handler)
    app.add_exception_handler(StrategyExecutionError, strategy_execution_error_handler)

    # 回测相关
    app.add_exception_handler(BacktestExecutionError, backtest_error_handler)
    app.add_exception_handler(BacktestError, backtest_error_handler)

    # 计算相关
    app.add_exception_handler(FeatureCalculationError, feature_calculation_error_handler)
    app.add_exception_handler(CalculationError, calculation_error_handler)

    # 数据库相关
    app.add_exception_handler(DatabaseConnectionError, database_connection_error_handler)
    app.add_exception_handler(QueryError, query_error_handler)
    app.add_exception_handler(DatabaseError, database_error_handler)

    # 外部 API 相关
    app.add_exception_handler(APIRateLimitError, api_rate_limit_error_handler)
    app.add_exception_handler(APITimeoutError, api_timeout_error_handler)
    app.add_exception_handler(ExternalAPIError, external_api_error_handler)

    # 配置相关
    app.add_exception_handler(ConfigValidationError, config_error_handler)
    app.add_exception_handler(ConfigError, config_error_handler)

    # 同步相关
    app.add_exception_handler(SyncTaskError, data_sync_error_handler)
    app.add_exception_handler(DataSyncError, data_sync_error_handler)

    # 权限相关
    app.add_exception_handler(PermissionError, permission_error_handler)

    # 基类异常处理器（兜底）
    app.add_exception_handler(BackendError, backend_error_handler)

    logger.info("✅ 全局异常处理器注册完成")
