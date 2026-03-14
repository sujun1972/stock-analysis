"""
概念数据同步服务

提供异步概念数据同步功能，支持进度跟踪和重试机制
"""

import asyncio
from typing import Dict, Optional
from loguru import logger

from app.services.config_service import ConfigService
from app.utils.retry import retry_async


class ConceptSyncService:
    """概念同步服务（支持任务追踪和重试）"""

    def __init__(self):
        self.config_service = ConfigService()

    async def sync_concepts(
        self,
        source: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict:
        """
        同步概念数据

        Args:
            source: 数据源（None=使用配置，em=东方财富，tushare=Tushare）
            task_id: Celery任务ID（用于任务追踪）

        Returns:
            {
                "concepts_count": 概念数量,
                "relationships_count": 股票关系数量,
                "data_source": 数据源
            }
        """
        module = "concept"

        try:
            # 1. 获取数据源配置
            config = await self.config_service.get_data_source_config()
            actual_source = source or config.get("concept_data_source", config["data_source"])

            logger.info(f"开始同步概念数据（数据源：{actual_source}）")

            # 2. 创建同步任务记录
            if task_id:
                await self.config_service.create_sync_task(
                    task_id=task_id,
                    module=module,
                    data_source=actual_source
                )

            # 3. 导入 ConceptFetcher（延迟导入）
            import sys
            from pathlib import Path
            core_path = Path(__file__).parent.parent.parent.parent / "core"
            if str(core_path) not in sys.path:
                sys.path.insert(0, str(core_path))

            from src.concept_fetcher import ConceptFetcher
            from src.database.connection_pool_manager import ConnectionPoolManager
            from src.config.settings import get_settings

            # 4. 创建数据库连接池
            settings = get_settings()
            db_settings = settings.database

            pool_manager = ConnectionPoolManager(
                config={
                    'host': db_settings.host,
                    'port': db_settings.port,
                    'database': db_settings.database,
                    'user': db_settings.user,
                    'password': db_settings.password
                },
                min_conn=2,
                max_conn=10
            )

            # 5. 定义重试回调
            async def on_retry_callback(retry_count, max_retries, error):
                if task_id:
                    await self.config_service.update_sync_task(
                        task_id=task_id,
                        error_message=f"重试 {retry_count}/{max_retries}: {error}",
                        progress=int((retry_count / max_retries) * 50)
                    )
                logger.warning(f"概念同步重试 {retry_count}/{max_retries}: {error}")

            # 6. 使用重试机制执行同步（最多3次重试）
            try:
                fetcher = ConceptFetcher(pool_manager)

                # 在线程中执行同步操作
                response = await retry_async(
                    asyncio.to_thread,
                    fetcher.fetch_and_save_concepts,
                    source=actual_source,
                    max_retries=3,
                    on_retry=on_retry_callback
                )

                if not response.is_success():
                    # 提取错误信息
                    error_msg = getattr(response, 'error_detail', None) or getattr(response, 'error', '同步失败')
                    raise Exception(str(error_msg))

                # 7. 更新任务状态为完成
                if task_id:
                    await self.config_service.update_sync_task(
                        task_id=task_id,
                        status="completed",
                        total_count=response.data.get('concepts_count', 0),
                        progress=100
                    )

                result = {
                    "concepts_count": response.data.get('concepts_count', 0),
                    "relationships_count": response.data.get('relationships_count', 0),
                    "data_source": actual_source
                }

                logger.success(f"✅ 概念数据同步成功: {result}")
                return result

            finally:
                # 关闭连接池
                pool_manager.close_all_connections()

        except Exception as e:
            logger.error(f"概念同步失败: {str(e)}", exc_info=True)

            # 更新任务状态为失败
            if task_id:
                await self.config_service.update_sync_task(
                    task_id=task_id,
                    status="failed",
                    error_message=str(e)
                )

            raise
