"""
三层架构监控模块
为三层架构回测系统提供专门的监控指标和日志记录
"""

import time
from typing import Callable, Optional, Dict, Any
from functools import wraps
from contextlib import contextmanager

from prometheus_client import Counter, Histogram, Gauge
from loguru import logger


# ========== Prometheus 指标定义 ==========

# 三层架构请求总数
three_layer_requests_total = Counter(
    'three_layer_requests_total',
    'Total number of three-layer requests',
    ['endpoint', 'status']  # endpoint: selectors/entries/exits/validate/backtest, status: success/failed
)

# 回测执行时间
three_layer_backtest_duration = Histogram(
    'three_layer_backtest_duration_seconds',
    'Duration of backtest execution in seconds',
    ['selector_type', 'entry_type', 'exit_type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# 缓存命中统计
three_layer_cache_hits = Counter(
    'three_layer_cache_hits_total',
    'Total number of cache hits',
    ['cache_type']  # cache_type: metadata/backtest
)

# 缓存未命中统计
three_layer_cache_misses = Counter(
    'three_layer_cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

# 缓存命中率
three_layer_cache_hit_rate = Gauge(
    'three_layer_cache_hit_rate',
    'Cache hit rate (0-1)',
    ['cache_type']
)

# 错误计数
three_layer_errors = Counter(
    'three_layer_errors_total',
    'Total number of errors',
    ['error_type', 'component']  # error_type: validation/execution/data, component: adapter/api
)

# 数据获取时间
three_layer_data_fetch_duration = Histogram(
    'three_layer_data_fetch_duration_seconds',
    'Duration of data fetching in seconds',
    ['data_type'],  # data_type: price/metadata
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# 回测中的股票数量
three_layer_backtest_stock_count = Histogram(
    'three_layer_backtest_stock_count',
    'Number of stocks in backtest',
    buckets=[1, 10, 50, 100, 500, 1000, 2000, 5000]
)

# 回测中的交易次数
three_layer_backtest_trade_count = Histogram(
    'three_layer_backtest_trade_count',
    'Number of trades in backtest',
    buckets=[1, 10, 50, 100, 500, 1000, 5000, 10000]
)

# 验证失败次数
three_layer_validation_failures = Counter(
    'three_layer_validation_failures_total',
    'Total number of validation failures',
    ['failure_reason']  # failure_reason: unknown_selector/unknown_entry/unknown_exit/invalid_params
)


# ========== 监控辅助类 ==========

class ThreeLayerMonitor:
    """
    三层架构监控器

    职责：
    1. 记录请求和响应指标
    2. 记录缓存命中率
    3. 记录错误和异常
    4. 记录性能数据
    5. 提供结构化日志
    """

    @staticmethod
    def record_request(endpoint: str, status: str = 'success'):
        """
        记录请求

        Args:
            endpoint: 端点名称 (selectors/entries/exits/validate/backtest)
            status: 请求状态 (success/failed)
        """
        three_layer_requests_total.labels(
            endpoint=endpoint,
            status=status
        ).inc()

        logger.bind(
            component='three_layer',
            endpoint=endpoint,
            status=status
        ).info(f"Three-layer request: {endpoint} - {status}")

    @staticmethod
    def record_cache_hit(cache_type: str, is_hit: bool):
        """
        记录缓存命中情况

        Args:
            cache_type: 缓存类型 (metadata/backtest)
            is_hit: 是否命中缓存
        """
        if is_hit:
            three_layer_cache_hits.labels(cache_type=cache_type).inc()
            logger.bind(
                component='three_layer',
                cache_type=cache_type,
                cache_hit=True
            ).debug(f"Cache hit: {cache_type}")
        else:
            three_layer_cache_misses.labels(cache_type=cache_type).inc()
            logger.bind(
                component='three_layer',
                cache_type=cache_type,
                cache_hit=False
            ).debug(f"Cache miss: {cache_type}")

        # 更新缓存命中率
        hits = three_layer_cache_hits.labels(cache_type=cache_type)._value.get()
        misses = three_layer_cache_misses.labels(cache_type=cache_type)._value.get()
        total = hits + misses
        if total > 0:
            hit_rate = hits / total
            three_layer_cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)

    @staticmethod
    def record_error(error_type: str, component: str, error_msg: str):
        """
        记录错误

        Args:
            error_type: 错误类型 (validation/execution/data)
            component: 组件名称 (adapter/api)
            error_msg: 错误消息
        """
        three_layer_errors.labels(
            error_type=error_type,
            component=component
        ).inc()

        logger.bind(
            component='three_layer',
            error_type=error_type,
            error_component=component
        ).error(f"Three-layer error [{error_type}]: {error_msg}")

    @staticmethod
    def record_validation_failure(failure_reason: str):
        """
        记录验证失败

        Args:
            failure_reason: 失败原因 (unknown_selector/unknown_entry/unknown_exit/invalid_params)
        """
        three_layer_validation_failures.labels(
            failure_reason=failure_reason
        ).inc()

        logger.bind(
            component='three_layer',
            failure_reason=failure_reason
        ).warning(f"Validation failure: {failure_reason}")

    @staticmethod
    @contextmanager
    def track_backtest_duration(selector_type: str, entry_type: str, exit_type: str):
        """
        跟踪回测执行时间的上下文管理器

        Args:
            selector_type: 选股器类型
            entry_type: 入场策略类型
            exit_type: 退出策略类型

        Usage:
            with ThreeLayerMonitor.track_backtest_duration('momentum', 'immediate', 'fixed_stop_loss'):
                # 执行回测
                pass
        """
        start_time = time.time()

        logger.bind(
            component='three_layer',
            selector_type=selector_type,
            entry_type=entry_type,
            exit_type=exit_type
        ).info(f"Backtest started: {selector_type}/{entry_type}/{exit_type}")

        try:
            yield
        finally:
            duration = time.time() - start_time

            # 记录Prometheus指标
            three_layer_backtest_duration.labels(
                selector_type=selector_type,
                entry_type=entry_type,
                exit_type=exit_type
            ).observe(duration)

            # 记录日志
            logger.bind(
                component='three_layer',
                selector_type=selector_type,
                entry_type=entry_type,
                exit_type=exit_type,
                duration_seconds=round(duration, 2),
                performance=True
            ).info(f"Backtest completed in {duration:.2f}s")

            # 慢回测警告（超过60秒）
            if duration > 60:
                logger.bind(
                    component='three_layer',
                    selector_type=selector_type,
                    entry_type=entry_type,
                    exit_type=exit_type,
                    duration_seconds=round(duration, 2)
                ).warning(f"Slow backtest: {duration:.2f}s")

    @staticmethod
    @contextmanager
    def track_data_fetch_duration(data_type: str):
        """
        跟踪数据获取时间的上下文管理器

        Args:
            data_type: 数据类型 (price/metadata)

        Usage:
            with ThreeLayerMonitor.track_data_fetch_duration('price'):
                # 获取数据
                pass
        """
        start_time = time.time()

        try:
            yield
        finally:
            duration = time.time() - start_time

            # 记录Prometheus指标
            three_layer_data_fetch_duration.labels(
                data_type=data_type
            ).observe(duration)

            # 记录日志
            logger.bind(
                component='three_layer',
                data_type=data_type,
                duration_seconds=round(duration, 2)
            ).debug(f"Data fetch completed: {data_type} in {duration:.2f}s")

    @staticmethod
    def record_backtest_stats(stock_count: int, trade_count: int, metrics: Dict[str, Any]):
        """
        记录回测统计数据

        Args:
            stock_count: 股票数量
            trade_count: 交易次数
            metrics: 回测指标字典
        """
        # 记录Prometheus指标
        three_layer_backtest_stock_count.observe(stock_count)
        three_layer_backtest_trade_count.observe(trade_count)

        # 记录详细日志
        logger.bind(
            component='three_layer',
            stock_count=stock_count,
            trade_count=trade_count,
            total_return=metrics.get('total_return'),
            sharpe_ratio=metrics.get('sharpe_ratio'),
            max_drawdown=metrics.get('max_drawdown'),
            performance=True
        ).info(f"Backtest stats: {stock_count} stocks, {trade_count} trades")


# ========== 装饰器 ==========

def monitor_three_layer_request(endpoint: str):
    """
    监控三层架构请求的装饰器

    Args:
        endpoint: 端点名称

    Usage:
        @monitor_three_layer_request('selectors')
        async def get_selectors():
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                ThreeLayerMonitor.record_request(endpoint, 'success')
                return result
            except Exception as e:
                ThreeLayerMonitor.record_request(endpoint, 'failed')
                ThreeLayerMonitor.record_error(
                    error_type='execution',
                    component='api',
                    error_msg=str(e)
                )
                raise
        return wrapper
    return decorator


def monitor_adapter_method(method_name: str):
    """
    监控适配器方法的装饰器

    Args:
        method_name: 方法名称

    Usage:
        @monitor_adapter_method('get_selectors')
        async def get_selectors(self):
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            logger.bind(
                component='three_layer_adapter',
                method=method_name
            ).debug(f"Adapter method started: {method_name}")

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                logger.bind(
                    component='three_layer_adapter',
                    method=method_name,
                    duration_seconds=round(duration, 2)
                ).debug(f"Adapter method completed: {method_name} in {duration:.2f}s")

                return result
            except Exception as e:
                duration = time.time() - start_time

                logger.bind(
                    component='three_layer_adapter',
                    method=method_name,
                    duration_seconds=round(duration, 2),
                    error_type=type(e).__name__
                ).error(f"Adapter method failed: {method_name} - {str(e)}")

                raise
        return wrapper
    return decorator
