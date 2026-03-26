"""
最强板块统计 Service
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from app.repositories import LimitCptRepository
from core.src.providers import DataProviderFactory


class LimitCptService:
    """最强板块统计业务逻辑层"""

    def __init__(self):
        self.limit_cpt_repo = LimitCptRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ LimitCptService initialized")

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认交易日期：今天有数据则返回今天，否则返回最近有数据的交易日（YYYY-MM-DD格式）
        """
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(
            self.limit_cpt_repo.exists_by_date, today
        )
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"

        latest = await asyncio.to_thread(
            self.limit_cpt_repo.get_latest_trade_date
        )
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_limit_cpt_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = 'asc'
    ) -> Dict:
        """
        获取最强板块统计数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 板块代码
            limit: 每页记录数
            offset: 偏移量（分页）
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            数据字典，包含 items、total、statistics
        """
        # 并发获取数据、总数和统计
        items_coro = asyncio.to_thread(
            self.limit_cpt_repo.get_by_date_range,
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        total_coro = asyncio.to_thread(
            self.limit_cpt_repo.get_count_by_date_range,
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code
        )
        statistics_coro = asyncio.to_thread(
            self.limit_cpt_repo.get_statistics,
            start_date=start_date,
            end_date=end_date
        )

        items, total, statistics = await asyncio.gather(
            items_coro, total_coro, statistics_coro
        )

        # 日期格式转换（YYYYMMDD -> YYYY-MM-DD）
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        return {
            "items": items,
            "total": total,
            "statistics": statistics
        }

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取最强板块统计信息

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD

        Returns:
            统计信息字典
        """
        # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        # 获取统计信息
        statistics = await asyncio.to_thread(
            self.limit_cpt_repo.get_statistics,
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        return statistics

    async def get_latest_data(self) -> Dict:
        """
        获取最新交易日的最强板块统计数据

        Returns:
            最新数据字典
        """
        # 获取最新交易日期
        latest_date = await asyncio.to_thread(
            self.limit_cpt_repo.get_latest_trade_date
        )

        if not latest_date:
            return {"items": [], "total": 0}

        # 获取该日期的数据
        items = await asyncio.to_thread(
            self.limit_cpt_repo.get_by_trade_date,
            trade_date=latest_date
        )

        # 日期格式转换（YYYYMMDD -> YYYY-MM-DD）
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        return {
            "items": items,
            "total": len(items),
            "latest_date": self._format_date(latest_date)
        }

    async def get_top_by_up_nums(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取涨停家数排名TOP数据

        Args:
            trade_date: 交易日期，格式：YYYY-MM-DD
            limit: 返回记录数

        Returns:
            排名TOP数据列表
        """
        # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
        trade_date_fmt = trade_date.replace('-', '') if trade_date else None

        # 获取TOP数据
        items = await asyncio.to_thread(
            self.limit_cpt_repo.get_top_by_up_nums,
            trade_date=trade_date_fmt,
            limit=limit
        )

        # 日期格式转换（YYYYMMDD -> YYYY-MM-DD）
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        return items

    async def sync_limit_cpt(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步最强板块统计数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 板块代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步最强板块统计数据: trade_date={trade_date}, ts_code={ts_code}, start_date={start_date}, end_date={end_date}")

            # 获取 Tushare Provider
            provider = self._get_provider()

            # 从 Tushare 获取数据
            df = await asyncio.to_thread(
                provider.get_limit_cpt_list,
                trade_date=trade_date,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据（可能是非交易日或数据尚未更新）"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条记录")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.limit_cpt_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条最强板块统计数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步最强板块统计数据失败: {e}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _get_provider(self):
        """获取 Tushare Provider"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        # 确保必要字段存在
        required_columns = ['trade_date', 'ts_code', 'name', 'rank']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必要字段: {col}")

        # 移除空记录
        df = df.dropna(subset=['trade_date', 'ts_code'])

        # 确保数值类型正确
        numeric_columns = ['days', 'cons_nums', 'up_nums', 'pct_chg', 'rank']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"数据验证和清洗完成，剩余 {len(df)} 条记录")
        return df

    def _format_date(self, date_str: str) -> str:
        """
        格式化日期（YYYYMMDD -> YYYY-MM-DD）

        Args:
            date_str: 日期字符串（YYYYMMDD）

        Returns:
            格式化后的日期（YYYY-MM-DD）
        """
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
