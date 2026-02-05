"""
Rate Limiting 中间件
使用 slowapi 实现请求限流
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger


# 创建限流器实例
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],  # 默认限制：每分钟200次请求
    storage_uri="memory://",  # 使用内存存储（生产环境建议使用 Redis）
    strategy="fixed-window",  # 固定窗口策略
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    自定义限流超出处理器
    """
    client_ip = get_remote_address(request)
    logger.warning(
        f"🚫 Rate limit exceeded | IP: {client_ip} | Path: {request.url.path} | "
        f"Limit: {exc.detail}"
    )

    # 返回标准的 429 响应
    return JSONResponse(
        content={
            "error": "rate_limit_exceeded",
            "message": "请求过于频繁，请稍后再试",
            "detail": exc.detail,
            "retry_after": getattr(exc, "retry_after", 60),
        },
        status_code=429,
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
    )


# 不同等级的限流装饰器
def strict_limit():
    """严格限流：适用于资源密集型操作"""
    return limiter.limit("10/minute")


def normal_limit():
    """普通限流：适用于一般API"""
    return limiter.limit("100/minute")


def relaxed_limit():
    """宽松限流：适用于轻量级查询"""
    return limiter.limit("300/minute")


def no_limit():
    """无限流：适用于健康检查等端点"""
    return limiter.exempt
