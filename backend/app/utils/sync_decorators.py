"""
同步服务装饰器

提供同步任务管理、错误处理、重试等装饰器
"""

import asyncio
from datetime import datetime
from functools import wraps
from typing import Callable, Optional

from loguru import logger

from app.core.exceptions import DatabaseError, DataSyncError, ExternalAPIError
from app.services.config_service import ConfigService
from app.utils.retry import retry_async
from app.utils.sync_helpers import generate_task_id


def with_task_tracking(
    module: str,
    update_global_status: bool = True,
    auto_task_id: bool = True
):
    """
    任务追踪装饰器

    自动创建和更新同步任务状态，包括成功、失败、进度等

    Args:
        module: 模块名称（如 'stock_list', 'daily'）
        update_global_status: 是否更新全局同步状态（兼容旧接口）
        auto_task_id: 是否自动生成task_id（True时会自动生成，False时需要从参数中获取）

    Usage:
        @with_task_tracking(module="stock_list")
        async def sync_method(self, ...):
            # 任务逻辑
            return {"total": 100}  # 必须返回包含total的字典
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            config_service = getattr(self, 'config_service', None)
            if not config_service:
                config_service = ConfigService()

            # 获取或生成task_id
            task_id = kwargs.get('task_id')
            if auto_task_id and not task_id:
                task_id = generate_task_id(module)
                kwargs['task_id'] = task_id

            try:
                # 获取数据源配置
                config = await config_service.get_data_source_config()
                data_source = kwargs.get('data_source') or config.get('data_source', 'unknown')

                # 创建任务记录
                if task_id:
                    await config_service.create_sync_task(
                        task_id=task_id,
                        module=module,
                        data_source=data_source
                    )

                # 执行实际任务
                result = await func(self, *args, **kwargs)

                # 从结果中提取统计信息
                total = result.get('total', 0)
                success = result.get('success', total)
                failed = result.get('failed', 0)

                # 更新任务状态为完成
                if task_id:
                    await config_service.update_sync_task(
                        task_id=task_id,
                        status="completed",
                        total_count=total,
                        success_count=success,
                        failed_count=failed,
                        progress=100,
                        error_message=""
                    )

                # 更新全局状态（兼容旧接口）
                if update_global_status:
                    await config_service.update_sync_status(
                        status="completed",
                        last_sync_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        progress=100,
                        total=total,
                        completed=success
                    )

                return result

            except (ExternalAPIError, DatabaseError) as e:
                error_msg = str(e)
                logger.error(f"{module}同步失败: {error_msg}")

                # 更新任务状态为失败
                if task_id:
                    await config_service.update_sync_task(
                        task_id=task_id,
                        status="failed",
                        error_message=error_msg
                    )

                # 更新全局状态
                if update_global_status:
                    await config_service.update_sync_status(status="failed")

                # 重新抛出特定异常
                raise

            except Exception as e:
                error_msg = str(e)
                logger.error(f"{module}同步失败: {error_msg}")

                # 更新任务状态为失败
                if task_id:
                    await config_service.update_sync_task(
                        task_id=task_id,
                        status="failed",
                        error_message=error_msg
                    )

                # 更新全局状态
                if update_global_status:
                    await config_service.update_sync_status(status="failed")

                # 包装为DataSyncError抛出
                raise DataSyncError(
                    f"{module}同步失败",
                    error_code=f"{module.upper()}_SYNC_FAILED",
                    task_id=task_id,
                    reason=error_msg
                )

        return wrapper
    return decorator


def with_retry_tracking(
    max_retries: int = 3,
    delay_base: float = 3.0,
    delay_strategy: str = "linear"
):
    """
    重试追踪装饰器

    为异步函数提供重试机制，并更新任务状态

    Args:
        max_retries: 最大重试次数
        delay_base: 基础延迟时间（秒）
        delay_strategy: 延迟策略（'linear', 'exponential'）

    Usage:
        @with_retry_tracking(max_retries=3)
        async def fetch_data(self, task_id, ...):
            # 可能失败的操作
            return data
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            config_service = getattr(self, 'config_service', None)
            task_id = kwargs.get('task_id')

            # 定义重试回调
            async def on_retry_callback(retry_count: int, max_retries_val: int, error: Exception):
                if config_service and task_id:
                    error_with_retry = f"重试 {retry_count}/{max_retries_val}: {str(error)}"
                    await config_service.update_sync_task(
                        task_id=task_id,
                        error_message=error_with_retry,
                        progress=int((retry_count / max_retries_val) * 50)
                    )
                logger.warning(f"重试 {retry_count}/{max_retries_val}: {error}")

            # 使用retry_async包装函数调用
            return await retry_async(
                func,
                self,
                *args,
                **kwargs,
                max_retries=max_retries,
                delay_base=delay_base,
                delay_strategy=delay_strategy,
                on_retry=on_retry_callback
            )

        return wrapper
    return decorator


def with_abort_check(check_interval: int = 1):
    """
    中止检查装饰器

    在批量操作中定期检查是否收到中止请求

    Args:
        check_interval: 检查间隔（处理多少项后检查一次）

    Usage:
        @with_abort_check(check_interval=10)
        async def batch_sync(self, codes):
            for idx, code in enumerate(codes):
                # 处理逻辑
                yield idx, code
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            config_service = getattr(self, 'config_service', None)

            # 清除之前的中止标志
            if config_service:
                await config_service.clear_sync_abort_flag()

            # 执行函数
            result = await func(self, *args, **kwargs)

            # 如果是生成器，包装它以添加中止检查
            if hasattr(result, '__aiter__'):
                async def checked_generator():
                    idx = 0
                    async for item in result:
                        # 定期检查中止标志
                        if idx % check_interval == 0 and config_service:
                            if await config_service.check_sync_abort_flag():
                                logger.warning(f"收到中止请求，停止操作")
                                return

                        yield item
                        idx += 1

                return checked_generator()

            return result

        return wrapper
    return decorator


def with_progress_tracking(total_key: str = 'total'):
    """
    进度追踪装饰器

    自动更新任务进度

    Args:
        total_key: 结果字典中总数的键名

    Usage:
        @with_progress_tracking(total_key='codes')
        async def process_batch(self, codes):
            # 处理逻辑
            return {"codes": len(codes), "processed": count}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            config_service = getattr(self, 'config_service', None)
            task_id = kwargs.get('task_id')

            # 初始化进度
            if config_service and task_id:
                await config_service.update_sync_status(
                    status="running",
                    progress=0
                )

            # 执行函数
            result = await func(self, *args, **kwargs)

            # 更新最终进度
            if config_service and task_id:
                total = result.get(total_key, 0)
                await config_service.update_sync_status(
                    progress=100,
                    total=total,
                    completed=total
                )

            return result

        return wrapper
    return decorator


def with_timeout(seconds: float):
    """
    超时控制装饰器

    为异步函数添加超时控制

    Args:
        seconds: 超时时间（秒）

    Usage:
        @with_timeout(30.0)
        async def fetch_data(self):
            # 可能耗时的操作
            return data
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"{func.__name__} 超时（{seconds}秒）")

        return wrapper
    return decorator
