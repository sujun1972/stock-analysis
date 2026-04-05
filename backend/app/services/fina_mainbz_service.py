"""
主营业务构成数据同步服务

提供主营业务构成数据的同步、查询等功能
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict
from loguru import logger

from app.repositories.fina_mainbz_repository import FinaMainbzRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class FinaMainbzService:
    """主营业务构成数据同步服务"""

    def __init__(self):
        self.fina_mainbz_repo = FinaMainbzRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ FinaMainbzService initialized")

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_fina_mainbz(
        self,
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步主营业务构成数据

        Args:
            ts_code: 股票代码（可选）
            period: 报告期 YYYYMMDD（可选，每个季度最后一天的日期）
            type: 类型，P按产品 D按地区 I按行业（可选）
            start_date: 报告期开始日期 YYYYMMDD（可选）
            end_date: 报告期结束日期 YYYYMMDD（可选）

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步主营业务构成数据: ts_code={ts_code}, period={period}, type={type}, start_date={start_date}, end_date={end_date}")

            # 获取 Tushare 数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_fina_mainbz_vip,
                ts_code=ts_code,
                period=period,
                type=type,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到主营业务构成数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条主营业务构成数据")

            # 数据验证和清洗：过滤掉缺少必需字段的记录
            required_fields = ['ts_code', 'end_date', 'bz_item']
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
                self.fina_mainbz_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条主营业务构成数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            error_msg = f"同步主营业务构成数据失败: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "records": 0,
                "error": error_msg
            }

    async def get_fina_mainbz_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取主营业务构成数据

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            period: 报告期 YYYYMMDD（可选）
            type: 类型，P按产品 D按地区 I按行业（可选）
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
                    self.fina_mainbz_repo.get_total_count,
                    start_date=start_date_q if not period else None,
                    end_date=end_date_q if not period else None,
                    ts_code=ts_code,
                    period=period
                ),
                asyncio.to_thread(
                    self.fina_mainbz_repo.get_by_date_range,
                    start_date=start_date_q,
                    end_date=end_date_q,
                    ts_code=ts_code,
                    type=type,
                    limit=limit,
                    offset=offset
                ) if not period else asyncio.to_thread(
                    self.fina_mainbz_repo.get_by_period,
                    period=period,
                    ts_code=ts_code,
                    type=type,
                    limit=limit
                ),
                asyncio.to_thread(
                    self.fina_mainbz_repo.get_statistics,
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
            logger.error(f"获取主营业务构成数据失败: {e}")
            raise

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        update_state_fn=None,
        concurrency: int = 5
    ) -> Dict:
        """
        逐只股票全量同步主营业务构成历史数据（5 并发，Redis Set 续继）

        按季度 period 切片时每季可达 10000+ 条，触达 Tushare 上限。
        改为按 ts_code 逐只拉取，每只股票记录数极少，彻底避免截断。
        """
        from app.repositories.stock_basic_repository import StockBasicRepository

        PROGRESS_KEY = "sync:fina_mainbz:full_history:progress"
        CONCURRENCY = max(1, concurrency)
        BATCH_SIZE = 50
        effective_start = start_date or "20090101"

        all_ts_codes = StockBasicRepository().get_listed_ts_codes(status='L')
        total = len(all_ts_codes)
        logger.info(f"全量同步主营业务构成: 共 {total} 只上市股票，start_date={effective_start}")

        completed_raw = redis_client.smembers(PROGRESS_KEY) if redis_client else set()
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
                    result = await self.sync_fina_mainbz(
                        ts_code=ts_code,
                        start_date=effective_start
                    )
                    if result.get("status") == "error":
                        error_count += 1
                        return
                    total_records += result.get("records", 0)
                    if redis_client:
                        redis_client.sadd(PROGRESS_KEY, ts_code)
                except Exception as e:
                    logger.error(f"✗ 主营业务构成 ts_code={ts_code} 同步失败: {e}")
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
            logger.info(f"[全量主营业务构成] 进度: {done}/{total} ({round(done/total*100,1)}%) 入库={total_records} 失败={error_count}")

        if redis_client:
            final_done = len(redis_client.smembers(PROGRESS_KEY))
            if final_done >= total:
                redis_client.delete(PROGRESS_KEY)
                logger.info("[全量主营业务构成] ✅ 全量同步完成，进度已清除")

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
        获取主营业务构成统计信息

        Args:
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            ts_code: 股票代码（可选）

        Returns:
            统计信息
        """
        try:
            statistics = await asyncio.to_thread(
                self.fina_mainbz_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )
            return statistics

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise
