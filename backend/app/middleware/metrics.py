"""
Prometheus 指标中间件
用于收集 HTTP 请求、响应时间、缓存命中率等指标
"""

import time
from typing import Callable
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

# ========== HTTP 请求指标 ==========

# HTTP 请求总数计数器
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

# HTTP 请求响应时间直方图
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

# HTTP 请求大小直方图
http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

# HTTP 响应大小直方图
http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000]
)

# ========== 缓存指标 ==========

# 缓存命中率
cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate (0-1)'
)

# 缓存命中次数
cache_hits_total = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

# 缓存未命中次数
cache_misses_total = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

# ========== 数据库指标 ==========

# 数据库连接池大小
database_connection_pool_size = Gauge(
    'database_connection_pool_size',
    'Database connection pool size'
)

# 数据库连接池使用数
database_connection_pool_in_use = Gauge(
    'database_connection_pool_in_use',
    'Number of database connections in use'
)

# 数据库查询响应时间
database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ========== 健康检查指标 ==========

# 健康检查失败次数
health_check_failures_total = Counter(
    'health_check_failures_total',
    'Total number of health check failures',
    ['service']
)

# ========== 业务指标 ==========

# 数据同步任务计数
data_sync_tasks_total = Counter(
    'data_sync_tasks_total',
    'Total number of data sync tasks',
    ['status']  # success, failed
)

# 回测任务计数
backtest_tasks_total = Counter(
    'backtest_tasks_total',
    'Total number of backtest tasks',
    ['status']  # success, failed
)

# 特征计算任务计数
feature_calculation_tasks_total = Counter(
    'feature_calculation_tasks_total',
    'Total number of feature calculation tasks',
    ['status']  # success, failed
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Prometheus 指标收集中间件
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理每个 HTTP 请求，收集指标
        """
        # 跳过 /metrics 端点本身，避免循环
        if request.url.path == "/metrics":
            return await call_next(request)

        # 记录请求开始时间
        start_time = time.time()

        # 获取请求大小
        request_size = int(request.headers.get("content-length", 0))

        # 处理请求
        try:
            response = await call_next(request)
        except Exception as e:
            # 记录异常
            logger.error(f"Request failed: {request.method} {request.url.path} - {e}")
            # 记录 5xx 错误
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status="500"
            ).inc()
            raise

        # 计算响应时间
        duration = time.time() - start_time

        # 获取响应大小
        response_size = int(response.headers.get("content-length", 0))

        # 记录指标
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        http_request_size_bytes.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(request_size)

        http_response_size_bytes.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(response_size)

        return response


async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """
    指标收集中间件函数版本（用于 @app.middleware("http") 装饰器）
    """
    middleware = MetricsMiddleware(app=None)
    return await middleware.dispatch(request, call_next)


def update_cache_metrics(cache_type: str, is_hit: bool):
    """
    更新缓存指标

    Args:
        cache_type: 缓存类型（如 'redis', 'memory'）
        is_hit: 是否命中缓存
    """
    if is_hit:
        cache_hits_total.labels(cache_type=cache_type).inc()
    else:
        cache_misses_total.labels(cache_type=cache_type).inc()

    # 计算命中率
    hits = cache_hits_total.labels(cache_type=cache_type)._value.get()
    misses = cache_misses_total.labels(cache_type=cache_type)._value.get()
    total = hits + misses
    if total > 0:
        cache_hit_rate.set(hits / total)


def update_database_pool_metrics(pool_size: int, in_use: int):
    """
    更新数据库连接池指标

    Args:
        pool_size: 连接池大小
        in_use: 正在使用的连接数
    """
    database_connection_pool_size.set(pool_size)
    database_connection_pool_in_use.set(in_use)


def record_database_query(query_type: str, duration: float):
    """
    记录数据库查询时间

    Args:
        query_type: 查询类型（如 'select', 'insert', 'update'）
        duration: 查询持续时间（秒）
    """
    database_query_duration_seconds.labels(query_type=query_type).observe(duration)


def record_health_check_failure(service: str):
    """
    记录健康检查失败

    Args:
        service: 服务名称
    """
    health_check_failures_total.labels(service=service).inc()


def record_data_sync_task(status: str):
    """
    记录数据同步任务

    Args:
        status: 任务状态（'success' 或 'failed'）
    """
    data_sync_tasks_total.labels(status=status).inc()


def record_backtest_task(status: str):
    """
    记录回测任务

    Args:
        status: 任务状态（'success' 或 'failed'）
    """
    backtest_tasks_total.labels(status=status).inc()


def record_feature_calculation_task(status: str):
    """
    记录特征计算任务

    Args:
        status: 任务状态（'success' 或 'failed'）
    """
    feature_calculation_tasks_total.labels(status=status).inc()
