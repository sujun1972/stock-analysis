"""
ST股票列表服务

处理ST股票数据的同步和查询业务逻辑
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from app.repositories.stock_st_repository import StockStRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class StockStService:
    """ST股票列表服务"""

    def __init__(self):
        self.stock_st_repo = StockStRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取 Tushare Provider"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_stock_st(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步ST股票列表数据

        Args:
            ts_code: 股票代码（可选）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            同步结果字典

        Examples:
            >>> service = StockStService()
            >>> result = await service.sync_stock_st(trade_date='20240115')
        """
        try:
            logger.info(
                f"开始同步ST股票数据: ts_code={ts_code}, trade_date={trade_date}, "
                f"start_date={start_date}, end_date={end_date}"
            )

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 调用 Provider 获取数据
            df = await asyncio.to_thread(
                provider.get_stock_st,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到ST股票数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条ST股票数据")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.stock_st_repo.bulk_upsert,
                df
            )

            logger.info(f"ST股票数据同步成功: {records} 条")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条ST股票数据"
            }

        except Exception as e:
            error_msg = f"同步ST股票数据失败: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": error_msg
            }

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗ST股票数据

        Args:
            df: 原始数据DataFrame

        Returns:
            清洗后的DataFrame
        """
        try:
            # 确保必需字段存在
            required_fields = ['ts_code', 'trade_date', 'name', 'type', 'type_name']
            for field in required_fields:
                if field not in df.columns:
                    logger.warning(f"缺少字段: {field}")
                    df[field] = None

            # 过滤掉缺少关键字段的行
            df = df[df['ts_code'].notna() & df['trade_date'].notna()]

            # 确保日期格式正确（YYYYMMDD）
            df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '')

            # 去重（按 ts_code + trade_date）
            df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')

            logger.info(f"数据清洗完成，保留 {len(df)} 条有效数据")

            return df

        except Exception as e:
            logger.error(f"数据清洗失败: {e}")
            raise

    async def get_stock_st_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        st_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 30
    ) -> Dict:
        """
        获取ST股票数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            ts_code: 股票代码
            st_type: ST类型
            page: 页码
            page_size: 每页大小

        Returns:
            包含数据和统计信息的字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 计算分页
            offset = (page - 1) * page_size

            # 获取数据
            items = await asyncio.to_thread(
                self.stock_st_repo.get_by_date_range,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                st_type=st_type,
                limit=page_size + offset
            )

            # 分页处理
            paginated_items = items[offset:offset + page_size]

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.stock_st_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in paginated_items:
                if item.get('trade_date'):
                    item['trade_date'] = self._format_date(item['trade_date'])

            return {
                "items": paginated_items,
                "total": len(items),
                "page": page,
                "page_size": page_size,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取ST股票数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取ST股票统计信息

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            statistics = await asyncio.to_thread(
                self.stock_st_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            if statistics.get('latest_date'):
                statistics['latest_date'] = self._format_date(statistics['latest_date'])
            if statistics.get('earliest_date'):
                statistics['earliest_date'] = self._format_date(statistics['earliest_date'])

            return statistics

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_type_distribution(
        self,
        trade_date: Optional[str] = None
    ) -> List[Dict]:
        """
        获取ST类型分布

        Args:
            trade_date: 交易日期 YYYY-MM-DD

        Returns:
            类型分布列表
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None

            distribution = await asyncio.to_thread(
                self.stock_st_repo.get_type_distribution,
                trade_date=trade_date_fmt
            )

            return distribution

        except Exception as e:
            logger.error(f"获取ST类型分布失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新的ST股票数据

        Returns:
            最新数据字典
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.stock_st_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "items": [],
                    "trade_date": None,
                    "total": 0
                }

            # 获取该日期的所有ST股票
            items = await asyncio.to_thread(
                self.stock_st_repo.get_by_trade_date,
                trade_date=latest_date
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('trade_date'):
                    item['trade_date'] = self._format_date(item['trade_date'])

            return {
                "items": items,
                "trade_date": self._format_date(latest_date),
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    def _format_date(self, date_str: str) -> str:
        """
        格式化日期：YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: 日期字符串 YYYYMMDD

        Returns:
            格式化后的日期字符串 YYYY-MM-DD
        """
        if not date_str or len(date_str) != 8:
            return date_str

        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
