"""
业绩快报数据同步服务

提供业绩快报数据的同步、查询等功能
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime
from loguru import logger

from app.repositories.express_repository import ExpressRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class ExpressService:
    """业绩快报数据同步服务"""

    def __init__(self):
        self.express_repo = ExpressRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ ExpressService initialized")

    @staticmethod
    def _generate_quarters(start_date: str) -> list:
        """生成从start_date起到今天的所有季度末日期列表"""
        start_year = int(start_date[:4])
        quarter_ends = [331, 630, 930, 1231]
        today_int = int(datetime.now().strftime("%Y%m%d"))
        start_int = int(start_date)
        periods = []
        for y in range(start_year, datetime.now().year + 1):
            for qe in quarter_ends:
                period_str = f"{y}{qe:04d}"
                if start_int <= int(period_str) <= today_int:
                    periods.append(period_str)
        return periods

    async def sync_full_history(self, redis_client, start_date: str = None, update_state_fn=None, concurrency: int = 3) -> dict:
        """按季度报告期全量同步业绩快报历史数据（支持中断续继）"""
        effective_start = start_date or '20090101'
        quarters = self._generate_quarters(effective_start)
        total_quarters = len(quarters)
        logger.info(f"全量同步业绩快报，共 {total_quarters} 个季度，起始: {effective_start}")

        PROGRESS_KEY = "sync:express:full_history:progress"
        try:
            completed_raw = redis_client.smembers(PROGRESS_KEY)
            completed = {p.decode() if isinstance(p, bytes) else p for p in completed_raw}
        except Exception:
            completed = set()

        pending = [q for q in quarters if q not in completed]
        logger.info(f"待同步季度数: {len(pending)}，已完成: {len(completed)}")

        total_records = 0
        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def sync_one(period: str):
            nonlocal total_records
            async with semaphore:
                try:
                    provider = self._get_provider()
                    df = await asyncio.to_thread(provider.get_express, period=period)
                    if df is not None and not df.empty:
                        count = await asyncio.to_thread(self.express_repo.bulk_upsert, df)
                        total_records += count
                        logger.info(f"[express] period={period} 同步 {count} 条")
                    else:
                        logger.info(f"[express] period={period} 无数据")
                    redis_client.sadd(PROGRESS_KEY, period)
                except Exception as e:
                    logger.error(f"[express] period={period} 同步失败: {e}")

        done = 0
        for period in pending:
            await sync_one(period)
            done += 1
            if update_state_fn and done % 10 == 0:
                pct = int((len(completed) + done) / total_quarters * 100)
                try:
                    update_state_fn(state='PROGRESS', meta={'progress': pct})
                except Exception:
                    pass

        try:
            redis_client.delete(PROGRESS_KEY)
        except Exception:
            pass

        logger.info(f"全量同步业绩快报完成，共同步 {total_records} 条记录")
        return {'status': 'success', 'records': total_records, 'quarters': total_quarters}

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_express(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> Dict:
        """
        同步业绩快报数据

        Args:
            ts_code: 股票代码（可选）
            ann_date: 公告日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            period: 报告期 YYYYMMDD（可选）

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步业绩快报数据: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

            # 获取 Tushare 数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_express,
                ts_code=ts_code,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                period=period
            )

            if df is None or df.empty:
                logger.warning("未获取到业绩快报数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条业绩快报数据")

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.express_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条业绩快报数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            error_msg = f"同步业绩快报数据失败: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "records": 0,
                "error": error_msg
            }

    async def get_express_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取业绩快报数据

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            period: 报告期 YYYYMMDD（可选）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        try:
            start_date_q = start_date or '19900101'
            end_date_q = end_date or '29991231'

            # 并发查询总数和数据
            total, items = await asyncio.gather(
                asyncio.to_thread(
                    self.express_repo.get_total_count,
                    start_date=start_date_q,
                    end_date=end_date_q,
                    ts_code=ts_code,
                    period=period
                ),
                asyncio.to_thread(
                    self.express_repo.get_by_date_range,
                    start_date=start_date_q,
                    end_date=end_date_q,
                    ts_code=ts_code,
                    limit=limit,
                    offset=offset
                )
            )

            # 转换单位（元 -> 亿元）
            for item in items:
                if item.get('revenue') is not None:
                    item['revenue'] = item['revenue'] / 100000000
                if item.get('operate_profit') is not None:
                    item['operate_profit'] = item['operate_profit'] / 100000000
                if item.get('total_profit') is not None:
                    item['total_profit'] = item['total_profit'] / 100000000
                if item.get('n_income') is not None:
                    item['n_income'] = item['n_income'] / 100000000
                if item.get('total_assets') is not None:
                    item['total_assets'] = item['total_assets'] / 100000000
                if item.get('total_hldr_eqy_exc_min_int') is not None:
                    item['total_hldr_eqy_exc_min_int'] = item['total_hldr_eqy_exc_min_int'] / 100000000

            return {
                "items": items,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取业绩快报数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取业绩快报统计信息

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            ts_code: 股票代码（可选）

        Returns:
            统计信息
        """
        try:
            stats = await asyncio.to_thread(
                self.express_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )

            # 转换单位（元 -> 亿元）
            if stats.get('avg_revenue'):
                stats['avg_revenue'] = stats['avg_revenue'] / 100000000
            if stats.get('max_revenue'):
                stats['max_revenue'] = stats['max_revenue'] / 100000000
            if stats.get('min_revenue'):
                stats['min_revenue'] = stats['min_revenue'] / 100000000
            if stats.get('avg_n_income'):
                stats['avg_n_income'] = stats['avg_n_income'] / 100000000

            return stats

        except Exception as e:
            logger.error(f"获取业绩快报统计信息失败: {e}")
            raise
