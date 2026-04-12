"""
股票日线数据服务

职责:
- 日线数据查询
- 增量/全量同步（继承 TushareSyncBase，委托给基类）
- 数据统计分析
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger

from app.repositories.stock_data_repository import StockDataRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.services.tushare_sync_base import TushareSyncBase
from app.services.stock_quote_cache import stock_quote_cache


class StockDailyService(TushareSyncBase):
    """
    股票日线数据服务

    继承 TushareSyncBase，增量与全量同步逻辑全部委托给基类。
    """

    TABLE_KEY = 'stock_daily'
    FULL_HISTORY_START_DATE = '20210101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:daily:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:daily:full_history:lock'

    def __init__(self):
        super().__init__()
        self.stock_repo = StockDataRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.info("✓ StockDailyService initialized")

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """
        增量同步日线数据。

        start_date / end_date 为 YYYYMMDD。未传时通过 get_suggested_start_date 自动计算。
        sync_strategy 来自 sync_configs.incremental_sync_strategy（如 by_date_range）。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        if sync_strategy is None:
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'

        if start_date is None:
            start_date = await self.get_suggested_start_date()

        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_daily_data_range,
            upsert_fn=self.stock_repo.bulk_upsert,
            clean_fn=None,
            table_key=self.TABLE_KEY,
            date_col='trade_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
        )

    # ------------------------------------------------------------------
    # 全量同步
    # ------------------------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 8,
        strategy: str = 'by_ts_code',
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict:
        """
        全量历史同步（支持 Redis 续继）。

        strategy 默认 by_ts_code（逐只股票拉取），
        也可改为 by_month（按月切片，适合按日期范围接口）。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_daily_data_range,
            upsert_fn=self.stock_repo.bulk_upsert,
            clean_fn=None,
            progress_key=self.FULL_HISTORY_PROGRESS_KEY,
            strategy=strategy,
            start_date=start_date,
            full_history_start=self.FULL_HISTORY_START_DATE,
            concurrency=concurrency,
            api_limit=api_limit,
            max_requests_per_minute=max_requests_per_minute,
            update_state_fn=update_state_fn,
            table_key=self.TABLE_KEY,
        )

    # ------------------------------------------------------------------
    # 建议起始日期
    # ------------------------------------------------------------------

    async def get_suggested_start_date(self) -> Optional[str]:
        """
        计算增量同步建议起始日期（YYYYMMDD）。

        候选起始 = 今天 - incremental_default_days（sync_configs，默认 7 天）
        上次结束 = sync_history 最近一次增量成功的 data_end_date
        实际起始 = min(候选, 上次结束)，取更早者保证数据连续
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7

        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')

        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )

        if last_end and last_end < candidate:
            logger.debug(f"[stock_daily] 建议起始={last_end}（上次结束={last_end} < 候选={candidate}）")
            return last_end

        logger.debug(f"[stock_daily] 建议起始={candidate}（候选={candidate}，上次结束={last_end}）")
        return candidate

    # ------------------------------------------------------------------
    # 单只股票同步（供 sync_daily_single_task 使用，保持向后兼容）
    # ------------------------------------------------------------------

    async def sync_single_stock(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        years: int = 5,
    ) -> Dict:
        """
        同步单只股票日线数据。

        Args:
            code:       股票 ts_code（必填）
            start_date: 开始日期 YYYYMMDD 或 YYYY-MM-DD
            end_date:   结束日期
            years:      未指定日期时的回看年数
        """
        start_date = start_date.replace('-', '') if start_date else None
        end_date = end_date.replace('-', '') if end_date else None

        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y%m%d')

        logger.info(f"同步 {code} 日线数据: {start_date} ~ {end_date}")

        provider = self._get_provider()
        df = await asyncio.to_thread(
            provider.get_daily_data_range,
            ts_code=code,
            start_date=start_date,
            end_date=end_date,
        )

        if df is None or df.empty:
            logger.warning(f"{code}: 无数据")
            return {"status": "success", "code": code, "count": 0, "message": "无数据"}

        count = await asyncio.to_thread(self.stock_repo.bulk_upsert, df)
        logger.info(f"✓ {code}: 同步完成 {count} 条")
        return {
            "status": "success",
            "code": code,
            "count": count,
            "date_range": f"{start_date} ~ {end_date}",
            "message": f"成功同步 {count} 条记录",
        }

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_daily_data(
        self,
        code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        page: int = 1,
    ) -> Dict:
        """查询日线数据（支持分页）"""
        try:
            if code:
                df = await asyncio.to_thread(
                    self.stock_repo.get_daily_data,
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                )

                if not df.empty:
                    df = df.reset_index()
                    if 'date' in df.columns:
                        df['date'] = df['date'].apply(
                            lambda d: d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)[:10]
                        )
                    df['code'] = code
                    quotes = await stock_quote_cache.get_quotes_batch([code])
                    df['name'] = quotes.get(code, {}).get('name', '')

                items = df.to_dict('records') if not df.empty else []
                total = len(items)
                start_idx = (page - 1) * limit
                items = items[start_idx:start_idx + limit]

            else:
                offset = (page - 1) * limit
                items, total = await self._get_latest_daily_data(
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    offset=offset,
                )

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": limit,
                "total_pages": (total + limit - 1) // limit,
            }

        except Exception as e:
            logger.error(f"查询日线数据失败: {e}")
            raise

    async def _get_latest_daily_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Dict], int]:
        """获取最近交易日的日线数据（多只股票，分页）"""
        db = self.stock_repo.db
        conn = db.pool_manager.get_connection()
        cursor = conn.cursor()
        try:
            if end_date:
                cursor.execute(
                    "SELECT MAX(trade_date) FROM trading_calendar"
                    " WHERE is_trading_day = true AND trade_date <= %s",
                    (end_date,),
                )
            else:
                cursor.execute(
                    "SELECT MAX(trade_date) FROM trading_calendar"
                    " WHERE is_trading_day = true AND trade_date <= CURRENT_DATE"
                )
            latest_date = (cursor.fetchone() or [None])[0]

            if not latest_date:
                return [], 0

            if start_date and str(latest_date) < start_date:
                return [], 0

            cursor.execute("SELECT COUNT(*) FROM stock_basic WHERE list_status = 'L'")
            total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT sd.code, sd.date, sd.open, sd.high, sd.low, sd.close,
                       sd.volume, sd.amount, sd.amplitude, sd.pct_change, sd.change, sd.turnover
                FROM stock_daily sd
                WHERE sd.date = %s
                  AND sd.code LIKE '%%.%%'
                ORDER BY sd.code
                LIMIT %s OFFSET %s
                """,
                (latest_date, limit, offset),
            )
            rows = cursor.fetchall()

        except Exception as e:
            logger.error(f"查询最新日线数据失败: {e}")
            raise
        finally:
            cursor.close()
            db.pool_manager.release_connection(conn)

        items = []
        ts_codes = []
        for row in rows:
            ts_codes.append(row[0])
            items.append({
                'code': row[0], 'name': '',
                'date': row[1].strftime('%Y-%m-%d') if row[1] else None,
                'open': float(row[2]) if row[2] is not None else None,
                'high': float(row[3]) if row[3] is not None else None,
                'low': float(row[4]) if row[4] is not None else None,
                'close': float(row[5]) if row[5] is not None else None,
                'volume': int(row[6]) if row[6] is not None else None,
                'amount': float(row[7]) if row[7] is not None else None,
                'amplitude': float(row[8]) if row[8] is not None else None,
                'pct_change': float(row[9]) if row[9] is not None else None,
                'change': float(row[10]) if row[10] is not None else None,
                'turnover': float(row[11]) if row[11] is not None else None,
            })

        if ts_codes:
            quotes = await stock_quote_cache.get_quotes_batch(ts_codes)
            for item in items:
                item['name'] = quotes.get(item['code'], {}).get('name', '')

        return items, total

    async def get_statistics(self) -> Dict:
        """获取日线数据全局统计"""
        db = self.stock_repo.db
        conn = db.pool_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM stock_basic WHERE list_status = 'L'")
            stock_count = cursor.fetchone()[0] or 0

            cursor.execute(
                """
                SELECT COUNT(*) FILTER (WHERE trade_date >= '2021-01-01'),
                       MAX(trade_date)
                FROM trading_calendar
                WHERE is_trading_day = true
                  AND trade_date <= CURRENT_DATE
                """
            )
            row = cursor.fetchone()
            trading_days = row[0] or 0
            latest_date = row[1].strftime('%Y-%m-%d') if row[1] else None

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {'stock_count': 0, 'record_count': 0, 'latest_date': None, 'earliest_date': None}
        finally:
            cursor.close()
            db.pool_manager.release_connection(conn)

        return {
            'stock_count': stock_count,
            'record_count': stock_count * trading_days,
            'latest_date': latest_date,
            'earliest_date': '2021-01-04',
        }

