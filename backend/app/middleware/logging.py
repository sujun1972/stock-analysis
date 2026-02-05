"""
日志中间件
记录所有HTTP请求和响应，包含结构化上下文信息
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging_config import get_logger

logger = get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    HTTP请求/响应日志中间件

    功能：
    - 记录每个请求的详细信息（方法、路径、客户端IP等）
    - 记录响应状态码和处理时间
    - 自动记录异常和错误
    - 结构化日志输出（JSON格式）
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录日志"""
        # 记录请求开始时间
        start_time = time.time()

        # 提取请求信息
        request_id = request.headers.get("X-Request-ID", "")
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # 记录请求日志（带结构化上下文）
        logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=client_ip,
            user_agent=user_agent,
        ).info(f"{request.method} {request.url.path}")

        try:
            # 处理请求
            response = await call_next(request)

            # 计算处理时间
            duration_ms = (time.time() - start_time) * 1000

            # 记录响应日志
            log_level = "info"
            if response.status_code >= 500:
                log_level = "error"
            elif response.status_code >= 400:
                log_level = "warning"

            # 使用性能标签，这些日志会单独记录到 performance_*.json
            logger.bind(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                performance=True,  # 标记为性能日志
            ).log(
                log_level.upper(),
                f"{request.method} {request.url.path} - {response.status_code} ({duration_ms:.2f}ms)",
            )

            # 慢请求警告（超过1秒）
            if duration_ms > 1000:
                logger.bind(
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    duration_ms=round(duration_ms, 2),
                ).warning(f"慢请求警告: {request.method} {request.url.path} 耗时 {duration_ms:.2f}ms")

            return response

        except Exception as e:
            # 计算处理时间
            duration_ms = (time.time() - start_time) * 1000

            # 记录异常日志
            logger.bind(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error_type=type(e).__name__,
            ).error(f"请求处理失败: {request.method} {request.url.path} - {str(e)}")

            # 重新抛出异常，让异常处理器处理
            raise


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    轻量级日志中间件函数（可选使用）
    如果不想使用 BaseHTTPMiddleware，可以直接使用这个函数
    """
    start_time = time.time()

    # 提取请求信息
    client_ip = request.client.host if request.client else "unknown"

    # 记录请求
    logger.bind(
        method=request.method,
        path=request.url.path,
        client_ip=client_ip,
    ).info(f"请求: {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # 记录响应
        logger.bind(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            performance=True,
        ).info(f"响应: {response.status_code} ({duration_ms:.2f}ms)")

        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.bind(
            method=request.method,
            path=request.url.path,
            duration_ms=round(duration_ms, 2),
        ).error(f"请求失败: {str(e)}")
        raise
