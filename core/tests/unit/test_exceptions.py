"""
测试统一异常处理系统

测试 src/exceptions.py 中定义的所有异常类
"""
import pytest
from src.exceptions import (
    # 基础异常
    StockAnalysisError,
    # 数据相关异常
    DataError,
    DataNotFoundError,
    DataValidationError,
    DataProviderError,
    DataSourceError,
    PipelineError,
    InsufficientDataError,
    # 数据库相关异常
    DatabaseError,
    DatabaseConnectionError,
    ConnectionError,
    QueryError,
    # 特征工程相关异常
    FeatureError,
    FeatureCalculationError,
    FeatureComputationError,
    FeatureStorageError,
    FeatureCacheError,
    # 模型相关异常
    ModelError,
    ModelTrainingError,
    ModelPredictionError,
    ModelNotFoundError,
    ModelValidationError,
    # 策略和回测相关异常
    StrategyError,
    SignalGenerationError,
    BacktestError,
    BacktestExecutionError,
    # 配置相关异常
    ConfigError,
    ConfigValidationError,
    ConfigFileNotFoundError,
    # 风险管理相关异常
    RiskManagementError,
    RiskLimitExceededError,
    DrawdownExceededError,
)


class TestStockAnalysisError:
    """测试基础异常类"""

    def test_basic_creation(self):
        """测试基本创建"""
        error = StockAnalysisError("测试错误")
        assert error.message == "测试错误"
        assert error.error_code == "StockAnalysisError"
        assert error.context == {}
        assert error.details == {}  # 向后兼容

    def test_with_error_code(self):
        """测试带错误代码的异常"""
        error = StockAnalysisError(
            "操作失败",
            error_code="OPERATION_FAILED"
        )
        assert error.message == "操作失败"
        assert error.error_code == "OPERATION_FAILED"

    def test_with_context(self):
        """测试带上下文的异常"""
        error = StockAnalysisError(
            "计算失败",
            error_code="CALC_ERROR",
            stock_code="000001",
            factor="MOM_20",
            value=None
        )
        assert error.context == {
            "stock_code": "000001",
            "factor": "MOM_20",
            "value": None
        }
        assert error.details == error.context  # 向后兼容

    def test_str_basic(self):
        """测试字符串表示（基本）"""
        error = StockAnalysisError("测试错误")
        assert str(error) == "测试错误"

    def test_str_with_error_code(self):
        """测试字符串表示（带错误代码）"""
        error = StockAnalysisError(
            "操作失败",
            error_code="OP_FAILED"
        )
        assert str(error) == "操作失败 (error_code=OP_FAILED)"

    def test_str_with_context(self):
        """测试字符串表示（带上下文）"""
        error = StockAnalysisError(
            "计算失败",
            stock_code="000001",
            factor="MOM_20"
        )
        # 上下文信息应该包含在字符串中
        error_str = str(error)
        assert "计算失败" in error_str
        assert "stock_code=000001" in error_str
        assert "factor=MOM_20" in error_str

    def test_str_with_error_code_and_context(self):
        """测试字符串表示（错误代码+上下文）"""
        error = StockAnalysisError(
            "计算失败",
            error_code="CALC_ERROR",
            stock_code="000001"
        )
        error_str = str(error)
        assert "计算失败" in error_str
        assert "error_code=CALC_ERROR" in error_str
        assert "stock_code=000001" in error_str

    def test_to_dict(self):
        """测试转换为字典"""
        error = StockAnalysisError(
            "数据错误",
            error_code="DATA_ERROR",
            stock_code="000001",
            field="close"
        )
        error_dict = error.to_dict()

        assert error_dict == {
            'error_type': 'StockAnalysisError',
            'error_code': 'DATA_ERROR',
            'message': '数据错误',
            'context': {
                'stock_code': '000001',
                'field': 'close'
            }
        }

    def test_raise_and_catch(self):
        """测试抛出和捕获"""
        with pytest.raises(StockAnalysisError) as exc_info:
            raise StockAnalysisError(
                "测试异常",
                error_code="TEST_ERROR",
                test_param="test_value"
            )

        error = exc_info.value
        assert error.message == "测试异常"
        assert error.error_code == "TEST_ERROR"
        assert error.context["test_param"] == "test_value"


class TestDataExceptions:
    """测试数据相关异常"""

    def test_data_error(self):
        """测试数据错误基类"""
        error = DataError("数据错误")
        assert isinstance(error, StockAnalysisError)
        assert error.message == "数据错误"

    def test_data_not_found_error(self):
        """测试数据不存在异常"""
        error = DataNotFoundError(
            "股票数据不存在",
            error_code="STOCK_NOT_FOUND",
            stock_code="999999",
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
        assert isinstance(error, DataError)
        assert error.message == "股票数据不存在"
        assert error.error_code == "STOCK_NOT_FOUND"
        assert error.context["stock_code"] == "999999"

    def test_data_validation_error(self):
        """测试数据验证失败异常"""
        error = DataValidationError(
            "股票代码格式不正确",
            error_code="INVALID_STOCK_CODE",
            stock_code="ABC",
            expected_format="6位数字"
        )
        assert isinstance(error, DataError)
        assert error.context["stock_code"] == "ABC"

    def test_data_provider_error(self):
        """测试数据提供者异常"""
        error = DataProviderError(
            "API调用失败",
            error_code="API_ERROR",
            provider="akshare",
            status_code=500
        )
        assert isinstance(error, DataError)
        assert error.context["provider"] == "akshare"

    def test_insufficient_data_error(self):
        """测试数据不足异常"""
        error = InsufficientDataError(
            "数据点不足",
            error_code="INSUFFICIENT_DATA",
            required_points=20,
            actual_points=10
        )
        assert error.context["required_points"] == 20
        assert error.context["actual_points"] == 10


class TestDatabaseExceptions:
    """测试数据库相关异常"""

    def test_database_connection_error(self):
        """测试数据库连接错误"""
        error = DatabaseConnectionError(
            "无法连接到数据库",
            error_code="DB_CONN_FAILED",
            host="localhost",
            port=5432
        )
        assert isinstance(error, DatabaseError)
        assert error.context["host"] == "localhost"

    def test_connection_error_alias(self):
        """测试ConnectionError别名"""
        assert ConnectionError is DatabaseConnectionError

    def test_query_error(self):
        """测试SQL查询错误"""
        error = QueryError(
            "查询执行失败",
            error_code="SQL_ERROR",
            query="SELECT * FROM stocks"
        )
        assert isinstance(error, DatabaseError)
        assert error.context["query"] == "SELECT * FROM stocks"


class TestFeatureExceptions:
    """测试特征工程相关异常"""

    def test_feature_calculation_error(self):
        """测试特征计算错误"""
        error = FeatureCalculationError(
            "因子计算失败",
            error_code="FACTOR_CALC_ERROR",
            factor_name="MOM_20",
            stock_code="000001"
        )
        assert isinstance(error, FeatureError)
        assert error.context["factor_name"] == "MOM_20"

    def test_feature_computation_error_alias(self):
        """测试FeatureComputationError别名"""
        assert FeatureComputationError is FeatureCalculationError

    def test_feature_storage_error(self):
        """测试特征存储错误"""
        error = FeatureStorageError(
            "特征保存失败",
            error_code="SAVE_ERROR",
            file_path="/data/features.parquet"
        )
        assert isinstance(error, FeatureError)
        assert error.context["file_path"] == "/data/features.parquet"

    def test_feature_cache_error(self):
        """测试特征缓存错误"""
        error = FeatureCacheError(
            "缓存读取失败",
            cache_key="features_000001"
        )
        assert isinstance(error, FeatureError)
        assert error.context["cache_key"] == "features_000001"


class TestModelExceptions:
    """测试模型相关异常"""

    def test_model_training_error(self):
        """测试模型训练错误"""
        error = ModelTrainingError(
            "训练失败",
            error_code="TRAINING_FAILED",
            model_type="LightGBM",
            n_samples=1000
        )
        assert isinstance(error, ModelError)
        assert error.context["model_type"] == "LightGBM"

    def test_model_prediction_error(self):
        """测试模型预测错误"""
        error = ModelPredictionError(
            "预测失败",
            model_name="lgb_v1"
        )
        assert isinstance(error, ModelError)

    def test_model_not_found_error(self):
        """测试模型不存在异常"""
        error = ModelNotFoundError(
            "模型文件不存在",
            model_path="/models/lgb.pkl"
        )
        assert isinstance(error, ModelError)

    def test_model_validation_error(self):
        """测试模型验证错误"""
        error = ModelValidationError(
            "模型性能不达标",
            metric="sharpe_ratio",
            actual_value=0.5,
            threshold=1.0
        )
        assert isinstance(error, ModelError)
        assert error.context["metric"] == "sharpe_ratio"


class TestStrategyAndBacktestExceptions:
    """测试策略和回测相关异常"""

    def test_signal_generation_error(self):
        """测试信号生成错误"""
        error = SignalGenerationError(
            "信号生成失败",
            strategy_name="MomentumStrategy",
            stock_code="000001"
        )
        assert isinstance(error, StrategyError)
        assert error.context["strategy_name"] == "MomentumStrategy"

    def test_backtest_execution_error(self):
        """测试回测执行错误"""
        error = BacktestExecutionError(
            "回测失败",
            strategy="MomentumStrategy",
            start_date="2024-01-01"
        )
        assert isinstance(error, BacktestError)
        assert error.context["strategy"] == "MomentumStrategy"


class TestConfigExceptions:
    """测试配置相关异常"""

    def test_config_validation_error(self):
        """测试配置验证错误"""
        error = ConfigValidationError(
            "参数无效",
            param_name="initial_capital",
            param_value=-1000,
            constraint="必须为正数"
        )
        assert isinstance(error, ConfigError)
        assert error.context["param_name"] == "initial_capital"

    def test_config_file_not_found_error(self):
        """测试配置文件不存在异常"""
        error = ConfigFileNotFoundError(
            "配置文件不存在",
            file_path="/config/settings.yaml"
        )
        assert isinstance(error, ConfigError)
        assert error.context["file_path"] == "/config/settings.yaml"


class TestRiskManagementExceptions:
    """测试风险管理相关异常"""

    def test_risk_limit_exceeded_error(self):
        """测试风险限制超出异常"""
        error = RiskLimitExceededError(
            "持仓超限",
            stock_code="000001",
            current_position=0.25,
            limit=0.20
        )
        assert isinstance(error, RiskManagementError)
        assert error.context["current_position"] == 0.25

    def test_drawdown_exceeded_error(self):
        """测试回撤超限异常"""
        error = DrawdownExceededError(
            "回撤超限",
            current_drawdown=0.25,
            threshold=0.20
        )
        assert isinstance(error, RiskManagementError)
        assert error.context["current_drawdown"] == 0.25


class TestExceptionHierarchy:
    """测试异常类层次结构"""

    def test_all_exceptions_inherit_from_base(self):
        """测试所有异常都继承自StockAnalysisError"""
        exceptions_to_test = [
            DataError,
            DatabaseError,
            FeatureError,
            ModelError,
            StrategyError,
            BacktestError,
            ConfigError,
            RiskManagementError,
        ]

        for exc_class in exceptions_to_test:
            assert issubclass(exc_class, StockAnalysisError)

    def test_data_exception_hierarchy(self):
        """测试数据异常层次"""
        assert issubclass(DataNotFoundError, DataError)
        assert issubclass(DataValidationError, DataError)
        assert issubclass(DataProviderError, DataError)

    def test_feature_exception_hierarchy(self):
        """测试特征异常层次"""
        assert issubclass(FeatureCalculationError, FeatureError)
        assert issubclass(FeatureStorageError, FeatureError)
        assert issubclass(FeatureCacheError, FeatureError)

    def test_model_exception_hierarchy(self):
        """测试模型异常层次"""
        assert issubclass(ModelTrainingError, ModelError)
        assert issubclass(ModelPredictionError, ModelError)
        assert issubclass(ModelNotFoundError, ModelError)


class TestExceptionIntegration:
    """测试异常集成场景"""

    def test_nested_exception_handling(self):
        """测试嵌套异常处理"""
        def inner_function():
            raise DataNotFoundError(
                "数据不存在",
                stock_code="000001"
            )

        def outer_function():
            try:
                inner_function()
            except DataError as e:
                # 重新包装为FeatureError
                raise FeatureCalculationError(
                    "特征计算失败（数据不存在）",
                    original_error=e.message,
                    **e.context
                )

        with pytest.raises(FeatureCalculationError) as exc_info:
            outer_function()

        error = exc_info.value
        assert "数据不存在" in error.context["original_error"]
        assert error.context["stock_code"] == "000001"

    def test_exception_serialization(self):
        """测试异常序列化"""
        error = DataProviderError(
            "API调用失败",
            error_code="API_ERROR",
            provider="akshare",
            endpoint="stock_zh_a_hist",
            status_code=500,
            retry_count=3
        )

        # 转换为字典
        error_dict = error.to_dict()

        # 验证字典包含所有信息
        assert error_dict["error_type"] == "DataProviderError"
        assert error_dict["error_code"] == "API_ERROR"
        assert error_dict["message"] == "API调用失败"
        assert error_dict["context"]["provider"] == "akshare"
        assert error_dict["context"]["status_code"] == 500

    def test_exception_with_complex_context(self):
        """测试带复杂上下文的异常"""
        import pandas as pd
        import numpy as np

        error = FeatureCalculationError(
            "计算失败",
            error_code="CALC_ERROR",
            stock_code="000001",
            factor="MOM_20",
            data_shape=(100, 5),
            nan_count=10,
            data_range=(0.0, 100.0)
        )

        # 验证复杂类型的上下文
        assert error.context["data_shape"] == (100, 5)
        assert error.context["nan_count"] == 10
        assert error.context["data_range"] == (0.0, 100.0)

        # 验证to_dict能处理复杂类型
        error_dict = error.to_dict()
        assert error_dict["context"]["data_shape"] == (100, 5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
