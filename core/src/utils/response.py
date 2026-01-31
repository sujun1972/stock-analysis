"""
统一API返回格式

提供标准化的API响应格式，支持成功、错误和警告三种状态。

该模块定义了整个stock-analysis项目的API返回格式:
- Response类提供统一的返回格式
- ResponseStatus枚举定义响应状态
- 支持元数据(metadata)用于传递额外信息
- 支持结构化输出(to_dict)用于API返回和序列化

Examples:
    >>> # 成功情况
    >>> response = Response.success(
    ...     data={'features': df, 'count': 125},
    ...     message="特征计算完成",
    ...     elapsed_time="2.5s",
    ...     n_features=125
    ... )
    >>> print(response.is_success())  # True
    >>> print(response.data['count'])  # 125

    >>> # 失败情况
    >>> response = Response.error(
    ...     error="数据验证失败",
    ...     error_code="DATA_VALIDATION_ERROR",
    ...     stock_code="000001",
    ...     field="close"
    ... )
    >>> print(response.is_success())  # False
    >>> print(response.error_code)  # DATA_VALIDATION_ERROR

    >>> # 警告情况
    >>> response = Response.warning(
    ...     message="部分数据缺失，已使用默认值填充",
    ...     data=processed_df,
    ...     missing_count=10
    ... )
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional
from enum import Enum


class ResponseStatus(Enum):
    """响应状态枚举

    Attributes:
        SUCCESS: 操作成功
        ERROR: 操作失败
        WARNING: 操作完成但有警告
    """
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Response:
    """统一返回格式

    提供标准化的API响应格式，包含状态、数据、消息、错误信息和元数据。

    Attributes:
        status: 响应状态(SUCCESS/ERROR/WARNING)
        data: 返回的数据，可以是任意类型
        message: 人类可读的消息
        error_message: 错误消息(仅在ERROR状态时使用)
        error_code: 机器可读的错误代码(仅在ERROR状态时使用)
        metadata: 额外的元数据，例如执行时间、数量统计等

    Examples:
        >>> # 使用类方法创建成功响应
        >>> resp = Response.success(
        ...     data={'result': [1, 2, 3]},
        ...     message="计算完成",
        ...     count=3,
        ...     elapsed=1.5
        ... )
        >>> resp.is_success()
        True

        >>> # 使用类方法创建错误响应
        >>> resp = Response.error(
        ...     error="文件不存在",
        ...     error_code="FILE_NOT_FOUND",
        ...     path="/tmp/data.csv"
        ... )
        >>> resp.is_success()
        False

        >>> # 转换为字典
        >>> resp.to_dict()
        {
            'status': 'error',
            'error': '文件不存在',
            'error_code': 'FILE_NOT_FOUND',
            'metadata': {'path': '/tmp/data.csv'}
        }
    """
    status: ResponseStatus
    data: Any = None
    message: str = ""
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        data: Any = None,
        message: str = "操作成功",
        **metadata
    ) -> 'Response':
        """创建成功响应

        Args:
            data: 返回的数据
            message: 成功消息，默认"操作成功"
            **metadata: 任意额外的元数据，如elapsed_time、count等

        Returns:
            Response对象，status=SUCCESS

        Examples:
            >>> # 返回DataFrame
            >>> resp = Response.success(
            ...     data=features_df,
            ...     message="特征计算完成",
            ...     n_features=125,
            ...     n_samples=1000,
            ...     elapsed_time="2.5s"
            ... )

            >>> # 返回字典
            >>> resp = Response.success(
            ...     data={'sharpe': 1.5, 'return': 0.25},
            ...     message="回测完成",
            ...     total_trades=150
            ... )

            >>> # 仅返回消息
            >>> resp = Response.success(message="数据已保存")
        """
        return cls(
            status=ResponseStatus.SUCCESS,
            data=data,
            message=message,
            metadata=metadata
        )

    @classmethod
    def error(
        cls,
        error: str,
        error_code: Optional[str] = None,
        data: Any = None,
        **metadata
    ) -> 'Response':
        """创建错误响应

        Args:
            error: 错误消息
            error_code: 机器可读的错误代码，如"DATA_VALIDATION_ERROR"
            data: 可选的部分数据(即使失败也可能有部分结果)
            **metadata: 错误相关的上下文信息

        Returns:
            Response对象，status=ERROR

        Examples:
            >>> # 数据验证错误
            >>> resp = Response.error(
            ...     error="股票代码不能为空",
            ...     error_code="EMPTY_STOCK_CODE",
            ...     field="stock_code",
            ...     value=""
            ... )

            >>> # 网络请求失败
            >>> resp = Response.error(
            ...     error="API请求失败",
            ...     error_code="API_REQUEST_FAILED",
            ...     provider="akshare",
            ...     status_code=500,
            ...     url="https://api.example.com"
            ... )

            >>> # 模型训练失败(附带部分数据)
            >>> resp = Response.error(
            ...     error="训练提前停止",
            ...     error_code="EARLY_STOPPING",
            ...     data={'best_iteration': 50, 'best_score': 0.75},
            ...     reason="验证集性能下降"
            ... )
        """
        return cls(
            status=ResponseStatus.ERROR,
            error_message=error,
            error_code=error_code,
            data=data,
            metadata=metadata
        )

    @classmethod
    def warning(
        cls,
        message: str,
        data: Any = None,
        **metadata
    ) -> 'Response':
        """创建警告响应

        表示操作完成，但有需要注意的情况。

        Args:
            message: 警告消息
            data: 返回的数据
            **metadata: 警告相关的额外信息

        Returns:
            Response对象，status=WARNING

        Examples:
            >>> # 部分数据缺失
            >>> resp = Response.warning(
            ...     message="部分数据缺失，已使用前向填充",
            ...     data=processed_df,
            ...     missing_count=15,
            ...     fill_method="forward"
            ... )

            >>> # 性能警告
            >>> resp = Response.warning(
            ...     message="计算时间超过预期",
            ...     data=results,
            ...     elapsed_time="120s",
            ...     expected_time="60s"
            ... )

            >>> # 数据质量警告
            >>> resp = Response.warning(
            ...     message="检测到异常值，已自动处理",
            ...     data=cleaned_data,
            ...     outlier_count=8,
            ...     method="winsorize"
            ... )
        """
        return cls(
            status=ResponseStatus.WARNING,
            message=message,
            data=data,
            metadata=metadata
        )

    def is_success(self) -> bool:
        """检查是否成功

        Returns:
            如果status为SUCCESS��返回True，否则返回False

        Examples:
            >>> resp = Response.success(data=[1, 2, 3])
            >>> resp.is_success()
            True

            >>> resp = Response.error(error="失败")
            >>> resp.is_success()
            False
        """
        return self.status == ResponseStatus.SUCCESS

    def is_error(self) -> bool:
        """检查是否为错误

        Returns:
            如果status为ERROR则返回True，否则返回False

        Examples:
            >>> resp = Response.error(error="失败")
            >>> resp.is_error()
            True

            >>> resp = Response.success(data=[1, 2, 3])
            >>> resp.is_error()
            False
        """
        return self.status == ResponseStatus.ERROR

    def is_warning(self) -> bool:
        """检查是否为警告

        Returns:
            如果status为WARNING则返回True，否则返回False

        Examples:
            >>> resp = Response.warning(message="注意", data=[1, 2, 3])
            >>> resp.is_warning()
            True

            >>> resp = Response.success(data=[1, 2, 3])
            >>> resp.is_warning()
            False
        """
        return self.status == ResponseStatus.WARNING

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        将Response对象转换为可序列化的字典，适合用于JSON API响应。
        只包含非空字段，减少冗余。

        Returns:
            包含响应信息的字典

        Examples:
            >>> # 成功响应
            >>> resp = Response.success(
            ...     data={'count': 100},
            ...     message="查询成功",
            ...     elapsed="0.5s"
            ... )
            >>> resp.to_dict()
            {
                'status': 'success',
                'message': '查询成功',
                'data': {'count': 100},
                'metadata': {'elapsed': '0.5s'}
            }

            >>> # 错误响应
            >>> resp = Response.error(
            ...     error="验证失败",
            ...     error_code="VALIDATION_ERROR",
            ...     field="price"
            ... )
            >>> resp.to_dict()
            {
                'status': 'error',
                'error': '验证失败',
                'error_code': 'VALIDATION_ERROR',
                'metadata': {'field': 'price'}
            }
        """
        result = {
            'status': self.status.value,
        }

        # 只添加非空字段
        if self.message:
            result['message'] = self.message

        if self.data is not None:
            result['data'] = self.data

        if self.error_message:
            result['error'] = self.error_message

        if self.error_code:
            result['error_code'] = self.error_code

        if self.metadata:
            result['metadata'] = self.metadata

        return result

    def __repr__(self) -> str:
        """字符串表示

        Returns:
            简洁的字符串表示

        Examples:
            >>> resp = Response.success(data={'count': 10}, message="完成")
            >>> repr(resp)
            "Response(status=SUCCESS, message='完成')"

            >>> resp = Response.error(error="失败", error_code="ERR001")
            >>> repr(resp)
            "Response(status=ERROR, error_code='ERR001')"
        """
        parts = [f"status={self.status.name}"]

        if self.is_success() and self.message:
            parts.append(f"message='{self.message}'")

        if self.is_error() and self.error_code:
            parts.append(f"error_code='{self.error_code}'")

        if self.data is not None:
            # 简化data的显示
            data_repr = str(type(self.data).__name__)
            parts.append(f"data=<{data_repr}>")

        return f"Response({', '.join(parts)})"


# 便捷函数别名
def success(data: Any = None, message: str = "操作成功", **metadata) -> Response:
    """创建成功响应的便捷函数

    等同于 Response.success()

    Args:
        data: 返回的数据
        message: 成功消息
        **metadata: 额外的元数据

    Returns:
        Response对象，status=SUCCESS

    Examples:
        >>> from src.utils.response import success
        >>> resp = success(data=[1, 2, 3], message="完成", count=3)
    """
    return Response.success(data=data, message=message, **metadata)


def error(error: str, error_code: Optional[str] = None, data: Any = None, **metadata) -> Response:
    """创建错误响应的便捷函数

    等同于 Response.error()

    Args:
        error: 错误消息
        error_code: 错误代码
        data: 可选的部分数据
        **metadata: 错误上下文

    Returns:
        Response对象，status=ERROR

    Examples:
        >>> from src.utils.response import error
        >>> resp = error(error="失败", error_code="ERR001", reason="超时")
    """
    return Response.error(error=error, error_code=error_code, data=data, **metadata)


def warning(message: str, data: Any = None, **metadata) -> Response:
    """创建警告响应的便捷函数

    等同于 Response.warning()

    Args:
        message: 警告消息
        data: 返回的数据
        **metadata: 警告相关信息

    Returns:
        Response对象，status=WARNING

    Examples:
        >>> from src.utils.response import warning
        >>> resp = warning(message="部分失败", data=results, failed_count=2)
    """
    return Response.warning(message=message, data=data, **metadata)
