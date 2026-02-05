"""
统一的 API 响应模型
提供一致的响应格式和工具函数
"""

from typing import TypeVar, Generic, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime


T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """
    统一的 API 响应模型

    提供一致的响应格式，支持泛型数据类型。

    Attributes:
        code: HTTP 状态码 (200, 400, 500 等)
        message: 响应消息
        data: 响应数据（泛型）
        timestamp: 响应时间戳
        request_id: 请求ID（可选，用于追踪）

    Example:
        >>> # 成功响应
        >>> ApiResponse.success(data={"total": 100})
        ApiResponse(code=200, message="success", data={"total": 100})

        >>> # 错误响应
        >>> ApiResponse.error(message="参数错误", code=400)
        ApiResponse(code=400, message="参数错误", data=None)

        >>> # 分页响应
        >>> ApiResponse.paginated(items=[...], total=100, page=1, page_size=20)
    """

    code: int = Field(..., description="HTTP 状态码")
    message: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="响应时间戳"
    )
    request_id: Optional[str] = Field(None, description="请求ID")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "success",
                "data": {"key": "value"},
                "timestamp": "2024-01-26T12:00:00",
                "request_id": "req_123456"
            }
        }

    # ==================== 便捷构造方法 ====================

    @classmethod
    def success(
        cls,
        data: Optional[T] = None,
        message: str = "success",
        request_id: Optional[str] = None
    ) -> "ApiResponse[T]":
        """
        创建成功响应

        Args:
            data: 响应数据
            message: 成功消息（默认 "success"）
            request_id: 请求ID

        Returns:
            ApiResponse: 成功响应对象
        """
        return cls(
            code=200,
            message=message,
            data=data,
            request_id=request_id
        )

    @classmethod
    def error(
        cls,
        message: str,
        code: int = 500,
        data: Optional[T] = None,
        request_id: Optional[str] = None
    ) -> "ApiResponse[T]":
        """
        创建错误响应

        Args:
            message: 错误消息
            code: HTTP 状态码（默认 500）
            data: 错误详情数据
            request_id: 请求ID

        Returns:
            ApiResponse: 错误响应对象
        """
        return cls(
            code=code,
            message=message,
            data=data,
            request_id=request_id
        )

    @classmethod
    def created(
        cls,
        data: Optional[T] = None,
        message: str = "created",
        request_id: Optional[str] = None
    ) -> "ApiResponse[T]":
        """
        创建资源创建成功响应 (201)

        Args:
            data: 创建的资源数据
            message: 成功消息
            request_id: 请求ID

        Returns:
            ApiResponse: 创建成功响应对象
        """
        return cls(
            code=201,
            message=message,
            data=data,
            request_id=request_id
        )

    @classmethod
    def no_content(
        cls,
        message: str = "no content",
        request_id: Optional[str] = None
    ) -> "ApiResponse[None]":
        """
        创建无内容响应 (204)

        Args:
            message: 响应消息
            request_id: 请求ID

        Returns:
            ApiResponse: 无内容响应对象
        """
        return cls(
            code=204,
            message=message,
            data=None,
            request_id=request_id
        )

    @classmethod
    def partial_content(
        cls,
        data: Optional[T] = None,
        message: str = "partial content",
        request_id: Optional[str] = None
    ) -> "ApiResponse[T]":
        """
        创建部分内容响应 (206)

        用于分页或部分成功的场景

        Args:
            data: 部分数据
            message: 响应消息
            request_id: 请求ID

        Returns:
            ApiResponse: 部分内容响应对象
        """
        return cls(
            code=206,
            message=message,
            data=data,
            request_id=request_id
        )

    @classmethod
    def bad_request(
        cls,
        message: str = "bad request",
        data: Optional[T] = None,
        request_id: Optional[str] = None
    ) -> "ApiResponse[T]":
        """
        创建错误请求响应 (400)

        Args:
            message: 错误消息
            data: 错误详情
            request_id: 请求ID

        Returns:
            ApiResponse: 错误请求响应对象
        """
        return cls(
            code=400,
            message=message,
            data=data,
            request_id=request_id
        )

    @classmethod
    def unauthorized(
        cls,
        message: str = "unauthorized",
        data: Optional[T] = None,
        request_id: Optional[str] = None
    ) -> "ApiResponse[T]":
        """
        创建未授权响应 (401)

        Args:
            message: 错误消息
            data: 错误详情
            request_id: 请求ID

        Returns:
            ApiResponse: 未授权响应对象
        """
        return cls(
            code=401,
            message=message,
            data=data,
            request_id=request_id
        )

    @classmethod
    def forbidden(
        cls,
        message: str = "forbidden",
        data: Optional[T] = None,
        request_id: Optional[str] = None
    ) -> "ApiResponse[T]":
        """
        创建禁止访问响应 (403)

        Args:
            message: 错误消息
            data: 错误详情
            request_id: 请求ID

        Returns:
            ApiResponse: 禁止访问响应对象
        """
        return cls(
            code=403,
            message=message,
            data=data,
            request_id=request_id
        )

    @classmethod
    def not_found(
        cls,
        message: str = "not found",
        data: Optional[T] = None,
        request_id: Optional[str] = None
    ) -> "ApiResponse[T]":
        """
        创建资源不存在响应 (404)

        Args:
            message: 错误消息
            data: 错误详情
            request_id: 请求ID

        Returns:
            ApiResponse: 资源不存在响应对象
        """
        return cls(
            code=404,
            message=message,
            data=data,
            request_id=request_id
        )

    @classmethod
    def conflict(
        cls,
        message: str = "conflict",
        data: Optional[T] = None,
        request_id: Optional[str] = None
    ) -> "ApiResponse[T]":
        """
        创建资源冲突响应 (409)

        Args:
            message: 错误消息
            data: 错误详情
            request_id: 请求ID

        Returns:
            ApiResponse: 资源冲突响应对象
        """
        return cls(
            code=409,
            message=message,
            data=data,
            request_id=request_id
        )

    @classmethod
    def internal_error(
        cls,
        message: str = "internal server error",
        data: Optional[T] = None,
        request_id: Optional[str] = None
    ) -> "ApiResponse[T]":
        """
        创建服务器内部错误响应 (500)

        Args:
            message: 错误消息
            data: 错误详情
            request_id: 请求ID

        Returns:
            ApiResponse: 服务器错误响应对象
        """
        return cls(
            code=500,
            message=message,
            data=data,
            request_id=request_id
        )

    @classmethod
    def warning(
        cls,
        data: Optional[T] = None,
        message: str = "warning",
        warning_code: Optional[str] = None,
        request_id: Optional[str] = None,
        **metadata
    ) -> "ApiResponse[T]":
        """
        创建警告响应 (206 Partial Content)

        用于操作成功但存在需要注意的情况。

        Args:
            data: 响应数据
            message: 警告消息
            warning_code: 警告代码（可选）
            request_id: 请求ID
            **metadata: 其他元数据（会合并到 data 中）

        Returns:
            ApiResponse: 警告响应对象

        Example:
            >>> ApiResponse.warning(
            ...     data={"result": "..."},
            ...     message="数据处理完成，但质量较低",
            ...     warning_code="LOW_QUALITY",
            ...     quality_score=0.75
            ... )
        """
        # 如果 data 是 None，创建空字典
        response_data = data if data is not None else {}

        # 如果 data 是字典，将 warning_code 和 metadata 合并进去
        if isinstance(response_data, dict):
            if warning_code:
                response_data["warning_code"] = warning_code
            response_data.update(metadata)

        return cls(
            code=206,
            message=message,
            data=response_data,
            request_id=request_id
        )

    # ==================== 特殊响应类型 ====================

    @classmethod
    def paginated(
        cls,
        items: list,
        total: int,
        page: int = 1,
        page_size: int = 20,
        message: str = "success",
        request_id: Optional[str] = None
    ) -> "ApiResponse[Dict[str, Any]]":
        """
        创建分页响应

        Args:
            items: 当前页数据列表
            total: 总记录数
            page: 当前页码
            page_size: 每页大小
            message: 响应消息
            request_id: 请求ID

        Returns:
            ApiResponse: 分页响应对象
        """
        return cls(
            code=200,
            message=message,
            data={
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            },
            request_id=request_id
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（向后兼容）

        Returns:
            Dict: 响应字典
        """
        result = {
            "code": self.code,
            "message": self.message,
            "data": self.data,
            "success": self.code < 400  # 状态码 < 400 表示成功
        }

        if self.request_id:
            result["request_id"] = self.request_id

        if self.timestamp:
            result["timestamp"] = self.timestamp

        return result


# ==================== 便捷函数 ====================

def success_response(
    data: Optional[Any] = None,
    message: str = "success"
) -> Dict[str, Any]:
    """
    快速创建成功响应字典（向后兼容）

    Args:
        data: 响应数据
        message: 成功消息

    Returns:
        Dict: 响应字典
    """
    return ApiResponse.success(data=data, message=message).to_dict()


def error_response(
    message: str,
    code: int = 500,
    data: Optional[Any] = None
) -> Dict[str, Any]:
    """
    快速创建错误响应字典（向后兼容）

    Args:
        message: 错误消息
        code: HTTP 状态码
        data: 错误详情

    Returns:
        Dict: 响应字典
    """
    return ApiResponse.error(message=message, code=code, data=data).to_dict()


def warning_response(
    data: Optional[Any] = None,
    message: str = "warning",
    warning_code: Optional[str] = None,
    **metadata
) -> Dict[str, Any]:
    """
    快速创建警告响应字典（向后兼容）

    Args:
        data: 响应数据
        message: 警告消息
        warning_code: 警告代码
        **metadata: 其他元数据

    Returns:
        Dict: 警告响应字典
    """
    return ApiResponse.warning(
        data=data,
        message=message,
        warning_code=warning_code,
        **metadata
    ).to_dict()


def paginated_response(
    items: list,
    total: int,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    快速创建分页响应字典（向后兼容）

    Args:
        items: 当前页数据
        total: 总记录数
        page: 当前页码
        page_size: 每页大小

    Returns:
        Dict: 分页响应字典
    """
    return ApiResponse.paginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    ).to_dict()
