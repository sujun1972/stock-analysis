"""
装饰器模块测试

测试覆盖：
- timer 装饰器（毫秒、秒、分钟格式）
- retry 装饰器（成功、失败、退避、异常类型）
- cache_result 装饰器（缓存命中、过期、清除）
- validate_args 装饰器（验证成功、失败）
"""

import time
import pytest
from unittest.mock import Mock, patch
from src.utils.decorators import timer, retry, cache_result, validate_args


class TestTimerDecorator:
    """测试 timer 装饰器"""

    @patch("src.utils.decorators.logger")
    def test_timer_milliseconds(self, mock_logger):
        """测试毫秒级耗时显示"""
        @timer
        def fast_function():
            time.sleep(0.01)  # 10ms
            return "done"

        result = fast_function()

        assert result == "done"
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "fast_function" in log_message
        assert "ms" in log_message
        assert "执行耗时" in log_message

    @patch("src.utils.decorators.logger")
    @patch("time.time")
    def test_timer_exactly_one_second(self, mock_time, mock_logger):
        """测试恰好 1 秒的边界情况"""
        mock_time.side_effect = [0, 1.0]

        @timer
        def one_second_function():
            return "one_sec"

        result = one_second_function()

        assert result == "one_sec"
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "one_second_function" in log_message
        assert "1.00s" in log_message

    @patch("src.utils.decorators.logger")
    def test_timer_seconds(self, mock_logger):
        """测试秒级耗时显示"""
        @timer
        def medium_function():
            time.sleep(0.15)  # 150ms
            return 42

        result = medium_function()

        assert result == 42
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "medium_function" in log_message
        assert "s" in log_message
        assert "执行耗时" in log_message

    @patch("src.utils.decorators.logger")
    @patch("time.time")
    def test_timer_minutes(self, mock_time, mock_logger):
        """测试分钟级耗时显示（模拟时间）"""
        # 模拟经过 90 秒
        mock_time.side_effect = [0, 90]

        @timer
        def slow_function():
            return "completed"

        result = slow_function()

        assert result == "completed"
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "slow_function" in log_message
        assert "m" in log_message  # 分钟标识
        assert "执行耗时" in log_message

    @patch("src.utils.decorators.logger")
    def test_timer_preserves_function_metadata(self, mock_logger):
        """测试装饰器保留函数元数据"""
        @timer
        def documented_function():
            """This is a test function"""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a test function"

    @patch("src.utils.decorators.logger")
    def test_timer_with_arguments(self, mock_logger):
        """测试带参数的函数"""
        @timer
        def add_numbers(a, b, c=10):
            return a + b + c

        result = add_numbers(1, 2, c=3)

        assert result == 6
        mock_logger.info.assert_called_once()

    @patch("src.utils.decorators.logger")
    def test_timer_with_exception(self, mock_logger):
        """测试函数抛出异常时的行为"""
        @timer
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()


class TestRetryDecorator:
    """测试 retry 装饰器"""

    @patch("src.utils.decorators.logger")
    def test_retry_success_first_attempt(self, mock_logger):
        """测试第一次尝试就成功"""
        @retry(max_attempts=3)
        def successful_function():
            return "success"

        result = successful_function()

        assert result == "success"
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    @patch("src.utils.decorators.logger")
    @patch("time.sleep")
    def test_retry_success_after_failures(self, mock_sleep, mock_logger):
        """测试失败后重试成功"""
        mock_func = Mock(side_effect=[
            ValueError("First fail"),
            ValueError("Second fail"),
            "success"
        ])

        @retry(max_attempts=3, delay=0.1)
        def flaky_function():
            return mock_func()

        result = flaky_function()

        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_logger.warning.call_count == 2
        mock_logger.error.assert_not_called()

    @patch("src.utils.decorators.logger")
    @patch("time.sleep")
    def test_retry_all_attempts_fail(self, mock_sleep, mock_logger):
        """测试所有尝试都失败"""
        @retry(max_attempts=3, delay=0.1)
        def always_fails():
            raise ConnectionError("Cannot connect")

        with pytest.raises(ConnectionError, match="Cannot connect"):
            always_fails()

        assert mock_logger.warning.call_count == 2
        mock_logger.error.assert_called_once()

    @patch("src.utils.decorators.logger")
    @patch("time.sleep")
    def test_retry_exponential_backoff(self, mock_sleep, mock_logger):
        """测试指数退避机制"""
        @retry(max_attempts=4, delay=1.0, backoff=2.0)
        def failing_function():
            raise RuntimeError("Error")

        with pytest.raises(RuntimeError):
            failing_function()

        # 验证 sleep 调用的延迟时间: 1.0, 2.0, 4.0
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [1.0, 2.0, 4.0]

    @patch("src.utils.decorators.logger")
    def test_retry_specific_exceptions(self, mock_logger):
        """测试只重试特定异常"""
        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def selective_failure():
            raise TypeError("Wrong type")

        with pytest.raises(TypeError, match="Wrong type"):
            selective_failure()

        mock_logger.warning.assert_not_called()

    @patch("src.utils.decorators.logger")
    @patch("time.sleep")
    def test_retry_multiple_exception_types(self, mock_sleep, mock_logger):
        """测试重试多种异常类型"""
        mock_func = Mock(side_effect=[
            ValueError("value error"),
            ConnectionError("connection error"),
            "success"
        ])

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError, ConnectionError))
        def multi_exception_function():
            return mock_func()

        result = multi_exception_function()

        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_logger.warning.call_count == 2

    @patch("src.utils.decorators.logger")
    @patch("time.sleep")
    def test_retry_preserves_function_metadata(self, mock_sleep, mock_logger):
        """测试装饰器保留函数元数据"""
        @retry(max_attempts=2)
        def documented_retry_function():
            """Retry test function"""
            return "ok"

        assert documented_retry_function.__name__ == "documented_retry_function"
        assert documented_retry_function.__doc__ == "Retry test function"

    @patch("src.utils.decorators.logger")
    @patch("time.sleep")
    def test_retry_with_arguments(self, mock_sleep, mock_logger):
        """测试带参数的重试函数"""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def function_with_args(x, y, z=10):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Not ready")
            return x + y + z

        result = function_with_args(1, 2, z=3)

        assert result == 6
        assert call_count == 2


class TestCacheResultDecorator:
    """测试 cache_result 装饰器"""

    @patch("src.utils.decorators.logger")
    def test_cache_hit(self, mock_logger):
        """测试缓存命中"""
        call_count = 0

        @cache_result()
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1

        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("计算新结果" in msg for msg in debug_calls)
        assert any("使用缓存结果" in msg for msg in debug_calls)

    @patch("src.utils.decorators.logger")
    def test_cache_different_arguments(self, mock_logger):
        """测试不同参数产生不同缓存"""
        call_count = 0

        @cache_result()
        def multiply(x, y):
            nonlocal call_count
            call_count += 1
            return x * y

        result1 = multiply(2, 3)
        result2 = multiply(4, 5)
        result3 = multiply(2, 3)

        assert result1 == 6
        assert result2 == 20
        assert result3 == 6
        assert call_count == 2

    @patch("src.utils.decorators.logger")
    def test_cache_with_kwargs(self, mock_logger):
        """测试带关键字参数的缓存"""
        call_count = 0

        @cache_result()
        def compute(a, b=10, c=20):
            nonlocal call_count
            call_count += 1
            return a + b + c

        result1 = compute(1, b=2, c=3)
        result2 = compute(1, c=3, b=2)

        assert result1 == 6
        assert result2 == 6
        assert call_count == 1

    @patch("src.utils.decorators.logger")
    @patch("time.time")
    def test_cache_expiration(self, mock_time, mock_logger):
        """测试缓存过期"""
        call_count = 0
        current_time = [100]

        def time_side_effect():
            result = current_time[0]
            current_time[0] += 1
            return result

        mock_time.side_effect = time_side_effect

        @cache_result(ttl=5)
        def cached_function(x):
            nonlocal call_count
            call_count += 1
            return x * 3

        result1 = cached_function(10)
        assert result1 == 30
        assert call_count == 1

        result2 = cached_function(10)
        assert result2 == 30
        assert call_count == 1

        # 模拟时间过去超过 TTL
        current_time[0] += 10

        result3 = cached_function(10)
        assert result3 == 30
        assert call_count == 2

        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("缓存过期" in msg for msg in debug_calls)

    @patch("src.utils.decorators.logger")
    def test_cache_no_ttl(self, mock_logger):
        """测试永不过期的缓存"""
        call_count = 0

        @cache_result(ttl=None)
        def permanent_cache(x):
            nonlocal call_count
            call_count += 1
            return x ** 2

        for _ in range(5):
            result = permanent_cache(7)
            assert result == 49

        assert call_count == 1

    @patch("src.utils.decorators.logger")
    def test_cache_clear(self, mock_logger):
        """测试清除缓存"""
        call_count = 0

        @cache_result()
        def clearable_function(x):
            nonlocal call_count
            call_count += 1
            return x + 100

        result1 = clearable_function(5)
        assert result1 == 105
        assert call_count == 1

        result2 = clearable_function(5)
        assert result2 == 105
        assert call_count == 1

        clearable_function.clear_cache()
        mock_logger.info.assert_called_once()
        assert "缓存已清除" in mock_logger.info.call_args[0][0]

        result3 = clearable_function(5)
        assert result3 == 105
        assert call_count == 2

    @patch("src.utils.decorators.logger")
    def test_cache_preserves_function_metadata(self, mock_logger):
        """测试装饰器保留函数元数据"""
        @cache_result(ttl=60)
        def documented_cache_function():
            """Cache test function"""
            return "cached"

        assert documented_cache_function.__name__ == "documented_cache_function"
        assert documented_cache_function.__doc__ == "Cache test function"
        assert hasattr(documented_cache_function, "clear_cache")


class TestValidateArgsDecorator:
    """测试 validate_args 装饰器"""

    def test_validate_args_success(self):
        """测试参数验证成功"""
        @validate_args(
            symbol=lambda x: len(x) == 6,
            period=lambda x: x > 0
        )
        def fetch_data(symbol: str, period: int):
            return f"Fetching {symbol} for {period} days"

        result = fetch_data("600000", 30)
        assert result == "Fetching 600000 for 30 days"

    def test_validate_args_failure(self):
        """测试参数验证失败"""
        @validate_args(
            age=lambda x: x >= 0,
            name=lambda x: len(x) > 0
        )
        def create_user(name: str, age: int):
            return f"User {name}, age {age}"

        with pytest.raises(ValueError, match="参数 'age' 验证失败"):
            create_user("Alice", -5)

        with pytest.raises(ValueError, match="参数 'name' 验证失败"):
            create_user("", 25)

    def test_validate_args_with_kwargs(self):
        """测试关键字参数验证"""
        @validate_args(
            price=lambda x: x > 0,
            quantity=lambda x: x >= 1
        )
        def place_order(symbol: str, price: float, quantity: int = 1):
            return f"Order: {symbol} @ {price} x {quantity}"

        result = place_order("AAPL", price=150.0, quantity=10)
        assert "150.0" in result

        with pytest.raises(ValueError, match="参数 'price' 验证失败"):
            place_order("AAPL", price=-10.0, quantity=5)

        with pytest.raises(ValueError, match="参数 'quantity' 验证失败"):
            place_order("AAPL", price=100.0, quantity=0)

    def test_validate_args_with_defaults(self):
        """测试带默认值的参数验证"""
        @validate_args(
            threshold=lambda x: 0 <= x <= 1
        )
        def filter_data(data: list, threshold: float = 0.5):
            return [x for x in data if x > threshold]

        result1 = filter_data([0.3, 0.6, 0.8])
        assert result1 == [0.6, 0.8]

        result2 = filter_data([0.3, 0.6, 0.8], threshold=0.7)
        assert result2 == [0.8]

        with pytest.raises(ValueError, match="参数 'threshold' 验证失败"):
            filter_data([0.1, 0.2], threshold=1.5)

    def test_validate_args_partial_validation(self):
        """测试只验证部分参数"""
        @validate_args(
            email=lambda x: "@" in x
        )
        def send_email(email: str, subject: str, body: str):
            return f"Sending to {email}: {subject}"

        result = send_email("test@example.com", "Hello", "World")
        assert "test@example.com" in result

        with pytest.raises(ValueError, match="参数 'email' 验证失败"):
            send_email("invalid-email", "Hello", "World")

    def test_validate_args_complex_validation(self):
        """测试复杂验证逻辑"""
        def is_valid_stock_code(code: str) -> bool:
            return (
                isinstance(code, str) and
                len(code) == 6 and
                code.isdigit() and
                code[0] in ('0', '3', '6')
            )

        @validate_args(
            stock_code=is_valid_stock_code,
            amount=lambda x: x >= 100 and x % 100 == 0
        )
        def buy_stock(stock_code: str, amount: int):
            return f"Buying {amount} shares of {stock_code}"

        result = buy_stock("600000", 500)
        assert "600000" in result

        with pytest.raises(ValueError, match="参数 'stock_code' 验证失败"):
            buy_stock("123456", 100)

        with pytest.raises(ValueError, match="参数 'amount' 验证失败"):
            buy_stock("600000", 150)

    def test_validate_args_preserves_function_metadata(self):
        """测试装饰器保留函数元数据"""
        @validate_args(x=lambda v: v > 0)
        def validated_function(x):
            """Validated test function"""
            return x * 2

        assert validated_function.__name__ == "validated_function"
        assert validated_function.__doc__ == "Validated test function"

    def test_validate_args_with_none_value(self):
        """测试 None 值的验证"""
        @validate_args(
            data=lambda x: x is not None
        )
        def process_data(data):
            return f"Processing {data}"

        result = process_data([1, 2, 3])
        assert "Processing" in result

        with pytest.raises(ValueError, match="参数 'data' 验证失败"):
            process_data(None)

    def test_validate_args_empty_validators(self):
        """测试空验证器"""
        @validate_args()
        def no_validation(a, b, c):
            return a + b + c

        result = no_validation(1, 2, 3)
        assert result == 6


class TestDecoratorsIntegration:
    """测试装饰器组合使用"""

    @patch("src.utils.decorators.logger")
    def test_timer_and_retry_combination(self, mock_logger):
        """测试 timer + retry 组合"""
        call_count = 0

        @timer
        @retry(max_attempts=3, delay=0.01)
        def flaky_timed_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = flaky_timed_function()

        assert result == "success"
        assert call_count == 2
        assert any("执行耗时" in str(call) for call in mock_logger.info.call_args_list)

    @patch("src.utils.decorators.logger")
    def test_cache_and_validate_combination(self, mock_logger):
        """测试 cache + validate 组合"""
        call_count = 0

        @cache_result(ttl=60)
        @validate_args(x=lambda v: v > 0)
        def cached_validated_function(x):
            nonlocal call_count
            call_count += 1
            return x ** 2

        result1 = cached_validated_function(5)
        assert result1 == 25
        assert call_count == 1

        result2 = cached_validated_function(5)
        assert result2 == 25
        assert call_count == 1

        with pytest.raises(ValueError, match="参数 'x' 验证失败"):
            cached_validated_function(-5)

    @patch("src.utils.decorators.logger")
    @patch("time.sleep")
    def test_all_decorators_combination(self, mock_sleep, mock_logger):
        """测试所有装饰器组合"""
        call_count = 0

        @timer
        @retry(max_attempts=2, delay=0.01)
        @cache_result(ttl=10)
        @validate_args(n=lambda v: v >= 0)
        def complex_function(n):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and n == 5:
                raise ValueError("First attempt fails")
            return n * 10

        result1 = complex_function(5)
        assert result1 == 50
        assert call_count == 2

        result2 = complex_function(5)
        assert result2 == 50
        assert call_count == 2

        result3 = complex_function(10)
        assert result3 == 100
        assert call_count == 3

        with pytest.raises(ValueError, match="参数 'n' 验证失败"):
            complex_function(-1)
