"""
港股通每月成交统计服务

职责:
- 处理港股通每月成交数据的业务逻辑
- 从 Tushare 获取数据并保存到数据库
- 提供数据查询和统计功能
"""

import asyncio
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from app.repositories import GgtMonthlyRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class GgtMonthlyService:
    """港股通每月成交统计服务"""

    def __init__(self):
        self.ggt_monthly_repo = GgtMonthlyRepository()
        self.provider_factory = DataProviderFactory()
        self.sync_history_repo = SyncHistoryRepository()

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始月份（YYYYMM）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'ggt_monthly')
        default_days = (cfg.get('incremental_default_days') or 365) if cfg else 365
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'ggt_monthly', 'incremental'
        )
        # last_end 可能是 YYYYMMDD 格式，截取月份部分
        if last_end:
            last_end_month = last_end[:6]
            if last_end_month < candidate:
                return last_end_month
        return candidate

    async def sync_incremental(self, start_date=None, end_date=None, sync_strategy=None, max_requests_per_minute=None) -> Dict:
        """增量同步（用 start_month/end_month 指定范围，记录 sync_history）

        ggt_monthly 接口只接受 month/start_month/end_month（YYYYMM 格式），
        增量同步用建议起始月份到当前月份的范围请求数据。
        """
        if start_date is not None:
            start_month = start_date[:6]
        else:
            start_month = await self.get_suggested_start_date()
        end_month = datetime.now().strftime('%Y%m') if end_date is None else end_date[:6]

        logger.info(f"[ggt_monthly] 增量同步 start_month={start_month} end_month={end_month}")

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create, 'ggt_monthly', 'incremental', 'by_month', start_month + '01',
        )
        try:
            result = await self.sync_data(start_month=start_month, end_month=end_month)
            data_end = end_month + '01'  # 转为 YYYYMMDD 格式存储
            await asyncio.to_thread(
                self.sync_history_repo.complete, history_id, 'success', result.get('records', 0), data_end, None,
            )
            return result
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete, history_id, 'failure', 0, None, str(e),
            )
            raise

    async def sync_data(
        self,
        month: Optional[str] = None,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None
    ) -> Dict:
        """
        同步港股通每月成交数据

        Args:
            month: 月度,格式:YYYYMM(可选)
            start_month: 开始月度,格式:YYYYMM(可选)
            end_month: 结束月度,格式:YYYYMM(可选)

        Returns:
            同步结果

        Examples:
            >>> service = GgtMonthlyService()
            >>> result = await service.sync_data(month='202403')
            >>> result = await service.sync_data(start_month='202401', end_month='202412')
        """
        try:
            logger.info(f"开始同步港股通每月成交数据: month={month}, start_month={start_month}, end_month={end_month}")

            # 1. 获取 Tushare Provider
            provider = self._get_provider()

            # 2. 调用 Provider 方法获取数据
            df = await asyncio.to_thread(
                provider.get_ggt_monthly,
                month=month,
                start_month=start_month,
                end_month=end_month
            )

            if df is None or df.empty:
                logger.warning("未获取到港股通每月成交数据")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(self.ggt_monthly_repo.bulk_upsert, df)

            logger.info(f"成功同步 {records} 条港股通每月成交数据")

            return {
                "status": "success",
                "message": f"成功同步 {records} 条数据",
                "records": records,
                "month_range": {
                    "start": df['month'].min() if not df.empty else None,
                    "end": df['month'].max() if not df.empty else None
                }
            }

        except Exception as e:
            logger.error(f"同步港股通每月成交数据失败: {e}")
            raise

    async def get_data(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取港股通每月成交数据

        Args:
            start_month: 开始月度,格式:YYYY-MM(可选)
            end_month: 结束月度,格式:YYYY-MM(可选)
            limit: 每页记录数(默认30)
            offset: 分页偏移量

        Returns:
            数据和统计信息
        """
        try:
            # 月度格式转换:YYYY-MM -> YYYYMM
            start_month_fmt = start_month.replace('-', '') if start_month else None
            end_month_fmt = end_month.replace('-', '') if end_month else None

            # 并发获取数据、总数、统计信息
            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.ggt_monthly_repo.get_by_month_range,
                    start_month=start_month_fmt,
                    end_month=end_month_fmt,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.ggt_monthly_repo.get_total_count,
                    start_month=start_month_fmt,
                    end_month=end_month_fmt
                ),
                asyncio.to_thread(
                    self.ggt_monthly_repo.get_statistics,
                    start_month=start_month_fmt,
                    end_month=end_month_fmt
                )
            )

            # 月度格式转换:YYYYMM -> YYYY-MM(便于前端显示)
            for item in items:
                if item.get('month'):
                    month_str = item['month']
                    item['month'] = f"{month_str[:4]}-{month_str[4:6]}"

            return {
                "items": items,
                "total": total,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取港股通每月成交数据失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新港股通每月成交数据

        Returns:
            最新数据和统计信息

        Examples:
            >>> service = GgtMonthlyService()
            >>> result = await service.get_latest_data()
        """
        try:
            # 获取最新月度
            latest_month = await asyncio.to_thread(self.ggt_monthly_repo.get_latest_month)

            if not latest_month:
                return {
                    "items": [],
                    "total": 0,
                    "latest_month": None
                }

            # 获取最近12个月的数据
            end_month = latest_month
            latest_date = datetime.strptime(latest_month, '%Y%m')
            start_date_dt = latest_date - timedelta(days=365)
            start_month = start_date_dt.strftime('%Y%m')

            # 获取数据
            items = await asyncio.to_thread(
                self.ggt_monthly_repo.get_by_month_range,
                start_month=start_month,
                end_month=end_month,
                limit=12
            )

            # 月度格式转换:YYYYMM -> YYYY-MM
            for item in items:
                if item.get('month'):
                    month_str = item['month']
                    item['month'] = f"{month_str[:4]}-{month_str[4:6]}"

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.ggt_monthly_repo.get_statistics,
                start_month=start_month,
                end_month=end_month
            )

            # 格式化最新月度
            latest_month_formatted = f"{latest_month[:4]}-{latest_month[4:6]}"

            return {
                "items": items,
                "total": len(items),
                "latest_month": latest_month_formatted,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取最新港股通每月成交数据失败: {e}")
            raise

    async def sync_full_history(
        self,
        update_state_fn=None,
        start_date: Optional[str] = None,
        **kwargs,
    ) -> Dict:
        """
        全量同步港股通每月成交历史数据

        ggt_monthly 接口不传日期参数时只返回部分历史数据（约至 202012），
        因此全量同步必须传 start_month/end_month 确保完整覆盖。
        start_month 从 sync_configs 的同步配置起始日期截取月份部分。

        Args:
            update_state_fn: Celery update_state 回调（可选）
            start_date: 起始日期 YYYYMMDD（可选，从 Celery 任务传入）

        Returns:
            同步结果字典，含 status、message、records
        """
        try:
            # 从 sync_configs 读取起始日期，截取月份
            if start_date:
                start_month = start_date[:6]
            else:
                cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'ggt_monthly')
                # sync_configs 没有专门的起始日期字段，用配置的回看天数兜底
                # 默认从 201411 开始（Tushare 数据最早月份）
                start_month = '201411'
            end_month = datetime.now().strftime('%Y%m')

            logger.info(f"开始全量同步港股通每月成交数据: start_month={start_month} end_month={end_month}")

            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={'progress': 10, 'message': '正在获取数据...'})

            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_ggt_monthly,
                start_month=start_month,
                end_month=end_month,
            )

            if df is None or df.empty:
                logger.warning("全量同步：未获取到港股通每月成交数据")
                return {"status": "success", "message": "未获取到数据", "records": 0}

            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={'progress': 60, 'message': f'获取到 {len(df)} 条，写入数据库...'})

            df = self._validate_and_clean_data(df)
            records = await asyncio.to_thread(self.ggt_monthly_repo.bulk_upsert, df)

            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={'progress': 100, 'message': f'完成，共 {records} 条'})

            logger.info(f"全量同步港股通每月成交数据完成：{records} 条")
            return {
                "status": "success",
                "message": f"全量同步完成，共 {records} 条数据",
                "records": records
            }

        except Exception as e:
            logger.error(f"全量同步港股通每月成交数据失败: {e}")
            raise

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
            df: 原始数据 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        if df is None or df.empty:
            return df

        # 确保必需字段存在
        required_fields = ['month', 'day_buy_amt', 'day_buy_vol', 'day_sell_amt', 'day_sell_vol',
                          'total_buy_amt', 'total_buy_vol', 'total_sell_amt', 'total_sell_vol']
        for field in required_fields:
            if field not in df.columns:
                logger.warning(f"缺少字段: {field}")
                df[field] = None

        # 数据类型转换
        if 'month' in df.columns:
            df['month'] = df['month'].astype(str)

        # 数值字段转换为浮点数
        numeric_fields = ['day_buy_amt', 'day_buy_vol', 'day_sell_amt', 'day_sell_vol',
                         'total_buy_amt', 'total_buy_vol', 'total_sell_amt', 'total_sell_vol']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')

        # 删除重复记录(按月度)
        df = df.drop_duplicates(subset=['month'], keep='last')

        # 按月度排序
        df = df.sort_values('month')

        logger.info(f"数据验证完成,共 {len(df)} 条记录")
        return df
