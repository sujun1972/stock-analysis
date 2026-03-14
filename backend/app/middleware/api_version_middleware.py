"""
API 版本管理中间件

自动在所有 API 响应中添加版本信息，并记录 API 调用日志。
"""

from typing import Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.api_versioning import APIVersion


class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    API 版本管理中间件

    功能：
    1. 在所有响应中自动添加 X-API-Version 响应头
    2. 记录每个 API 调用的版本信息
    3. 验证客户端请求的版本是否受支持
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并添加版本信息

        Args:
            request: HTTP 请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP 响应（已添加版本头）
        """
        # 只处理 /api/ 开头的路由
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # 提取客户端请求的版本
        client_version = (
            request.headers.get("X-API-Version")
            or request.query_params.get("api_version")
            or APIVersion.get_default_version()
        )

        # 验证版本是否受支持
        if not APIVersion.is_supported(client_version):
            logger.warning(
                f"Unsupported API version requested: {client_version} "
                f"for {request.method} {request.url.path}"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "code": 400,
                    "message": f"API version '{client_version}' is not supported",
                    "data": {
                        "supported_versions": list(APIVersion.SUPPORTED_VERSIONS),
                        "current_version": APIVersion.CURRENT_VERSION,
                    },
                    "success": False,
                },
            )

        # 记录 API 调用
        logger.debug(
            f"API Call: {request.method} {request.url.path} "
            f"(client_version={client_version}, user_agent={request.headers.get('user-agent', 'unknown')})"
        )

        # 调用下一个处理器
        response = await call_next(request)

        # 添加版本信息到响应头
        response.headers["X-API-Version"] = APIVersion.CURRENT_VERSION
        response.headers["X-API-Supported-Versions"] = ", ".join(
            sorted(APIVersion.SUPPORTED_VERSIONS)
        )

        return response
