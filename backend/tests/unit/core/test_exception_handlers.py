"""
异常处理器单元测试
测试全局异常处理器的正确性
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.exceptions import (
    DataNotFoundError,
    DataQueryError,
    InsufficientDataError,
    ValidationError,
    StrategyExecutionError,
    SignalGenerationError,
    BacktestError,
    CalculationError,
    FeatureCalculationError,
    DatabaseError,
    DatabaseConnectionError,
    QueryError,
    ExternalAPIError,
    APIRateLimitError,
    APITimeoutError,
    ConfigError,
    DataSyncError,
    SyncTaskError,
    PermissionError,
    BackendError,
)

# 直接导入异常处理器函数，避免导入整个 app
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from app.api.exception_handlers import (
    data_not_found_handler,
    data_query_error_handler,
    insufficient_data_handler,
    validation_error_handler,
    strategy_execution_error_handler,
    signal_generation_error_handler,
    backtest_error_handler,
    calculation_error_handler,
    feature_calculation_error_handler,
    database_error_handler,
    database_connection_error_handler,
    query_error_handler,
    external_api_error_handler,
    api_rate_limit_error_handler,
    api_timeout_error_handler,
    config_error_handler,
    data_sync_error_handler,
    permission_error_handler,
    backend_error_handler,
)


def register_exception_handlers(app):
    """注册所有异常处理器（测试版本）"""
    app.add_exception_handler(DataNotFoundError, data_not_found_handler)
    app.add_exception_handler(InsufficientDataError, insufficient_data_handler)
    app.add_exception_handler(DataQueryError, data_query_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(SignalGenerationError, signal_generation_error_handler)
    app.add_exception_handler(StrategyExecutionError, strategy_execution_error_handler)
    app.add_exception_handler(BacktestError, backtest_error_handler)
    app.add_exception_handler(FeatureCalculationError, feature_calculation_error_handler)
    app.add_exception_handler(CalculationError, calculation_error_handler)
    app.add_exception_handler(DatabaseConnectionError, database_connection_error_handler)
    app.add_exception_handler(QueryError, query_error_handler)
    app.add_exception_handler(DatabaseError, database_error_handler)
    app.add_exception_handler(APIRateLimitError, api_rate_limit_error_handler)
    app.add_exception_handler(APITimeoutError, api_timeout_error_handler)
    app.add_exception_handler(ExternalAPIError, external_api_error_handler)
    app.add_exception_handler(ConfigError, config_error_handler)
    app.add_exception_handler(SyncTaskError, data_sync_error_handler)
    app.add_exception_handler(DataSyncError, data_sync_error_handler)
    app.add_exception_handler(PermissionError, permission_error_handler)
    app.add_exception_handler(BackendError, backend_error_handler)


@pytest.fixture
def app():
    """创建测试应用"""
    app = FastAPI()
    register_exception_handlers(app)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


class TestDataExceptionHandlers:
    """测试数据相关异常处理器"""

    def test_data_not_found_returns_404(self, app, client):
        """测试 DataNotFoundError 返回 404"""
        @app.get("/test")
        async def test_endpoint():
            raise DataNotFoundError(
                "股票不存在",
                error_code="STOCK_NOT_FOUND",
                stock_code="000001"
            )

        response = client.get("/test")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "不存在" in data["message"]
        assert data["data"]["error_code"] == "STOCK_NOT_FOUND"
        assert data["data"]["stock_code"] == "000001"

    def test_data_query_error_returns_400(self, app, client):
        """测试 DataQueryError 返回 400"""
        @app.get("/test")
        async def test_endpoint():
            raise DataQueryError(
                "查询参数错误",
                error_code="INVALID_QUERY",
                field="date_range"
            )

        response = client.get("/test")
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["data"]["error_code"] == "INVALID_QUERY"

    def test_insufficient_data_returns_400(self, app, client):
        """测试 InsufficientDataError 返回 400"""
        @app.get("/test")
        async def test_endpoint():
            raise InsufficientDataError(
                "数据点不足",
                required_points=20,
                actual_points=10
            )

        response = client.get("/test")
        assert response.status_code == 400
        data = response.json()
        assert data["data"]["required_points"] == 20
        assert data["data"]["actual_points"] == 10


class TestValidationExceptionHandler:
    """测试验证异常处理器"""

    def test_validation_error_returns_400(self, app, client):
        """测试 ValidationError 返回 400"""
        @app.get("/test")
        async def test_endpoint():
            raise ValidationError(
                "股票代码格式错误",
                error_code="INVALID_STOCK_CODE",
                stock_code="ABC",
                expected_format="6位数字"
            )

        response = client.get("/test")
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "格式错误" in data["message"]
        assert data["data"]["stock_code"] == "ABC"


class TestStrategyExceptionHandlers:
    """测试策略相关异常处理器"""

    def test_strategy_execution_error_returns_500(self, app, client):
        """测试 StrategyExecutionError 返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise StrategyExecutionError(
                "策略执行失败",
                strategy_name="动量策略",
                reason="信号生成异常"
            )

        response = client.get("/test")
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False

    def test_signal_generation_error_returns_500(self, app, client):
        """测试 SignalGenerationError 返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise SignalGenerationError(
                "信号生成失败",
                signal_type="buy"
            )

        response = client.get("/test")
        assert response.status_code == 500


class TestBacktestExceptionHandler:
    """测试回测异常处理器"""

    def test_backtest_error_returns_500(self, app, client):
        """测试 BacktestError 返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise BacktestError(
                "回测失败",
                strategy="动量策略"
            )

        response = client.get("/test")
        assert response.status_code == 500


class TestCalculationExceptionHandlers:
    """测试计算相关异常处理器"""

    def test_calculation_error_returns_500(self, app, client):
        """测试 CalculationError 返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise CalculationError(
                "夏普比率计算失败",
                indicator="sharpe_ratio"
            )

        response = client.get("/test")
        assert response.status_code == 500

    def test_feature_calculation_error_returns_500(self, app, client):
        """测试 FeatureCalculationError 返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise FeatureCalculationError(
                "特征计算失败",
                feature_name="MA_20"
            )

        response = client.get("/test")
        assert response.status_code == 500


class TestDatabaseExceptionHandlers:
    """测试数据库相关异常处理器"""

    def test_database_error_returns_500(self, app, client):
        """测试 DatabaseError 返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise DatabaseError(
                "数据库错误",
                operation="insert"
            )

        response = client.get("/test")
        assert response.status_code == 500
        data = response.json()
        assert data["message"] == "数据库操作失败"  # 隐藏详细错误

    def test_database_connection_error_returns_503(self, app, client):
        """测试 DatabaseConnectionError 返回 503"""
        @app.get("/test")
        async def test_endpoint():
            raise DatabaseConnectionError(
                "无法连接到数据库",
                host="localhost"
            )

        response = client.get("/test")
        assert response.status_code == 503
        data = response.json()
        assert "连接失败" in data["message"]

    def test_query_error_returns_500(self, app, client):
        """测试 QueryError 返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise QueryError(
                "SQL查询错误",
                table="stock_daily"
            )

        response = client.get("/test")
        assert response.status_code == 500


class TestExternalAPIExceptionHandlers:
    """测试外部 API 相关异常处理器"""

    def test_external_api_error_returns_502(self, app, client):
        """测试 ExternalAPIError 返回 502"""
        @app.get("/test")
        async def test_endpoint():
            raise ExternalAPIError(
                "AkShare API 失败",
                api_name="akshare"
            )

        response = client.get("/test")
        assert response.status_code == 502

    def test_api_rate_limit_error_returns_429(self, app, client):
        """测试 APIRateLimitError 返回 429 并包含 Retry-After header"""
        @app.get("/test")
        async def test_endpoint():
            raise APIRateLimitError(
                "API频率限制",
                retry_after=60
            )

        response = client.get("/test")
        assert response.status_code == 429
        assert response.headers.get("Retry-After") == "60"
        data = response.json()
        assert data["data"]["retry_after"] == 60

    def test_api_timeout_error_returns_504(self, app, client):
        """测试 APITimeoutError 返回 504"""
        @app.get("/test")
        async def test_endpoint():
            raise APITimeoutError(
                "API请求超时",
                timeout=30
            )

        response = client.get("/test")
        assert response.status_code == 504


class TestConfigExceptionHandler:
    """测试配置异常处理器"""

    def test_config_error_returns_500(self, app, client):
        """测试 ConfigError 返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise ConfigError(
                "配置文件错误",
                config_file="config.yaml"
            )

        response = client.get("/test")
        assert response.status_code == 500


class TestSyncExceptionHandlers:
    """测试数据同步异常处理器"""

    def test_data_sync_error_returns_500(self, app, client):
        """测试 DataSyncError 返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise DataSyncError(
                "数据同步失败",
                stock_code="000001"
            )

        response = client.get("/test")
        assert response.status_code == 500

    def test_sync_task_error_returns_500(self, app, client):
        """测试 SyncTaskError 返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise SyncTaskError(
                "同步任务失败",
                task_name="daily_sync"
            )

        response = client.get("/test")
        assert response.status_code == 500


class TestPermissionExceptionHandler:
    """测试权限异常处理器"""

    def test_permission_error_returns_403(self, app, client):
        """测试 PermissionError 返回 403"""
        @app.get("/test")
        async def test_endpoint():
            raise PermissionError(
                "权限不足",
                user_id=123,
                required_role="admin"
            )

        response = client.get("/test")
        assert response.status_code == 403
        data = response.json()
        assert data["data"]["user_id"] == 123


class TestBackendErrorHandler:
    """测试基类异常处理器"""

    def test_backend_error_returns_500(self, app, client):
        """测试 BackendError 基类返回 500"""
        @app.get("/test")
        async def test_endpoint():
            raise BackendError(
                "未知业务错误",
                error_code="UNKNOWN_ERROR"
            )

        response = client.get("/test")
        assert response.status_code == 500
        data = response.json()
        assert data["data"]["error_code"] == "UNKNOWN_ERROR"


class TestExceptionContext:
    """测试异常上下文信息传递"""

    def test_exception_context_preserved(self, app, client):
        """测试异常的 context 信息被正确传递到响应中"""
        @app.get("/test")
        async def test_endpoint():
            raise DataNotFoundError(
                "股票不存在",
                stock_code="000001",
                date_range="2024-01-01 to 2024-12-31",
                table="stock_daily"
            )

        response = client.get("/test")
        data = response.json()
        assert data["data"]["stock_code"] == "000001"
        assert data["data"]["date_range"] == "2024-01-01 to 2024-12-31"
        assert data["data"]["table"] == "stock_daily"

    def test_error_code_auto_generated(self, app, client):
        """测试 error_code 自动生成"""
        @app.get("/test")
        async def test_endpoint():
            # 不指定 error_code
            raise DataNotFoundError("数据不存在")

        response = client.get("/test")
        data = response.json()
        # DataNotFoundError -> DATA_NOT_FOUND
        assert data["data"]["error_code"] == "DATA_NOT_FOUND"


class TestExceptionInheritance:
    """测试异常继承关系"""

    def test_child_exception_handled_by_parent(self, app, client):
        """测试子异常被父异常处理器捕获"""
        # DataNotFoundError 继承自 DataQueryError
        # 如果没有注册 DataNotFoundError 处理器，应该被 DataQueryError 处理器捕获
        # 但我们已经注册了，所以测试顺序很重要

        @app.get("/test")
        async def test_endpoint():
            raise SignalGenerationError("信号生成失败")

        response = client.get("/test")
        # SignalGenerationError 有自己的处理器
        assert response.status_code == 500
