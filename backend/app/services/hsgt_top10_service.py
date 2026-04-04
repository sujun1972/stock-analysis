"""
沪深股通十大成交股服务

提供沪深股通十大成交股数据的同步和查询功能
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from loguru import logger

from app.repositories.hsgt_top10_repository import HsgtTop10Repository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class HsgtTop10Service:
    """沪深股通十大成交股服务"""

    def __init__(self):
        self.hsgt_top10_repo = HsgtTop10Repository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取 Tushare Provider"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_hsgt_top10(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        market_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步沪深股通十大成交股数据

        Args:
            ts_code: 股票代码（可选）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            market_type: 市场类型 1:沪市 3:深市（可选）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步沪深股通十大成交股数据: ts_code={ts_code}, trade_date={trade_date}, "
                       f"start_date={start_date}, end_date={end_date}, market_type={market_type}")

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 调用 Provider 方法获取数据
            df = await asyncio.to_thread(
                provider.get_hsgt_top10,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                market_type=market_type
            )

            if df is None or df.empty:
                logger.warning("未获取到沪深股通十大成交股数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库（使用Repository的bulk_upsert）
            records = await asyncio.to_thread(
                self.hsgt_top10_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条沪深股通十大成交股记录")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条记录"
            }

        except Exception as e:
            logger.error(f"同步沪深股通十大成交股数据失败: {e}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始数据DataFrame

        Returns:
            清洗后的DataFrame
        """
        # 确保必需字段存在
        required_fields = ['trade_date', 'ts_code', 'market_type']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 数据类型转换
        if 'rank' in df.columns:
            df['rank'] = df['rank'].fillna(0).astype(int)

        # 移除trade_date为空的记录
        df = df[df['trade_date'].notna()]

        logger.debug(f"数据验证完成，共 {len(df)} 条有效记录")
        return df

    async def get_hsgt_top10_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        market_type: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        查询沪深股通十大成交股数据

        Args:
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            ts_code: 股票代码（可选）
            market_type: 市场类型 1:沪市 3:深市（可选）
            limit: 返回记录数限制

        Returns:
            数据字典，包含items和total
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 查询数据和总数
            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.hsgt_top10_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    market_type=market_type,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.hsgt_top10_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    market_type=market_type
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（用于前端显示）
            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

            return {
                "items": items,
                "total": total
            }

        except Exception as e:
            logger.error(f"查询沪深股通十大成交股数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        market_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            market_type: 市场类型（可选）

        Returns:
            统计数据字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 获取统计数据
            stats = await asyncio.to_thread(
                self.hsgt_top10_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                market_type=market_type
            )

            # 单位转换：元 -> 亿元
            if stats:
                stats['avg_amount_yi'] = stats.get('avg_amount', 0) / 100000000
                stats['avg_net_amount_yi'] = stats.get('avg_net_amount', 0) / 100000000
                stats['max_amount_yi'] = stats.get('max_amount', 0) / 100000000
                stats['total_net_amount_yi'] = stats.get('total_net_amount', 0) / 100000000

            return stats

        except Exception as e:
            logger.error(f"获取沪深股通十大成交股统计信息失败: {e}")
            raise

    async def get_latest_data(
        self,
        market_type: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        获取最新数据

        Args:
            market_type: 市场类型（可选）
            limit: 返回记录数

        Returns:
            最新数据字典
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.hsgt_top10_repo.get_latest_trade_date
            )

            if not latest_date:
                return {"items": [], "total": 0, "latest_date": None}

            # 查询最新日期的数据
            items = await asyncio.to_thread(
                self.hsgt_top10_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                market_type=market_type,
                limit=limit
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

            # 格式化最新日期
            latest_date_formatted = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:]}"

            return {
                "items": items,
                "total": len(items),
                "latest_date": latest_date_formatted
            }

        except Exception as e:
            logger.error(f"获取最新沪深股通十大成交股数据失败: {e}")
            raise

    async def get_top_by_net_amount(
        self,
        trade_date: str,
        market_type: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取指定日期净成交金额排名前N的股票

        Args:
            trade_date: 交易日期 YYYY-MM-DD
            market_type: 市场类型（可选）
            limit: 返回记录数

        Returns:
            排名数据字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            trade_date_fmt = trade_date.replace('-', '')

            # 查询排名数据
            items = await asyncio.to_thread(
                self.hsgt_top10_repo.get_top_by_net_amount,
                trade_date=trade_date_fmt,
                limit=limit,
                market_type=market_type
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取净成交金额排名失败: {e}")
            raise

    # ------------------------------------------------------------------ #
    # 全量历史同步（按月切片 + Redis 续继）
    # ------------------------------------------------------------------ #
    FULL_HISTORY_START_DATE = "20150101"
    FULL_HISTORY_PROGRESS_KEY = "sync:hsgt_top10:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:hsgt_top10:full_history:lock"
    FULL_HISTORY_CONCURRENCY = 5

    @staticmethod
    def _generate_months(start_date: str, end_date: str) -> List[tuple]:
        """
        将日期范围切分为自然月片段，每片返回 (month_start, month_end)，均为 YYYYMMDD 格式。

        按月切片原因：hsgt_top10 每交易日沪市10条+深市10条=20条，
        单月约 20×22=440 条，远低于 Tushare 单次 5000 条上限，且月份数量可控。
        """
        cur = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
        end = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
        months = []
        while cur <= end:
            # 月初
            ms = cur.replace(day=1)
            # 月末：下月1日减1天
            if ms.month == 12:
                me = date(ms.year + 1, 1, 1) - timedelta(days=1)
            else:
                me = date(ms.year, ms.month + 1, 1) - timedelta(days=1)
            me = min(me, end)
            months.append((ms.strftime('%Y%m%d'), me.strftime('%Y%m%d')))
            cur = me + timedelta(days=1)
        return months

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        update_state_fn=None
    ) -> Dict:
        """
        按月切片全量同步沪深股通十大成交股历史数据（支持 Redis 续继）

        每月约 440 条，安全低于 Tushare 5000 条上限。
        5 并发，Redis Set 记录已完成月份起始日，支持中断续继。

        Args:
            redis_client: Redis 客户端，用于进度续继
            start_date: 同步起始日期 YYYYMMDD，不传则使用 FULL_HISTORY_START_DATE
            update_state_fn: Celery self.update_state 回调，用于上报进度

        Returns:
            同步结果统计
        """
        effective_start = start_date or self.FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")
        months = self._generate_months(effective_start, today)
        total = len(months)
        logger.info(f"[全量hsgt_top10] 共 {total} 个月段需要同步")

        completed_set = redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY)
        logger.info(f"[全量hsgt_top10] 已完成 {len(completed_set)} 个，剩余 {total - len(completed_set)} 个")

        pending = [(ms, me) for ms, me in months if ms not in completed_set]

        provider = self._get_provider()
        success_count = 0
        skip_count = len(completed_set)
        error_count = 0
        total_records = 0

        sem = asyncio.Semaphore(self.FULL_HISTORY_CONCURRENCY)

        async def sync_month(ms: str, me: str):
            async with sem:
                try:
                    df = await asyncio.to_thread(
                        provider.get_hsgt_top10,
                        start_date=ms,
                        end_date=me
                    )
                    records = 0
                    if df is not None and not df.empty:
                        df = self._validate_and_clean_data(df)
                        records = await asyncio.to_thread(self.hsgt_top10_repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    return ms, me, False, 0, str(e)

        BATCH_SIZE = self.FULL_HISTORY_CONCURRENCY * 2
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_month(ms, me) for ms, me in batch])

            for ms, me, ok, records, err in results:
                if ok:
                    redis_client.sadd(self.FULL_HISTORY_PROGRESS_KEY, ms)
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
                    logger.error(f"[全量hsgt_top10] {ms}~{me} 失败（下次续继）: {err}")

            done = skip_count + success_count
            if update_state_fn:
                update_state_fn(
                    state='PROGRESS',
                    meta={
                        'current': done,
                        'total': total,
                        'percent': round(done / total * 100, 1),
                        'records': total_records,
                        'errors': error_count
                    }
                )
            logger.info(f"[全量hsgt_top10] 进度: {done}/{total} ({round(done/total*100,1)}%) "
                        f"入库={total_records} 失败={error_count}")

        final_done = len(redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info("[全量hsgt_top10] ✅ 全量同步完成，进度已清除")

        return {
            "status": "success",
            "total": total,
            "success": success_count,
            "skipped": skip_count,
            "errors": error_count,
            "records": total_records,
            "message": f"同步完成 {success_count} 个月段，入库 {total_records} 条，失败 {error_count} 个"
        }
