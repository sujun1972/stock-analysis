"""
同步服务基类

提供所有同步服务的公共功能和标准化接口
"""

import asyncio
from abc import ABC
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from loguru import logger

from app.core.exceptions import ExternalAPIError
from app.services.config_service import ConfigService
from app.services.data_service import DataDownloadService
from app.utils.retry import retry_async
from app.utils.sync_helpers import (
    check_response_success,
    create_provider,
    generate_task_id,
)


class BaseSyncService(ABC):
    """
    同步服务基类

    提供以下公共功能：
    - 配置管理
    - 数据源配置获取
    - Provider创建
    - 任务ID生成
    - 任务状态管理
    - 重试机制
    - 响应检查
    - 进度追踪
    """

    def __init__(self):
        """初始化同步服务基类"""
        self.config_service = ConfigService()
        self.data_service = DataDownloadService()

    # ==================== 配置管理 ====================

    async def get_config(self) -> Dict:
        """
        获取数据源配置

        Returns:
            数据源配置字典
        """
        return await self.config_service.get_data_source_config()

    def create_data_provider(
        self,
        source: str,
        token: Optional[str] = None,
        retry_count: int = 1
    ):
        """
        创建数据提供者

        Args:
            source: 数据源名称
            token: API令牌（可选）
            retry_count: Provider内部重试次数（默认1，禁用内部重试）

        Returns:
            数据提供者实例
        """
        return create_provider(source, token, retry_count)

    # ==================== 任务管理 ====================

    def generate_task_id(self, module: str) -> str:
        """
        生成任务ID

        Args:
            module: 模块名称

        Returns:
            任务ID
        """
        return generate_task_id(module)

    async def create_task(
        self,
        task_id: str,
        module: str,
        data_source: str
    ):
        """
        创建同步任务记录

        Args:
            task_id: 任务ID
            module: 模块名称
            data_source: 数据源
        """
        await self.config_service.create_sync_task(
            task_id=task_id,
            module=module,
            data_source=data_source
        )

    async def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        total_count: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 状态（可选）
            progress: 进度（可选）
            total_count: 总数（可选）
            success_count: 成功数（可选）
            failed_count: 失败数（可选）
            error_message: 错误信息（可选）
        """
        await self.config_service.update_sync_task(
            task_id=task_id,
            status=status,
            progress=progress,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            error_message=error_message
        )

    async def complete_task(
        self,
        task_id: str,
        total: int,
        success: Optional[int] = None,
        failed: int = 0
    ):
        """
        标记任务为完成

        Args:
            task_id: 任务ID
            total: 总数
            success: 成功数（默认等于total）
            failed: 失败数（默认0）
        """
        success_count = success if success is not None else total

        await self.update_task(
            task_id=task_id,
            status="completed",
            total_count=total,
            success_count=success_count,
            failed_count=failed,
            progress=100,
            error_message=""
        )

    async def fail_task(self, task_id: str, error_message: str):
        """
        标记任务为失败

        Args:
            task_id: 任务ID
            error_message: 错误信息
        """
        await self.update_task(
            task_id=task_id,
            status="failed",
            error_message=error_message
        )

    # ==================== 全局状态管理（兼容旧接口） ====================

    async def update_global_status(
        self,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        total: Optional[int] = None,
        completed: Optional[int] = None,
        last_sync_date: Optional[str] = None
    ):
        """
        更新全局同步状态

        Args:
            status: 状态
            progress: 进度
            total: 总数
            completed: 完成数
            last_sync_date: 最后同步时间
        """
        await self.config_service.update_sync_status(
            status=status,
            progress=progress,
            total=total,
            completed=completed,
            last_sync_date=last_sync_date
        )

    # ==================== 重试机制 ====================

    async def create_retry_callback(self, task_id: str) -> Callable:
        """
        创建重试回调函数

        Args:
            task_id: 任务ID

        Returns:
            重试回调函数
        """
        async def on_retry(retry_count: int, max_retries: int, error: Exception):
            error_with_retry = f"重试 {retry_count}/{max_retries}: {str(error)}"
            await self.update_task(
                task_id=task_id,
                error_message=error_with_retry,
                progress=int((retry_count / max_retries) * 50)
            )
            logger.warning(error_with_retry)

        return on_retry

    async def retry_operation(
        self,
        operation: Callable,
        *args,
        task_id: Optional[str] = None,
        max_retries: int = 3,
        delay_base: float = 3.0,
        delay_strategy: str = "linear",
        **kwargs
    ) -> Any:
        """
        执行带重试的操作

        Args:
            operation: 要执行的操作
            *args: 操作参数
            task_id: 任务ID（可选，用于更新重试状态）
            max_retries: 最大重试次数
            delay_base: 基础延迟时间
            delay_strategy: 延迟策略
            **kwargs: 操作关键字参数

        Returns:
            操作结果
        """
        on_retry = None
        if task_id:
            on_retry = await self.create_retry_callback(task_id)

        return await retry_async(
            operation,
            *args,
            max_retries=max_retries,
            delay_base=delay_base,
            delay_strategy=delay_strategy,
            on_retry=on_retry,
            **kwargs
        )

    # ==================== 响应处理 ====================

    def check_and_extract_data(self, response: Any, error_context: str = "操作") -> Any:
        """
        检查API响应并提取数据

        Args:
            response: API响应对象
            error_context: 错误上下文

        Returns:
            响应数据

        Raises:
            ExternalAPIError: 响应失败时
        """
        return check_response_success(response, error_context)

    # ==================== 中止控制 ====================

    async def clear_abort_flag(self):
        """清除中止标志"""
        await self.config_service.clear_sync_abort_flag()

    async def check_abort_flag(self) -> bool:
        """
        检查是否收到中止请求

        Returns:
            是否应该中止
        """
        return await self.config_service.check_sync_abort_flag()

    # ==================== 日期工具 ====================

    def calculate_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        years: Optional[int] = None,
        days: Optional[int] = None
    ) -> Dict[str, str]:
        """
        计算日期范围

        Args:
            start_date: 开始日期（格式：YYYYMMDD 或 YYYY-MM-DD）
            end_date: 结束日期（默认今天）
            years: 历史年数（当未提供start_date时使用）
            days: 历史天数（优先于years）

        Returns:
            {"start": "YYYYMMDD", "end": "YYYYMMDD"}
        """
        result = {}

        # 处理结束日期
        if end_date:
            result["end"] = end_date.replace("-", "")
        else:
            result["end"] = datetime.now().strftime("%Y%m%d")

        # 处理开始日期
        if start_date:
            result["start"] = start_date.replace("-", "")
        else:
            # 根据天数或年数计算
            if days:
                delta = timedelta(days=days)
            elif years:
                delta = timedelta(days=years * 365)
            else:
                delta = timedelta(days=5 * 365)  # 默认5年

            start_dt = datetime.now() - delta
            result["start"] = start_dt.strftime("%Y%m%d")

        return result

    # ==================== 执行线程操作 ====================

    async def run_in_thread(
        self,
        func: Callable,
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        在线程中执行同步函数

        Args:
            func: 同步函数
            *args: 函数参数
            timeout: 超时时间（秒，可选）
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            TimeoutError: 超时时
        """
        operation = asyncio.to_thread(func, *args, **kwargs)

        if timeout:
            try:
                return await asyncio.wait_for(operation, timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"{func.__name__} 超时（{timeout}秒）")
        else:
            return await operation

    # ==================== 日志辅助 ====================

    def log_info(self, message: str):
        """记录信息日志"""
        logger.info(message)

    def log_success(self, message: str):
        """记录成功日志"""
        logger.info(f"✓ {message}")

    def log_warning(self, message: str):
        """记录警告日志"""
        logger.warning(f"⚠️ {message}")

    def log_error(self, message: str):
        """记录错误日志"""
        logger.error(f"✗ {message}")

    def log_progress(self, current: int, total: int, item: Optional[str] = None):
        """
        记录进度日志

        Args:
            current: 当前进度
            total: 总数
            item: 当前项目描述（可选）
        """
        progress = int((current / total) * 100) if total > 0 else 0
        item_str = f" {item}" if item else ""
        logger.info(f"[{current}/{total}]{item_str} ({progress}%)")
