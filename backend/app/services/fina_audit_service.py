"""
财务审计意见数据服务

Author: Claude
Date: 2026-03-22
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from loguru import logger
import pandas as pd

from app.repositories.fina_audit_repository import FinaAuditRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class FinaAuditService:
    """财务审计意见数据服务"""

    def __init__(self):
        self.fina_audit_repo = FinaAuditRepository()
        self.provider_factory = DataProviderFactory()
        self.sync_history_repo = SyncHistoryRepository()

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'fina_audit')
        default_days = (cfg.get('incremental_default_days') or 90) if cfg else 90
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'fina_audit', 'incremental'
        )
        return last_end if (last_end and last_end < candidate) else candidate

    async def sync_incremental(self, start_date=None, end_date=None, sync_strategy=None, max_requests_per_minute=None) -> Dict:
        """
        增量同步财务审计意见数据（自动计算日期范围并记录 sync_history）。

        fina_audit 接口要求 ts_code 为必填参数，不能只传 start_date/end_date。
        遍历全部上市股票，逐只请求最近 N 天内的数据。
        """
        from app.repositories.stock_basic_repository import StockBasicRepository

        if start_date is None:
            start_date = await self.get_suggested_start_date()
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        logger.info(f"[fina_audit] 增量同步 start_date={start_date} end_date={end_date}")

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create, 'fina_audit', 'incremental', sync_strategy or 'by_ts_code', start_date,
        )
        try:
            all_ts_codes = await asyncio.to_thread(
                StockBasicRepository().get_listed_ts_codes, status='L'
            )
            logger.info(f"[fina_audit] 增量同步 {len(all_ts_codes)} 只股票 {start_date}~{end_date}")

            total_records = 0
            errors = 0
            sem = asyncio.Semaphore(5)

            async def sync_one(ts_code: str):
                async with sem:
                    try:
                        result = await self.sync_fina_audit(
                            ts_code=ts_code, start_date=start_date, end_date=end_date
                        )
                        return result.get('records', 0), None
                    except Exception as e:
                        return 0, str(e)

            BATCH_SIZE = 50
            for batch_start in range(0, len(all_ts_codes), BATCH_SIZE):
                batch = all_ts_codes[batch_start:batch_start + BATCH_SIZE]
                results = await asyncio.gather(*[sync_one(c) for c in batch])
                for records, err in results:
                    if err:
                        errors += 1
                    else:
                        total_records += records

                done = min(batch_start + BATCH_SIZE, len(all_ts_codes))
                logger.info(f"[fina_audit] 增量进度: {done}/{len(all_ts_codes)} 入库={total_records} 失败={errors}")

            result = {
                "status": "success",
                "records": total_records,
                "message": f"增量同步完成 {total_records} 条（{len(all_ts_codes)} 只股票，失败 {errors}）"
            }
            await asyncio.to_thread(
                self.sync_history_repo.complete, history_id, 'success', total_records, end_date, None,
            )
            return result
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete, history_id, 'failure', 0, None, str(e),
            )
            raise

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def get_fina_audit_data(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取财务审计意见数据

        Args:
            ts_code: 股票代码
            ann_date: 公告日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            period: 报告期 YYYYMMDD
            limit: 限制返回记录数
            offset: 偏移量

        Returns:
            包含数据列表和统计信息的字典
        """
        try:
            effective_start = start_date or ann_date
            effective_end = end_date or period

            total, items, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.fina_audit_repo.get_total_count,
                    start_date=effective_start,
                    end_date=effective_end,
                    ts_code=ts_code
                ),
                asyncio.to_thread(
                    self.fina_audit_repo.get_by_date_range,
                    start_date=effective_start,
                    end_date=effective_end,
                    ts_code=ts_code,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.fina_audit_repo.get_statistics,
                    start_date=effective_start,
                    end_date=effective_end
                )
            )

            return {
                "items": items,
                "total": total,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取财务审计意见数据失败: {e}")
            raise

    async def sync_fina_audit(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> Dict:
        """
        同步财务审计意见数据

        Args:
            ts_code: 股票代码
            ann_date: 公告日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            period: 报告期 YYYYMMDD

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步财务审计意见数据: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 从 Tushare 获取数据
            df = await asyncio.to_thread(
                provider.get_fina_audit,
                ts_code=ts_code,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                period=period
            )

            if df is None or df.empty:
                logger.warning("未获取到财务审计意见数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.fina_audit_repo.bulk_upsert,
                df
            )

            logger.info(f"✓ 财务审计意见数据同步成功: {records} 条记录")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条记录"
            }

        except Exception as e:
            logger.error(f"同步财务审计意见数据失败: {e}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        # 确保必需字段存在
        required_fields = ['ts_code', 'ann_date', 'end_date']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 移除完全重复的行
        df = df.drop_duplicates(subset=['ts_code', 'ann_date', 'end_date'], keep='first')

        # 确保日期格式正确（移除任何非数字字符）
        if 'ann_date' in df.columns:
            df['ann_date'] = df['ann_date'].astype(str).str.replace(r'\D', '', regex=True)

        if 'end_date' in df.columns:
            df['end_date'] = df['end_date'].astype(str).str.replace(r'\D', '', regex=True)

        # 处理数值字段
        if 'audit_fees' in df.columns:
            df['audit_fees'] = pd.to_numeric(df['audit_fees'], errors='coerce')

        logger.debug(f"数据清洗完成，剩余 {len(df)} 条记录")
        return df

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        update_state_fn=None,
        concurrency: int = 5
    ) -> Dict:
        """
        逐只股票全量同步财务审计意见历史数据（5 并发，Redis Set 续继）

        fina_audit 接口要求 ts_code 为必填，不支持全市场拉取，
        必须按 ts_code 逐只请求。
        """
        from app.repositories.stock_basic_repository import StockBasicRepository

        PROGRESS_KEY = "sync:fina_audit:full_history:progress"
        CONCURRENCY = max(1, concurrency)
        BATCH_SIZE = 50

        all_ts_codes = StockBasicRepository().get_listed_ts_codes(status='L')
        total = len(all_ts_codes)
        logger.info(f"财务审计意见全量同步: 共 {total} 只上市股票，start_date={start_date or '20090101'}")

        try:
            completed_raw = redis_client.smembers(PROGRESS_KEY)
            completed = {p.decode() if isinstance(p, bytes) else p for p in completed_raw}
        except Exception:
            completed = set()

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
                    result = await self.sync_fina_audit(
                        ts_code=ts_code,
                        start_date=start_date
                    )
                    if result.get('status') == 'error':
                        error_count += 1
                        return
                    total_records += result.get('records', 0)
                    redis_client.sadd(PROGRESS_KEY, ts_code)
                except Exception as e:
                    logger.error(f"✗ 财务审计意见 ts_code={ts_code} 同步失败: {e}")
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
            logger.info(f"[全量财务审计意见] 进度: {done}/{total} ({round(done/total*100,1)}%) 入库={total_records} 失败={error_count}")

        try:
            final_done = len(redis_client.smembers(PROGRESS_KEY))
            if final_done >= total:
                redis_client.delete(PROGRESS_KEY)
                logger.info("[全量财务审计意见] ✅ 全量同步完成，进度已清除")
        except Exception:
            pass

        return {
            "status": "success",
            "records": total_records,
            "total": total,
            "errors": error_count,
            "message": f"同步完成 {total - error_count} 只，入库 {total_records} 条，失败 {error_count} 只"
        }

    async def get_latest_audit(self, ts_code: str) -> Optional[Dict]:
        """
        获取指定股票的最新审计意见

        Args:
            ts_code: 股票代码

        Returns:
            最新审计意见，如果不存在则返回 None
        """
        try:
            result = await asyncio.to_thread(
                self.fina_audit_repo.get_latest_by_ts_code,
                ts_code
            )
            return result
        except Exception as e:
            logger.error(f"获取最新审计意见失败: {e}")
            raise
