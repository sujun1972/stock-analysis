"""
实时行情数据服务

负责实时行情数据的查询、统计和同步
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.stock_realtime_repository import StockRealtimeRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class StockRealtimeService:
    """实时行情数据服务"""

    def __init__(self):
        self.realtime_repo = StockRealtimeRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self, source: str = 'akshare'):
        """
        获取数据提供者

        Args:
            source: 数据源名称（akshare 或 tushare）

        Returns:
            数据提供者实例
        """
        if source.lower() == 'tushare':
            return self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        else:
            return self.provider_factory.create_provider(source='akshare')

    async def get_all_realtime(
        self,
        page: int = 1,
        page_size: int = 30
    ) -> Dict:
        """
        获取所有实时行情数据（支持分页）

        Args:
            page: 页码（从1开始）
            page_size: 每页记录数

        Returns:
            实时行情数据列表和总数
        """
        try:
            # 计算偏移量
            offset = (page - 1) * page_size

            # 并发查询数据和总数
            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.realtime_repo.get_all,
                    limit=page_size,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.realtime_repo.count_all
                )
            )

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }

        except Exception as e:
            logger.error(f"查询实时行情数据失败: {e}")
            raise

    async def get_by_code(self, code: str) -> Optional[Dict]:
        """
        根据股票代码查询实时行情

        Args:
            code: 股票代码

        Returns:
            实时行情数据，不存在返回None
        """
        try:
            return await asyncio.to_thread(
                self.realtime_repo.get_by_code,
                code
            )

        except Exception as e:
            logger.error(f"查询股票 {code} 实时行情失败: {e}")
            raise

    async def get_top_gainers(self, limit: int = 50) -> Dict:
        """
        获取涨幅榜前N名

        Args:
            limit: 返回记录数

        Returns:
            涨幅榜数据
        """
        try:
            items = await asyncio.to_thread(
                self.realtime_repo.get_top_gainers,
                limit
            )

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"查询涨幅榜失败: {e}")
            raise

    async def get_top_losers(self, limit: int = 50) -> Dict:
        """
        获取跌幅榜前N名

        Args:
            limit: 返回记录数

        Returns:
            跌幅榜数据
        """
        try:
            items = await asyncio.to_thread(
                self.realtime_repo.get_top_losers,
                limit
            )

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"查询跌幅榜失败: {e}")
            raise

    async def get_statistics(self) -> Dict:
        """
        获取实时行情统计信息

        Returns:
            统计信息字典
        """
        try:
            return await asyncio.to_thread(
                self.realtime_repo.get_statistics
            )

        except Exception as e:
            logger.error(f"查询实时行情统计信息失败: {e}")
            raise

    async def sync_realtime_quotes(
        self,
        codes: Optional[List[str]] = None,
        batch_size: Optional[int] = 100,
        update_oldest: bool = False,
        data_source: str = 'akshare'
    ) -> Dict:
        """
        同步实时行情数据

        Args:
            codes: 股票代码列表（None表示全部）
            batch_size: 批次大小
            update_oldest: 是否优先更新最旧的数据
            data_source: 数据源（akshare 或 tushare）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步实时行情: codes={codes}, batch_size={batch_size}, "
                       f"update_oldest={update_oldest}, data_source={data_source}")

            # 获取数据提供者
            provider = self._get_provider(data_source)

            # 定义保存回调函数
            saved_count = 0

            def save_callback(quote: dict):
                nonlocal saved_count
                try:
                    # 这里直接调用 data_insert_manager 的方法
                    # 因为Repository层不适合处理单条增量保存
                    from src.database.db_manager import DatabaseManager
                    db = DatabaseManager()
                    db.save_realtime_quote_single(quote, data_source)
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"保存 {quote.get('code', 'Unknown')} 失败: {e}")

            # 获取实时行情（带回调保存）
            response = await asyncio.to_thread(
                provider.get_realtime_quotes,
                codes=codes,
                save_callback=save_callback
            )

            # 检查响应
            if not response or not response.data or response.data.empty:
                error_msg = "未获取到实时行情数据"

                # 如果没有保存任何数据，说明获取失败
                if saved_count == 0:
                    logger.error(error_msg + "，同步失败")
                    raise Exception(
                        f"{error_msg}。可能原因：\n"
                        f"1. 当前为非交易时段（开盘时间：9:30-11:30, 13:00-15:00）\n"
                        f"2. 网络连接失败或数据源无响应\n"
                        f"3. 数据源接口限流或维护中\n\n"
                        f"建议：在交易时段重试，或检查网络连接"
                    )
                else:
                    # 有部分数据保存成功
                    logger.warning(f"{error_msg}，但已保存 {saved_count} 条记录")
                    return {
                        "status": "partial_success",
                        "total": saved_count,
                        "message": f"部分成功：已保存 {saved_count} 条记录，但未获取到更多数据"
                    }

            logger.info(f"实时行情同步完成: {saved_count} 只股票")

            return {
                "status": "success",
                "total": saved_count,
                "batch_size": batch_size or "all",
                "update_mode": "oldest_first" if update_oldest else "full",
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": f"成功同步 {saved_count} 条记录"
            }

        except TimeoutError as e:
            logger.error(f"同步超时: {e}")
            # 超时时，部分数据可能已保存
            if saved_count > 0:
                return {
                    "status": "partial_success",
                    "total": saved_count,
                    "timeout": True,
                    "message": f"部分成功：已保存 {saved_count} 条记录，但发生超时"
                }
            raise

        except Exception as e:
            logger.error(f"同步实时行情失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
