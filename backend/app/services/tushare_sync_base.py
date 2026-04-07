"""
Tushare 通用同步基类

将全量同步（by_ts_code / by_date_range）和增量同步的通用逻辑抽象为可复用的方法。
子类只需传入 fetch_fn / upsert_fn / clean_fn 即可，无需重复实现翻页、切片、Redis 续继等逻辑。

继承链：TushareSyncBase → BaseSyncService（提供 _get_provider）
"""

import asyncio
import traceback
from datetime import datetime, timedelta, date
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger

from app.services.extended_sync.base_sync_service import BaseSyncService


class TushareSyncBase(BaseSyncService):
    """
    Tushare 数据同步通用基类。

    提供：
      - _generate_months / _generate_weeks / _generate_dates / _generate_segments
      - run_full_sync     — 全量同步入口（分发到 by_ts_code 或 by_date_range）
      - run_incremental_sync — 增量同步入口（含切片、翻页、sync_history 记录）

    子类需提供：
      - TABLE_KEY（用于日志前缀，可选）
      - sync_history_repo（通过 getattr 可选调用，缺失时跳过 sync_history 记录）
    """

    # Tushare offset 约 100,000 触发通用错误，留 10% 安全余量
    MAX_OFFSET = 90_000

    # ------------------------------------------------------------------
    # 日期切片工具
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_months(start_date: str, end_date: str) -> List[Tuple[str, str]]:
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
    def _generate_weeks(start_date: str, end_date: str) -> List[Tuple[str, str]]:
        """将日期范围切分为 7 天窗口片段，每片返回 (week_start, week_end)，均为 YYYYMMDD。"""
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
    def _generate_dates(start_date: str, end_date: str) -> List[Tuple[str, str]]:
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

    def _generate_segments(self, strategy: str, start_date: str, end_date: str) -> List[Tuple[str, str]]:
        """根据策略生成切片片段列表。"""
        if strategy == 'by_week':
            return self._generate_weeks(start_date, end_date)
        elif strategy == 'by_date':
            return self._generate_dates(start_date, end_date)
        else:  # by_month（默认）
            return self._generate_months(start_date, end_date)

    # ------------------------------------------------------------------
    # 全量同步入口
    # ------------------------------------------------------------------

    async def run_full_sync(
        self,
        redis_client,
        fetch_fn: Callable,
        upsert_fn: Callable,
        clean_fn: Optional[Callable],
        progress_key: str,
        strategy: str = 'by_month',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        full_history_start: str = '20050101',
        concurrency: int = 5,
        api_limit: int = 6000,
        max_requests_per_minute: int = 0,
        update_state_fn: Optional[Callable] = None,
        fetch_kwargs: Optional[Dict] = None,
        table_key: str = '',
    ) -> Dict:
        """
        全量同步入口，根据 strategy 分发到相应实现。

        Args:
            redis_client:           Redis 客户端（用于续继进度 Set）
            fetch_fn:               同步数据获取函数（Tushare provider 方法），签名见下方说明
            upsert_fn:              同步数据写入函数（Repository.bulk_upsert），签名：fn(df) -> int
            clean_fn:               数据清洗函数，签名：fn(df) -> df；为 None 时跳过清洗
            progress_key:           Redis Set key，如 'sync:share_float:full_history:progress'
            strategy:               切片策略：'by_month'|'by_week'|'by_date'|'by_ts_code'
            start_date:             全量同步起始日期 YYYYMMDD；None 时使用 full_history_start
            end_date:               全量同步截止日期 YYYYMMDD；None 时使用今日
            full_history_start:     strategy=by_ts_code 时的默认历史起始日期
            concurrency:            并发数
            api_limit:              单次请求上限（用于分页判断）
            max_requests_per_minute: Tushare 限速（0=不限速）
            update_state_fn:        Celery update_state 回调，可选
            fetch_kwargs:           传给 fetch_fn 的额外固定参数（如 content_type='I'）
            table_key:              仅用于日志前缀

        fetch_fn 调用签名约定：
          - by_ts_code：fetch_fn(ts_code=ts_code, start_date=..., end_date=...,
                                 limit=api_limit, offset=offset, **fetch_kwargs)
          - by_date_range：fetch_fn(start_date=ms, end_date=me,
                                    limit=api_limit, offset=offset, **fetch_kwargs)

        Returns:
            {"status", "total", "success", "skipped", "errors", "records", "message"}
        """
        fetch_kwargs = fetch_kwargs or {}
        if strategy == 'by_ts_code':
            return await self._full_sync_by_ts_code(
                redis_client=redis_client,
                fetch_fn=fetch_fn,
                upsert_fn=upsert_fn,
                clean_fn=clean_fn,
                progress_key=progress_key,
                start_date=start_date,
                full_history_start=full_history_start,
                concurrency=concurrency,
                api_limit=api_limit,
                max_requests_per_minute=max_requests_per_minute,
                update_state_fn=update_state_fn,
                fetch_kwargs=fetch_kwargs,
                table_key=table_key,
            )
        return await self._full_sync_by_date_range(
            redis_client=redis_client,
            fetch_fn=fetch_fn,
            upsert_fn=upsert_fn,
            clean_fn=clean_fn,
            progress_key=progress_key,
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            full_history_start=full_history_start,
            concurrency=concurrency,
            api_limit=api_limit,
            max_requests_per_minute=max_requests_per_minute,
            update_state_fn=update_state_fn,
            fetch_kwargs=fetch_kwargs,
            table_key=table_key,
        )

    # ------------------------------------------------------------------
    # 全量同步：逐只股票
    # ------------------------------------------------------------------

    async def _full_sync_by_ts_code(
        self,
        redis_client,
        fetch_fn: Callable,
        upsert_fn: Callable,
        clean_fn: Optional[Callable],
        progress_key: str,
        start_date: Optional[str],
        full_history_start: str,
        concurrency: int,
        api_limit: int,
        max_requests_per_minute: int,
        update_state_fn: Optional[Callable],
        fetch_kwargs: Dict,
        table_key: str,
    ) -> Dict:
        """逐只股票全量同步（支持 Redis 续继、翻页）"""
        from app.repositories.stock_basic_repository import StockBasicRepository

        tag = f'[全量{table_key}]' if table_key else '[全量by_ts_code]'
        all_ts_codes = await asyncio.to_thread(StockBasicRepository().get_listed_ts_codes, status='L')
        total = len(all_ts_codes)

        completed_set = redis_client.smembers(progress_key)
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        pending = [c for c in all_ts_codes if c not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        total_records = 0

        effective_start = start_date or full_history_start
        today = datetime.now().strftime('%Y%m%d')
        sem = asyncio.Semaphore(max(1, concurrency))
        MAX_OFFSET = self.MAX_OFFSET

        logger.info(f"{tag} 策略=by_ts_code api_limit={api_limit} 共 {total} 只 已完成={skip_count}")

        async def sync_one(ts_code: str):
            async with sem:
                try:
                    records = 0
                    offset = 0
                    while True:
                        if offset >= MAX_OFFSET:
                            logger.warning(f"{tag} {ts_code} offset={offset} 达上限，停止翻页")
                            break
                        df = await asyncio.to_thread(
                            fetch_fn,
                            ts_code=ts_code,
                            start_date=effective_start,
                            end_date=today,
                            limit=api_limit,
                            offset=offset,
                            **fetch_kwargs,
                        )
                        if df is None or df.empty:
                            break
                        raw_count = len(df)
                        if clean_fn is not None:
                            df = clean_fn(df)
                        if df is not None and not df.empty:
                            records += await asyncio.to_thread(upsert_fn, df)
                        if raw_count < api_limit:
                            break
                        offset += api_limit
                        logger.info(f"{tag} {ts_code} 触发分页（原始={raw_count}>={api_limit}），offset={offset}")
                    return ts_code, True, records, None
                except Exception as e:
                    return ts_code, False, 0, str(e)

        BATCH_SIZE = 50
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start: batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_one(c) for c in batch])
            for ts_code, ok, records, err in results:
                if ok:
                    redis_client.sadd(progress_key, ts_code)
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
                    logger.error(f"{tag} {ts_code} 失败（下次续继）: {err}")
            done = skip_count + success_count
            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={
                    'current': done, 'total': total,
                    'percent': round(done / total * 100, 1) if total else 0,
                    'records': total_records, 'errors': error_count,
                })
            logger.info(
                f"{tag} 进度: {done}/{total} "
                f"({round(done / total * 100, 1) if total else 0}%) "
                f"入库={total_records} 失败={error_count}"
            )

        final_done = len(redis_client.smembers(progress_key))
        if final_done >= total:
            redis_client.delete(progress_key)
            logger.info(f"{tag} ✅ 全量同步完成（by_ts_code），进度已清除")

        return {
            "status": "success",
            "total": total,
            "success": success_count,
            "skipped": skip_count,
            "errors": error_count,
            "records": total_records,
            "message": (
                f"同步完成 {success_count} 只股票，"
                f"入库 {total_records} 条，失败 {error_count} 只"
            ),
        }

    # ------------------------------------------------------------------
    # 全量同步：按日期切片
    # ------------------------------------------------------------------

    async def _full_sync_by_date_range(
        self,
        redis_client,
        fetch_fn: Callable,
        upsert_fn: Callable,
        clean_fn: Optional[Callable],
        progress_key: str,
        strategy: str,
        start_date: Optional[str],
        end_date: Optional[str],
        full_history_start: str,
        concurrency: int,
        api_limit: int,
        max_requests_per_minute: int,
        update_state_fn: Optional[Callable],
        fetch_kwargs: Dict,
        table_key: str,
    ) -> Dict:
        """按日期切片全量同步（支持 Redis 续继、翻页）"""
        tag = f'[全量{table_key}]' if table_key else f'[全量{strategy}]'
        effective_start = start_date or full_history_start
        effective_end = end_date or datetime.now().strftime('%Y%m%d')
        segments = self._generate_segments(strategy, effective_start, effective_end)
        total = len(segments)

        completed_set = redis_client.smembers(progress_key)
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        pending = [(ms, me) for ms, me in segments if ms not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        total_records = 0

        sem = asyncio.Semaphore(max(1, concurrency))
        MAX_OFFSET = self.MAX_OFFSET

        logger.info(
            f"{tag} 策略={strategy} api_limit={api_limit} "
            f"共 {total} 个片段 已完成={skip_count}"
        )

        async def sync_segment(ms: str, me: str):
            async with sem:
                try:
                    records = 0
                    offset = 0
                    while True:
                        if offset >= MAX_OFFSET:
                            logger.warning(
                                f"{tag} {ms}~{me} offset={offset} 达上限 {MAX_OFFSET}，"
                                f"停止翻页（已入库 {records} 条）"
                            )
                            break
                        df = await asyncio.to_thread(
                            fetch_fn,
                            start_date=ms,
                            end_date=me,
                            limit=api_limit,
                            offset=offset,
                            **fetch_kwargs,
                        )
                        if df is None or df.empty:
                            break
                        raw_count = len(df)
                        if clean_fn is not None:
                            df = clean_fn(df)
                        if df is not None and not df.empty:
                            records += await asyncio.to_thread(upsert_fn, df)
                        if raw_count < api_limit:
                            break
                        offset += api_limit
                        logger.info(
                            f"{tag} {ms}~{me} 触发分页（原始={raw_count}>={api_limit}），offset={offset}"
                        )
                    return ms, me, True, records, None
                except Exception as e:
                    return ms, me, False, 0, str(e)

        BATCH_SIZE = max(1, concurrency)
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start: batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_segment(ms, me) for ms, me in batch])
            for ms, me, ok, records, err in results:
                if ok:
                    redis_client.sadd(progress_key, ms)
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
                    logger.error(f"{tag} {ms}~{me} 失败（下次续继）: {err}")
            done = skip_count + success_count
            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={
                    'current': done, 'total': total,
                    'percent': round(done / total * 100, 1) if total else 0,
                    'records': total_records, 'errors': error_count,
                })
            logger.info(
                f"{tag} 进度: {done}/{total} "
                f"({round(done / total * 100, 1) if total else 0}%) "
                f"入库={total_records} 失败={error_count}"
            )

        final_done = len(redis_client.smembers(progress_key))
        if final_done >= total:
            redis_client.delete(progress_key)
            logger.info(f"{tag} ✅ 全量同步完成（{strategy}），进度已清除")

        return {
            "status": "success",
            "total": total,
            "success": success_count,
            "skipped": skip_count,
            "errors": error_count,
            "records": total_records,
            "message": (
                f"同步完成 {success_count} 个片段（策略={strategy} limit={api_limit}），"
                f"入库 {total_records} 条，失败 {error_count} 个"
            ),
        }

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def run_incremental_sync(
        self,
        fetch_fn: Callable,
        upsert_fn: Callable,
        clean_fn: Optional[Callable],
        table_key: str,
        date_col: str,
        sync_strategy: Optional[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
        api_limit: int = 6000,
        extra_fetch_kwargs: Optional[Dict] = None,
    ) -> Dict:
        """
        通用增量同步。

        Args:
            fetch_fn:               同步数据获取函数（Tushare provider 方法）
            upsert_fn:              数据写入函数，签名：fn(df) -> int
            clean_fn:               数据清洗函数；为 None 时跳过清洗
            table_key:              sync_configs / sync_history 的表键，如 'share_float'
            date_col:               DataFrame 中用于确定 data_end_date 的日期列名
            sync_strategy:          同步策略字符串，来自 sync_configs.incremental_sync_strategy
            start_date:             增量同步起始日期 YYYYMMDD
            end_date:               增量同步截止日期 YYYYMMDD；None 时使用今日
            max_requests_per_minute: Tushare 限速
            api_limit:              单次请求上限
            extra_fetch_kwargs:     额外参数（ts_code / ann_date 等），仅在单次请求分支中传入

        Returns:
            {"status", "records", "data_end_date", "message"} 或
            {"status": "error", "records", "error"}
        """
        extra_fetch_kwargs = extra_fetch_kwargs or {}
        # effective_end 仅用于切片生成（必须有终点）；传给 fetch_fn 时用原始 end_date，
        # 保持 None 则让 Tushare 自行决定截止范围（不截断未来数据）
        effective_end = end_date or datetime.now().strftime('%Y%m%d')

        # 写 sync_history running 记录（可选）
        history_id = None
        sync_history_repo = getattr(self, 'sync_history_repo', None)
        if sync_history_repo is not None:
            history_id = await asyncio.to_thread(
                sync_history_repo.create,
                table_key, 'incremental', sync_strategy, start_date,
            )

        try:
            logger.info(
                f"开始增量同步 {table_key}: strategy={sync_strategy} "
                f"start={start_date} end={end_date or '(不限)'}"
            )

            all_dfs = []
            date_slice_strategies = {'by_month', 'by_week', 'by_date'}
            MAX_OFFSET = self.MAX_OFFSET

            if start_date and sync_strategy == 'by_ts_code':
                # 逐只股票请求，起始日期由调用方算好（回看天数/上次成功记录取较早者）
                from app.repositories.stock_basic_repository import StockBasicRepository
                all_ts_codes = await asyncio.to_thread(
                    StockBasicRepository().get_listed_ts_codes, status='L'
                )
                logger.info(
                    f"[{table_key}] 增量 by_ts_code：共 {len(all_ts_codes)} 只股票，"
                    f"start={start_date} end={end_date or '(不限)'} api_limit={api_limit}"
                )
                sem = asyncio.Semaphore(5)

                async def _fetch_one_ts(ts_code: str):
                    async with sem:
                        offset = 0
                        dfs = []
                        while True:
                            if offset >= MAX_OFFSET:
                                logger.warning(
                                    f"[{table_key}] {ts_code} offset={offset} 达上限，停止翻页"
                                )
                                break
                            df = await asyncio.to_thread(
                                fetch_fn,
                                ts_code=ts_code,
                                start_date=start_date,
                                end_date=end_date,   # 保持原始值，None 时不传截止日期
                                limit=api_limit,
                                offset=offset,
                            )
                            if df is None or df.empty:
                                break
                            raw_count = len(df)
                            dfs.append(df)
                            if raw_count < api_limit:
                                break
                            offset += api_limit
                        return dfs

                BATCH_SIZE = 50
                for batch_start in range(0, len(all_ts_codes), BATCH_SIZE):
                    batch = all_ts_codes[batch_start: batch_start + BATCH_SIZE]
                    batch_results = await asyncio.gather(*[_fetch_one_ts(c) for c in batch])
                    for dfs in batch_results:
                        all_dfs.extend(dfs)

            elif start_date and sync_strategy == 'by_date_range':
                # 整段请求 + 翻页
                logger.info(
                    f"[{table_key}] 增量按时间段 {start_date}~{end_date or '(不限)'}，api_limit={api_limit}"
                )
                offset = 0
                while True:
                    if offset >= MAX_OFFSET:
                        logger.warning(
                            f"[{table_key}] offset={offset} 达上限 {MAX_OFFSET}，停止翻页"
                        )
                        break
                    df = await asyncio.to_thread(
                        fetch_fn,
                        start_date=start_date,
                        end_date=end_date,           # 保持原始值，None 时不传截止日期
                        limit=api_limit,
                        offset=offset,
                    )
                    if df is None or df.empty:
                        break
                    raw_count = len(df)
                    all_dfs.append(df)
                    if raw_count < api_limit:
                        break
                    offset += api_limit
                    logger.info(
                        f"[{table_key}] 触发分页（原始={raw_count}>={api_limit}），offset={offset}"
                    )

            elif start_date and sync_strategy in date_slice_strategies:
                # 切片请求 + 每段翻页
                # 切片必须有终点，使用 effective_end（今日）；但每段的 end_date 由切片算法精确给出
                segments = self._generate_segments(sync_strategy, start_date, effective_end)
                logger.info(
                    f"[{table_key}] 增量切片 strategy={sync_strategy} "
                    f"共 {len(segments)} 个片段 api_limit={api_limit}"
                )
                for ms, me in segments:
                    offset = 0
                    while True:
                        if offset >= MAX_OFFSET:
                            logger.warning(
                                f"[{table_key}] {ms}~{me} offset={offset} 达上限 {MAX_OFFSET}，停止翻页"
                            )
                            break
                        df = await asyncio.to_thread(
                            fetch_fn,
                            start_date=ms,
                            end_date=me,             # 切片端点，始终有值
                            limit=api_limit,
                            offset=offset,
                        )
                        if df is None or df.empty:
                            break
                        raw_count = len(df)
                        all_dfs.append(df)
                        if raw_count < api_limit:
                            break
                        offset += api_limit
                        logger.info(
                            f"[{table_key}] {ms}~{me} 触发分页（原始={raw_count}>={api_limit}），offset={offset}"
                        )

            else:
                # 单次请求（不带日期，或按 ts_code / ann_date 等参数查询）
                # 只在单次分支传 extra_fetch_kwargs，切片分支不传（避免参数冲突）
                df = await asyncio.to_thread(
                    fetch_fn,
                    start_date=start_date,
                    end_date=end_date,
                    **extra_fetch_kwargs,
                )
                if df is not None and not df.empty:
                    all_dfs.append(df)

            if not all_dfs:
                logger.warning(f"[{table_key}] 增量同步：未获取到数据")
                if sync_history_repo is not None and history_id is not None:
                    await asyncio.to_thread(
                        sync_history_repo.complete, history_id, 'success', 0, None, None
                    )
                return {"status": "success", "records": 0, "message": "未获取到数据"}

            # 合并所有片段
            combined = (
                pd.concat(all_dfs, ignore_index=True) if len(all_dfs) > 1 else all_dfs[0]
            )
            logger.info(
                f"[{table_key}] 获取到 {len(combined)} 条原始数据（{len(all_dfs)} 个片段）"
            )

            # 清洗
            if clean_fn is not None:
                combined = clean_fn(combined)

            # 取 date_col 最大值作为 data_end_date
            actual_end_date = None
            if date_col and date_col in combined.columns:
                max_val = combined[date_col].dropna().max()
                if max_val and str(max_val).strip():
                    actual_end_date = str(max_val).replace('-', '')[:8]

            records = await asyncio.to_thread(upsert_fn, combined)
            logger.info(
                f"[{table_key}] 增量同步完成，入库 {records} 条，"
                f"实际数据最大日期={actual_end_date}"
            )

            if sync_history_repo is not None and history_id is not None:
                await asyncio.to_thread(
                    sync_history_repo.complete,
                    history_id, 'success', records, actual_end_date, None,
                )

            return {
                "status": "success",
                "records": records,
                "data_end_date": actual_end_date,
                "message": f"成功同步 {records} 条数据",
            }

        except Exception as e:
            error_msg = f"增量同步 {table_key} 失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            if sync_history_repo is not None and history_id is not None:
                await asyncio.to_thread(
                    sync_history_repo.complete, history_id, 'failure', 0, None, str(e)
                )
            return {"status": "error", "records": 0, "error": error_msg}
