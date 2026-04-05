"""
利润表数据Service

管理利润表数据的业务逻辑
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict
from loguru import logger
import pandas as pd

from app.repositories.income_repository import IncomeRepository
from core.src.providers import DataProviderFactory

# 全量同步 Redis key / 并发数

class IncomeService:
    """利润表数据服务"""

    def __init__(self):
        self.income_repo = IncomeRepository()
        self.provider_factory = DataProviderFactory()

    async def get_income_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        查询利润表数据

        Args:
            start_date: 开始日期（报告期），格式：YYYY-MM-DD
            end_date: 结束日期（报告期），格式：YYYY-MM-DD
            ts_code: 股票代码
            report_type: 报告类型（1-12）
            comp_type: 公司类型（1-4）
            limit: 限制返回记录数

        Returns:
            包含数据列表和总数的字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 查询总数
            total = await asyncio.to_thread(
                self.income_repo.get_record_count,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                report_type=report_type,
                comp_type=comp_type
            )

            # 查询数据（带分页）
            items = await asyncio.to_thread(
                self.income_repo.get_by_date_range_with_offset,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                report_type=report_type,
                comp_type=comp_type,
                limit=limit,
                offset=offset
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
                    'total_revenue', 'revenue', 'oper_cost',
                    'sell_exp', 'admin_exp', 'fin_exp', 'rd_exp',
                    'operate_profit', 'total_profit', 'income_tax',
                    'n_income', 'n_income_attr_p', 'minority_gain',
                    'ebit', 'ebitda'
                ]
                for field in amount_fields:
                    if item.get(field) is not None:
                        item[field] = round(item[field] / 10000, 2)

            return {
                'items': items,
                'total': total
            }

        except Exception as e:
            logger.error(f"查询利润表数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期（报告期），格式：YYYY-MM-DD
            end_date: 结束日期（报告期），格式：YYYY-MM-DD
            ts_code: 股票代码
            report_type: 报告类型

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 获取统计
            statistics = await asyncio.to_thread(
                self.income_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                report_type=report_type
            )

            # 金额单位转换：元 -> 万元
            amount_fields = [
                'avg_revenue', 'avg_net_income', 'avg_income_attr_p',
                'sum_revenue', 'sum_net_income',
                'max_revenue', 'max_net_income'
            ]
            for field in amount_fields:
                if field in statistics and statistics[field] is not None:
                    statistics[field] = round(statistics[field] / 10000, 2)

            return statistics

        except Exception as e:
            logger.error(f"获取利润表统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Optional[Dict]:
        """
        获取最新利润表数据

        Args:
            ts_code: 股票代码

        Returns:
            最新利润表记录
        """
        try:
            latest_date = await asyncio.to_thread(
                self.income_repo.get_latest_end_date,
                ts_code=ts_code
            )

            if not latest_date:
                return None

            items = await asyncio.to_thread(
                self.income_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=1
            )

            if items:
                item = items[0]
                # 日期格式转换
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('f_ann_date'):
                    item['f_ann_date'] = self._format_date(item['f_ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])

                # 金额单位转换
                amount_fields = [
                    'total_revenue', 'revenue', 'oper_cost',
                    'sell_exp', 'admin_exp', 'fin_exp', 'rd_exp',
                    'operate_profit', 'total_profit', 'income_tax',
                    'n_income', 'n_income_attr_p', 'minority_gain',
                    'ebit', 'ebitda'
                ]
                for field in amount_fields:
                    if item.get(field) is not None:
                        item[field] = round(item[field] / 10000, 2)

                return item

            return None

        except Exception as e:
            logger.error(f"获取最新利润表数据失败: {e}")
            raise

    async def sync_income(
        self,
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> Dict:
        """
        同步利润表数据

        Args:
            ts_code: 股票代码
            period: 报告期（YYYYMMDD或YYYYQQ格式）
            start_date: 开始日期
            end_date: 结束日期
            report_type: 报告类型

        Returns:
            同步结果字典
        """
        try:
            # 1. 从Tushare获取数据
            provider = self._get_provider()

            logger.info(f"开始从Tushare获取利润表数据: ts_code={ts_code}, period={period}, "
                       f"start_date={start_date}, end_date={end_date}")

            df = await asyncio.to_thread(
                provider.get_income,
                ts_code=ts_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                report_type=report_type
            )

            if df is None or df.empty:
                logger.warning("未获取到利润表数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.income_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条利润表数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条记录"
            }

        except Exception as e:
            logger.error(f"同步利润表数据失败: {e}")
            raise

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        update_state_fn=None
    ) -> Dict:
        """
        逐只股票全量同步利润表历史数据（5 并发，Redis Set 续继）

        按 ts_code 逐只调用 income_vip，每只股票数据量极少，彻底避免 Tushare
        单次返回上限导致的数据截断。Redis Set 记录已完成 ts_code，中断后自动续继。

        Args:
            redis_client: Redis 客户端，用于进度续继
            start_date: 起始日期 YYYYMMDD，不传则使用 '20090101'
            update_state_fn: Celery self.update_state 回调，用于上报进度
        """
        from app.repositories.stock_basic_repository import StockBasicRepository

        PROGRESS_KEY = "sync:income:full_history:progress"
        CONCURRENCY = 5
        BATCH_SIZE = 50
        effective_start = start_date or '20090101'
        today = datetime.now().strftime("%Y%m%d")

        all_ts_codes = StockBasicRepository().get_listed_ts_codes(status='L')
        total = len(all_ts_codes)
        logger.info(f"[全量利润表] 共 {total} 只上市股票，start_date={effective_start}")

        completed_set = redis_client.smembers(PROGRESS_KEY)
        completed_set = {v.decode() if isinstance(v, bytes) else v for v in completed_set}
        logger.info(f"[全量利润表] 已完成 {len(completed_set)} 只，剩余 {total - len(completed_set)} 只")

        pending = [c for c in all_ts_codes if c not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        sem = asyncio.Semaphore(CONCURRENCY)

        async def sync_one(ts_code: str):
            nonlocal success_count, error_count
            async with sem:
                try:
                    result = await self.sync_income(
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
                    logger.error(f"[全量利润表] ts_code={ts_code} 失败: {e}")
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
            logger.info(f"[全量利润表] 进度: {done}/{total} ({round(done/total*100,1)}%) 成功={success_count} 失败={error_count}")

        final_done = len(redis_client.smembers(PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(PROGRESS_KEY)
            logger.info("[全量利润表] ✅ 全量同步完成，进度已清除")

        return {
            "status": "success", "total": total,
            "success": success_count, "skipped": skip_count, "errors": error_count,
            "message": f"同步完成 {success_count} 只，跳过 {skip_count} 只，失败 {error_count} 只"
        }

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        if df is None or df.empty:
            return df

        # 确保必需字段存在
        required_fields = ['ts_code', 'end_date', 'report_type']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 删除关键字段为空的记录
        df = df.dropna(subset=required_fields)

        # 日期格式标准化（确保为YYYYMMDD格式）
        date_fields = ['ann_date', 'f_ann_date', 'end_date']
        for field in date_fields:
            if field in df.columns:
                df[field] = df[field].astype(str).str.replace('-', '')

        logger.info(f"数据验证完成，有效记录数: {len(df)}")

        return df

    def _format_date(self, date_str: str) -> str:
        """
        格式化日期：YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: YYYYMMDD格式的日期字符串

        Returns:
            YYYY-MM-DD格式的日期字符串
        """
        if not date_str or len(date_str) != 8:
            return date_str

        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
