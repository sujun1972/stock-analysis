"""
同步服务辅助函数

提供同步服务的公共工具函数
"""

from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger
from src.providers import DataProviderFactory

from app.core.exceptions import ExternalAPIError


def generate_task_id(module: str) -> str:
    """
    生成任务ID

    Args:
        module: 模块名称（如 'stock_list', 'daily', 'realtime'）

    Returns:
        格式化的任务ID（如 'stock_list_20240115123456'）
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{module}_{timestamp}"


def create_provider(
    source: str,
    token: Optional[str] = None,
    retry_count: int = 1
):
    """
    创建数据提供者

    Args:
        source: 数据源名称
        token: API令牌（可选）
        retry_count: 内部重试次数（默认1，禁用内部重试）

    Returns:
        数据提供者实例
    """
    return DataProviderFactory.create_provider(
        source=source,
        token=token or "",
        retry_count=retry_count
    )


def check_response_success(response: Any, error_context: str = "操作") -> Any:
    """
    检查API响应是否成功并返回数据

    Args:
        response: API响应对象
        error_context: 错误上下文描述

    Returns:
        响应中的数据（response.data）

    Raises:
        ExternalAPIError: 当响应不成功时
    """
    if not response.is_success():
        raise ExternalAPIError(
            response.error_message or f"{error_context}失败",
            error_code=response.error_code or "API_ERROR"
        )
    return response.data


def format_error_message(error: Exception) -> str:
    """
    格式化错误信息

    Args:
        error: 异常对象

    Returns:
        格式化的错误消息
    """
    if hasattr(error, 'message'):
        return error.message
    return str(error)


def calculate_progress(current: int, total: int, max_progress: int = 100) -> int:
    """
    计算进度百分比

    Args:
        current: 当前进度
        total: 总数
        max_progress: 最大进度值（默认100）

    Returns:
        进度百分比（0-max_progress）
    """
    if total <= 0:
        return 0
    return int((current / total) * max_progress)


def format_date_range(start_date: Optional[str], end_date: Optional[str]) -> Dict[str, str]:
    """
    格式化日期范围（去除连字符）

    Args:
        start_date: 开始日期（支持 'YYYYMMDD' 或 'YYYY-MM-DD'）
        end_date: 结束日期（支持 'YYYYMMDD' 或 'YYYY-MM-DD'）

    Returns:
        {"start": "YYYYMMDD", "end": "YYYYMMDD"}
    """
    result = {}

    if start_date:
        result["start"] = start_date.replace("-", "")

    if end_date:
        result["end"] = end_date.replace("-", "")
    else:
        result["end"] = datetime.now().strftime("%Y%m%d")

    return result


def create_sync_result(
    total: int,
    success_count: int = 0,
    failed_count: int = 0,
    skipped_count: int = 0,
    **extra_fields
) -> Dict:
    """
    创建统一的同步结果字典

    Args:
        total: 总数
        success_count: 成功数量
        failed_count: 失败数量
        skipped_count: 跳过数量
        **extra_fields: 额外字段

    Returns:
        同步结果字典
    """
    result = {
        "total": total,
        "success": success_count,
        "failed": failed_count,
        "skipped": skipped_count
    }

    # 添加额外字段
    result.update(extra_fields)

    return result


async def log_sync_progress(
    current: int,
    total: int,
    code: Optional[str] = None,
    status: str = "处理中",
    logger_instance=logger
):
    """
    记录同步进度日志

    Args:
        current: 当前进度
        total: 总数
        code: 股票代码（可选）
        status: 状态描述
        logger_instance: 日志实例
    """
    progress = calculate_progress(current, total)
    code_str = f" {code}" if code else ""
    logger_instance.info(f"[{current}/{total}]{code_str}: {status} ({progress}%)")
