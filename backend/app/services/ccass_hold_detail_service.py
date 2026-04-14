"""
中央结算系统持股明细数据服务

处理中央结算系统持股明细数据的业务逻辑。
继承 TushareSyncBase，同步逻辑委托给基类。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.ccass_hold_detail_repository import CcassHoldDetailRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class CcassHoldDetailService(TushareSyncBase):
    """中央结算系统持股明细数据服务"""

    TABLE_KEY = 'ccass_hold_detail'
    FULL_HISTORY_START_DATE = '20160401'
    FULL_HISTORY_PROGRESS_KEY = 'sync:ccass_hold_detail:full_history:progress'

    def __init__(self):
        super().__init__()
        self.ccass_hold_detail_repo = CcassHoldDetailRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ CcassHoldDetailService initialized")

    # ------------------------------------------------------------------
    # 增量同步（标准入口）
    # ------------------------------------------------------------------

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """标准增量同步入口（无参数时自动从 sync_configs 读取配置，手动记录 sync_history）"""
        if start_date is None:
            start_date = await self.get_suggested_start_date()

        # 记录 sync_history
        history_id = await asyncio.to_thread(
            self.sync_history_repo.create,
            self.TABLE_KEY, 'incremental', 'by_date', start_date,
        )

        try:
            result = await self.sync_ccass_hold_detail(
                start_date=start_date,
                end_date=end_date,
                max_requests_per_minute=max_requests_per_minute,
            )
            data_end = end_date or datetime.now().strftime('%Y%m%d')
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'success', result.get('records', 0), data_end, None,
            )
            return result
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', 0, None, str(e),
            )
            raise

    async def sync_ccass_hold_detail(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步中央结算系统持股明细数据。

        ccass_hold_detail 接口要求 ts_code 或 trade_date 至少传一个，
        不支持 start_date/end_date 范围查询。

        有 ts_code 或 trade_date 时：单次请求（支持翻页）。
        无参数时：从 sync_configs 读取回看天数，逐交易日请求（与全量的 by_date 策略一致）。
        """
        from app.repositories.trading_calendar_repository import TradingCalendarRepository

        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute)

        # 有明确的 ts_code 或 trade_date 时，单次请求 + 翻页
        if ts_code or trade_date:
            all_dfs = []
            offset = 0
            while True:
                df = await asyncio.to_thread(
                    provider.get_ccass_hold_detail,
                    ts_code=ts_code, hk_code=hk_code, trade_date=trade_date,
                    limit=api_limit, offset=offset,
                )
                if df is None or df.empty:
                    break
                all_dfs.append(df)
                if len(df) < api_limit:
                    break
                offset += api_limit

            if not all_dfs:
                return {"status": "success", "records": 0, "message": "未获取到数据"}

            import pandas as pd
            combined = pd.concat(all_dfs, ignore_index=True) if len(all_dfs) > 1 else all_dfs[0]
            combined = self._validate_and_clean_data(combined)
            records = await asyncio.to_thread(self.ccass_hold_detail_repo.bulk_upsert, combined)
            return {"status": "success", "records": records, "message": f"成功同步 {records} 条记录"}

        # 无参数：逐交易日遍历（by_date + trade_date 参数）
        effective_start = start_date or await self.get_suggested_start_date()
        effective_end = end_date or datetime.now().strftime('%Y%m%d')

        cal_repo = TradingCalendarRepository()
        trading_days = await asyncio.to_thread(
            cal_repo.get_trading_days_between, effective_start, effective_end
        )

        if not trading_days:
            return {"status": "success", "records": 0, "message": "无需同步的交易日"}

        logger.info(f"[ccass_hold_detail] 增量同步 {len(trading_days)} 个交易日 ({effective_start}~{effective_end})")

        total_records = 0
        errors = 0
        sem = asyncio.Semaphore(3)

        async def sync_day(day: str):
            async with sem:
                try:
                    day_dfs = []
                    offset = 0
                    while True:
                        df = await asyncio.to_thread(
                            provider.get_ccass_hold_detail,
                            trade_date=day, limit=api_limit, offset=offset,
                        )
                        if df is None or df.empty:
                            break
                        day_dfs.append(df)
                        if len(df) < api_limit:
                            break
                        offset += api_limit
                    if not day_dfs:
                        return 0, None
                    import pandas as pd
                    combined = pd.concat(day_dfs, ignore_index=True) if len(day_dfs) > 1 else day_dfs[0]
                    combined = self._validate_and_clean_data(combined)
                    records = await asyncio.to_thread(self.ccass_hold_detail_repo.bulk_upsert, combined)
                    return records, None
                except Exception as e:
                    return 0, str(e)

        BATCH_SIZE = 15
        for batch_start in range(0, len(trading_days), BATCH_SIZE):
            batch = trading_days[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_day(d) for d in batch])
            for records, err in results:
                if err:
                    errors += 1
                    logger.error(f"[ccass_hold_detail] 同步失败: {err}")
                else:
                    total_records += records
            done = min(batch_start + BATCH_SIZE, len(trading_days))
            logger.info(f"[ccass_hold_detail] 进度: {done}/{len(trading_days)} 入库={total_records} 失败={errors}")

        return {
            "status": "success",
            "records": total_records,
            "message": f"增量同步完成 {total_records} 条（{len(trading_days)} 个交易日，失败 {errors}）"
        }

    # ------------------------------------------------------------------
    # 全量历史同步
    # ------------------------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        strategy: str = 'by_date',
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict:
        """全量同步历史数据（按交易日切片，Redis Set 续继）

        ccass_hold_detail 接口实际上不支持只传 start_date/end_date，
        必须传 ts_code 或 trade_date 之一，故使用 by_date + date_param='trade_date'
        逐日请求（每日约 7000 条，在 6000 上限附近，需要翻页）。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_ccass_hold_detail,
            upsert_fn=self.ccass_hold_detail_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            progress_key=self.FULL_HISTORY_PROGRESS_KEY,
            strategy=strategy,
            start_date=start_date,
            full_history_start=self.FULL_HISTORY_START_DATE,
            concurrency=concurrency,
            api_limit=api_limit,
            max_requests_per_minute=max_requests_per_minute,
            update_state_fn=update_state_fn,
            table_key=self.TABLE_KEY,
            date_param='trade_date',
        )

    # ------------------------------------------------------------------
    # 建议起始日期
    # ------------------------------------------------------------------

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）。"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 30) if cfg else 30
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )
        if last_end and last_end < candidate:
            return last_end
        return candidate

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _validate_and_clean_data(self, df):
        """验证和清洗数据"""
        if df is None or df.empty:
            return df

        required_columns = ['trade_date', 'ts_code', 'col_participant_id']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必要字段: {col}")

        # col_participant_id 是主键的一部分（NOT NULL），过滤空值行
        null_mask = df['col_participant_id'].isna() | (df['col_participant_id'] == '')
        null_count = null_mask.sum()
        if null_count > 0:
            logger.warning(f"过滤掉 {null_count} 条 col_participant_id 为空的记录")
            df = df[~null_mask]

        original_count = len(df)
        df = df.drop_duplicates(subset=['trade_date', 'ts_code', 'col_participant_id'])
        if len(df) < original_count:
            logger.warning(f"移除了 {original_count - len(df)} 条重复数据")

        df = df.replace('', None)

        import pandas as pd
        if 'col_shareholding' in df.columns:
            df['col_shareholding'] = pd.to_numeric(df['col_shareholding'], errors='coerce')
        if 'col_shareholding_percent' in df.columns:
            df['col_shareholding_percent'] = pd.to_numeric(df['col_shareholding_percent'], errors='coerce')

        logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
        return df

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def resolve_default_trade_date(self) -> Optional[str]:
        """返回最近有数据的交易日期（YYYY-MM-DD），用于前端日期选择器回填。"""
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.ccass_hold_detail_repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.ccass_hold_detail_repo.get_latest_trade_date)
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_ccass_hold_detail_data(
        self,
        ts_code: Optional[str] = None,
        col_participant_id: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict:
        """查询中央结算系统持股明细数据"""
        try:
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            if trade_date_fmt and not start_date_fmt and not end_date_fmt:
                start_date_fmt = trade_date_fmt
                end_date_fmt = trade_date_fmt

            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.ccass_hold_detail_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    col_participant_id=col_participant_id,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.ccass_hold_detail_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    col_participant_id=col_participant_id
                ),
                asyncio.to_thread(
                    self.ccass_hold_detail_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                )
            )

            return {"items": items, "statistics": statistics, "total": total}

        except Exception as e:
            logger.error(f"获取中央结算系统持股明细数据失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """获取最新的中央结算系统持股明细数据"""
        try:
            latest_date = await asyncio.to_thread(
                self.ccass_hold_detail_repo.get_latest_trade_date, ts_code=ts_code
            )
            if not latest_date:
                return []

            items = await asyncio.to_thread(
                self.ccass_hold_detail_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=limit
            )
            return items

        except Exception as e:
            logger.error(f"获取最新中央结算系统持股明细数据失败: {e}")
            raise

    async def get_top_participants(
        self,
        trade_date: str,
        ts_code: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """获取指定日期的TOP持股机构"""
        try:
            return await asyncio.to_thread(
                self.ccass_hold_detail_repo.get_top_participants,
                trade_date=trade_date,
                ts_code=ts_code,
                limit=limit
            )
        except Exception as e:
            logger.error(f"获取TOP持股机构失败: {e}")
            raise
