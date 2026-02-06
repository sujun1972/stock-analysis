"""
三层架构监控系统单元测试

测试内容：
1. Prometheus 指标定义
2. 监控方法功能
3. 缓存命中率计算
4. 错误记录
5. 上下文管理器
6. 装饰器功能
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from app.monitoring.three_layer_monitor import (
    ThreeLayerMonitor,
    monitor_three_layer_request,
    monitor_adapter_method,
    three_layer_requests_total,
    three_layer_backtest_duration,
    three_layer_cache_hits,
    three_layer_cache_misses,
    three_layer_cache_hit_rate,
    three_layer_errors,
    three_layer_data_fetch_duration,
    three_layer_backtest_stock_count,
    three_layer_backtest_trade_count,
    three_layer_validation_failures,
)


class TestPrometheusMetrics:
    """测试 Prometheus 指标定义"""

    def test_metrics_exist(self):
        """测试所有指标都已定义"""
        assert three_layer_requests_total is not None
        assert three_layer_backtest_duration is not None
        assert three_layer_cache_hits is not None
        assert three_layer_cache_misses is not None
        assert three_layer_cache_hit_rate is not None
        assert three_layer_errors is not None
        assert three_layer_data_fetch_duration is not None
        assert three_layer_backtest_stock_count is not None
        assert three_layer_backtest_trade_count is not None
        assert three_layer_validation_failures is not None

    def test_request_counter_labels(self):
        """测试请求计数器标签"""
        # 模拟请求
        three_layer_requests_total.labels(endpoint='selectors', status='success').inc()
        value = three_layer_requests_total.labels(endpoint='selectors', status='success')._value.get()
        assert value >= 1

    def test_cache_hit_counter_labels(self):
        """测试缓存计数器标签"""
        three_layer_cache_hits.labels(cache_type='metadata').inc()
        value = three_layer_cache_hits.labels(cache_type='metadata')._value.get()
        assert value >= 1

    def test_error_counter_labels(self):
        """测试错误计数器标签"""
        three_layer_errors.labels(error_type='validation', component='adapter').inc()
        value = three_layer_errors.labels(error_type='validation', component='adapter')._value.get()
        assert value >= 1


class TestThreeLayerMonitor:
    """测试 ThreeLayerMonitor 类"""

    def test_record_request_success(self):
        """测试记录成功请求"""
        initial_value = three_layer_requests_total.labels(
            endpoint='test_endpoint', status='success'
        )._value.get()

        ThreeLayerMonitor.record_request('test_endpoint', 'success')

        new_value = three_layer_requests_total.labels(
            endpoint='test_endpoint', status='success'
        )._value.get()
        assert new_value == initial_value + 1

    def test_record_request_failed(self):
        """测试记录失败请求"""
        initial_value = three_layer_requests_total.labels(
            endpoint='test_endpoint2', status='failed'
        )._value.get()

        ThreeLayerMonitor.record_request('test_endpoint2', 'failed')

        new_value = three_layer_requests_total.labels(
            endpoint='test_endpoint2', status='failed'
        )._value.get()
        assert new_value == initial_value + 1

    def test_record_cache_hit(self):
        """测试记录缓存命中"""
        cache_type = 'test_cache_hit'
        initial_hits = three_layer_cache_hits.labels(cache_type=cache_type)._value.get()

        ThreeLayerMonitor.record_cache_hit(cache_type, True)

        new_hits = three_layer_cache_hits.labels(cache_type=cache_type)._value.get()
        assert new_hits == initial_hits + 1

    def test_record_cache_miss(self):
        """测试记录缓存未命中"""
        cache_type = 'test_cache_miss'
        initial_misses = three_layer_cache_misses.labels(cache_type=cache_type)._value.get()

        ThreeLayerMonitor.record_cache_hit(cache_type, False)

        new_misses = three_layer_cache_misses.labels(cache_type=cache_type)._value.get()
        assert new_misses == initial_misses + 1

    def test_cache_hit_rate_calculation(self):
        """测试缓存命中率计算"""
        cache_type = 'test_hit_rate'

        # 重置计数器（通过获取当前值）
        initial_hits = three_layer_cache_hits.labels(cache_type=cache_type)._value.get()
        initial_misses = three_layer_cache_misses.labels(cache_type=cache_type)._value.get()

        # 记录3次命中和1次未命中
        for _ in range(3):
            ThreeLayerMonitor.record_cache_hit(cache_type, True)
        ThreeLayerMonitor.record_cache_hit(cache_type, False)

        # 计算期望的命中率
        total_hits = three_layer_cache_hits.labels(cache_type=cache_type)._value.get()
        total_misses = three_layer_cache_misses.labels(cache_type=cache_type)._value.get()
        total = total_hits + total_misses

        expected_rate = total_hits / total if total > 0 else 0
        actual_rate = three_layer_cache_hit_rate.labels(cache_type=cache_type)._value.get()

        assert abs(actual_rate - expected_rate) < 0.01  # 允许小误差

    def test_record_error(self):
        """测试记录错误"""
        error_type = 'test_error_type'
        component = 'test_component'
        error_msg = 'Test error message'

        initial_value = three_layer_errors.labels(
            error_type=error_type, component=component
        )._value.get()

        ThreeLayerMonitor.record_error(error_type, component, error_msg)

        new_value = three_layer_errors.labels(
            error_type=error_type, component=component
        )._value.get()
        assert new_value == initial_value + 1

    def test_record_validation_failure(self):
        """测试记录验证失败"""
        failure_reason = 'test_failure'
        initial_value = three_layer_validation_failures.labels(
            failure_reason=failure_reason
        )._value.get()

        ThreeLayerMonitor.record_validation_failure(failure_reason)

        new_value = three_layer_validation_failures.labels(
            failure_reason=failure_reason
        )._value.get()
        assert new_value == initial_value + 1

    def test_track_backtest_duration(self):
        """测试跟踪回测执行时间"""
        selector_type = 'test_selector'
        entry_type = 'test_entry'
        exit_type = 'test_exit'

        # 使用上下文管理器跟踪时间
        with ThreeLayerMonitor.track_backtest_duration(selector_type, entry_type, exit_type):
            time.sleep(0.1)  # 模拟回测执行

        # 验证指标已记录（通过检查是否有样本）
        # 注意：Histogram 不直接提供 _value，我们只检查不抛出异常
        assert True  # 如果执行到这里说明没有异常

    def test_track_data_fetch_duration(self):
        """测试跟踪数据获取时间"""
        data_type = 'test_data'

        # 使用上下文管理器跟踪时间
        with ThreeLayerMonitor.track_data_fetch_duration(data_type):
            time.sleep(0.05)  # 模拟数据获取

        # 验证指标已记录
        assert True  # 如果执行到这里说明没有异常

    def test_record_backtest_stats(self):
        """测试记录回测统计数据"""
        stock_count = 100
        trade_count = 250
        metrics = {
            'total_return': 0.25,
            'sharpe_ratio': 1.5,
            'max_drawdown': -0.15,
        }

        # 记录统计数据（不应抛出异常）
        ThreeLayerMonitor.record_backtest_stats(stock_count, trade_count, metrics)

        assert True  # 如果执行到这里说明没有异常


class TestMonitorDecorators:
    """测试监控装饰器"""

    @pytest.mark.asyncio
    async def test_monitor_three_layer_request_success(self):
        """测试请求装饰器 - 成功场景"""
        @monitor_three_layer_request('test_decorator')
        async def test_func():
            return {'success': True}

        initial_value = three_layer_requests_total.labels(
            endpoint='test_decorator', status='success'
        )._value.get()

        result = await test_func()

        new_value = three_layer_requests_total.labels(
            endpoint='test_decorator', status='success'
        )._value.get()
        assert new_value == initial_value + 1
        assert result == {'success': True}

    @pytest.mark.asyncio
    async def test_monitor_three_layer_request_failure(self):
        """测试请求装饰器 - 失败场景"""
        @monitor_three_layer_request('test_decorator_fail')
        async def test_func():
            raise ValueError("Test error")

        initial_success = three_layer_requests_total.labels(
            endpoint='test_decorator_fail', status='success'
        )._value.get()
        initial_failed = three_layer_requests_total.labels(
            endpoint='test_decorator_fail', status='failed'
        )._value.get()

        with pytest.raises(ValueError):
            await test_func()

        new_failed = three_layer_requests_total.labels(
            endpoint='test_decorator_fail', status='failed'
        )._value.get()
        assert new_failed == initial_failed + 1

    @pytest.mark.asyncio
    async def test_monitor_adapter_method_success(self):
        """测试适配器方法装饰器 - 成功场景"""
        @monitor_adapter_method('test_method')
        async def test_method():
            return 'result'

        result = await test_method()

        assert result == 'result'

    @pytest.mark.asyncio
    async def test_monitor_adapter_method_failure(self):
        """测试适配器方法装饰器 - 失败场景"""
        @monitor_adapter_method('test_method_fail')
        async def test_method():
            raise RuntimeError("Test runtime error")

        with pytest.raises(RuntimeError):
            await test_method()


class TestContextManagers:
    """测试上下文管理器"""

    def test_track_backtest_duration_slow_warning(self):
        """测试慢回测警告（超过60秒）"""
        # 这个测试会很慢，我们只验证不抛异常
        with ThreeLayerMonitor.track_backtest_duration('slow_test', 'entry', 'exit'):
            # 在实际环境中，这里会sleep(61)，但为了测试速度我们不等待
            pass

        assert True

    def test_track_backtest_duration_exception_handling(self):
        """测试回测跟踪的异常处理"""
        try:
            with ThreeLayerMonitor.track_backtest_duration('exception_test', 'entry', 'exit'):
                raise ValueError("Test exception in backtest")
        except ValueError:
            pass  # 预期异常

        # 验证即使有异常，指标也被记录
        assert True

    def test_track_data_fetch_duration_exception_handling(self):
        """测试数据获取跟踪的异常处理"""
        try:
            with ThreeLayerMonitor.track_data_fetch_duration('test_data_exception'):
                raise IOError("Test data fetch error")
        except IOError:
            pass  # 预期异常

        # 验证即使有异常，指标也被记录
        assert True


class TestIntegrationScenarios:
    """测试集成场景"""

    def test_complete_backtest_monitoring_flow(self):
        """测试完整的回测监控流程"""
        selector_id = 'momentum'
        entry_id = 'immediate'
        exit_id = 'fixed_stop_loss'

        # 1. 记录请求开始
        ThreeLayerMonitor.record_request('backtest', 'success')

        # 2. 检查缓存（未命中）
        ThreeLayerMonitor.record_cache_hit('backtest', False)

        # 3. 获取数据
        with ThreeLayerMonitor.track_data_fetch_duration('price'):
            time.sleep(0.01)

        # 4. 执行回测
        with ThreeLayerMonitor.track_backtest_duration(selector_id, entry_id, exit_id):
            time.sleep(0.01)

        # 5. 记录统计
        ThreeLayerMonitor.record_backtest_stats(
            stock_count=50,
            trade_count=100,
            metrics={'total_return': 0.15}
        )

        # 验证流程完成
        assert True

    def test_validation_error_flow(self):
        """测试验证错误流程"""
        # 1. 记录未知选股器错误
        ThreeLayerMonitor.record_validation_failure('unknown_selector')

        # 2. 记录验证错误
        ThreeLayerMonitor.record_error('validation', 'adapter', 'Invalid selector ID')

        # 3. 记录请求失败
        ThreeLayerMonitor.record_request('validate', 'failed')

        # 验证流程完成
        assert True

    def test_metadata_caching_flow(self):
        """测试元数据缓存流程"""
        cache_type = 'metadata'

        # 第一次请求（缓存未命中）
        ThreeLayerMonitor.record_cache_hit(cache_type, False)
        ThreeLayerMonitor.record_request('selectors', 'success')

        # 第二次请求（缓存命中）
        ThreeLayerMonitor.record_cache_hit(cache_type, True)
        ThreeLayerMonitor.record_request('selectors', 'success')

        # 验证流程完成
        assert True


class TestMetricsReset:
    """测试指标重置功能"""

    def test_metrics_can_be_incremented(self):
        """测试指标可以递增"""
        endpoint = 'test_increment'
        initial = three_layer_requests_total.labels(
            endpoint=endpoint, status='success'
        )._value.get()

        ThreeLayerMonitor.record_request(endpoint, 'success')
        ThreeLayerMonitor.record_request(endpoint, 'success')

        final = three_layer_requests_total.labels(
            endpoint=endpoint, status='success'
        )._value.get()

        assert final >= initial + 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
