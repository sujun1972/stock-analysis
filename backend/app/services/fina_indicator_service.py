"""
财务指标数据同步服务

提供财务指标数据的同步、查询等功能
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime
from loguru import logger

from app.repositories.fina_indicator_repository import FinaIndicatorRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class FinaIndicatorService:
    """财务指标数据同步服务"""

    def __init__(self):
        self.fina_indicator_repo = FinaIndicatorRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ FinaIndicatorService initialized")

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_fina_indicator(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> Dict:
        """
        同步财务指标数据

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
            logger.info(f"开始同步财务指标数据: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

            # 获取 Tushare 数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_fina_indicator,
                ts_code=ts_code,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                period=period
            )

            if df is None or df.empty:
                logger.warning("未获取到财务指标数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条财务指标数据")

            # 数据验证和清洗：过滤掉缺少必需字段的记录
            required_fields = ['ts_code', 'ann_date', 'end_date']
            before_count = len(df)
            df = df.dropna(subset=required_fields)
            after_count = len(df)

            if before_count > after_count:
                logger.warning(f"过滤掉 {before_count - after_count} 条缺少必需字段的记录")

            if df.empty:
                logger.warning("过滤后无有效数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "过滤后无有效数据"
                }

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.fina_indicator_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条财务指标数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            error_msg = f"同步财务指标数据失败: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "records": 0,
                "error": error_msg
            }

    async def get_fina_indicator_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取财务指标数据

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            period: 报告期 YYYYMMDD（可选）
            limit: 限制返回数量
            offset: 偏移量

        Returns:
            数据列表
        """
        try:
            start_date_q = start_date or '19900101'
            end_date_q = end_date or '29991231'

            total, items, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.fina_indicator_repo.get_total_count,
                    start_date=start_date_q,
                    end_date=end_date_q,
                    ts_code=ts_code,
                    period=period
                ),
                asyncio.to_thread(
                    self.fina_indicator_repo.get_by_date_range,
                    start_date=start_date_q,
                    end_date=end_date_q,
                    ts_code=ts_code,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.fina_indicator_repo.get_statistics,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code
                )
            )

            return {
                "items": items,
                "total": total,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取财务指标数据失败: {str(e)}")
            raise

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        update_state_fn=None,
        concurrency: int = 5
    ) -> Dict:
        """
        逐只股票全量同步财务指标历史数据（5 并发，Redis Set 续继）

        按 ts_code 逐只调用 fina_indicator_vip，每只股票记录数极少，彻底避免
        Tushare 单次返回上限导致的数据截断。Redis Set 记录已完成 ts_code，中断后自动续继。
        """
        from app.repositories.stock_basic_repository import StockBasicRepository

        PROGRESS_KEY = "sync:fina_indicator:full_history:progress"
        CONCURRENCY = max(1, concurrency)
        BATCH_SIZE = 50
        effective_start = start_date or "20090101"

        all_ts_codes = StockBasicRepository().get_listed_ts_codes(status='L')
        total = len(all_ts_codes)
        logger.info(f"财务指标全量同步: 共 {total} 只上市股票，start_date={effective_start}")

        completed_raw = redis_client.smembers(PROGRESS_KEY)
        completed = {p.decode() if isinstance(p, bytes) else p for p in (completed_raw or [])}
        pending = [c for c in all_ts_codes if c not in completed]
        skip_count = len(completed)
        logger.info(f"已完成 {skip_count} 只，待同步 {len(pending)} 只")

        sem = asyncio.Semaphore(CONCURRENCY)
        total_records = 0
        error_count = 0

        async def sync_one(ts_code: str):
            nonlocal total_records, error_count
            async with sem:
                try:
                    result = await self.sync_fina_indicator(
                        ts_code=ts_code,
                        start_date=effective_start
                    )
                    if result.get("status") == "error":
                        error_count += 1
                        return
                    total_records += result.get("records", 0)
                    redis_client.sadd(PROGRESS_KEY, ts_code)
                except Exception as e:
                    logger.error(f"✗ 财务指标 ts_code={ts_code} 同步失败: {e}")
                    error_count += 1

        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            await asyncio.gather(*[sync_one(c) for c in batch])
            done = skip_count + batch_start + len(batch)
            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={
                    'current': done, 'total': total,
                    'percent': round(done / total * 100, 1),
                    'records': total_records, 'errors': error_count
                })
            logger.info(f"[全量财务指标] 进度: {done}/{total} ({round(done/total*100,1)}%) 入库={total_records} 失败={error_count}")

        final_done = len(redis_client.smembers(PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(PROGRESS_KEY)
            logger.info("[全量财务指标] ✅ 全量同步完成，进度已清除")

        return {
            "status": "success",
            "records": total_records,
            "total": total,
            "errors": error_count,
            "message": f"同步完成 {total - error_count} 只，入库 {total_records} 条，失败 {error_count} 只"
        }

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取财务指标统计信息

        Args:
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            ts_code: 股票代码（可选）

        Returns:
            统计信息
        """
        try:
            statistics = await asyncio.to_thread(
                self.fina_indicator_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )
            return statistics
        except Exception as e:
            logger.error(f"获取财务指标统计信息失败: {str(e)}")
            raise
