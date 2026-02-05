"""
Middleware 模块
包含各种中间件，如指标收集、日志记录等
"""

from app.middleware.metrics import metrics_middleware

__all__ = ["metrics_middleware"]
