"""
资产负债表数据Service

管理资产负债表数据的业务逻辑
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
from loguru import logger
import pandas as pd

from app.repositories.balancesheet_repository import BalancesheetRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class BalancesheetService:
    """资产负债表数据服务"""

    def __init__(self):
        self.balancesheet_repo = BalancesheetRepository()
        self.provider_factory = DataProviderFactory()
        self.sync_history_repo = SyncHistoryRepository()

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'balancesheet')
        default_days = (cfg.get('incremental_default_days') or 90) if cfg else 90
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'balancesheet', 'incremental'
        )
        return last_end if (last_end and last_end < candidate) else candidate

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步（标准入口，自动计算日期范围并记录 sync_history）"""
        if start_date is None:
            start_date = await self.get_suggested_start_date()
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        logger.info(f"[balancesheet] 增量同步 start_date={start_date} end_date={end_date}")

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create,
            'balancesheet', 'incremental', sync_strategy or 'by_date_range', start_date,
        )

        try:
            result = await self.sync_balancesheet(start_date=start_date, end_date=end_date)
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'success', result.get('records', 0), end_date, None,
            )
            return result
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', 0, None, str(e),
            )
            raise

    async def get_balancesheet_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        查询资产负债表数据

        Args:
            start_date: 开始日期（公告日期），格式：YYYY-MM-DD
            end_date: 结束日期（公告日期），格式：YYYY-MM-DD
            ts_code: 股票代码
            period: 报告期，格式：YYYY-MM-DD
            report_type: 报告类型（1-12）
            limit: 限制返回记录数

        Returns:
            包含数据列表和总数的字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'
            period_fmt = period.replace('-', '') if period else None

            # 查询总数和数据（并发）
            total, items = await asyncio.gather(
                asyncio.to_thread(
                    self.balancesheet_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    period=period_fmt,
                    report_type=report_type
                ),
                asyncio.to_thread(
                    self.balancesheet_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    period=period_fmt,
                    report_type=report_type,
                    limit=limit,
                    offset=offset
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('f_ann_date'):
                    item['f_ann_date'] = self._format_date(item['f_ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])

                # 金额单位转换：元 -> 万元
                amount_fields = [
                    'total_share', 'cap_rese', 'undistr_porfit', 'surplus_rese',
                    'money_cap', 'total_cur_assets', 'total_nca', 'total_assets',
                    'total_cur_liab', 'total_ncl', 'total_liab',
                    'total_hldr_eqy_exc_min_int', 'total_hldr_eqy_inc_min_int',
                    'total_liab_hldr_eqy'
                ]
                for field in amount_fields:
                    if item.get(field) is not None:
                        item[field] = round(item[field] / 10000, 2)

            return {
                'items': items,
                'total': total
            }

        except Exception as e:
            logger.error(f"查询资产负债表数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期（公告日期），格式：YYYY-MM-DD
            end_date: 结束日期（公告日期），格式：YYYY-MM-DD
            ts_code: 股票代码

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 获取统计
            statistics = await asyncio.to_thread(
                self.balancesheet_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )

            # 金额单位转换：元 -> 万元
            amount_fields = [
                'avg_total_assets', 'avg_total_liab', 'avg_equity'
            ]
            for field in amount_fields:
                if field in statistics and statistics[field] is not None:
                    statistics[field] = round(statistics[field] / 10000, 2)

            return statistics

        except Exception as e:
            logger.error(f"获取资产负债表统计信息失败: {e}")
            raise

    async def get_latest_data(
        self,
        ts_code: Optional[str] = None,
        limit: int = 10
    ) -> Dict:
        """
        获取最新的资产负债表数据

        Args:
            ts_code: 股票代码（可选）
            limit: 限制返回记录数

        Returns:
            数据字典
        """
        try:
            # 获取最新公告日期
            latest_date = await asyncio.to_thread(
                self.balancesheet_repo.get_latest_ann_date,
                ts_code=ts_code
            )

            if not latest_date:
                return {'items': [], 'total': 0}

            # 查询最新日期的数据
            items = await asyncio.to_thread(
                self.balancesheet_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=limit
            )

            # 日期格式转换
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('f_ann_date'):
                    item['f_ann_date'] = self._format_date(item['f_ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])

            return {
                'items': items,
                'total': len(items)
            }

        except Exception as e:
            logger.error(f"获取最新资产负债表数据失败: {e}")
            raise

    async def sync_balancesheet(
        self,
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        report_type: str = '1',
        comp_type: Optional[str] = None
    ) -> Dict:
        """
        同步资产负债表数据

        Args:
            ts_code: 股票代码（可选）
            period: 报告期（YYYYMMDD格式，如 20231231表示年报）
            start_date: 开始日期（YYYYMMDD格式）
            end_date: 结束日期（YYYYMMDD格式）
            report_type: 报告类型（默认1-合并报表）
            comp_type: 公司类型（1一般工商业2银行3保险4证券）

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步资产负债表数据: ts_code={ts_code}, period={period}, "
                       f"start_date={start_date}, end_date={end_date}")

            # 1. 获取 Tushare Provider
            provider = await asyncio.to_thread(
                self._get_provider
            )

            # 2. 调用 Tushare API 获取数据
            df = await asyncio.to_thread(
                provider.get_balancesheet,
                ts_code=ts_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                report_type=report_type,
                comp_type=comp_type
            )

            if df is None or df.empty:
                logger.warning("未获取到资产负债表数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取了 {len(df)} 条资产负债表数据")

            # 3. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 4. 批量插入数据库（通过 Repository）
            records = await asyncio.to_thread(
                self.balancesheet_repo.bulk_upsert,
                df
            )

            # 5. 触发 value_metrics 增量重算（脏数据合批，由 Celery Beat 每 5 分钟 flush）
            try:
                from app.services.value_metrics import ValueMetricsTrigger
                if 'ts_code' in df.columns and records > 0:
                    dirty_codes = df['ts_code'].dropna().astype(str).unique().tolist()
                    ValueMetricsTrigger.mark_dirty(dirty_codes, source='balancesheet')
            except Exception as e:
                logger.debug(f"[balancesheet] 触发 value_metrics 重算失败（不影响主流程）: {e}")

            logger.info(f"成功同步 {records} 条资产负债表数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步资产负债表数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        update_state_fn=None,
        concurrency: int = 5
    ) -> Dict:
        """
        逐只股票全量同步资产负债表历史数据（5 并发，Redis Set 续继）

        按 ts_code 逐只调用 balancesheet_vip，每只股票数据量极少，彻底避免 Tushare
        单次返回上限导致的数据截断。Redis Set 记录已完成 ts_code，中断后自动续继。

        Args:
            redis_client: Redis 客户端，用于进度续继
            start_date: 起始日期 YYYYMMDD，不传则使用 '20090101'
            update_state_fn: Celery self.update_state 回调，用于上报进度
        """
        from app.repositories.stock_basic_repository import StockBasicRepository

        PROGRESS_KEY = "sync:balancesheet:full_history:progress"
        CONCURRENCY = max(1, concurrency)
        BATCH_SIZE = 50
        effective_start = start_date or '20090101'
        today = datetime.now().strftime("%Y%m%d")

        all_ts_codes = StockBasicRepository().get_listed_ts_codes(status='L')
        total = len(all_ts_codes)
        logger.info(f"[全量资产负债表] 共 {total} 只上市股票，start_date={effective_start}")

        completed_set = redis_client.smembers(PROGRESS_KEY)
        completed_set = {v.decode() if isinstance(v, bytes) else v for v in completed_set}
        logger.info(f"[全量资产负债表] 已完成 {len(completed_set)} 只，剩余 {total - len(completed_set)} 只")

        pending = [c for c in all_ts_codes if c not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        sem = asyncio.Semaphore(CONCURRENCY)

        async def sync_one(ts_code: str):
            nonlocal success_count, error_count
            async with sem:
                try:
                    result = await self.sync_balancesheet(
                        ts_code=ts_code,
                        start_date=effective_start,
                        end_date=today,
                        report_type='1'
                    )
                    if result.get("status") == "error":
                        error_count += 1
                        return
                    redis_client.sadd(PROGRESS_KEY, ts_code)
                    success_count += 1
                except Exception as e:
                    logger.error(f"[全量资产负债表] ts_code={ts_code} 失败: {e}")
                    error_count += 1

        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            await asyncio.gather(*[sync_one(c) for c in batch])
            done = skip_count + success_count + error_count
            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={
                    'current': done, 'total': total,
                    'percent': round(done / total * 100, 1),
                    'success': success_count, 'errors': error_count
                })
            logger.info(f"[全量资产负债表] 进度: {done}/{total} ({round(done/total*100,1)}%) 成功={success_count} 失败={error_count}")

        final_done = len(redis_client.smembers(PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(PROGRESS_KEY)
            logger.info("[全量资产负债表] ✅ 全量同步完成，进度已清除")

        return {
            "status": "success", "total": total,
            "success": success_count, "skipped": skip_count, "errors": error_count,
            "message": f"同步完成 {success_count} 只，跳过 {skip_count} 只，失败 {error_count} 只"
        }

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        # 1. 检查必需字段
        required_fields = ['ts_code', 'ann_date', 'end_date', 'report_type']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 2. 去除空值行（基于主键字段）
        df = df.dropna(subset=required_fields)

        # 3. 去重（基于主键）
        df = df.drop_duplicates(subset=['ts_code', 'ann_date', 'end_date', 'report_type'], keep='last')

        logger.info(f"数据清洗完成，剩余 {len(df)} 条有效数据")

        return df

    @staticmethod
    def _format_date(date_str: str) -> str:
        """
        日期格式转换：YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: YYYYMMDD 格式的日期字符串

        Returns:
            YYYY-MM-DD 格式的日期字符串
        """
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
