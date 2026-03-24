"""
港股通每日成交统计服务

职责：
- 处理港股通成交数据的业务逻辑
- 从 Tushare 获取数据并保存到数据库
- 提供数据查询和统计功能
"""

import asyncio
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from app.repositories import GgtDailyRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class GgtDailyService:
    """港股通每日成交统计服务"""

    def __init__(self):
        self.ggt_daily_repo = GgtDailyRepository()
        self.provider_factory = DataProviderFactory()

    async def sync_data(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步港股通成交数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（可选）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            同步结果

        Examples:
            >>> service = GgtDailyService()
            >>> result = await service.sync_data(trade_date='20240315')
            >>> result = await service.sync_data(start_date='20240301', end_date='20240315')
        """
        try:
            logger.info(f"开始同步港股通成交数据: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 1. 获取 Tushare Provider
            provider = self._get_provider()

            # 2. 调用 Provider 方法获取数据
            df = await asyncio.to_thread(
                provider.get_ggt_daily,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到港股通成交数据")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(self.ggt_daily_repo.bulk_upsert, df)

            logger.info(f"成功同步 {records} 条港股通成交数据")

            return {
                "status": "success",
                "message": f"成功同步 {records} 条数据",
                "records": records,
                "date_range": {
                    "start": df['trade_date'].min() if not df.empty else None,
                    "end": df['trade_date'].max() if not df.empty else None
                }
            }

        except Exception as e:
            logger.error(f"同步港股通成交数据失败: {e}")
            raise

    async def get_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> Dict:
        """
        获取港股通成交数据

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）
            limit: 返回记录数限制（默认30）

        Returns:
            数据和统计信息

        Examples:
            >>> service = GgtDailyService()
            >>> result = await service.get_data(start_date='2024-03-01', limit=50)
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 获取数据
            items = await asyncio.to_thread(
                self.ggt_daily_repo.get_by_date_range,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                limit=limit
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（便于前端显示）
            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.ggt_daily_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return {
                "items": items,
                "total": len(items),
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取港股通成交数据失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新港股通成交数据

        Returns:
            最新数据和统计信息

        Examples:
            >>> service = GgtDailyService()
            >>> result = await service.get_latest_data()
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(self.ggt_daily_repo.get_latest_trade_date)

            if not latest_date:
                return {
                    "items": [],
                    "total": 0,
                    "latest_date": None
                }

            # 获取最近30天的数据
            end_date = latest_date
            start_date_dt = datetime.strptime(latest_date, '%Y%m%d') - timedelta(days=30)
            start_date = start_date_dt.strftime('%Y%m%d')

            # 获取数据
            items = await asyncio.to_thread(
                self.ggt_daily_repo.get_by_date_range,
                start_date=start_date,
                end_date=end_date,
                limit=30
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.ggt_daily_repo.get_statistics,
                start_date=start_date,
                end_date=end_date
            )

            # 格式化最新日期
            latest_date_formatted = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}"

            return {
                "items": items,
                "total": len(items),
                "latest_date": latest_date_formatted,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取最新港股通成交数据失败: {e}")
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
        required_fields = ['trade_date', 'buy_amount', 'buy_volume', 'sell_amount', 'sell_volume']
        for field in required_fields:
            if field not in df.columns:
                logger.warning(f"缺少字段: {field}")
                df[field] = None

        # 数据类型转换
        if 'trade_date' in df.columns:
            df['trade_date'] = df['trade_date'].astype(str)

        # 数值字段转换为浮点数
        numeric_fields = ['buy_amount', 'buy_volume', 'sell_amount', 'sell_volume']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')

        # 删除重复记录（按交易日期）
        df = df.drop_duplicates(subset=['trade_date'], keep='last')

        # 按日期排序
        df = df.sort_values('trade_date')

        logger.info(f"数据验证完成，共 {len(df)} 条记录")
        return df
