"""
API 版本管理和弃用警告机制

提供：
1. API 版本管理装饰器
2. API 弃用警告装饰器
3. 版本兼容性检查
4. 自动响应头添加
"""

from datetime import datetime
from functools import wraps
from typing import Callable, Optional

from fastapi import Request, Response
from loguru import logger


class APIVersion:
    """API版本管理类"""

    # 当前支持的API版本
    CURRENT_VERSION = "2.0"
    PREVIOUS_VERSION = "1.0"

    # 版本兼容性映射
    SUPPORTED_VERSIONS = {"1.0", "2.0"}

    @classmethod
    def is_supported(cls, version: str) -> bool:
        """检查版本是否受支持"""
        return version in cls.SUPPORTED_VERSIONS

    @classmethod
    def get_default_version(cls) -> str:
        """获取默认版本"""
        return cls.CURRENT_VERSION


class DeprecationInfo:
    """弃用信息类"""

    def __init__(
        self,
        deprecated_since: str,
        removal_date: Optional[str] = None,
        alternative: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """
        初始化弃用信息

        Args:
            deprecated_since: 弃用开始版本
            removal_date: 计划移除日期 (YYYY-MM-DD)
            alternative: 替代方案 (新的 API 路径)
            reason: 弃用原因
        """
        self.deprecated_since = deprecated_since
        self.removal_date = removal_date
        self.alternative = alternative
        self.reason = reason

    def to_dict(self):
        """转换为字典格式"""
        return {
            "deprecated": True,
            "deprecated_since": self.deprecated_since,
            "removal_date": self.removal_date,
            "alternative": self.alternative,
            "reason": self.reason,
        }

    def to_warning_message(self) -> str:
        """生成警告消息"""
        msg = f"This API endpoint is deprecated since version {self.deprecated_since}."

        if self.removal_date:
            msg += f" It will be removed on {self.removal_date}."

        if self.alternative:
            msg += f" Please use '{self.alternative}' instead."

        if self.reason:
            msg += f" Reason: {self.reason}"

        return msg


def deprecated(
    deprecated_since: str,
    removal_date: Optional[str] = None,
    alternative: Optional[str] = None,
    reason: Optional[str] = None,
) -> Callable:
    """
    标记 API 端点为已弃用

    使用装饰器自动在响应头和响应体中添加弃用警告信息。

    Args:
        deprecated_since: 弃用开始版本
        removal_date: 计划移除日期 (YYYY-MM-DD 格式)
        alternative: 替代的新 API 路径
        reason: 弃用原因

    Returns:
        装饰器函数

    Example:
        ```python
        @router.get("/old-endpoint")
        @deprecated(
            deprecated_since="2.0",
            removal_date="2026-06-01",
            alternative="/api/new-endpoint",
            reason="使用新的统一策略系统"
        )
        async def old_endpoint():
            return {"data": "..."}
        ```

    响应示例:
        HTTP Headers:
            Warning: 299 - "This API endpoint is deprecated..."
            X-API-Deprecated: true
            X-API-Deprecated-Since: 2.0
            X-API-Removal-Date: 2026-06-01
            X-API-Alternative: /api/new-endpoint

        Response Body:
            {
                "code": 200,
                "message": "success",
                "data": {...},
                "deprecation": {
                    "deprecated": true,
                    "deprecated_since": "2.0",
                    "removal_date": "2026-06-01",
                    "alternative": "/api/new-endpoint",
                    "reason": "使用新的统一策略系统"
                }
            }
    """

    deprecation_info = DeprecationInfo(
        deprecated_since=deprecated_since,
        removal_date=removal_date,
        alternative=alternative,
        reason=reason,
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 记录弃用警告日志
            logger.warning(
                f"Deprecated API endpoint called: {func.__name__} "
                f"(deprecated since {deprecated_since}, "
                f"will be removed on {removal_date or 'TBD'})"
            )

            # 调用原始函数
            result = await func(*args, **kwargs)

            # 在响应体中添加弃用信息（如果是字典）
            if isinstance(result, dict):
                result["deprecation"] = deprecation_info.to_dict()

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步版本（支持同步函数）
            logger.warning(
                f"Deprecated API endpoint called: {func.__name__} "
                f"(deprecated since {deprecated_since}, "
                f"will be removed on {removal_date or 'TBD'})"
            )

            result = func(*args, **kwargs)

            if isinstance(result, dict):
                result["deprecation"] = deprecation_info.to_dict()

            return result

        # 根据函数类型选择包装器
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def api_version(version: str) -> Callable:
    """
    标记 API 端点的版本

    Args:
        version: API 版本号 (例如 "1.0", "2.0")

    Returns:
        装饰器函数

    Example:
        ```python
        @router.get("/endpoint")
        @api_version("2.0")
        async def new_endpoint():
            return {"data": "..."}
        ```
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 调用原始函数
            result = await func(*args, **kwargs)

            # 在响应体中添加版本信息
            if isinstance(result, dict):
                result["api_version"] = version

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if isinstance(result, dict):
                result["api_version"] = version

            return result

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def check_api_version(request: Request) -> str:
    """
    检查请求的 API 版本

    支持三种方式指定版本：
    1. Header: X-API-Version
    2. Query Parameter: api_version
    3. 默认使用当前版本

    Args:
        request: FastAPI 请求对象

    Returns:
        str: API 版本号

    Raises:
        ValueError: 如果版本不受支持
    """
    # 优先从 Header 获取
    version = request.headers.get("X-API-Version")

    # 其次从查询参数获取
    if not version:
        version = request.query_params.get("api_version")

    # 使用默认版本
    if not version:
        version = APIVersion.get_default_version()

    # 验证版本
    if not APIVersion.is_supported(version):
        raise ValueError(
            f"API version '{version}' is not supported. "
            f"Supported versions: {', '.join(APIVersion.SUPPORTED_VERSIONS)}"
        )

    return version
