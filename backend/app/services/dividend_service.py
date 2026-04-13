"""
分红送股数据服务

提供分红送股数据的同步和查询服务
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from app.repositories.dividend_repository import DividendRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.stock_daily_repository import StockDailyRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class DividendService:
    """分红送股数据服务"""

    def __init__(self):
        self.dividend_repo = DividendRepository()
        self.stock_daily_repo = StockDailyRepository()
        self.provider_factory = DataProviderFactory()

    async def sync_incremental(self) -> Dict:
        """增量同步：从 sync_configs 读取回看天数，自动计算日期范围。"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'dividend')
        default_days = (cfg.get('incremental_default_days') or 90) if cfg else 90
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        logger.info(f"[dividend] 增量同步 start_date={start_date} end_date={end_date}（回看 {default_days} 天）")
        return await self.sync_dividend()

    async def sync_full_history(self, redis_client, start_date: str = None, update_state_fn=None, concurrency: int = 5) -> dict:
        """
        逐只股票全量同步分红送股历史数据（5 并发，Redis Set 续继）

        按 ts_code 逐只调用 dividend 接口，每只股票记录数极少，彻底避免 Tushare
        单次返回上限导致的数据截断。Redis Set 记录已完成 ts_code，中断后自动续继。
        """
        from app.repositories.stock_basic_repository import StockBasicRepository

        PROGRESS_KEY = "sync:dividend:full_history:progress"
        CONCURRENCY = max(1, concurrency)
        BATCH_SIZE = 50

        all_ts_codes = StockBasicRepository().get_listed_ts_codes(status='L')
        total = len(all_ts_codes)
        logger.info(f"全量同步分红送股，共 {total} 只上市股票，起始: {start_date or '20090101'}")

        try:
            completed_raw = redis_client.smembers(PROGRESS_KEY)
            completed = {p.decode() if isinstance(p, bytes) else p for p in completed_raw}
        except Exception:
            completed = set()

        pending = [c for c in all_ts_codes if c not in completed]
        logger.info(f"待同步股票: {len(pending)}，已完成: {len(completed)}")

        total_records = 0
        error_count = 0
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def sync_one(ts_code: str):
            nonlocal total_records, error_count
            async with semaphore:
                try:
                    result = await self.sync_dividend(ts_code=ts_code)
                    if result.get('status') == 'success':
                        total_records += result.get('records', 0)
                        redis_client.sadd(PROGRESS_KEY, ts_code)
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(f"[dividend] ts_code={ts_code} 同步失败: {e}")
                    error_count += 1

        skip_count = len(completed)
        success_count = 0
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            await asyncio.gather(*[sync_one(c) for c in batch])
            # 重新计算成功数（通过 Redis Set 大小）
            try:
                done = len(redis_client.smembers(PROGRESS_KEY))
            except Exception:
                done = skip_count + (batch_start + len(batch))
            if update_state_fn:
                pct = round(done / total * 100, 1)
                try:
                    update_state_fn(state='PROGRESS', meta={'current': done, 'total': total, 'percent': pct})
                except Exception:
                    pass
            logger.info(f"[全量分红送股] 进度: {done}/{total} ({round(done/total*100,1)}%) 入库={total_records} 失败={error_count}")

        try:
            final_done = len(redis_client.smembers(PROGRESS_KEY))
            if final_done >= total:
                redis_client.delete(PROGRESS_KEY)
                logger.info("[全量分红送股] ✅ 全量同步完成，进度已清除")
        except Exception:
            pass

        logger.info(f"全量同步分红送股完成，共同步 {total_records} 条记录，失败 {error_count} 只")
        return {'status': 'success', 'records': total_records, 'total': total, 'errors': error_count}

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    def _get_latest_trade_date(self) -> str:
        """
        获取最近交易日

        Returns:
            最近交易日，格式：YYYYMMDD
        """
        # 使用上证指数（000001）获取最近交易日
        latest_date = self.stock_daily_repo.get_latest_trade_date('000001')
        if latest_date:
            # 转换格式：YYYY-MM-DD -> YYYYMMDD
            return latest_date.replace('-', '')
        else:
            # 如果没有数据，返回当前日期
            from datetime import datetime
            return datetime.now().strftime('%Y%m%d')

    async def sync_dividend(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        record_date: Optional[str] = None,
        ex_date: Optional[str] = None,
        imp_ann_date: Optional[str] = None
    ) -> Dict:
        """
        同步分红送股数据

        Args:
            ts_code: 股票代码（可选）
            ann_date: 公告日期 YYYYMMDD（可选）
            record_date: 股权登记日 YYYYMMDD（可选）
            ex_date: 除权除息日 YYYYMMDD（可选）
            imp_ann_date: 实施公告日 YYYYMMDD（可选）
            注意：如果未提供任何参数，将使用最近交易日作为公告日期

        Returns:
            同步结果字典
        """
        try:
            # 如果未提供任何参数，使用最近交易日作为公告日期
            if not any([ts_code, ann_date, record_date, ex_date, imp_ann_date]):
                ann_date = self._get_latest_trade_date()
                logger.info(f"未提供任何参数，使用最近交易日作为公告日期: {ann_date}")

            logger.info(f"开始同步分红送股数据: ts_code={ts_code}, ann_date={ann_date}, record_date={record_date}, ex_date={ex_date}, imp_ann_date={imp_ann_date}")

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 从 Tushare 获取数据
            df = await asyncio.to_thread(
                provider.get_dividend,
                ts_code=ts_code,
                ann_date=ann_date,
                record_date=record_date,
                ex_date=ex_date,
                imp_ann_date=imp_ann_date
            )

            if df is None or df.empty:
                logger.warning("未获取到分红送股数据")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(self.dividend_repo.bulk_upsert, df)

            logger.info(f"✓ 分红送股数据同步成功，共 {records} 条记录")
            return {
                "status": "success",
                "message": f"成功同步 {records} 条记录",
                "records": records
            }

        except Exception as e:
            logger.error(f"同步分红送股数据失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "records": 0
            }

    def _validate_and_clean_data(self, df) -> any:
        """
        验证和清洗数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        # 确保必需字段存在
        required_fields = ['ts_code', 'end_date', 'ann_date']
        for field in required_fields:
            if field not in df.columns:
                logger.warning(f"缺少必需字段: {field}")
                df[field] = None

        # 过滤主键字段为空的行（ann_date 为主键一部分，不能为 NULL）
        before = len(df)
        df = df.dropna(subset=['ts_code', 'end_date', 'ann_date'])
        dropped = before - len(df)
        if dropped > 0:
            logger.warning(f"过滤掉 {dropped} 条主键字段为空的记录（ann_date/end_date/ts_code 为 null）")

        # 处理空值（将NaN替换为None）
        df = df.where(df.notna(), None)

        logger.debug(f"✓ 数据验证完成，共 {len(df)} 条记录")
        return df

    async def get_dividend_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        查询分红送股数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            limit: 返回记录数限制
            offset: 偏移量（用于分页）

        Returns:
            查询结果字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 并发查询总数、数据和统计
            total, items, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.dividend_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                ),
                asyncio.to_thread(
                    self.dividend_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.dividend_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = f"{item['ann_date'][:4]}-{item['ann_date'][4:6]}-{item['ann_date'][6:]}"
                if item.get('end_date'):
                    item['end_date'] = f"{item['end_date'][:4]}-{item['end_date'][4:6]}-{item['end_date'][6:]}"
                if item.get('record_date'):
                    item['record_date'] = f"{item['record_date'][:4]}-{item['record_date'][4:6]}-{item['record_date'][6:]}"
                if item.get('ex_date'):
                    item['ex_date'] = f"{item['ex_date'][:4]}-{item['ex_date'][4:6]}-{item['ex_date'][6:]}"
                if item.get('pay_date'):
                    item['pay_date'] = f"{item['pay_date'][:4]}-{item['pay_date'][4:6]}-{item['pay_date'][6:]}"
                if item.get('div_listdate'):
                    item['div_listdate'] = f"{item['div_listdate'][:4]}-{item['div_listdate'][4:6]}-{item['div_listdate'][6:]}"
                if item.get('imp_ann_date'):
                    item['imp_ann_date'] = f"{item['imp_ann_date'][:4]}-{item['imp_ann_date'][4:6]}-{item['imp_ann_date'][6:]}"
                if item.get('base_date'):
                    item['base_date'] = f"{item['base_date'][:4]}-{item['base_date'][4:6]}-{item['base_date'][6:]}"

            return {
                "items": items,
                "statistics": statistics,
                "total": total
            }

        except Exception as e:
            logger.error(f"查询分红送股数据失败: {e}")
            raise
