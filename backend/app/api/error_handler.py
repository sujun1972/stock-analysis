"""
API 错误处理装饰器
统一处理所有 API 端点的异常，提供一致的错误响应格式
"""

from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException
from loguru import logger
import traceback
import re


class APIError(Exception):
    """API 基础异常类"""
    def __init__(self, message: str, status_code: int = 500, details: Any = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class BadRequestError(APIError):
    """400 错误请求"""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, 400, details)


class NotFoundError(APIError):
    """404 资源不存在"""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, 404, details)


class ConflictError(APIError):
    """409 资源冲突"""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, 409, details)


class InternalServerError(APIError):
    """500 服务器内部错误"""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, 500, details)


def handle_api_errors(func: Callable) -> Callable:
    """
    API 错误处理装饰器

    自动捕获并处理常见异常，返回统一的错误响应格式。

    支持的异常类型：
    - ValueError: 400 Bad Request
    - FileNotFoundError: 404 Not Found
    - KeyError: 400 Bad Request
    - TypeError: 400 Bad Request
    - APIError 及其子类: 自定义状态码
    - HTTPException: 直接抛出
    - 其他异常: 500 Internal Server Error

    使用示例：
    ```python
    @router.get("/endpoint")
    @handle_api_errors
    async def my_endpoint():
        # 业务逻辑，无需 try-except
        result = await service.do_something()
        return result
    ```
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # 执行原函数
            return await func(*args, **kwargs)

        except HTTPException:
            # FastAPI 的 HTTPException 直接抛出
            raise

        except APIError as e:
            # 自定义 API 异常
            logger.warning(f"API 错误 [{e.status_code}]: {e.message}")
            if e.details:
                logger.debug(f"错误详情: {e.details}")
            raise HTTPException(
                status_code=e.status_code,
                detail={
                    "success": False,
                    "message": e.message,
                    "details": e.details
                } if e.details else {
                    "success": False,
                    "message": e.message
                }
            )

        except ValueError as e:
            # 参数错误
            logger.warning(f"参数错误: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": f"参数错误: {str(e)}"
                }
            )

        except (FileNotFoundError, KeyError) as e:
            # 资源不存在
            error_type = "文件" if isinstance(e, FileNotFoundError) else "资源"
            logger.warning(f"{error_type}不存在: {str(e)}")
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": f"{error_type}不存在: {str(e)}"
                }
            )

        except TypeError as e:
            # 类型错误
            logger.warning(f"类型错误: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": f"类型错误: {str(e)}"
                }
            )

        except PermissionError as e:
            # 权限错误
            logger.warning(f"权限不足: {str(e)}")
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "message": f"权限不足: {str(e)}"
                }
            )

        except Exception as e:
            # 未预期的服务器错误
            error_id = id(e)
            raw_error = str(e)

            # 记录完整错误到日志（包含敏感信息，仅用于调试）
            logger.error(
                f"服务器错误 [ID:{error_id}]: {raw_error}",
                exc_info=True
            )

            # 清理错误消息，移除敏感信息
            safe_message = _sanitize_error_message(raw_error)

            # 返回安全的错误响应
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "message": safe_message,
                    "error_id": error_id
                }
            )

    return wrapper


def handle_api_errors_sync(func: Callable) -> Callable:
    """
    同步函数的 API 错误处理装饰器

    用法与 handle_api_errors 相同，但用于同步函数。

    使用示例：
    ```python
    @router.get("/endpoint")
    @handle_api_errors_sync
    def my_sync_endpoint():
        result = service.do_something()
        return result
    ```
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except HTTPException:
            raise

        except APIError as e:
            logger.warning(f"API 错误 [{e.status_code}]: {e.message}")
            if e.details:
                logger.debug(f"错误详情: {e.details}")
            raise HTTPException(
                status_code=e.status_code,
                detail={
                    "success": False,
                    "message": e.message,
                    "details": e.details
                } if e.details else {
                    "success": False,
                    "message": e.message
                }
            )

        except ValueError as e:
            logger.warning(f"参数错误: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": f"参数错误: {str(e)}"
                }
            )

        except (FileNotFoundError, KeyError) as e:
            error_type = "文件" if isinstance(e, FileNotFoundError) else "资源"
            logger.warning(f"{error_type}不存在: {str(e)}")
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": f"{error_type}不存在: {str(e)}"
                }
            )

        except TypeError as e:
            logger.warning(f"类型错误: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": f"类型错误: {str(e)}"
                }
            )

        except PermissionError as e:
            logger.warning(f"权限不足: {str(e)}")
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "message": f"权限不足: {str(e)}"
                }
            )

        except Exception as e:
            error_id = id(e)
            raw_error = str(e)

            # 记录完整错误到日志
            logger.error(
                f"服务器错误 [ID:{error_id}]: {raw_error}",
                exc_info=True
            )

            # 清理错误消息
            safe_message = _sanitize_error_message(raw_error)

            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "message": safe_message,
                    "error_id": error_id
                }
            )

    return wrapper


# 便捷的异常抛出函数
def raise_bad_request(message: str, details: Any = None) -> None:
    """抛出 400 错误"""
    raise BadRequestError(message, details)


def raise_not_found(message: str, details: Any = None) -> None:
    """抛出 404 错误"""
    raise NotFoundError(message, details)


def raise_conflict(message: str, details: Any = None) -> None:
    """抛出 409 错误"""
    raise ConflictError(message, details)


def raise_internal_error(message: str, details: Any = None) -> None:
    """抛出 500 错误"""
    raise InternalServerError(message, details)


def _is_database_error(error_msg: str) -> bool:
    """
    检测是否为数据库相关错误

    Args:
        error_msg: 错误消息

    Returns:
        True 如果是数据库错误
    """
    db_indicators = [
        'column', 'table', 'database', 'sql', 'query',
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'FROM', 'WHERE',
        'constraint', 'foreign key', 'primary key', 'index',
        'LINE', 'HINT', 'relation', 'schema'
    ]
    error_lower = error_msg.lower()
    return any(indicator.lower() in error_lower for indicator in db_indicators)


def _sanitize_error_message(error_msg: str) -> str:
    """
    清理错误消息，移除敏感信息

    Args:
        error_msg: 原始错误消息

    Returns:
        清理后的错误消息
    """
    # 如果是数据库错误，返回通用消息
    if _is_database_error(error_msg):
        return "数据查询失败，请稍后重试"

    # 移除可能的文件路径
    error_msg = re.sub(r'/[^\s]+\.py', '[file]', error_msg)

    # 移除可能的 SQL 语句
    error_msg = re.sub(r'(SELECT|INSERT|UPDATE|DELETE)[\s\S]*?(FROM|INTO|SET|WHERE)', '[SQL]', error_msg, flags=re.IGNORECASE)

    # 截断过长的错误消息
    if len(error_msg) > 200:
        error_msg = error_msg[:200] + "..."

    return error_msg
