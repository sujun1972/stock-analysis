"""
股票列表同步服务
负责股票列表、新股、退市股票的同步
"""

import asyncio
from datetime import datetime
from typing import Dict

from app.core.exceptions import DatabaseError, DataSyncError, ExternalAPIError
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.services.base_sync_service import BaseSyncService


class StockListSyncService(BaseSyncService):
    """
    股票列表同步服务

    职责：
    - 同步正常股票列表
    - 同步新股列表
    - 同步退市股票列表
    - 任务状态追踪
    - 重试逻辑管理
    """

    def __init__(self):
        super().__init__()
        self.sync_history_repo = SyncHistoryRepository()

    async def sync_stock_list(self) -> Dict:
        """
        同步股票列表

        Returns:
            同步结果字典
        """
        task_id = self.generate_task_id("stock_list")
        history_id = await asyncio.to_thread(
            self.sync_history_repo.create,
            'stock_basic', 'incremental', 'snapshot', None,
        )

        try:
            # 获取数据源配置
            config = await self.get_config()

            # 创建同步任务记录
            await self.create_task(
                task_id=task_id,
                module="stock_list",
                data_source=config["data_source"]
            )

            # 创建数据提供者（禁用内部重试，由外层控制）
            provider = self.create_data_provider(
                source=config["data_source"],
                token=config.get("tushare_token", ""),
                retry_count=1
            )

            self.log_info(f"使用 {config['data_source']} 获取股票列表...")

            # 使用重试工具获取股票列表
            stock_list_response = await self.retry_operation(
                asyncio.to_thread,
                provider.get_stock_list,
                task_id=task_id,
                max_retries=3,
                delay_base=3.0,
                delay_strategy="linear"
            )

            # 检查响应状态并提取数据
            stock_list = self.check_and_extract_data(stock_list_response, "获取股票列表")

            # 保存到数据库
            count = await self.run_in_thread(
                self.data_service.db.save_stock_list,
                stock_list,
                config["data_source"]
            )

            # 更新任务状态为完成
            await self.complete_task(task_id=task_id, total=count)

            # 同时更新全局状态（兼容旧接口）
            await self.update_global_status(
                status="completed",
                last_sync_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                progress=100,
                total=count,
                completed=count
            )

            self.log_success(f"股票列表同步完成: {count} 只")
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'success', count, None, None,
            )
            return {"total": count}

        except ExternalAPIError as e:
            error_msg = str(e)
            self.log_error(f"同步股票列表失败: {error_msg}")
            await self.fail_task(task_id=task_id, error_message=error_msg)
            await self.update_global_status(status="failed")
            await asyncio.to_thread(
                self.sync_history_repo.complete, history_id, 'failure', 0, None, error_msg,
            )
            raise DataSyncError(
                "股票列表同步失败: 数据源API调用失败",
                error_code="STOCK_LIST_SYNC_API_FAILED",
                task_id=task_id,
                data_source=config["data_source"],
                reason=error_msg
            )
        except DatabaseError as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete, history_id, 'failure', 0, None, str(e),
            )
            raise
        except Exception as e:
            error_msg = str(e)
            self.log_error(f"同步股票列表失败: {error_msg}")
            await self.fail_task(task_id=task_id, error_message=error_msg)
            await self.update_global_status(status="failed")
            await asyncio.to_thread(
                self.sync_history_repo.complete, history_id, 'failure', 0, None, error_msg,
            )
            raise DataSyncError(
                "股票列表同步失败",
                error_code="STOCK_LIST_SYNC_FAILED",
                task_id=task_id,
                reason=error_msg
            )
