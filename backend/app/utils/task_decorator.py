"""
定时任务装饰器
用于自动记录任务执行日志
"""

from functools import wraps
from loguru import logger
from typing import Callable, Any


def log_task_execution(task_name: str, module: str):
    """
    任务执行日志装饰器

    自动记录任务的开始、成功和失败状态到数据库

    Args:
        task_name: 任务名称（用于数据库查询）
        module: 模块名称

    Example:
        @celery_app.task(name='sync.stock_list')
        @log_task_execution('daily_stock_list_sync', 'stock_list')
        def sync_stock_list_task():
            # 任务逻辑
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            history_id = None

            try:
                # 记录任务开始
                from app.utils.task_logger import create_task_logger
                task_logger = create_task_logger()
                history_id = task_logger.log_task_start(task_name, module)

                # 执行任务
                result = func(*args, **kwargs)

                # 记录任务成功
                if history_id:
                    result_summary = None
                    if isinstance(result, dict):
                        result_summary = result
                    task_logger.log_task_success(history_id, result_summary)

                return result

            except Exception as e:
                # 记录任务失败
                if history_id:
                    from app.utils.task_logger import create_task_logger
                    task_logger = create_task_logger()
                    task_logger.log_task_failure(
                        history_id,
                        str(e),
                        {'error_type': type(e).__name__}
                    )

                # 重新抛出异常，让Celery处理重试逻辑
                raise

        return wrapper
    return decorator
