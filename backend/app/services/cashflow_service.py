"""
现金流量表数据Service

管理现金流量表数据的业务逻辑
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
from loguru import logger
import pandas as pd

from app.repositories.cashflow_repository import CashflowRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class CashflowService:
    """现金流量表数据服务"""

    def __init__(self):
        self.cashflow_repo = CashflowRepository()
        self.provider_factory = DataProviderFactory()

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def sync_incremental(self) -> Dict:
        """
        增量同步现金流量表数据。

        从 sync_configs 读取 incremental_default_days（默认 90），
        计算最近公告期范围（start_date/end_date），拉取全市场数据。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'cashflow')
        default_days = (cfg.get('incremental_default_days') or 90) if cfg else 90

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')

        logger.info(f"[cashflow] 增量同步 start_date={start_date} end_date={end_date}（回看 {default_days} 天）")
        return await self.sync_cashflow(start_date=start_date, end_date=end_date)

    async def get_cashflow_data(
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
        查询现金流量表数据

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

            # 并发查询总数和数据
            total, items = await asyncio.gather(
                asyncio.to_thread(
                    self.cashflow_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    period=period_fmt,
                    report_type=report_type
                ),
                asyncio.to_thread(
                    self.cashflow_repo.get_by_date_range,
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
                    'net_profit', 'finan_exp',
                    'n_cashflow_act', 'c_fr_sale_sg', 'c_paid_goods_s', 'c_paid_to_for_empl', 'c_paid_for_taxes',
                    'n_cashflow_inv_act', 'c_disp_withdrwl_invest', 'c_pay_acq_const_fiolta',
                    'n_cash_flows_fnc_act', 'c_recp_borrow', 'c_prepay_amt_borr',
                    'n_incr_cash_cash_equ', 'c_cash_equ_beg_period', 'c_cash_equ_end_period',
                    'free_cashflow', 'im_net_cashflow_oper_act'
                ]
                for field in amount_fields:
                    if item.get(field) is not None:
                        item[field] = round(item[field] / 10000, 2)

            return {
                'items': items,
                'total': total
            }

        except Exception as e:
            logger.error(f"查询现金流量表数据失败: {e}")
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
                self.cashflow_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )

            # 金额单位转换：元 -> 万元
            amount_fields = [
                'avg_operating_cf', 'avg_free_cf', 'max_operating_cf', 'min_operating_cf'
            ]
            for field in amount_fields:
                if field in statistics and statistics[field] is not None:
                    statistics[field] = round(statistics[field] / 10000, 2)

            return statistics

        except Exception as e:
            logger.error(f"获取现金流量表统计信息失败: {e}")
            raise

    async def get_latest_data(
        self,
        ts_code: Optional[str] = None,
        limit: int = 10
    ) -> Dict:
        """
        获取最新的现金流量表数据

        Args:
            ts_code: 股票代码（可选）
            limit: 限制返回记录数

        Returns:
            数据字典
        """
        try:
            items = await asyncio.to_thread(
                self.cashflow_repo.get_latest,
                ts_code=ts_code,
                limit=limit
            )

            # 日期格式转换
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])

                # 金额单位转换：元 -> 万元
                amount_fields = [
                    'n_cashflow_act', 'n_cashflow_inv_act', 'n_cash_flows_fnc_act',
                    'free_cashflow', 'n_incr_cash_cash_equ'
                ]
                for field in amount_fields:
                    if item.get(field) is not None:
                        item[field] = round(item[field] / 10000, 2)

            return {
                'items': items,
                'total': len(items)
            }

        except Exception as e:
            logger.error(f"获取最新现金流量表数据失败: {e}")
            raise

    async def sync_cashflow(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> Dict:
        """
        同步现金流量表数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            period: 报告期，格式：YYYYMMDD
            report_type: 报告类型（1-12）

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步现金流量表数据: ts_code={ts_code}, period={period}, start_date={start_date}, end_date={end_date}")

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 从 Tushare 获取数据
            df = await asyncio.to_thread(
                provider.get_cashflow,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                period=period,
                report_type=report_type
            )

            if df is None or df.empty:
                logger.warning("没有获取到现金流量表数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "没有可同步的数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条现金流量表数据")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.cashflow_repo.bulk_upsert,
                df
            )

            logger.info(f"✓ 现金流量表数据同步完成: {records} 条记录")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条现金流量表数据"
            }

        except Exception as e:
            logger.error(f"同步现金流量表数据失败: {e}")
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
        逐只股票全量同步现金流量表历史数据（5 并发，Redis Set 续继）

        按 ts_code 逐只调用 cashflow_vip，每只股票数据量极少，彻底避免 Tushare
        单次返回上限导致的数据截断。Redis Set 记录已完成 ts_code，中断后自动续继。

        Args:
            redis_client: Redis 客户端，用于进度续继
            start_date: 起始日期 YYYYMMDD，不传则使用 '20090101'
            update_state_fn: Celery self.update_state 回调，用于上报进度
        """
        from app.repositories.stock_basic_repository import StockBasicRepository

        PROGRESS_KEY = "sync:cashflow:full_history:progress"
        CONCURRENCY = max(1, concurrency)
        BATCH_SIZE = 50
        effective_start = start_date or '20090101'
        today = datetime.now().strftime("%Y%m%d")

        all_ts_codes = StockBasicRepository().get_listed_ts_codes(status='L')
        total = len(all_ts_codes)
        logger.info(f"[全量现金流量表] 共 {total} 只上市股票，start_date={effective_start}")

        completed_set = redis_client.smembers(PROGRESS_KEY)
        completed_set = {v.decode() if isinstance(v, bytes) else v for v in completed_set}
        logger.info(f"[全量现金流量表] 已完成 {len(completed_set)} 只，剩余 {total - len(completed_set)} 只")

        pending = [c for c in all_ts_codes if c not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        total_records = 0
        sem = asyncio.Semaphore(CONCURRENCY)

        async def sync_one(ts_code: str):
            nonlocal success_count, error_count, total_records
            async with sem:
                try:
                    result = await self.sync_cashflow(
                        ts_code=ts_code,
                        start_date=effective_start,
                        end_date=today,
                        report_type='1'
                    )
                    if result.get("status") == "error":
                        error_count += 1
                        return
                    total_records += result.get("records", 0)
                    redis_client.sadd(PROGRESS_KEY, ts_code)
                    success_count += 1
                except Exception as e:
                    logger.error(f"[全量现金流量表] ts_code={ts_code} 失败: {e}")
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
            logger.info(f"[全量现金流量表] 进度: {done}/{total} ({round(done/total*100,1)}%) 成功={success_count} 失败={error_count}")

        final_done = len(redis_client.smembers(PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(PROGRESS_KEY)
            logger.info("[全量现金流量表] ✅ 全量同步完成，进度已清除")

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
        if df is None or df.empty:
            return df

        # 确保必需字段存在
        required_fields = ['ts_code', 'end_date', 'report_type']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 移除 ts_code, end_date, report_type 全为空的行
        df = df.dropna(subset=['ts_code', 'end_date', 'report_type'], how='all')

        # 填充空字符串为 None（避免 'nan' 字符串）
        df = df.where(pd.notnull(df), None)

        # 确保日期格式正确（YYYYMMDD）
        date_fields = ['ann_date', 'f_ann_date', 'end_date']
        for field in date_fields:
            if field in df.columns:
                df[field] = df[field].astype(str).str.replace('-', '').str.replace('.0', '')
                df[field] = df[field].replace('None', None).replace('nan', None).replace('', None)

        return df

    def _format_date(self, date_str: str) -> str:
        """
        格式化日期：YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: 日期字符串

        Returns:
            格式化后的日期
        """
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
