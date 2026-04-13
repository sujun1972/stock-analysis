"""
业绩预告数据Service

管理业绩预告数据的业务逻辑
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from app.repositories.forecast_repository import ForecastRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class ForecastService:
    """业绩预告数据服务"""

    def __init__(self):
        self.forecast_repo = ForecastRepository()
        self.provider_factory = DataProviderFactory()

    async def sync_incremental(self) -> Dict:
        """增量同步：从 sync_configs 读取回看天数，自动计算日期范围。"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'forecast')
        default_days = (cfg.get('incremental_default_days') or 90) if cfg else 90
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        logger.info(f"[forecast] 增量同步 start_date={start_date} end_date={end_date}（回看 {default_days} 天）")
        return await self.sync_forecast(start_date=start_date, end_date=end_date)

    async def get_forecast_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        type_: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        查询业绩预告数据

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            ts_code: 股票代码
            period: 报告期
            type_: 预告类型
            limit: 限制返回记录数

        Returns:
            包含数据列表和总数的字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'
            period_fmt = period.replace('-', '') if period else None

            # 并发查询数据和总数
            total, items = await asyncio.gather(
                asyncio.to_thread(
                    self.forecast_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    period=period_fmt,
                    type_=type_
                ),
                asyncio.to_thread(
                    self.forecast_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    period=period_fmt,
                    type_=type_,
                    limit=limit,
                    offset=offset
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])
                if item.get('first_ann_date'):
                    item['first_ann_date'] = self._format_date(item['first_ann_date'])

            return {
                'items': items,
                'total': total
            }

        except Exception as e:
            logger.error(f"查询业绩预告数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        type_: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            ts_code: 股票代码
            type_: 预告类型

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 获取统计
            statistics = await asyncio.to_thread(
                self.forecast_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                type_=type_
            )

            return statistics

        except Exception as e:
            logger.error(f"获取业绩预告统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Optional[Dict]:
        """
        获取最新业绩预告数据

        Args:
            ts_code: 股票代码

        Returns:
            最新业绩预告记录
        """
        try:
            latest_date = await asyncio.to_thread(
                self.forecast_repo.get_latest_ann_date,
                ts_code=ts_code
            )

            if not latest_date:
                return None

            items = await asyncio.to_thread(
                self.forecast_repo.get_by_date_range,
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
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])
                if item.get('first_ann_date'):
                    item['first_ann_date'] = self._format_date(item['first_ann_date'])

                return item

            return None

        except Exception as e:
            logger.error(f"获取最新业绩预告数据失败: {e}")
            raise

    async def sync_forecast(
        self,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        type_: Optional[str] = None
    ) -> Dict:
        """
        同步业绩预告数据

        Args:
            ann_date: 公告日期，格式：YYYYMMDD
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            period: 报告期，格式：YYYYMMDD
            type_: 预告类型

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步业绩预告数据: ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}, type={type_}")

            # 1. 获取Tushare数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_forecast,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                period=period,
                type_=type_
            )

            if df is None or df.empty:
                logger.warning("未获取到业绩预告数据")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            logger.info(f"获取到 {len(df)} 条业绩预告数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.forecast_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条业绩预告记录")

            return {
                "status": "success",
                "message": f"成功同步 {records} 条记录",
                "records": records
            }

        except Exception as e:
            logger.error(f"同步业绩预告数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": str(e),
                "error": str(e),
                "records": 0
            }

    @staticmethod
    def _generate_quarters(start_date: str) -> List[str]:
        """生成从start_date起到今天的所有季度末日期列表"""
        start_year = int(start_date[:4])
        quarter_ends = [331, 630, 930, 1231]
        today_int = int(datetime.now().strftime("%Y%m%d"))
        start_int = int(start_date)
        periods = []
        for y in range(start_year, datetime.now().year + 1):
            for qe in quarter_ends:
                period_str = f"{y}{qe:04d}"
                if start_int <= int(period_str) <= today_int:
                    periods.append(period_str)
        return periods

    async def sync_full_history(self, redis_client, start_date: str = None, update_state_fn=None, concurrency: int = 3) -> Dict:
        """按季度报告期全量同步业绩预告历史数据（支持中断续继）"""
        import asyncio as _asyncio

        effective_start = start_date or '20090101'
        quarters = self._generate_quarters(effective_start)
        total_quarters = len(quarters)
        logger.info(f"全量同步业绩预告，共 {total_quarters} 个季度，起始: {effective_start}")

        PROGRESS_KEY = "sync:forecast:full_history:progress"

        # 读取已完成的季度
        try:
            completed_raw = redis_client.smembers(PROGRESS_KEY)
            completed = {p.decode() if isinstance(p, bytes) else p for p in completed_raw}
        except Exception:
            completed = set()

        pending = [q for q in quarters if q not in completed]
        logger.info(f"待同步季度数: {len(pending)}，已完成: {len(completed)}")

        total_records = 0
        semaphore = _asyncio.Semaphore(max(1, concurrency))

        async def sync_one(period: str):
            nonlocal total_records
            async with semaphore:
                try:
                    provider = self._get_provider()
                    df = await _asyncio.to_thread(
                        provider.get_forecast,
                        period=period
                    )
                    if df is not None and not df.empty:
                        df = self._validate_and_clean_data(df)
                        count = await _asyncio.to_thread(self.forecast_repo.bulk_upsert, df)
                        total_records += count
                        logger.info(f"[forecast] period={period} 同步 {count} 条")
                    else:
                        logger.info(f"[forecast] period={period} 无数据")
                    redis_client.sadd(PROGRESS_KEY, period)
                except Exception as e:
                    logger.error(f"[forecast] period={period} 同步失败: {e}")

        done = 0
        for period in pending:
            await sync_one(period)
            done += 1
            if update_state_fn and done % 10 == 0:
                pct = int((len(completed) + done) / total_quarters * 100)
                try:
                    update_state_fn(state='PROGRESS', meta={'progress': pct, 'current': done, 'total': len(pending)})
                except Exception:
                    pass

        # 完成后删除进度key
        try:
            redis_client.delete(PROGRESS_KEY)
        except Exception:
            pass

        logger.info(f"全量同步业绩预告完成，共同步 {total_records} 条记录")
        return {'status': 'success', 'records': total_records, 'quarters': total_quarters}

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    def _validate_and_clean_data(self, df):
        """验证和清洗数据"""
        # 确保必需字段存在
        required_fields = ['ts_code', 'ann_date', 'end_date']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 移除空的必需字段
        df = df.dropna(subset=['ts_code', 'ann_date', 'end_date'])

        # 确保日期格式正确（YYYYMMDD）
        df['ann_date'] = df['ann_date'].astype(str)
        df['end_date'] = df['end_date'].astype(str)

        # 处理可选的日期字段
        if 'first_ann_date' in df.columns:
            df['first_ann_date'] = df['first_ann_date'].astype(str).replace('nan', None)
            df['first_ann_date'] = df['first_ann_date'].replace('None', None)

        # 处理字符串字段
        for str_field in ['type', 'summary', 'change_reason']:
            if str_field in df.columns:
                df[str_field] = df[str_field].astype(str).replace('nan', None)
                df[str_field] = df[str_field].replace('None', None)

        logger.info(f"数据清洗完成，剩余 {len(df)} 条记录")
        return df

    def _format_date(self, date_str: str) -> str:
        """格式化日期：YYYYMMDD -> YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
