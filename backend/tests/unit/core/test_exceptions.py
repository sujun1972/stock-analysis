"""
自定义异常类单元测试
测试异常类的结构和功能
"""

import pytest

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
    get_exception_class,
)


class TestBackendError:
    """测试基类异常 BackendError"""

    def test_basic_exception(self):
        """测试基本异常创建"""
        exc = BackendError("测试错误")
        assert exc.message == "测试错误"
        assert exc.error_code == "BACKEND"  # 自动生成
        assert exc.context == {}

    def test_exception_with_error_code(self):
        """测试带 error_code 的异常"""
        exc = BackendError("测试错误", error_code="CUSTOM_ERROR")
        assert exc.message == "测试错误"
        assert exc.error_code == "CUSTOM_ERROR"

    def test_exception_with_context(self):
        """测试带上下文的异常"""
        exc = BackendError(
            "测试错误",
            error_code="TEST_ERROR",
            user_id=123,
            operation="test"
        )
        assert exc.context["user_id"] == 123
        assert exc.context["operation"] == "test"

    def test_to_dict(self):
        """测试 to_dict 方法"""
        exc = BackendError(
            "测试错误",
            error_code="TEST_ERROR",
            user_id=123
        )
        result = exc.to_dict()
        assert result["message"] == "测试错误"
        assert result["error_code"] == "TEST_ERROR"
        assert result["user_id"] == 123

    def test_str_representation(self):
        """测试字符串表示"""
        exc = BackendError(
            "测试错误",
            error_code="TEST_ERROR",
            stock_code="000001"
        )
        result = str(exc)
        assert "[TEST_ERROR]" in result
        assert "测试错误" in result
        assert "stock_code" in result

    def test_repr(self):
        """测试 repr 表示"""
        exc = BackendError("测试错误", error_code="TEST")
        result = repr(exc)
        assert "BackendError" in result
        assert "测试错误" in result


class TestErrorCodeGeneration:
    """测试错误代码自动生成"""

    def test_data_query_error_code(self):
        """测试 DataQueryError 错误代码生成"""
        exc = DataQueryError("查询失败")
        assert exc.error_code == "DATA_QUERY"

    def test_data_not_found_error_code(self):
        """测试 DataNotFoundError 错误代码生成"""
        exc = DataNotFoundError("数据不存在")
        assert exc.error_code == "DATA_NOT_FOUND"

    def test_strategy_execution_error_code(self):
        """测试 StrategyExecutionError 错误代码生成"""
        exc = StrategyExecutionError("策略失败")
        assert exc.error_code == "STRATEGY_EXECUTION"

    def test_database_connection_error_code(self):
        """测试 DatabaseConnectionError 错误代码生成"""
        exc = DatabaseConnectionError("连接失败")
        assert exc.error_code == "DATABASE_CONNECTION"


class TestDataExceptions:
    """测试数据相关异常"""

    def test_data_query_error(self):
        """测试 DataQueryError"""
        exc = DataQueryError(
            "查询失败",
            stock_code="000001",
            table="stock_daily"
        )
        assert exc.message == "查询失败"
        assert exc.context["stock_code"] == "000001"
        assert exc.context["table"] == "stock_daily"

    def test_data_not_found_error(self):
        """测试 DataNotFoundError"""
        exc = DataNotFoundError(
            "股票不存在",
            stock_code="999999"
        )
        assert exc.message == "股票不存在"
        assert exc.context["stock_code"] == "999999"

    def test_insufficient_data_error(self):
        """测试 InsufficientDataError"""
        exc = InsufficientDataError(
            "数据不足",
            required_points=20,
            actual_points=10
        )
        assert exc.context["required_points"] == 20
        assert exc.context["actual_points"] == 10


class TestValidationError:
    """测试验证异常"""

    def test_validation_error(self):
        """测试 ValidationError"""
        exc = ValidationError(
            "参数错误",
            field="stock_code",
            expected="6位数字",
            actual="ABC"
        )
        assert exc.context["field"] == "stock_code"
        assert exc.context["expected"] == "6位数字"


class TestStrategyExceptions:
    """测试策略相关异常"""

    def test_strategy_execution_error(self):
        """测试 StrategyExecutionError"""
        exc = StrategyExecutionError(
            "策略执行失败",
            strategy_name="动量策略",
            reason="数据不足"
        )
        assert exc.context["strategy_name"] == "动量策略"

    def test_signal_generation_error(self):
        """测试 SignalGenerationError"""
        exc = SignalGenerationError(
            "信号生成失败",
            signal_type="buy"
        )
        assert exc.context["signal_type"] == "buy"


class TestBacktestExceptions:
    """测试回测相关异常"""

    def test_backtest_error(self):
        """测试 BacktestError"""
        exc = BacktestError(
            "回测失败",
            strategy="动量策略"
        )
        assert exc.context["strategy"] == "动量策略"

    def test_backtest_execution_error(self):
        """测试 BacktestExecutionError"""
        exc = BacktestExecutionError(
            "回测引擎失败",
            error_message="内存不足"
        )
        assert exc.context["error_message"] == "内存不足"


class TestCalculationExceptions:
    """测试计算相关异常"""

    def test_calculation_error(self):
        """测试 CalculationError"""
        exc = CalculationError(
            "计算失败",
            indicator="sharpe_ratio"
        )
        assert exc.context["indicator"] == "sharpe_ratio"

    def test_feature_calculation_error(self):
        """测试 FeatureCalculationError"""
        exc = FeatureCalculationError(
            "特征计算失败",
            feature_name="MA_20"
        )
        assert exc.context["feature_name"] == "MA_20"


class TestDatabaseExceptions:
    """测试数据库相关异常"""

    def test_database_error(self):
        """测试 DatabaseError"""
        exc = DatabaseError(
            "数据库错误",
            operation="insert",
            table="stock_daily"
        )
        assert exc.context["operation"] == "insert"

    def test_database_connection_error(self):
        """测试 DatabaseConnectionError"""
        exc = DatabaseConnectionError(
            "连接失败",
            host="localhost",
            port=5432
        )
        assert exc.context["host"] == "localhost"
        assert exc.context["port"] == 5432

    def test_query_error(self):
        """测试 QueryError"""
        exc = QueryError(
            "SQL错误",
            table="stock_daily",
            error_message="语法错误"
        )
        assert exc.context["table"] == "stock_daily"


class TestExternalAPIExceptions:
    """测试外部 API 相关异常"""

    def test_external_api_error(self):
        """测试 ExternalAPIError"""
        exc = ExternalAPIError(
            "API失败",
            api_name="akshare",
            endpoint="/stock/hist"
        )
        assert exc.context["api_name"] == "akshare"

    def test_api_rate_limit_error(self):
        """测试 APIRateLimitError"""
        exc = APIRateLimitError(
            "频率限制",
            retry_after=60
        )
        assert exc.retry_after == 60
        assert exc.context["retry_after"] == 60

    def test_api_rate_limit_custom_retry(self):
        """测试 APIRateLimitError 自定义重试时间"""
        exc = APIRateLimitError(
            "频率限制",
            retry_after=120,
            api_name="test"
        )
        assert exc.retry_after == 120

    def test_api_timeout_error(self):
        """测试 APITimeoutError"""
        exc = APITimeoutError(
            "请求超时",
            timeout=30
        )
        assert exc.context["timeout"] == 30


class TestConfigExceptions:
    """测试配置相关异常"""

    def test_config_error(self):
        """测试 ConfigError"""
        exc = ConfigError(
            "配置错误",
            config_file="config.yaml"
        )
        assert exc.context["config_file"] == "config.yaml"

    def test_config_validation_error(self):
        """测试 ConfigValidationError"""
        exc = ConfigValidationError(
            "配置验证失败",
            field="port",
            expected="1-65535",
            actual=0
        )
        assert exc.context["field"] == "port"


class TestSyncExceptions:
    """测试数据同步相关异常"""

    def test_data_sync_error(self):
        """测试 DataSyncError"""
        exc = DataSyncError(
            "同步失败",
            stock_code="000001",
            sync_type="daily"
        )
        assert exc.context["stock_code"] == "000001"
        assert exc.context["sync_type"] == "daily"

    def test_sync_task_error(self):
        """测试 SyncTaskError"""
        exc = SyncTaskError(
            "任务失败",
            task_name="daily_sync"
        )
        assert exc.context["task_name"] == "daily_sync"


class TestPermissionError:
    """测试权限异常"""

    def test_permission_error(self):
        """测试 PermissionError"""
        exc = PermissionError(
            "权限不足",
            user_id=123,
            required_role="admin"
        )
        assert exc.context["user_id"] == 123
        assert exc.context["required_role"] == "admin"


class TestExceptionInheritance:
    """测试异常继承关系"""

    def test_data_not_found_inherits_from_data_query(self):
        """测试 DataNotFoundError 继承自 DataQueryError"""
        exc = DataNotFoundError("测试")
        assert isinstance(exc, DataNotFoundError)
        assert isinstance(exc, DataQueryError)
        assert isinstance(exc, BackendError)
        assert isinstance(exc, Exception)

    def test_signal_generation_inherits_from_strategy(self):
        """测试 SignalGenerationError 继承自 StrategyExecutionError"""
        exc = SignalGenerationError("测试")
        assert isinstance(exc, SignalGenerationError)
        assert isinstance(exc, StrategyExecutionError)

    def test_feature_calculation_inherits_from_calculation(self):
        """测试 FeatureCalculationError 继承自 CalculationError"""
        exc = FeatureCalculationError("测试")
        assert isinstance(exc, FeatureCalculationError)
        assert isinstance(exc, CalculationError)


class TestGetExceptionClass:
    """测试 get_exception_class 工具函数"""

    def test_get_data_query_exception(self):
        """测试获取 DataQueryError 类"""
        cls = get_exception_class("data_query")
        assert cls == DataQueryError

    def test_get_validation_exception(self):
        """测试获取 ValidationError 类"""
        cls = get_exception_class("validation")
        assert cls == ValidationError

    def test_get_database_exception(self):
        """测试获取 DatabaseError 类"""
        cls = get_exception_class("database")
        assert cls == DatabaseError

    def test_get_sync_exception(self):
        """测试获取 DataSyncError 类"""
        cls = get_exception_class("sync")
        assert cls == DataSyncError

    def test_invalid_exception_type_raises_key_error(self):
        """测试无效的异常类型抛出 KeyError"""
        with pytest.raises(KeyError):
            get_exception_class("invalid_type")

    def test_use_get_exception_class_to_raise(self):
        """测试使用 get_exception_class 抛出异常"""
        cls = get_exception_class("data_not_found")
        exc = cls("股票不存在", stock_code="000001")
        assert isinstance(exc, DataNotFoundError)
        assert exc.context["stock_code"] == "000001"
