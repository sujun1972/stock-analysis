"""
港股通十大成交股服务

提供港股通十大成交股数据的同步和查询功能
根据Tushare ggt_top10接口
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger

from app.repositories.ggt_top10_repository import GgtTop10Repository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class GgtTop10Service:
    """港股通十大成交股服务"""

    def __init__(self):
        self.ggt_top10_repo = GgtTop10Repository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取 Tushare Provider"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_ggt_top10(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        market_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步港股通十大成交股数据

        Args:
            ts_code: 股票代码（可选）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            market_type: 市场类型 2:港股通(沪) 4:港股通(深)（可选）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步港股通十大成交股数据: ts_code={ts_code}, trade_date={trade_date}, "
                       f"start_date={start_date}, end_date={end_date}, market_type={market_type}")

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 调用 Provider 方法获取数据
            df = await asyncio.to_thread(
                provider.get_ggt_top10,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                market_type=market_type
            )

            if df is None or df.empty:
                logger.warning("未获取到港股通十大成交股数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库（使用Repository的bulk_upsert）
            records = await asyncio.to_thread(
                self.ggt_top10_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条港股通十大成交股记录")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条记录"
            }

        except Exception as e:
            logger.error(f"同步港股通十大成交股数据失败: {e}")
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

    async def get_ggt_top10_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        market_type: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        查询港股通十大成交股数据

        Args:
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            ts_code: 股票代码（可选）
            market_type: 市场类型 2:港股通(沪) 4:港股通(深)（可选）
            limit: 每页记录数
            offset: 分页偏移量

        Returns:
            数据字典，包含items和total
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 并发查询数据和总数
            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.ggt_top10_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    market_type=market_type,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.ggt_top10_repo.get_total_count,
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
            logger.error(f"查询港股通十大成交股数据失败: {e}")
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
                self.ggt_top10_repo.get_statistics,
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
            logger.error(f"获取港股通十大成交股统计信息失败: {e}")
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
                self.ggt_top10_repo.get_latest_trade_date
            )

            if not latest_date:
                return {"items": [], "total": 0, "latest_date": None}

            # 查询最新日期的数据
            items = await asyncio.to_thread(
                self.ggt_top10_repo.get_by_date_range,
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
            logger.error(f"获取最新港股通十大成交股数据失败: {e}")
            raise

    async def get_top_by_net_amount(
        self,
        trade_date: str,
        market_type: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取指定日期净买入金额排名前N的股票

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
                self.ggt_top10_repo.get_top_by_net_amount,
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
            logger.error(f"获取净买入金额排名失败: {e}")
            raise

    # ------------------------------------------------------------------ #
    # 全量历史同步（逐交易日 + Redis 续继）
    # ggt_top10 接口只支持 trade_date（单日），不支持 start_date/end_date
    # 每日约 20 条，10 并发，用 trading_calendar 获取交易日列表
    # ------------------------------------------------------------------ #
    FULL_HISTORY_START_DATE = "20150101"
    FULL_HISTORY_PROGRESS_KEY = "sync:ggt_top10:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:ggt_top10:full_history:lock"
    FULL_HISTORY_CONCURRENCY = 10

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        update_state_fn=None
    ) -> Dict:
        """
        逐交易日全量同步港股通十大成交股历史数据（支持 Redis 续继）

        ggt_top10 接口只支持按 trade_date 单日查询，每日约 20 条。
        从 trading_calendar 获取交易日列表，10 并发逐日请求。
        Redis Set 记录已完成的交易日，支持中断续继。

        Args:
            redis_client: Redis 客户端
            start_date: 同步起始日期 YYYYMMDD，不传则使用 FULL_HISTORY_START_DATE
            update_state_fn: Celery self.update_state 回调
        """
        from app.repositories.trading_calendar_repository import TradingCalendarRepository

        effective_start = start_date or self.FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        # 获取交易日列表
        cal_repo = TradingCalendarRepository()
        trading_days = await asyncio.to_thread(
            cal_repo.get_trading_days_between, effective_start, today
        )
        total = len(trading_days)
        logger.info(f"[全量ggt_top10] 共 {total} 个交易日需要同步")

        completed_set = redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY)
        # Redis 存储的可能是 bytes，统一转为 str
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        logger.info(f"[全量ggt_top10] 已完成 {len(completed_set)} 个，剩余 {total - len(completed_set)} 个")

        pending = [d for d in trading_days if d not in completed_set]

        provider = self._get_provider()
        success_count = 0
        skip_count = len(completed_set)
        error_count = 0
        total_records = 0

        sem = asyncio.Semaphore(self.FULL_HISTORY_CONCURRENCY)

        async def sync_day(trade_date: str):
            async with sem:
                try:
                    df = await asyncio.to_thread(
                        provider.get_ggt_top10,
                        trade_date=trade_date
                    )
                    records = 0
                    if df is not None and not df.empty:
                        df = self._validate_and_clean_data(df)
                        records = await asyncio.to_thread(self.ggt_top10_repo.bulk_upsert, df)
                    return trade_date, True, records, None
                except Exception as e:
                    return trade_date, False, 0, str(e)

        BATCH_SIZE = self.FULL_HISTORY_CONCURRENCY * 3
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_day(d) for d in batch])

            for trade_date, ok, records, err in results:
                if ok:
                    redis_client.sadd(self.FULL_HISTORY_PROGRESS_KEY, trade_date)
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
                    logger.error(f"[全量ggt_top10] {trade_date} 失败（下次续继）: {err}")

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
            logger.info(f"[全量ggt_top10] 进度: {done}/{total} ({round(done/total*100,1)}%) "
                        f"入库={total_records} 失败={error_count}")

        final_done = len(redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info("[全量ggt_top10] ✅ 全量同步完成，进度已清除")

        return {
            "status": "success",
            "total": total,
            "success": success_count,
            "skipped": skip_count,
            "errors": error_count,
            "records": total_records,
            "message": f"同步完成 {success_count} 个交易日，入库 {total_records} 条，失败 {error_count} 个"
        }
