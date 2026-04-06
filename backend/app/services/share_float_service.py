"""
限售股解禁服务

处理限售股解禁数据的业务逻辑
"""

import asyncio
import traceback
from typing import Optional, Dict
from datetime import datetime, timedelta, date
from loguru import logger
import pandas as pd

from app.repositories.share_float_repository import ShareFloatRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class ShareFloatService:
    """限售股解禁服务"""

    FULL_HISTORY_START_DATE = "20050101"
    FULL_HISTORY_PROGRESS_KEY = "sync:share_float:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:share_float:full_history:lock"
    FULL_HISTORY_CONCURRENCY = 5

    def __init__(self):
        self.share_float_repo = ShareFloatRepository()
        self.sync_history_repo = SyncHistoryRepository()
        self.provider_factory = DataProviderFactory()

    @staticmethod
    def _generate_months(start_date: str, end_date: str) -> list:
        """将日期范围切分为自然月片段，每片返回 (month_start, month_end)，均为 YYYYMMDD。"""
        import calendar
        start_d = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
        end_d = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
        segments = []
        cur = date(start_d.year, start_d.month, 1)
        while cur <= end_d:
            ms = max(cur, start_d)
            last_day = calendar.monthrange(cur.year, cur.month)[1]
            me = min(date(cur.year, cur.month, last_day), end_d)
            segments.append((ms.strftime('%Y%m%d'), me.strftime('%Y%m%d')))
            if cur.month == 12:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 1, 1)
        return segments

    @staticmethod
    def _generate_weeks(start_date: str, end_date: str) -> list:
        """将日期范围切分为7天窗口片段，每片返回 (week_start, week_end)，均为 YYYYMMDD。"""
        start_d = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
        end_d = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
        segments = []
        cur = start_d
        while cur <= end_d:
            ws = cur
            we = min(cur + timedelta(days=6), end_d)
            segments.append((ws.strftime('%Y%m%d'), we.strftime('%Y%m%d')))
            cur = we + timedelta(days=1)
        return segments

    @staticmethod
    def _generate_dates(start_date: str, end_date: str) -> list:
        """将日期范围切分为逐日片段，每片返回 (day, day)，均为 YYYYMMDD。"""
        start_d = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
        end_d = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
        segments = []
        cur = start_d
        while cur <= end_d:
            ds = cur.strftime('%Y%m%d')
            segments.append((ds, ds))
            cur += timedelta(days=1)
        return segments

    def _generate_segments(self, strategy: str, start_date: str, end_date: str) -> list:
        """根据策略生成切片片段列表。"""
        if strategy == 'by_week':
            return self._generate_weeks(start_date, end_date)
        elif strategy == 'by_date':
            return self._generate_dates(start_date, end_date)
        else:  # by_month（默认）
            return self._generate_months(start_date, end_date)

    async def sync_full_history(self, redis_client, start_date: Optional[str] = None, concurrency: int = 5,
                                strategy: str = 'by_month', update_state_fn=None,
                                max_requests_per_minute: int = 0) -> Dict:
        """全量同步限售股解禁历史数据（支持 Redis 续继）

        strategy 支持：
          'by_month'  — 按自然月切片（默认，推荐，单次上限6000条）
          'by_week'   — 按7天窗口切片
          'by_date'   — 逐日切片
          'by_ts_code'— 逐只股票切片（按 ts_code 请求全部历史记录）
        """
        if strategy == 'by_ts_code':
            return await self._sync_full_history_by_ts_code(redis_client, start_date, concurrency, update_state_fn, max_requests_per_minute)
        return await self._sync_full_history_by_date_range(redis_client, start_date, concurrency, strategy, update_state_fn, max_requests_per_minute)

    async def _sync_full_history_by_ts_code(self, redis_client, start_date: Optional[str], concurrency: int,
                                             update_state_fn, max_requests_per_minute: int = 0) -> Dict:
        """逐只股票全量同步限售股解禁历史数据（支持 Redis 续继）"""
        from app.repositories.stock_basic_repository import StockBasicRepository
        from app.repositories.sync_config_repository import SyncConfigRepository

        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'share_float')
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000

        all_ts_codes = await asyncio.to_thread(StockBasicRepository().get_listed_ts_codes, status='L')
        total = len(all_ts_codes)
        logger.info(f"[全量share_float] 策略=by_ts_code，api_limit={api_limit}，共 {total} 只股票需要同步")

        completed_set = redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY)
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        pending = [c for c in all_ts_codes if c not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        total_records = 0

        provider = self._get_provider(max_requests_per_minute)
        sem = asyncio.Semaphore(max(1, concurrency))
        effective_start = start_date or self.FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")
        MAX_OFFSET = 90000

        async def sync_one(ts_code: str):
            async with sem:
                try:
                    records = 0
                    offset = 0
                    while True:
                        if offset > MAX_OFFSET:
                            logger.warning(f"[全量share_float] {ts_code} offset={offset} 超过上限，停止翻页")
                            break
                        df = await asyncio.to_thread(
                            provider.get_share_float,
                            ts_code=ts_code, start_date=effective_start, end_date=today,
                            limit=api_limit, offset=offset,
                        )
                        if df is None or df.empty:
                            break
                        raw_count = len(df)
                        df = self._validate_and_clean_data(df)
                        records += await asyncio.to_thread(self.share_float_repo.bulk_upsert, df)
                        if raw_count < api_limit:
                            break
                        offset += api_limit
                        logger.info(f"[全量share_float] {ts_code} 触发分页（原始={raw_count} >= {api_limit}），offset={offset}")
                    return ts_code, True, records, None
                except Exception as e:
                    return ts_code, False, 0, str(e)

        BATCH_SIZE = 50
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_one(c) for c in batch])
            for ts_code, ok, records, err in results:
                if ok:
                    redis_client.sadd(self.FULL_HISTORY_PROGRESS_KEY, ts_code)
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
                    logger.error(f"[全量share_float] {ts_code} 失败（下次续继）: {err}")
            done = skip_count + success_count
            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={'current': done, 'total': total,
                    'percent': round(done / total * 100, 1), 'records': total_records, 'errors': error_count})
            logger.info(f"[全量share_float] 进度: {done}/{total} ({round(done/total*100,1)}%) 入库={total_records} 失败={error_count}")

        final_done = len(redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info("[全量share_float] ✅ 全量同步完成（by_ts_code），进度已清除")

        return {"status": "success", "total": total, "success": success_count,
                "skipped": skip_count, "errors": error_count, "records": total_records,
                "message": f"同步完成 {success_count} 只股票，入库 {total_records} 条，失败 {error_count} 只"}

    async def _sync_full_history_by_date_range(self, redis_client, start_date: Optional[str], concurrency: int,
                                               strategy: str, update_state_fn,
                                               max_requests_per_minute: int = 0) -> Dict:
        """按日期切片全量同步限售股解禁历史数据（支持 Redis 续继、超限分页）"""
        from app.repositories.sync_config_repository import SyncConfigRepository
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'share_float')
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000

        effective_start = start_date or self.FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")
        segments = self._generate_segments(strategy, effective_start, today)
        total = len(segments)
        logger.info(f"[全量share_float] 策略={strategy} api_limit={api_limit}，共 {total} 个片段需要同步")

        completed_set = redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY)
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        pending = [(ms, me) for ms, me in segments if ms not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        total_records = 0

        provider = self._get_provider(max_requests_per_minute)
        sem = asyncio.Semaphore(max(1, concurrency))

        MAX_OFFSET = 90000  # Tushare offset 上限约 100000，超过即停止翻页

        async def sync_segment(ms: str, me: str):
            async with sem:
                try:
                    records = 0
                    offset = 0
                    while True:
                        if offset > MAX_OFFSET:
                            logger.warning(f"[全量share_float] {ms}~{me} offset={offset} 超过上限 {MAX_OFFSET}，停止翻页（当前片段已入库 {records} 条）")
                            break
                        df = await asyncio.to_thread(
                            provider.get_share_float,
                            start_date=ms, end_date=me,
                            limit=api_limit, offset=offset,
                        )
                        if df is None or df.empty:
                            break
                        raw_count = len(df)  # 分页判断必须用清洗前的原始行数
                        df = self._validate_and_clean_data(df)
                        records += await asyncio.to_thread(self.share_float_repo.bulk_upsert, df)
                        if raw_count < api_limit:
                            break
                        offset += api_limit
                        logger.info(f"[全量share_float] {ms}~{me} 触发分页（原始={raw_count} >= {api_limit}），offset={offset}")
                    return ms, me, True, records, None
                except Exception as e:
                    return ms, me, False, 0, str(e)

        BATCH_SIZE = max(1, concurrency)
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_segment(ms, me) for ms, me in batch])
            for ms, me, ok, records, err in results:
                if ok:
                    redis_client.sadd(self.FULL_HISTORY_PROGRESS_KEY, ms)
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
                    logger.error(f"[全量share_float] {ms}~{me} 失败（下次续继）: {err}")
            done = skip_count + success_count
            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={'current': done, 'total': total,
                    'percent': round(done / total * 100, 1), 'records': total_records, 'errors': error_count})
            logger.info(f"[全量share_float] 进度: {done}/{total} ({round(done/total*100,1)}%) 入库={total_records} 失败={error_count}")

        final_done = len(redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info(f"[全量share_float] ✅ 全量同步完成（{strategy}），进度已清除")

        return {"status": "success", "total": total, "success": success_count,
                "skipped": skip_count, "errors": error_count, "records": total_records,
                "message": f"同步完成 {success_count} 个片段（策略={strategy} limit={api_limit}），入库 {total_records} 条，失败 {error_count} 个"}

    async def get_share_float_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        float_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        获取限售股解禁数据

        Args:
            start_date: 开始日期（解禁日期），格式：YYYYMMDD
            end_date: 结束日期（解禁日期），格式：YYYYMMDD
            ts_code: 股票代码
            ann_date: 公告日期，格式：YYYYMMDD
            float_date: 解禁日期，格式：YYYYMMDD
            limit: 返回记录数限制

        Returns:
            包含数据列表和总数的字典
        """
        try:
            # 查询数据
            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.share_float_repo.get_by_date_range,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code,
                    ann_date=ann_date,
                    float_date=float_date,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.share_float_repo.get_count,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code
                )
            )

            # 格式化数据
            for item in items:
                # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('float_date'):
                    item['float_date'] = self._format_date(item['float_date'])

                # 数值格式化
                if item.get('float_share') is not None:
                    item['float_share'] = round(item['float_share'], 2)
                if item.get('float_ratio') is not None:
                    item['float_ratio'] = round(item['float_ratio'], 4)

            return {
                "items": items,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取限售股解禁数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取限售股解禁统计信息

        Args:
            start_date: 开始日期（解禁日期），格式：YYYYMMDD
            end_date: 结束日期（解禁日期），格式：YYYYMMDD
            ts_code: 股票代码

        Returns:
            统计信息字典
        """
        try:
            stats = await asyncio.to_thread(
                self.share_float_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )

            # 单位转换和格式化
            stats['total_float_share_yi'] = round(stats['total_float_share'] / 100000000, 2)  # 股 -> 亿股
            stats['avg_float_ratio_percent'] = round(stats['avg_float_ratio'] * 100, 2)  # 比例 -> 百分比
            stats['max_float_ratio_percent'] = round(stats['max_float_ratio'] * 100, 2)

            return stats

        except Exception as e:
            logger.error(f"获取限售股解禁统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Dict:
        """
        获取最新的限售股解禁数据

        Args:
            ts_code: 股票代码

        Returns:
            最新数据字典
        """
        try:
            # 获取最新解禁日期
            latest_date = await asyncio.to_thread(
                self.share_float_repo.get_latest_float_date,
                ts_code=ts_code
            )

            if not latest_date:
                return {
                    "latest_date": None,
                    "items": []
                }

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.share_float_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=100
            )

            # 格式化数据
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('float_date'):
                    item['float_date'] = self._format_date(item['float_date'])
                if item.get('float_share') is not None:
                    item['float_share'] = round(item['float_share'], 2)
                if item.get('float_ratio') is not None:
                    item['float_ratio'] = round(item['float_ratio'], 4)

            return {
                "latest_date": self._format_date(latest_date),
                "items": items
            }

        except Exception as e:
            logger.error(f"获取最新限售股解禁数据失败: {e}")
            raise

    async def get_suggested_start_date(self) -> Optional[str]:
        """
        计算增量同步的建议起始日期（YYYYMMDD）。

        逻辑：
          候选起始 = 今天 - incremental_default_days（从 sync_configs 读取，默认 90 天）
          上次结束 = sync_history 中最近一次增量成功的 data_end_date
          实际起始 = min(候选起始, 上次结束)，即取两者中更早的，保证数据连续不遗漏
        """
        from app.repositories.sync_config_repository import SyncConfigRepository

        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'share_float')
        default_days = (cfg.get('incremental_default_days') or 90) if cfg else 90

        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')

        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'share_float', 'incremental'
        )

        if last_end and last_end < candidate:
            suggested = last_end
            logger.debug(f"[share_float] 建议起始={suggested}（上次结束={last_end} < 候选={candidate}）")
        else:
            suggested = candidate
            logger.debug(f"[share_float] 建议起始={suggested}（候选={candidate}，上次结束={last_end}）")

        return suggested

    async def sync_share_float(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        float_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """
        增量同步限售股解禁数据。

        当 start_date 存在且 sync_strategy 为日期切片策略时（by_month/by_week/by_date），
        按切片逐段请求并支持每段翻页（api_limit）。
        否则（无 start_date 或 by_ts_code 等策略）执行单次全量请求。

        Args:
            ts_code: 股票代码（by_ts_code 策略时使用）
            ann_date: 公告日期 YYYYMMDD
            float_date: 解禁日期 YYYYMMDD
            start_date: 时间范围起始 YYYYMMDD（by_date/by_month/by_week 策略时使用）
            end_date: 时间范围结束 YYYYMMDD
            sync_strategy: 同步策略（from sync_configs.incremental_sync_strategy）
        """
        effective_end = end_date or datetime.now().strftime('%Y%m%d')

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create,
            'share_float', 'incremental', sync_strategy, start_date,
        )

        try:
            logger.info(
                f"开始增量同步限售股解禁: strategy={sync_strategy} "
                f"ts_code={ts_code} start={start_date} end={end_date}"
            )

            from app.repositories.sync_config_repository import SyncConfigRepository
            cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'share_float')
            api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000

            provider = self._get_provider(max_requests_per_minute)
            all_dfs = []

            # by_date_range：按用户传入的整段时间请求（不切片），只翻页
            # by_month/by_week/by_date：切片后每段翻页
            date_slice_strategies = {'by_month', 'by_week', 'by_date'}

            MAX_OFFSET = 90000  # Tushare offset 上限约 100000

            if start_date and sync_strategy == 'by_date_range':
                # 整段请求 + 翻页
                logger.info(f"[share_float] 增量按时间段 {start_date}~{effective_end}，api_limit={api_limit}")
                offset = 0
                while True:
                    if offset > MAX_OFFSET:
                        logger.warning(f"[share_float] offset={offset} 超过上限 {MAX_OFFSET}，停止翻页")
                        break
                    df = await asyncio.to_thread(
                        provider.get_share_float,
                        start_date=start_date, end_date=effective_end,
                        limit=api_limit, offset=offset,
                    )
                    if df is None or df.empty:
                        break
                    raw_count = len(df)
                    all_dfs.append(df)
                    if raw_count < api_limit:
                        break
                    offset += api_limit
                    logger.info(f"[share_float] 触发分页（原始={raw_count} >= {api_limit}），offset={offset}")

            elif start_date and sync_strategy in date_slice_strategies:
                # 切片请求 + 每段翻页（兼容历史配置）
                segments = self._generate_segments(sync_strategy, start_date, effective_end)
                logger.info(f"[share_float] 增量切片 strategy={sync_strategy}，共 {len(segments)} 个片段，api_limit={api_limit}")
                for ms, me in segments:
                    offset = 0
                    while True:
                        if offset > MAX_OFFSET:
                            logger.warning(f"[share_float] {ms}~{me} offset={offset} 超过上限 {MAX_OFFSET}，停止翻页")
                            break
                        df = await asyncio.to_thread(
                            provider.get_share_float,
                            start_date=ms, end_date=me,
                            limit=api_limit, offset=offset,
                        )
                        if df is None or df.empty:
                            break
                        raw_count = len(df)
                        all_dfs.append(df)
                        if raw_count < api_limit:
                            break
                        offset += api_limit
                        logger.info(f"[share_float] {ms}~{me} 触发分页（原始={raw_count} >= {api_limit}），offset={offset}")

            else:
                # 单次请求：不传日期（取最新）或按 ts_code / ann_date 查询
                df = await asyncio.to_thread(
                    provider.get_share_float,
                    ts_code=ts_code,
                    ann_date=ann_date,
                    float_date=float_date,
                    start_date=start_date,
                    end_date=end_date,
                )
                if df is not None and not df.empty:
                    all_dfs.append(df)

            if not all_dfs:
                logger.warning("[share_float] 增量同步：未获取到数据")
                await asyncio.to_thread(self.sync_history_repo.complete, history_id, 'success', 0, None, None)
                return {"status": "success", "records": 0, "message": "未获取到数据"}

            # 合并所有片段数据
            combined = pd.concat(all_dfs, ignore_index=True) if len(all_dfs) > 1 else all_dfs[0]
            logger.info(f"[share_float] 获取到 {len(combined)} 条原始数据（{len(all_dfs)} 个片段）")
            combined = self._validate_and_clean_data(combined)

            # 从实际数据中取最大日期作为 data_end_date
            actual_end_date = None
            date_col = next((c for c in ('float_date', 'ann_date') if c in combined.columns), None)
            if date_col:
                max_val = combined[date_col].dropna().max()
                if max_val and str(max_val).strip():
                    actual_end_date = str(max_val).replace('-', '')[:8]

            records = await asyncio.to_thread(self.share_float_repo.bulk_upsert, combined)
            logger.info(f"[share_float] 增量同步完成，入库 {records} 条，实际数据最大日期={actual_end_date}")

            await asyncio.to_thread(self.sync_history_repo.complete, history_id, 'success', records, actual_end_date, None)

            return {
                "status": "success",
                "records": records,
                "data_end_date": actual_end_date,
                "message": f"成功同步 {records} 条数据",
            }

        except Exception as e:
            error_msg = f"增量同步限售股解禁失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            await asyncio.to_thread(self.sync_history_repo.complete, history_id, 'failure', 0, None, str(e))
            return {"status": "error", "records": 0, "error": error_msg}

    def _get_provider(self, max_requests_per_minute: Optional[int] = None):
        """获取Tushare数据提供者（惰性初始化，按 rpm 值缓存）

        Args:
            max_requests_per_minute: 覆盖全局限速配置。
                None  = 使用全局设置（从 config 表读取）
                0     = 不限速
                正整数 = 按此值限速
        """
        cache_key = f'_provider_{max_requests_per_minute}'
        cached = getattr(self, cache_key, None)
        if cached is not None:
            return cached

        if max_requests_per_minute is not None:
            effective_rpm = max_requests_per_minute
        else:
            effective_rpm = 0
            try:
                from app.repositories.config_repository import ConfigRepository
                raw = ConfigRepository().get_config_value("max_requests_per_minute")
                if raw is not None:
                    effective_rpm = int(raw)
            except Exception:
                pass

        provider = self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN,
            max_requests_per_minute=effective_rpm,
        )
        setattr(self, cache_key, provider)
        return provider

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        if df is None or df.empty:
            return df

        # 复制数据，避免修改原始 DataFrame
        df = df.copy()

        # 必需字段检查
        required_cols = ['ts_code', 'ann_date', 'float_date', 'holder_name']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        # 删除重复记录
        original_count = len(df)
        df = df.drop_duplicates(subset=['ts_code', 'ann_date', 'float_date', 'holder_name'])
        if len(df) < original_count:
            logger.warning(f"删除了 {original_count - len(df)} 条重复记录")

        # 删除 NaN 值
        df = df.dropna(subset=required_cols)

        # 数据类型转换
        if 'float_share' in df.columns:
            df['float_share'] = pd.to_numeric(df['float_share'], errors='coerce')

        if 'float_ratio' in df.columns:
            df['float_ratio'] = pd.to_numeric(df['float_ratio'], errors='coerce')

        logger.info(f"数据验证完成，有效记录数: {len(df)}")

        return df

    def _format_date(self, date_str: str) -> str:
        """
        格式化日期：YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: YYYYMMDD 格式的日期字符串

        Returns:
            YYYY-MM-DD 格式的日期字符串
        """
        if not date_str or len(date_str) != 8:
            return date_str

        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except Exception:
            return date_str
