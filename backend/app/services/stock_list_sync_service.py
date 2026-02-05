"""
股票列表同步服务
负责股票列表、新股、退市股票的同步
"""

import asyncio
from datetime import datetime
from typing import Dict

from loguru import logger
from src.providers import DataProviderFactory

from app.core.exceptions import DatabaseError, DataSyncError, ExternalAPIError
from app.services.config_service import ConfigService
from app.services.data_service import DataDownloadService
from app.utils.retry import retry_async


class StockListSyncService:
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
        """初始化股票列表同步服务"""
        self.config_service = ConfigService()
        self.data_service = DataDownloadService()

    async def sync_stock_list(self) -> Dict:
        """
        同步股票列表

        Returns:
            同步结果字典
        """
        task_id = f"stock_list_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            # 获取数据源配置
            config = await self.config_service.get_data_source_config()

            # 创建同步任务记录
            await self.config_service.create_sync_task(
                task_id=task_id, module="stock_list", data_source=config["data_source"]
            )

            # 创建数据提供者（禁用内部重试，由外层控制）
            provider = DataProviderFactory.create_provider(
                source=config["data_source"],
                token=config.get("tushare_token", ""),
                retry_count=1,  # 禁用 Provider 内部重试
            )

            logger.info(f"使用 {config['data_source']} 获取股票列表...")

            # 定义重试回调函数，用于更新任务状态
            async def on_retry_callback(retry_count: int, max_retries: int, error: Exception):
                error_with_retry = f"重试 {retry_count}/{max_retries}: {str(error)}"
                await self.config_service.update_sync_task(
                    task_id=task_id,
                    error_message=error_with_retry,
                    progress=int((retry_count / max_retries) * 50),  # 重试进度占 50%
                )

            # 使用重试工具获取股票列表
            stock_list = await retry_async(
                asyncio.to_thread,
                provider.get_stock_list,
                max_retries=3,
                delay_base=3.0,
                delay_strategy="linear",
                on_retry=on_retry_callback,
            )

            # 保存到数据库
            count = await asyncio.to_thread(
                self.data_service.db.save_stock_list, stock_list, config["data_source"]
            )

            # 更新任务状态为完成
            await self.config_service.update_sync_task(
                task_id=task_id,
                status="completed",
                total_count=count,
                success_count=count,
                failed_count=0,
                progress=100,
                error_message="",  # 清空错误信息
            )

            # 同时更新全局状态（兼容旧接口）
            await self.config_service.update_sync_status(
                status="completed",
                last_sync_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                progress=100,
                total=count,
                completed=count,
            )

            logger.info(f"✓ 股票列表同步完成: {count} 只")

            return {"total": count}

        except ExternalAPIError as e:
            # API调用失败
            error_msg = str(e)
            logger.error(f"同步股票列表失败: {error_msg}")

            # 更新任务状态为失败
            await self.config_service.update_sync_task(
                task_id=task_id, status="failed", error_message=error_msg
            )

            # 同时更新全局状态（兼容旧接口）
            await self.config_service.update_sync_status(status="failed")

            raise DataSyncError(
                "股票列表同步失败: 数据源API调用失败",
                error_code="STOCK_LIST_SYNC_API_FAILED",
                task_id=task_id,
                data_source=config["data_source"],
                reason=error_msg,
            )
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"同步股票列表失败: {error_msg}")

            # 更新任务状态为失败
            await self.config_service.update_sync_task(
                task_id=task_id, status="failed", error_message=error_msg
            )

            # 同时更新全局状态（兼容旧接口）
            await self.config_service.update_sync_status(status="failed")

            raise DataSyncError(
                "股票列表同步失败",
                error_code="STOCK_LIST_SYNC_FAILED",
                task_id=task_id,
                reason=error_msg,
            )

    async def sync_new_stocks(self, days: int = 30) -> Dict:
        """
        同步新股列表

        Args:
            days: 最近天数 (默认 30 天)

        Returns:
            同步结果字典
        """
        task_id = f"new_stocks_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            # 获取数据源配置
            config = await self.config_service.get_data_source_config()

            # 创建同步任务记录
            await self.config_service.create_sync_task(
                task_id=task_id, module="new_stocks", data_source=config["data_source"]
            )

            # 创建数据提供者
            provider = DataProviderFactory.create_provider(
                source=config["data_source"], token=config.get("tushare_token", ""), retry_count=1
            )

            logger.info(f"使用 {config['data_source']} 获取最近 {days} 天的新股...")

            # 定义重试回调函数
            async def on_retry_callback(retry_count: int, max_retries: int, error: Exception):
                error_with_retry = f"重试 {retry_count}/{max_retries}: {str(error)}"
                await self.config_service.update_sync_task(
                    task_id=task_id,
                    error_message=error_with_retry,
                    progress=int((retry_count / max_retries) * 50),
                )

            # 使用重试工具获取新股列表
            new_stocks = await retry_async(
                asyncio.to_thread,
                provider.get_new_stocks,
                days,
                max_retries=3,
                delay_base=3.0,
                delay_strategy="linear",
                on_retry=on_retry_callback,
            )

            # 保存到数据库（新股自动添加到股票基础表）
            count = await asyncio.to_thread(
                self.data_service.db.save_stock_list, new_stocks, config["data_source"]
            )

            # 更新任务状态为完成
            await self.config_service.update_sync_task(
                task_id=task_id,
                status="completed",
                total_count=count,
                success_count=count,
                failed_count=0,
                progress=100,
                error_message="",
            )

            logger.info(f"✓ 新股列表同步完成: {count} 只")

            return {"total": count}

        except ExternalAPIError as e:
            # API调用失败
            error_msg = str(e)
            logger.error(f"同步新股列表失败: {error_msg}")

            await self.config_service.update_sync_task(
                task_id=task_id, status="failed", error_message=error_msg
            )

            raise DataSyncError(
                "新股列表同步失败: 数据源API调用失败",
                error_code="NEW_STOCKS_SYNC_API_FAILED",
                task_id=task_id,
                data_source=config["data_source"],
                days=days,
                reason=error_msg,
            )
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"同步新股列表失败: {error_msg}")

            await self.config_service.update_sync_task(
                task_id=task_id, status="failed", error_message=error_msg
            )

            raise DataSyncError(
                "新股列表同步失败",
                error_code="NEW_STOCKS_SYNC_FAILED",
                task_id=task_id,
                days=days,
                reason=error_msg,
            )

    async def sync_delisted_stocks(self) -> Dict:
        """
        同步退市股票列表

        Returns:
            同步结果字典
        """
        task_id = f"delisted_stocks_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            # 获取数据源配置
            config = await self.config_service.get_data_source_config()

            # 创建同步任务记录
            await self.config_service.create_sync_task(
                task_id=task_id, module="delisted_stocks", data_source=config["data_source"]
            )

            # 创建数据提供者
            provider = DataProviderFactory.create_provider(
                source=config["data_source"], token=config.get("tushare_token", ""), retry_count=1
            )

            logger.info(f"使用 {config['data_source']} 获取退市股票列表...")

            # 定义重试回调函数
            async def on_retry_callback(retry_count: int, max_retries: int, error: Exception):
                error_with_retry = f"重试 {retry_count}/{max_retries}: {str(error)}"
                await self.config_service.update_sync_task(
                    task_id=task_id,
                    error_message=error_with_retry,
                    progress=int((retry_count / max_retries) * 50),
                )

            # 使用重试工具获取退市股票列表
            delisted_stocks = await retry_async(
                asyncio.to_thread,
                provider.get_delisted_stocks,
                max_retries=3,
                delay_base=3.0,
                delay_strategy="linear",
                on_retry=on_retry_callback,
            )

            # 更新数据库中股票的状态为"退市"
            count = 0

            for _, row in delisted_stocks.iterrows():
                code = row["code"]
                try:
                    # 使用 save_stock_list 保存，但状态设为"退市"
                    stock_df = delisted_stocks[delisted_stocks["code"] == code].copy()
                    stock_df["status"] = "退市"

                    await asyncio.to_thread(
                        self.data_service.db.save_stock_list, stock_df, config["data_source"]
                    )
                    count += 1
                except DatabaseError:
                    # 数据库错误向上传播
                    raise
                except Exception as e:
                    logger.warning(f"更新退市股票 {code} 失败: {e}")
                    # 单个股票失败不影响整体，继续处理下一个

            # 更新任务状态为完成
            await self.config_service.update_sync_task(
                task_id=task_id,
                status="completed",
                total_count=len(delisted_stocks),
                success_count=count,
                failed_count=len(delisted_stocks) - count,
                progress=100,
                error_message="",
            )

            logger.info(f"✓ 退市股票列表同步完成: {count} 只")

            return {"total": count}

        except ExternalAPIError as e:
            # API调用失败
            error_msg = str(e)
            logger.error(f"同步退市股票列表失败: {error_msg}")

            await self.config_service.update_sync_task(
                task_id=task_id, status="failed", error_message=error_msg
            )

            raise DataSyncError(
                "退市股票列表同步失败: 数据源API调用失败",
                error_code="DELISTED_STOCKS_SYNC_API_FAILED",
                task_id=task_id,
                data_source=config["data_source"],
                reason=error_msg,
            )
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"同步退市股票列表失败: {error_msg}")

            await self.config_service.update_sync_task(
                task_id=task_id, status="failed", error_message=error_msg
            )

            raise DataSyncError(
                "退市股票列表同步失败",
                error_code="DELISTED_STOCKS_SYNC_FAILED",
                task_id=task_id,
                reason=error_msg,
            )
