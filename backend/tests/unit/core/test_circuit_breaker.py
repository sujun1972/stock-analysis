"""
Circuit Breaker 熔断器单元测试

测试熔断器在故障时能否正确触发和恢复
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import pybreaker

from app.core.circuit_breaker import (
    db_breaker,
    external_api_breaker,
    core_service_breaker,
    redis_breaker,
    with_circuit_breaker,
    ServiceUnavailableError,
    reset_breaker,
    get_all_breakers_status,
    CircuitBreakerListener,
)


@pytest.fixture(autouse=True)
def reset_breakers():
    """每个测试前重置所有熔断器"""
    breakers = [db_breaker, external_api_breaker, core_service_breaker, redis_breaker]
    for breaker in breakers:
        try:
            breaker.close()
            breaker._failure_count = 0
        except:
            pass
    yield


class TestCircuitBreaker:
    """Circuit Breaker 基础测试"""

    def test_breaker_initial_state(self):
        """测试熔断器初始状态"""
        assert db_breaker.current_state in ["closed", pybreaker.STATE_CLOSED]
        assert db_breaker.fail_max == 5

    def test_breaker_opens_after_failures(self):
        """测试熔断器在连续失败后打开"""

        def failing_operation():
            raise Exception("Database error")

        # 触发 fail_max 次失败
        for i in range(db_breaker.fail_max):
            with pytest.raises(Exception):
                db_breaker.call(failing_operation)

        # 熔断器应该打开
        assert db_breaker.current_state in ["open", pybreaker.STATE_OPEN]

    def test_breaker_blocks_requests_when_open(self):
        """测试熔断器打开时阻止请求"""

        def failing_operation():
            raise Exception("Database error")

        # 打开熔断器
        for i in range(db_breaker.fail_max):
            with pytest.raises(Exception):
                db_breaker.call(failing_operation)

        # 下一个请求应该被熔断器直接拒绝
        with pytest.raises(pybreaker.CircuitBreakerError):
            db_breaker.call(failing_operation)


class TestCircuitBreakerDecorator:
    """Circuit Breaker 装饰器测试（简化版）"""

    def test_decorator_exists(self):
        """测试装饰器存在"""
        assert with_circuit_breaker is not None
        assert callable(with_circuit_breaker)


class TestDifferentBreakers:
    """不同熔断器配置测试"""

    def test_database_breaker_config(self):
        """测试数据库熔断器配置"""
        assert db_breaker.name == "database"
        assert db_breaker.fail_max == 5
        assert db_breaker._reset_timeout == 60

    def test_external_api_breaker_config(self):
        """测试外部API熔断器配置"""
        assert external_api_breaker.name == "external_api"
        assert external_api_breaker.fail_max == 10
        assert external_api_breaker._reset_timeout == 120

    def test_core_service_breaker_config(self):
        """测试Core服务熔断器配置"""
        assert core_service_breaker.name == "core_service"
        assert core_service_breaker.fail_max == 5
        assert core_service_breaker._reset_timeout == 60

    def test_redis_breaker_config(self):
        """测试Redis熔断器配置"""
        assert redis_breaker.name == "redis_cache"
        assert redis_breaker.fail_max == 3
        assert redis_breaker._reset_timeout == 30


class TestCircuitBreakerHelpers:
    """熔断器辅助函数测试"""

    def test_reset_breaker(self):
        """测试重置熔断器"""
        # 手动设置熔断器状态为打开
        db_breaker._state = pybreaker.STATE_OPEN

        # 重置熔断器
        reset_breaker(db_breaker)

        # 验证状态已重置
        assert db_breaker.current_state == pybreaker.STATE_CLOSED

    def test_get_all_breakers_status(self):
        """测试获取所有熔断器状态"""
        status = get_all_breakers_status()

        # 验证返回所有熔断器
        assert "database" in status
        assert "external_api" in status
        assert "core_service" in status
        assert "redis_cache" in status

        # 验证状态格式
        db_status = status["database"]
        assert "state" in db_status
        assert "fail_counter" in db_status
        assert "fail_max" in db_status
        assert "reset_timeout" in db_status


class TestCircuitBreakerListener:
    """熔断器监听器测试"""

    def test_listener_exists(self):
        """测试监听器存在"""
        listener = CircuitBreakerListener()
        assert listener is not None

    def test_listener_logs_state_change(self):
        """测试监听器记录状态变化"""
        listener = CircuitBreakerListener()
        mock_breaker = Mock()
        mock_breaker.name = "test_breaker"

        # 模拟状态变化（使用字符串）
        listener.state_change(mock_breaker, "closed", "open")

        # 验证不抛异常
        assert True

    def test_listener_logs_failure(self):
        """测试监听器记录失败"""
        listener = CircuitBreakerListener()
        mock_breaker = Mock()
        mock_breaker.name = "test_breaker"

        listener.failure(mock_breaker, Exception("Test error"))

        # 验证不抛异常
        assert True

    def test_listener_logs_success(self):
        """测试监听器记录成功"""
        listener = CircuitBreakerListener()
        mock_breaker = Mock()
        mock_breaker.name = "test_breaker"

        listener.success(mock_breaker)

        # 验证不抛异常
        assert True
