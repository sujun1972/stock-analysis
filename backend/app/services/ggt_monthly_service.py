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
from core.src.providers import DataProviderFactory
from app.core.config import settings


class GgtMonthlyService:
    """港股通每月成交统计服务"""

    def __init__(self):
        self.ggt_monthly_repo = GgtMonthlyRepository()
        self.provider_factory = DataProviderFactory()

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

    def _get_provider(self):
        """获取 Tushare Provider"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

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
