"""
测试错误处理工具模块

测试 src/utils/error_handling.py 中的装饰器和工具函数
"""
import time
import pytest
import pandas as pd
from unittest.mock import Mock, patch

from src.utils.error_handling import (
    handle_errors,
    retry_on_error,
    log_errors,
    safe_execute,
    format_exception_message,
)
from src.exceptions import (
    StockAnalysisError,
    DataError,
    DataProviderError,
    FeatureCalculationError,
    ModelTrainingError,
)


class TestHandleErrors:
    """测试handle_errors装饰器"""

    def test_no_error(self):
        """测试正常执行（无异常）"""
        @handle_errors(DataError)
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_catch_exception_return_default(self):
        """测试捕获异常并返回默认值"""
        @handle_errors(DataProviderError, default_return="default")
        def failing_function():
            raise DataProviderError("API失败", provider="akshare")

        result = failing_function()
        assert result == "default"

    def test_catch_exception_return_none(self):
        """测试捕获异常返回None"""
        @handle_errors(DataError)
        def failing_function():
            raise DataError("数据错误")

        result = failing_function()
        assert result is None

    def test_catch_exception_return_dataframe(self):
        """测试捕获异常返回DataFrame"""
        @handle_errors(DataProviderError, default_return=pd.DataFrame())
        def failing_function():
            raise DataProviderError("获取失败")

        result = failing_function()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_catch_multiple_exception_types(self):
        """测试捕获多种异常类型"""
        @handle_errors((DataError, FeatureCalculationError), default_return="error")
        def function_with_data_error():
            raise DataError("数据错误")

        @handle_errors((DataError, FeatureCalculationError), default_return="error")
        def function_with_feature_error():
            raise FeatureCalculationError("特征错误")

        assert function_with_data_error() == "error"
        assert function_with_feature_error() == "error"

    def test_reraise_option(self):
        """测试reraise选项"""
        @handle_errors(DataError, reraise=True)
        def failing_function():
            raise DataError("数据错误", error_code="TEST_ERROR")

        with pytest.raises(DataError) as exc_info:
            failing_function()

        assert exc_info.value.error_code == "TEST_ERROR"

    def test_custom_message(self):
        """测试自定义错误消息"""
        @handle_errors(
            DataError,
            custom_message="自定义消息",
            default_return=None
        )
        def failing_function():
            raise DataError("原始错误")

        # 应该记录自定义消息但不抛出异常
        result = failing_function()
        assert result is None

    def test_log_level(self):
        """测试不同日志级别"""
        @handle_errors(DataError, log_level="warning", default_return=None)
        def failing_function():
            raise DataError("数据错误")

        result = failing_function()
        assert result is None

    def test_stock_analysis_error_logging(self):
        """测试StockAnalysisError的日志记录"""
        @handle_errors(DataProviderError, default_return=None)
        def failing_function():
            raise DataProviderError(
                "API失败",
                error_code="API_ERROR",
                provider="akshare",
                status_code=500
            )

        result = failing_function()
        assert result is None

    def test_standard_exception_logging(self):
        """测试标准异常的日志记录"""
        @handle_errors(ValueError, default_return="default")
        def failing_function():
            raise ValueError("标准异常")

        result = failing_function()
        assert result == "default"

    def test_uncaught_exception(self):
        """测试未捕获的异常类型"""
        @handle_errors(DataError, default_return="default")
        def failing_function():
            raise ModelTrainingError("模型错误")  # 不同类型的异常

        # 应该抛出未捕获的异常
        with pytest.raises(ModelTrainingError):
            failing_function()


class TestRetryOnError:
    """测试retry_on_error装饰器"""

    def test_successful_first_attempt(self):
        """测试第一次尝试就成功"""
        call_count = 0

        @retry_on_error(max_attempts=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_and_succeed(self):
        """测试重试后成功"""
        call_count = 0

        @retry_on_error(max_attempts=3, delay=0.1, backoff_factor=1)
        def function_fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DataProviderError("临时失败")
            return "success"

        result = function_fails_twice()
        assert result == "success"
        assert call_count == 3

    def test_all_retries_fail(self):
        """测试所有重试都失败"""
        call_count = 0

        @retry_on_error(max_attempts=3, delay=0.1)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise DataProviderError("永久失败", attempt=call_count)

        with pytest.raises(DataProviderError) as exc_info:
            always_failing_function()

        assert call_count == 3
        assert exc_info.value.context["attempt"] == 3

    def test_retry_with_backoff(self):
        """测试指数退避"""
        timestamps = []

        @retry_on_error(max_attempts=3, delay=0.1, backoff_factor=2.0)
        def failing_function():
            timestamps.append(time.time())
            raise DataProviderError("失败")

        with pytest.raises(DataProviderError):
            failing_function()

        # 验证重试次数
        assert len(timestamps) == 3

        # 验证延迟时间（大致）
        # 第1次到第2次: ~0.1秒
        # 第2次到第3次: ~0.2秒
        if len(timestamps) >= 2:
            delay1 = timestamps[1] - timestamps[0]
            assert 0.08 < delay1 < 0.15  # 0.1秒左右

        if len(timestamps) >= 3:
            delay2 = timestamps[2] - timestamps[1]
            assert 0.18 < delay2 < 0.25  # 0.2秒左右

    def test_retry_specific_exceptions(self):
        """测试只对特定异常重试"""
        call_count = 0

        @retry_on_error(
            max_attempts=3,
            delay=0.1,
            exception_class=(DataProviderError, DataError)
        )
        def function_with_different_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise DataProviderError("可重试错误")
            else:
                raise ModelTrainingError("不可重试错误")

        # 第一次抛出DataProviderError会重试
        # 第二次抛出ModelTrainingError不会重试，直接抛出
        with pytest.raises(ModelTrainingError):
            function_with_different_errors()

        assert call_count == 2

    def test_no_reraise(self):
        """测试reraise=False"""
        @retry_on_error(max_attempts=2, delay=0.1, reraise=False)
        def always_failing_function():
            raise DataError("失败")

        result = always_failing_function()
        assert result is None

    def test_log_retries_disabled(self):
        """测试禁用重试日志"""
        call_count = 0

        @retry_on_error(max_attempts=2, delay=0.1, log_retries=False)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise DataError("失败")

        with pytest.raises(DataError):
            failing_function()

        assert call_count == 2


class TestLogErrors:
    """测试log_errors装饰器"""

    def test_normal_execution(self):
        """测试正常执行"""
        @log_errors()
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_log_and_reraise(self):
        """测试记录日志并重新抛出"""
        @log_errors()
        def failing_function():
            raise DataError("数据错误", stock_code="000001")

        with pytest.raises(DataError) as exc_info:
            failing_function()

        assert exc_info.value.message == "数据错误"

    def test_include_args(self):
        """测试包含函数参数"""
        @log_errors(include_args=True)
        def function_with_args(a, b, c=10):
            raise DataError("错误")

        with pytest.raises(DataError):
            function_with_args(1, 2, c=3)

    def test_different_log_levels(self):
        """测试不同日志级别"""
        @log_errors(log_level="critical")
        def critical_error():
            raise DataError("严重错误")

        @log_errors(log_level="warning")
        def warning_error():
            raise DataError("警告错误")

        with pytest.raises(DataError):
            critical_error()

        with pytest.raises(DataError):
            warning_error()

    def test_exclude_traceback(self):
        """测试不包含调用栈"""
        @log_errors(include_traceback=False)
        def failing_function():
            raise DataError("错误")

        with pytest.raises(DataError):
            failing_function()


class TestSafeExecute:
    """测试safe_execute函数"""

    def test_successful_execution(self):
        """测试成功执行"""
        def successful_func(a, b):
            return a + b

        result = safe_execute(successful_func, 1, 2)
        assert result == 3

    def test_catch_exception_return_default(self):
        """测试捕获异常返回默认值"""
        def failing_func():
            raise DataError("错误")

        result = safe_execute(
            failing_func,
            default_return="default"
        )
        assert result == "default"

    def test_with_kwargs(self):
        """测试使用关键字参数"""
        def func_with_kwargs(a, b, c=10):
            return a + b + c

        result = safe_execute(func_with_kwargs, 1, 2, c=3)
        assert result == 6

    def test_specific_exception_class(self):
        """测试捕获特定异常类"""
        def func_with_data_error():
            raise DataError("数据错误")

        def func_with_model_error():
            raise ModelTrainingError("模型错误")

        # 捕获DataError
        result1 = safe_execute(
            func_with_data_error,
            exception_class=DataError,
            default_return="caught"
        )
        assert result1 == "caught"

        # 不捕获ModelTrainingError
        with pytest.raises(ModelTrainingError):
            safe_execute(
                func_with_model_error,
                exception_class=DataError,
                default_return="caught"
            )

    def test_disable_logging(self):
        """测试禁用日志"""
        def failing_func():
            raise DataError("错误")

        result = safe_execute(
            failing_func,
            log_error=False,
            default_return=None
        )
        assert result is None

    def test_with_stock_analysis_error(self):
        """测试处理StockAnalysisError"""
        def func_with_custom_error():
            raise DataProviderError(
                "API失败",
                error_code="API_ERROR",
                provider="akshare"
            )

        result = safe_execute(
            func_with_custom_error,
            default_return=pd.DataFrame()
        )
        assert isinstance(result, pd.DataFrame)


class TestFormatExceptionMessage:
    """测试format_exception_message函数"""

    def test_format_stock_analysis_error(self):
        """测试格式化自定义异常"""
        error = DataProviderError(
            "API调用失败",
            error_code="API_ERROR",
            provider="akshare",
            status_code=500
        )

        message = format_exception_message(error)

        assert "DataProviderError" in message
        assert "API_ERROR" in message
        assert "API调用失败" in message
        assert "provider=akshare" in message
        assert "status_code=500" in message

    def test_format_stock_analysis_error_no_context(self):
        """测试格式化无上下文的自定义异常"""
        error = DataError("简单错误")

        message = format_exception_message(error)

        assert "DataError" in message
        assert "简单错误" in message

    def test_format_standard_exception(self):
        """测试格式化标准异常"""
        error = ValueError("值错误")

        message = format_exception_message(error)

        assert "ValueError" in message
        assert "值错误" in message

    def test_format_exception_with_complex_context(self):
        """测试格式化带复杂上下文的异常"""
        error = FeatureCalculationError(
            "计算失败",
            error_code="CALC_ERROR",
            factor="MOM_20",
            data_shape=(100, 5),
            nan_count=15
        )

        message = format_exception_message(error)

        assert "FeatureCalculationError" in message
        assert "CALC_ERROR" in message
        assert "factor=MOM_20" in message
        assert "data_shape=" in message
        assert "nan_count=15" in message


class TestErrorHandlingIntegration:
    """测试错误处理集成场景"""

    def test_combined_decorators(self):
        """测试组合使用多个装饰器"""
        call_count = 0

        @handle_errors(DataProviderError, default_return="fallback")
        @retry_on_error(max_attempts=2, delay=0.1)
        def function_with_combined_decorators():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise DataProviderError("临时失败")
            return "success"

        result = function_with_combined_decorators()
        assert result == "success"
        assert call_count == 2

    def test_nested_safe_execute(self):
        """测试嵌套safe_execute"""
        def inner_func():
            raise DataError("内部错误")

        def outer_func():
            return safe_execute(
                inner_func,
                default_return="inner_default"
            )

        result = safe_execute(
            outer_func,
            default_return="outer_default"
        )
        assert result == "inner_default"

    def test_real_world_data_fetching(self):
        """测试真实场景：数据获取"""
        @retry_on_error(max_attempts=3, delay=0.1)
        @handle_errors(DataProviderError, default_return=pd.DataFrame())
        def fetch_stock_data(stock_code: str):
            # 模拟API调用
            if stock_code == "INVALID":
                raise DataProviderError(
                    "无效股票代码",
                    stock_code=stock_code
                )
            return pd.DataFrame({"close": [100, 101, 102]})

        # 正常情况
        df = fetch_stock_data("000001")
        assert len(df) == 3

        # 异常情况
        df = fetch_stock_data("INVALID")
        assert len(df) == 0

    def test_real_world_feature_calculation(self):
        """测试真实场景：特征计算"""
        @log_errors(include_args=True)
        @handle_errors(
            (FeatureCalculationError, DataError),
            default_return=pd.DataFrame()
        )
        def calculate_features(data: pd.DataFrame):
            if data.empty:
                raise FeatureCalculationError(
                    "输入数据为空",
                    error_code="EMPTY_INPUT"
                )
            # 模拟特征计算
            return pd.DataFrame({"MOM_20": [0.1, 0.2, 0.3]})

        # 正常情况
        df = calculate_features(pd.DataFrame({"close": [100, 101, 102]}))
        assert len(df) == 3

        # 异常情况
        df = calculate_features(pd.DataFrame())
        assert len(df) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
